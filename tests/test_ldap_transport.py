from unittest.mock import MagicMock, patch

import pytest

from nexus.ldap_auth import LDAPAuthenticator, LDAPAuthenticationError, validate_ldap_transport
from conftest import login
from test_ldap import LDAP_CONFIG


@pytest.mark.parametrize('url,start,verify', [
    ('ldap://directory.test', '0', '1'),
    ('ldaps://directory.test', '0', '0'),
    ('ldaps://user:secret@directory.test', '0', '1'),
    ('ldaps://directory.test:99999', '0', '1'),
    ('ldaps://directory.test/path', '0', '1'),
    ('ldaps://[broken', '0', '1'),
])
def test_insecure_or_malformed_ldap_transport_is_rejected(url, start, verify):
    with pytest.raises(LDAPAuthenticationError):
        validate_ldap_transport(dict(ldap_url=url, ldap_start_tls=start, ldap_verify_tls=verify))


def test_failed_starttls_never_sends_bind_credentials(tmp_path):
    auth = LDAPAuthenticator(str(tmp_path / 'secret'))
    settings = dict(ldap_url='ldap://directory.test', ldap_start_tls='1', ldap_verify_tls='1')
    connection = MagicMock()
    connection.start_tls.return_value = False
    with patch('nexus.ldap_auth.Connection', return_value=connection):
        with pytest.raises(LDAPAuthenticationError):
            auth.test_connection(settings)
    connection.bind.assert_not_called()
    connection.unbind.assert_called_once()


def test_ldap_draft_test_does_not_save_settings_or_secret(client, app):
    login(client, 'admin@example.test', 'AdminPass!2026')
    response = client.post('/api/admin/ldap/test', json=LDAP_CONFIG)
    assert response.status_code == 200
    saved = client.get('/api/admin/ldap').json()
    assert saved['enabled'] is False
    assert saved['url'] == ''
    assert saved['bind_password_configured'] is False


def test_secret_replacement_leaves_no_temporary_files(tmp_path):
    auth = LDAPAuthenticator(str(tmp_path / 'secret'))
    auth.set_bind_password('first')
    auth.set_bind_password('second')
    assert (tmp_path / 'secret').read_text() == 'second'
    assert list(tmp_path.iterdir()) == [tmp_path / 'secret']
