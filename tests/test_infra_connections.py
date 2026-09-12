from conftest import login
from types import SimpleNamespace

from nexus.infra_connection import InfraConnectionPayload, collect_remote_infra


def enable_infra(app):
    app.state.store.update_settings({
        'infra_agent_enabled': '1', 'infra_agent_admin_only': '1',
        'infra_live_enabled': '1',
    })


def profile(name, host, revision=0):
    return {
        'name': name, 'host': host, 'port': 22, 'username': 'nexus-observer',
        'identity_file': 'observer-key', 'revision': revision,
    }


def test_multiple_infra_servers_are_pinned_to_separate_chats(client, app):
    enable_infra(app)
    login(client, 'admin@example.test', 'AdminPass!2026')
    calls = []

    def remote(settings, mode):
        calls.append((settings.host, mode))
        return {'generated_at': '2026-09-12T08:00:00+00:00',
                'hostname': settings.host, 'scope': 'sanitized_read_only'}

    app.state.infra_connections.remote_collector = remote
    ids = []
    for name, host in [('Web EU', 'web-eu.internal'), ('Worker US', 'worker-us.internal')]:
        created = client.post('/api/admin/infra/connections', json=profile(name, host))
        assert created.status_code == 201, created.text
        ids.append(created.json()['id'])
    calls.clear()  # Saving deliberately validates each endpoint once.

    choices = client.get('/api/infra/connections').json()['connections']
    assert [item['id'] for item in choices] == ['local', *ids]
    for server_id, host, mode in zip(ids, ['web-eu.internal', 'worker-us.internal'], ['snapshot', 'live']):
        chat = client.post('/api/conversations', json={
            'agent_mode': 'infra', 'infra_connection_id': server_id})
        assert chat.status_code == 201, chat.text
        assert chat.json()['infra_connection_id'] == server_id
        reply = client.post(f'/api/conversations/{chat.json()["id"]}/messages', json={
            'agent_mode': 'infra', 'infra_source': mode, 'content': 'Server health?'})
        assert reply.status_code == 201, reply.text
        source = next(s for s in reply.json()['assistant']['sources'] if s.get('type') == 'infra')
        assert source['connection_id'] == server_id
        assert source['server'] == host
        assert client.delete(f'/api/admin/infra/connections/{server_id}?revision=1').status_code == 409
    assert calls == [('web-eu.internal', 'snapshot'), ('worker-us.internal', 'live')]


def test_infra_connection_lifecycle_and_no_fallback(client, app):
    enable_infra(app)
    login(client, 'admin@example.test', 'AdminPass!2026')
    app.state.infra_connections.remote_collector = lambda settings, mode: {
        'generated_at': '2026-09-12T08:00:00+00:00', 'hostname': settings.host}
    created = client.post('/api/admin/infra/connections', json=profile('Primary', 'one.internal'))
    assert created.status_code == 201
    server_id = created.json()['id']
    assert 'command' not in created.json()
    assert client.post('/api/conversations', json={
        'agent_mode': 'infra', 'infra_connection_id': 'missing'}).status_code == 422
    changed = profile('Primary renamed', 'one.internal', 1)
    assert client.put(f'/api/admin/infra/connections/{server_id}', json=changed).status_code == 200
    assert client.delete(f'/api/admin/infra/connections/{server_id}?revision=1').status_code == 409
    assert client.delete(f'/api/admin/infra/connections/{server_id}?revision=2').is_success


def test_regular_user_only_sees_local_infra_server(client, app):
    enable_infra(app)
    app.state.store.update_settings({'infra_agent_admin_only': '0'})
    login(client, 'admin@example.test', 'AdminPass!2026')
    app.state.infra_connections.remote_collector = lambda settings, mode: {
        'generated_at': '2026-09-12T08:00:00+00:00', 'hostname': settings.host}
    created = client.post('/api/admin/infra/connections', json=profile('Private', 'private.internal'))
    server_id = created.json()['id']
    client.post('/api/auth/logout')
    client.post('/api/auth/register', json={
        'name': 'Ordinary User', 'email': 'ordinary@example.test', 'password': 'UserPass!2026'})
    choices = client.get('/api/infra/connections').json()['connections']
    assert choices == [{'id': 'local', 'name': 'Local Nexus server', 'kind': 'local'}]
    assert client.post('/api/conversations', json={
        'agent_mode': 'infra', 'infra_connection_id': server_id}).status_code == 403


def test_infra_identity_path_and_host_are_rejected_before_collection(client, app):
    login(client, 'admin@example.test', 'AdminPass!2026')
    calls = []
    app.state.infra_connections.remote_collector = lambda settings, mode: calls.append(True)
    invalid_path = profile('Unsafe', 'safe.internal')
    invalid_path['identity_file'] = '../root-key'
    assert client.post('/api/admin/infra/connections/test', json=invalid_path).status_code == 422
    invalid_host = profile('Unsafe', '-oProxyCommand=bad')
    assert client.post('/api/admin/infra/connections/test', json=invalid_host).status_code == 422
    assert calls == []


def test_remote_collector_uses_fixed_strict_ssh_command(monkeypatch, tmp_path):
    key_root = tmp_path / 'keys'
    key_root.mkdir()
    (key_root / 'observer-key').write_text('private fixture', encoding='utf-8')
    known_hosts = tmp_path / 'known_hosts'
    known_hosts.write_text('host fixture', encoding='utf-8')
    captured = {}

    def run(command, **kwargs):
        captured.update(command=command, kwargs=kwargs)
        return SimpleNamespace(returncode=0, stdout='{"generated_at":"2026-09-12T08:00:00Z"}', stderr='')

    monkeypatch.setattr('nexus.infra_connection.subprocess.run', run)
    settings = InfraConnectionPayload(**profile('Edge', 'edge.internal'))
    result = collect_remote_infra(settings, 'snapshot', key_root=key_root, known_hosts=known_hosts)
    assert result['generated_at']
    assert captured['command'][-3:] == ['nexus-observer@edge.internal', '/usr/local/bin/nexus-infra-readonly', 'snapshot']
    assert 'StrictHostKeyChecking=yes' in captured['command']
    assert 'shell' not in captured['kwargs']
