import sqlite3

import pytest
from fastapi.testclient import TestClient

from conftest import register
from nexus.app import create_app
from nexus.store import Store
from nexus.store import StorageQuotaExceeded


def test_custom_host_cookie_path_and_registration_policy(tmp_path, monkeypatch):
    monkeypatch.setenv('NEXUS_ALLOWED_HOSTS', 'chat.example.test,testserver')
    monkeypatch.setenv('NEXUS_BASE_PATH', '/assist')
    monkeypatch.setenv('NEXUS_REGISTRATION_ENABLED', '0')
    app = create_app(database_path=str(tmp_path / 'app.db'),
                     synthetic_database_path=str(tmp_path / 'data.db'), secure_cookies=True)
    with TestClient(app, base_url='https://chat.example.test') as client:
        assert client.get('/').status_code == 200
        assert register(client).status_code == 403
        assert client.get('/api/auth/config').json()['registration_enabled'] is False
        app.state.store.create_local_user(name='Admin', password='StrongPassword2026')
        response = client.post('/api/auth/login', json={'identifier': 'Admin', 'password': 'StrongPassword2026'})
        assert response.status_code == 200
        assert 'Path=/assist' in response.headers['set-cookie']
        assert client.get('/ready').status_code == 200


def test_deactivation_revokes_sessions_permanently(app):
    store = app.state.store
    user = store.create_local_user(name='Session test', password='StrongPassword2026')
    token = store.create_session(user['id'])
    store.update_user(user['id'], is_active=False)
    store.update_user(user['id'], is_active=True)
    assert store.user_for_session(token) is None


def test_ldap_identity_cannot_be_reassigned(app):
    store = app.state.store
    identity = dict(identifier='alice', name='Alice', email=None, directory_dn='uid=alice,dc=old')
    store.upsert_ldap_user(**identity)
    with pytest.raises(sqlite3.IntegrityError):
        store.upsert_ldap_user(**{**identity, 'directory_dn': 'uid=mallory,dc=new'})


def test_long_bcrypt_password_is_rejected_instead_of_truncated(client):
    response = register(client, password='Aa1' + 'x' * 70)
    assert response.status_code == 422


def test_validation_never_echoes_password(client):
    secret = 'sensitive' * 200
    response = client.post('/api/auth/login', json={'identifier': 'admin', 'password': secret})
    assert response.status_code == 422
    assert secret not in response.text


def test_rag_quota_rejects_whole_batch(app, monkeypatch):
    monkeypatch.setenv('NEXUS_RAG_MAX_DOCUMENTS', '2')
    store = app.state.store
    store.create_rag_document('one.md', 'Original document.')
    with pytest.raises(StorageQuotaExceeded):
        store.create_rag_documents([('two.md', 'Second document.'), ('three.md', 'Third document.')])
    assert len(store.list_rag_documents()) == 1


def test_username_cannot_shadow_another_accounts_email(app):
    store = app.state.store
    store.create_local_user(name='person@example.test', password='StrongPassword2026')
    with pytest.raises(sqlite3.IntegrityError):
        store.create_user(name='Other person', email='person@example.test', password='StrongPassword2026')


def test_request_body_limit_and_correlation_id(client):
    response = client.post('/api/auth/login', content=b'x' * (256 * 1024 + 1),
                           headers={'Content-Type': 'application/json'})
    assert response.status_code == 413
    assert len(response.headers['x-request-id']) == 32


def test_admin_audit_pagination_is_protected(client, app):
    from conftest import login
    register(client)
    assert client.get('/api/admin/audit').status_code == 403
    client.post('/api/auth/logout')
    login(client, 'admin@example.test', 'AdminPass!2026')
    app.state.store.audit(1, 'test.event', 'test')
    events = client.get('/api/admin/audit?limit=1').json()['events']
    assert len(events) == 1
    assert client.get(f'/api/admin/audit?before_id={events[0]["id"]}').status_code == 200


def test_chat_admission_limit_releases_slots_and_keeps_health_available():
    import asyncio
    from nexus.middleware import ChatAdmissionLimit

    async def exercise():
        entered, finish = asyncio.Event(), asyncio.Event()
        async def application(scope, receive, send):
            if scope['path'].endswith('/messages'):
                entered.set()
                await finish.wait()
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})
        middleware = ChatAdmissionLimit(application, maximum=1)
        async def request(path, method='POST'):
            responses = []
            async def receive():
                return {'type': 'http.request', 'body': b''}
            async def send(message):
                responses.append(message)
            await middleware({'type': 'http', 'method': method, 'path': path}, receive, send)
            return responses[0]['status']
        first = asyncio.create_task(request('/api/conversations/1/messages'))
        await entered.wait()
        assert await request('/api/conversations/2/messages/stream') == 429
        assert await request('/health', 'GET') == 200
        finish.set()
        assert await first == 200
        assert await request('/api/conversations/3/messages') == 200
    asyncio.run(exercise())
