import sqlite3
from conftest import login


def test_two_saved_databases_are_bound_to_separate_chats(client, app):
    login(client, 'admin@example.test', 'AdminPass!2026')
    root = app.state.database_connections.sqlite_root
    root.mkdir()
    ids = []
    for name, amount in [('north', 10), ('south', 20)]:
        with sqlite3.connect(root / f'{name}.sqlite3') as db:
            db.execute('CREATE TABLE revenue (amount INTEGER)')
            db.execute('INSERT INTO revenue VALUES (?)', (amount,))
        response = client.post('/api/admin/data/connections', json={
            'name': name, 'kind': 'sqlite', 'database': f'{name}.sqlite3',
            'tables': ['revenue'], 'read_only_confirmed': True, 'egress_confirmed': True})
        assert response.status_code == 201, response.text
        ids.append(response.json()['id'])
    assert len(set(ids)) == 2
    for connection_id, amount in zip(ids, [10, 20]):
        chat = client.post('/api/conversations', json={'agent_mode': 'data', 'database_connection_id': connection_id})
        assert chat.status_code == 201, chat.text
        assert chat.json()['database_connection_id'] == connection_id
        reply = client.post(f'/api/conversations/{chat.json()["id"]}/messages', json={
            'agent_mode': 'data', 'content': 'SELECT amount FROM revenue'})
        assert reply.status_code == 201, reply.text
        assert app.state.fake_ai.report_calls[-1]['query_result']['rows'] == [{'amount': amount}]
        assert reply.json()['assistant']['sources'][0]['connection_id'] == connection_id
        assert client.delete(f'/api/admin/data/connections/{connection_id}?revision=1').status_code == 409


def test_unknown_database_does_not_fall_back_to_demo(client):
    login(client, 'admin@example.test', 'AdminPass!2026')
    response = client.post('/api/conversations', json={'agent_mode': 'data', 'database_connection_id': 'missing'})
    assert response.status_code == 422


def test_profile_lifecycle_revisions_and_endpoint_binding(client, app):
    login(client, 'admin@example.test', 'AdminPass!2026')
    manager = app.state.database_connections
    manager.sqlite_root.mkdir()
    for filename in ['first.sqlite3', 'second.sqlite3']:
        with sqlite3.connect(manager.sqlite_root / filename) as db:
            db.execute('CREATE TABLE revenue (amount INTEGER)')
    payload = {'name': 'Reporting', 'kind': 'sqlite', 'database': 'first.sqlite3',
               'tables': ['revenue'], 'read_only_confirmed': True, 'egress_confirmed': True}
    created = client.post('/api/admin/data/connections', json=payload)
    assert created.status_code == 201
    profile_id = created.json()['id']
    url = f'/api/admin/data/connections/{profile_id}'
    assert 'password' not in created.json()
    assert client.put(url, json=payload).status_code == 409
    payload.update(revision=1, name='Renamed')
    assert client.put(url, json=payload).status_code == 200
    assert client.delete(url + '?revision=1').status_code == 409
    from nexus.database_connection import DatabaseConnections
    reopened = DatabaseConnections(manager.path, manager.demo, sqlite_root=manager.sqlite_root)
    assert reopened.profiles()[0]['name'] == 'Renamed'
    chat = client.post('/api/conversations', json={
        'agent_mode': 'data', 'database_connection_id': profile_id}).json()
    payload.update(revision=2, database='second.sqlite3')
    assert client.put(url, json=payload).status_code == 409
    assert client.delete(url + '?revision=2').status_code == 409
    assert client.delete(f'/api/conversations/{chat["id"]}').is_success
    assert client.delete(url + '?revision=2').is_success
    assert reopened.profiles() == []
    assert client.post('/api/conversations', json={
        'agent_mode': 'data', 'database_connection_id': profile_id}).status_code == 422
