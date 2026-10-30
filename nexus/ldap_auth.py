from __future__ import annotations

import os
import ssl
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from ldap3 import BASE, SUBTREE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars


class LDAPAuthenticationError(RuntimeError):
    pass


def validate_ldap_transport(settings: dict[str, str]):
    try:
        parsed = urlparse(settings.get('ldap_url', ''))
        port = parsed.port
    except ValueError as error:
        raise LDAPAuthenticationError('Invalid LDAP URL or port.') from error
    if (parsed.scheme not in {'ldap', 'ldaps'} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {'', '/'} or parsed.query or parsed.fragment
            or any(char.isspace() for char in parsed.netloc) or port == 0):
        raise LDAPAuthenticationError('Use an LDAP server URL without credentials or a path.')
    if parsed.scheme == 'ldaps' and settings.get('ldap_start_tls') == '1':
        raise LDAPAuthenticationError('StartTLS requires ldap://, not ldaps://.')
    if parsed.scheme == 'ldap' and settings.get('ldap_start_tls') != '1':
        raise LDAPAuthenticationError('LDAP requires LDAPS or StartTLS.')
    if settings.get('ldap_verify_tls', '1') != '1':
        raise LDAPAuthenticationError('TLS certificate verification is required.')
    return parsed


class LDAPAuthenticator:
    def __init__(self, secret_path: str):
        self.secret_path = Path(secret_path)

    def has_bind_password(self) -> bool:
        return self.secret_path.is_file()

    def set_bind_password(self, password: str) -> None:
        self.secret_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, path = tempfile.mkstemp(prefix='.ldap-', dir=self.secret_path.parent)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                stream.write(password)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(path, self.secret_path)
        finally:
            Path(path).unlink(missing_ok=True)

    def clear_bind_password(self) -> None:
        self.secret_path.unlink(missing_ok=True)

    def _bind_password(self) -> str:
        if not self.has_bind_password():
            return ""
        return self.secret_path.read_text(encoding="utf-8")

    @staticmethod
    def _server(settings: dict[str, str]) -> Server:
        parsed = validate_ldap_transport(settings)
        tls = Tls(
            ca_certs_file=os.getenv('NEXUS_LDAP_CA_FILE') or None,
            validate=(
                ssl.CERT_REQUIRED
                if settings.get("ldap_verify_tls", "1") == "1"
                else ssl.CERT_NONE
            )
        )
        return Server(
            parsed.hostname,
            port=parsed.port or (636 if parsed.scheme == "ldaps" else 389),
            use_ssl=parsed.scheme == "ldaps",
            tls=tls,
            connect_timeout=8,
        )

    def _service_connection(self, settings: dict[str, str], password: str | None = None) -> Connection:
        password = self._bind_password() if password is None else password
        if settings.get('ldap_bind_dn') and not password:
            raise LDAPAuthenticationError('A service bind password is required.')
        connection = Connection(
            self._server(settings),
            user=settings.get("ldap_bind_dn") or None,
            password=password,
            auto_referrals=False,
            receive_timeout=10,
            raise_exceptions=True,
        )
        try:
            connection.open()
            if settings.get('ldap_start_tls') == '1' and not connection.start_tls():
                raise LDAPAuthenticationError('LDAP TLS negotiation failed.')
            if not connection.bind():
                raise LDAPAuthenticationError('LDAP service bind failed.')
            return connection
        except Exception:
            self._close(connection)
            raise

    @staticmethod
    def _close(connection):
        if connection is not None:
            try:
                connection.unbind()
            except (LDAPException, OSError):
                pass

    def test_connection(self, settings: dict[str, str], password: str | None = None) -> dict[str, str]:
        connection = None
        try:
            connection = self._service_connection(settings, password)
            found = connection.search(
                settings["ldap_base_dn"],
                "(objectClass=*)",
                search_scope=BASE,
                attributes=[],
                time_limit=8,
            )
            if not found or len(connection.entries) != 1:
                raise LDAPAuthenticationError('LDAP Base DN was not found.')
            return {"message": "LDAP connection successful."}
        except (LDAPException, OSError, ValueError) as error:
            raise LDAPAuthenticationError("LDAP connection failed.") from error
        finally:
            self._close(connection)

    def authenticate(
        self, settings: dict[str, str], identifier: str, password: str
    ) -> dict[str, str | None] | None:
        service_connection = None
        user_connection = None
        if not identifier.strip() or not password:
            return None
        try:
            service_connection = self._service_connection(settings)
            user_filter = settings["ldap_user_filter"].replace(
                "{username}", escape_filter_chars(identifier.strip())
            )
            found = service_connection.search(
                settings["ldap_base_dn"],
                user_filter,
                search_scope=SUBTREE,
                attributes=[
                    settings["ldap_name_attribute"],
                    settings["ldap_email_attribute"],
                ],
                size_limit=2,
                time_limit=8,
            )
            if not found or len(service_connection.entries) != 1:
                return None
            entry = service_connection.entries[0]
            user_connection = Connection(
                self._server(settings),
                user=entry.entry_dn,
                password=password,
                auto_referrals=False,
                receive_timeout=10,
                raise_exceptions=True,
            )
            user_connection.open()
            if settings.get('ldap_start_tls') == '1' and not user_connection.start_tls():
                raise LDAPAuthenticationError('LDAP TLS negotiation failed.')
            if not user_connection.bind():
                return None

            def attribute_value(name: str) -> str | None:
                value = entry.entry_attributes_as_dict.get(name)
                if isinstance(value, list):
                    return str(value[0]) if value else None
                return str(value) if value is not None else None

            return {
                "username": identifier.strip(),
                "name": attribute_value(settings["ldap_name_attribute"])
                or identifier.strip(),
                "email": attribute_value(settings["ldap_email_attribute"]),
                "dn": entry.entry_dn,
            }
        except (LDAPException, OSError, ValueError) as error:
            raise LDAPAuthenticationError("LDAP authentication failed.") from error
        finally:
            self._close(user_connection)
            self._close(service_connection)
