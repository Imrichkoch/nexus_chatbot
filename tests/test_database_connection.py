from conftest import login, register
import sqlite3
import pytest

from nexus.database_connection import ConnectionSettings, ExternalDatabase, validated_query
from nexus.data_agent import QueryRejected


def test_database_settings_are_admin_only_and_default_to_demo(client):
    assert client.get('/api/admin/data/connection').status_code == 401
    register(client)
    assert client.get('/api/admin/data/connection').status_code == 403
    client.post('/api/auth/logout')
    login(client, 'admin@example.test', 'AdminPass!2026')
    response = client.get('/api/admin/data/connection')
    assert response.status_code == 200
    assert response.json()['kind'] == 'demo'
    assert 'password' not in response.json()


def test_database_settings_reject_unknown_drivers(client):
    login(client, 'admin@example.test', 'AdminPass!2026')
    response = client.put('/api/admin/data/connection', json={'kind': 'arbitrary+plugin'})
    assert response.status_code == 422


def test_external_database_requires_explicit_safety_acknowledgements(client):
    login(client, 'admin@example.test', 'AdminPass!2026')
    response = client.put('/api/admin/data/connection', json={
        'kind': 'postgresql', 'host': 'db.example.test', 'port': 5432,
        'database': 'reporting', 'username': 'reader', 'password': 'Secret123!',
        'schema_name': 'public', 'tables': ['customers'],
    })
    assert response.status_code == 422
    assert 'Secret123!' not in response.text


@pytest.fixture
def sqlite_source(app):
    root = app.state.database_connections.sqlite_root
    root.mkdir()
    with sqlite3.connect(root / 'reporting.sqlite3') as db:
        db.executescript('CREATE TABLE revenue (country TEXT, amount INTEGER);'
                         "INSERT INTO revenue VALUES ('SK', 120), ('DE', 240);"
                         'CREATE TABLE private_notes (note TEXT);')
    return dict(kind='sqlite', database='reporting.sqlite3', schema_name='main',
                tables=['revenue'], read_only_confirmed=True, egress_confirmed=True)


def test_external_sqlite_test_activate_report_and_return_to_demo(client, app, sqlite_source):
    login(client, 'admin@example.test', 'AdminPass!2026')
    tested = client.post('/api/admin/data/connection/test', json=sqlite_source)
    assert tested.status_code == 200, tested.text
    assert 'revenue' in tested.json()['tables']
    assert client.get('/api/admin/data/connection').json()['kind'] == 'demo'
    saved = client.put('/api/admin/data/connection', json=sqlite_source)
    assert saved.status_code == 200, saved.text
    assert client.get('/api/admin/data/schema').json()['fictional'] is False
    chat = client.post('/api/conversations', json={'title': 'External', 'agent_mode': 'data'}).json()
    report = client.post(f'/api/conversations/{chat["id"]}/messages', json={
        'content': 'SELECT country, amount FROM revenue ORDER BY amount DESC', 'agent_mode': 'data'})
    assert report.status_code == 201, report.text
    captured = app.state.fake_ai.report_calls[-1]['query_result']
    assert captured['fictional'] is False
    assert captured['rows'][0] == {'country': 'DE', 'amount': 240}
    assert 'LIMIT 101' in app.state.fake_ai.report_calls[-1]['sql']
    source = app.state.database_connections.snapshot()
    with pytest.raises(QueryRejected):
        source.execute('DROP TABLE revenue')
    with pytest.raises(QueryRejected):
        source.execute('SELECT * FROM private_notes')
    assert source.execute('SELECT COUNT(*) AS n FROM revenue')['rows'] == [{'n': 2}]
    restored = client.put('/api/admin/data/connection', json={'kind': 'demo', 'revision': saved.json()['revision']})
    assert restored.status_code == 409  # A live chat must not silently change databases.
    client.delete(f'/api/conversations/{chat["id"]}')
    restored = client.put('/api/admin/data/connection', json={'kind': 'demo', 'revision': saved.json()['revision']})
    assert restored.status_code == 200
    assert client.get('/api/admin/data/schema').json()['fictional'] is True


def test_external_source_is_admin_only_even_if_demo_was_public(client, app, sqlite_source):
    login(client, 'admin@example.test', 'AdminPass!2026')
    assert client.put('/api/admin/data/connection', json=sqlite_source).status_code == 200
    client.post('/api/auth/logout')
    register(client)
    assert client.get('/api/capabilities').json()['data_agent_available'] is True  # Demo remains available.
    assert [c['id'] for c in client.get('/api/data/connections').json()['connections']] == ['demo']
    response = client.post('/api/conversations', json={'agent_mode': 'data', 'database_connection_id': 'legacy'})
    assert response.status_code == 403
    assert not app.state.fake_ai.report_calls


def test_password_is_not_returned_and_cannot_follow_a_changed_host(client, app, monkeypatch):
    login(client, 'admin@example.test', 'AdminPass!2026')
    monkeypatch.setattr(ExternalDatabase, 'inspect_schema', lambda self: {'tables': ['revenue'], 'schema': 'revenue(amount INTEGER)'})
    payload = dict(kind='postgresql', host='db.example.test', database='reporting', username='reader',
                   password='Secret123!', tables=['revenue'], read_only_confirmed=True, egress_confirmed=True)
    response = client.put('/api/admin/data/connection', json=payload)
    assert response.status_code == 200
    assert 'Secret123!' not in response.text and 'password' not in response.json()
    assert response.json()['password_configured'] is True
    payload.update(password='', revision=response.json()['revision'])
    assert client.put('/api/admin/data/connection', json={**payload, 'host': 'other.example.test'}).status_code == 422
    assert client.put('/api/admin/data/connection', json={**payload, 'revision': 0}).status_code == 409
    assert client.put('/api/admin/data/connection', json=payload).status_code == 200
    assert 'Secret123!' not in client.get('/api/admin/data/schema').text
    assert 'Secret123!' not in client.get('/api/admin/audit').text


@pytest.mark.parametrize('sql', [
    'DROP TABLE revenue', 'SELECT * FROM revenue; DELETE FROM revenue',
    'SELECT * INTO backup FROM revenue', 'SELECT * FROM revenue FOR UPDATE',
    'SELECT pg_sleep(10)', 'SELECT load_file(\'/etc/passwd\')',
    'SELECT * FROM other.revenue', 'SELECT * FROM private_notes',
    'WITH private_notes AS (SELECT * FROM private_notes) SELECT * FROM private_notes',
    'SELECT * FROM revenue UNION SELECT * FROM private_notes',
    'SELECT * FROM revenue /* comment */', 'SELECT set_config(\'x\', \'y\', false)',
    'SELECT * FROM dblink(\'x\', \'SELECT 1\')', 'SELECT public.my_func(amount) FROM revenue',
    'WITH x AS (DELETE FROM revenue RETURNING *) SELECT * FROM x',
])
def test_reporting_sql_rejects_mutations_functions_and_unapproved_tables(sql):
    with pytest.raises(QueryRejected):
        validated_query(sql, ConnectionSettings(kind='postgresql', tables=['revenue']))


@pytest.mark.parametrize('kind', ['postgresql', 'mysql', 'mariadb', 'mssql', 'oracle', 'sqlite'])
def test_reporting_query_uses_selected_sql_dialect(kind):
    config = ConnectionSettings(kind=kind, database='reporting', username='reader', tables=['revenue'])
    query = validated_query('SELECT country, SUM(amount) AS total FROM revenue GROUP BY country', config)
    assert '101' in query and 'revenue' in query
    assert 'TOP 101' in query if kind == 'mssql' else True


def test_cte_is_resolved_without_allowing_a_hidden_base_table():
    config = ConnectionSettings(kind='postgresql', tables=['revenue'])
    assert '101' in validated_query('WITH totals AS (SELECT SUM(amount) AS n FROM revenue) SELECT * FROM totals', config)


def test_sqlite_path_escape_does_not_open_a_database(client):
    login(client, 'admin@example.test', 'AdminPass!2026')
    response = client.post('/api/admin/data/connection/test', json={
        'kind': 'sqlite', 'database': '../nexus.sqlite3', 'read_only_confirmed': True, 'egress_confirmed': True})
    assert response.status_code == 422


def test_failed_source_activation_preserves_last_working_source(client, sqlite_source):
    login(client, 'admin@example.test', 'AdminPass!2026')
    saved = client.put('/api/admin/data/connection', json=sqlite_source).json()
    response = client.put('/api/admin/data/connection', json={
        **sqlite_source, 'database': 'missing.sqlite3', 'revision': saved['revision']})
    assert response.status_code == 422
    assert client.get('/api/admin/data/connection').json()['database'] == 'reporting.sqlite3'


def test_external_source_result_text_is_bounded(app, sqlite_source):
    source = ExternalDatabase(ConnectionSettings(**sqlite_source), sqlite_root=app.state.database_connections.sqlite_root)
    with sqlite3.connect(source.sqlite_root / sqlite_source['database']) as db:
        db.executemany('INSERT INTO revenue VALUES (?, ?)', [('x' * 8000, n) for n in range(30)])
    result = source.execute('SELECT country, amount FROM revenue')
    assert result['truncated'] and result['cells_truncated']
    assert sum(len(str(value)) for row in result['rows'] for value in row.values()) < 65000


@pytest.mark.parametrize('kind', ['postgresql', 'mysql', 'mariadb', 'mssql', 'oracle'])
def test_driver_loads_and_structured_url_preserves_password(kind, tmp_path):
    secret = 'pw@/;{}:#?'
    source = ExternalDatabase(ConnectionSettings(kind=kind, host='db.example.test', database='reporting',
        username='reader', password=secret, read_only_confirmed=True, egress_confirmed=True), sqlite_root=tmp_path)
    engine = source.engine()
    try:
        assert engine.url.password == secret
        assert secret not in str(engine.url)
    finally:
        engine.dispose()
