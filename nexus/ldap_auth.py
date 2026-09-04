from __future__ import annotations

import os
import ssl
from pathlib import Path
from urllib.parse import urlparse

from ldap3 import BASE, SUBTREE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars


class LDAPAuthenticationError(RuntimeError):
    pass


class LDAPAuthenticator:
    def __init__(self, secret_path: str):
        self.secret_path = Path(secret_path)

    def has_bind_password(self) -> bool:
        return self.secret_path.is_file()

    def set_bind_password(self, password: str) -> None:
        self.secret_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.secret_path.with_suffix(".tmp")
        temporary.write_text(password, encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.secret_path)

    def clear_bind_password(self) -> None:
        self.secret_path.unlink(missing_ok=True)

    def _bind_password(self) -> str:
        if not self.has_bind_password():
            return ""
        return self.secret_path.read_text(encoding="utf-8")

    @staticmethod
    def _server(settings: dict[str, str]) -> Server:
        parsed = urlparse(settings["ldap_url"])
        if parsed.scheme not in {"ldap", "ldaps"} or not parsed.hostname:
            raise LDAPAuthenticationError("LDAP URL must use ldap:// or ldaps://.")
        tls = Tls(
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

    def _service_connection(self, settings: dict[str, str]) -> Connection:
        connection = Connection(
            self._server(settings),
            user=settings.get("ldap_bind_dn") or None,
            password=self._bind_password(),
            receive_timeout=10,
            raise_exceptions=True,
        )
        connection.open()
        if settings.get("ldap_start_tls") == "1":
            connection.start_tls()
        connection.bind()
        return connection

    def test_connection(self, settings: dict[str, str]) -> dict[str, str]:
        connection = None
        try:
            connection = self._service_connection(settings)
            connection.search(
                settings["ldap_base_dn"],
                "(objectClass=*)",
                search_scope=BASE,
                attributes=[],
            )
            return {"message": "LDAP connection successful."}
        except (LDAPException, OSError, ValueError) as error:
            raise LDAPAuthenticationError("LDAP connection failed.") from error
        finally:
            if connection:
                connection.unbind()

    def authenticate(
        self, settings: dict[str, str], identifier: str, password: str
    ) -> dict[str, str | None] | None:
        service_connection = None
        user_connection = None
        try:
            service_connection = self._service_connection(settings)
            user_filter = settings["ldap_user_filter"].replace(
                "{username}", escape_filter_chars(identifier.strip())
            )
            service_connection.search(
                settings["ldap_base_dn"],
                user_filter,
                search_scope=SUBTREE,
                attributes=[
                    settings["ldap_name_attribute"],
                    settings["ldap_email_attribute"],
                ],
                size_limit=2,
            )
            if len(service_connection.entries) != 1:
                return None
            entry = service_connection.entries[0]
            user_connection = Connection(
                self._server(settings),
                user=entry.entry_dn,
                password=password,
                receive_timeout=10,
                raise_exceptions=True,
            )
            user_connection.open()
            if settings.get("ldap_start_tls") == "1":
                user_connection.start_tls()
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
            if user_connection:
                user_connection.unbind()
            if service_connection:
                service_connection.unbind()
