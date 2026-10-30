from conftest import login


def test_rag_only_excludes_other_agents(client, app, monkeypatch):
    monkeypatch.setenv('NEXUS_RAG_ONLY', '1')
    assert login(client, 'admin@example.test', 'AdminPass!2026').status_code == 200
    capabilities = client.get('/api/capabilities').json()
    assert capabilities['rag_only'] is True
    assert capabilities['rag_enabled'] is True
    assert capabilities['data_agent_available'] is False
    assert capabilities['infra_agent_available'] is False
    for path in ('/api/admin/data/schema', '/api/admin/infra/status',
                 '/api/data/connections', '/api/infra/connections'):
        assert client.get(path).status_code == 404
    for mode in ('data', 'infra'):
        assert client.post('/api/conversations', json={'agent_mode': mode}).status_code == 404
        assert client.get('/api/conversations', params={'agent_mode': mode}).status_code == 404
    assert client.post('/api/conversations', json={'agent_mode': 'general'}).status_code == 201
    assert client.get('/api/admin/rag/documents').status_code == 200


def test_rag_only_does_not_initialize_infra_or_reporting(tmp_path, monkeypatch):
    from nexus.app import create_app
    monkeypatch.setenv('NEXUS_RAG_ONLY', '1')
    app = create_app(database_path=str(tmp_path / 'rag.db'), secure_cookies=False)
    assert not hasattr(app.state, 'infra_connections')
    assert not hasattr(app.state, 'database_connections')
    assert not hasattr(app.state, 'synthetic_database')
