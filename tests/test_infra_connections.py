from conftest import login
from types import SimpleNamespace
import sys

from nexus.infra_connection import (
    InfraConnectionPayload,
    collect_remote_infra,
    collect_windows_winrm,
)


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


def windows_profile(name='Windows App', host='win-app.internal', revision=0):
    return {
        'kind': 'windows_winrm', 'name': name, 'host': host, 'port': 5986,
        'username': 'CORP\\nexus-observer', 'identity_file': '',
        'password': 'TemporarySecret!2026', 'auth': 'ntlm',
        'revision': revision,
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


def test_windows_ssh_uses_only_fixed_powershell_collector(monkeypatch, tmp_path):
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
    settings = InfraConnectionPayload(**{
        **profile('Windows SSH', 'win.internal'), 'kind': 'windows_ssh'})
    collect_remote_infra(settings, 'live', key_root=key_root, known_hosts=known_hosts)

    assert captured['command'][-3] == 'nexus-observer@win.internal'
    assert captured['command'][-2:] == [
        'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy AllSigned '
        '-File C:\\ProgramData\\NexusChat\\nexus-infra-readonly.ps1 -Mode',
        'live',
    ]
    assert 'shell' not in captured['kwargs']


def test_winrm_password_is_saved_outside_profile_json(client, app):
    enable_infra(app)
    login(client, 'admin@example.test', 'AdminPass!2026')
    seen = []
    app.state.infra_connections.remote_collector = lambda settings, mode: (
        seen.append((settings.kind, settings.password, mode)) or
        {'generated_at': '2026-09-12T08:00:00+00:00', 'hostname': settings.host}
    )

    created = client.post('/api/admin/infra/connections', json=windows_profile())

    assert created.status_code == 201, created.text
    body = created.json()
    assert body['kind'] == 'windows_winrm'
    assert body['password_configured'] is True
    assert 'password' not in body
    assert 'TemporarySecret!2026' not in app.state.infra_connections.path.read_text(encoding='utf-8')
    secret = app.state.infra_connections.secret_root / body['id']
    assert secret.read_text(encoding='utf-8') == 'TemporarySecret!2026'
    assert seen == [('windows_winrm', 'TemporarySecret!2026', 'live')]


def test_winrm_rejects_missing_password(client, app):
    login(client, 'admin@example.test', 'AdminPass!2026')
    app.state.infra_connections.remote_collector = lambda settings, mode: {
        'generated_at': '2026-09-12T08:00:00+00:00'}
    missing = windows_profile()
    missing['password'] = ''
    assert client.post('/api/admin/infra/connections/test', json=missing).status_code == 422


def test_winrm_validates_tls_and_runs_only_fixed_collector(monkeypatch, tmp_path):
    captured = {}

    class Session:
        def __init__(self, endpoint, **kwargs):
            captured.update(endpoint=endpoint, kwargs=kwargs)

        def run_cmd(self, executable, arguments):
            captured.update(executable=executable, arguments=arguments)
            return SimpleNamespace(
                status_code=0,
                std_out=b'{"generated_at":"2026-09-12T08:00:00Z"}',
            )

    monkeypatch.setitem(sys.modules, 'winrm', SimpleNamespace(Session=Session))
    settings = InfraConnectionPayload(**windows_profile())

    result = collect_windows_winrm(settings, 'snapshot', ca_root=tmp_path)

    assert result['generated_at']
    assert captured['endpoint'] == 'https://win-app.internal:5986/wsman'
    assert captured['kwargs']['server_cert_validation'] == 'validate'
    assert captured['executable'] == 'powershell.exe'
    assert captured['arguments'][-3:] == [
        'C:\\ProgramData\\NexusChat\\nexus-infra-readonly.ps1', '-Mode', 'snapshot']
