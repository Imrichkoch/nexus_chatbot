from conftest import login, register


LDAP_CONFIG = {
    "enabled": True,
    "url": "ldaps://directory.example.test:636",
    "start_tls": False,
    "verify_tls": True,
    "base_dn": "ou=people,dc=example,dc=test",
    "bind_dn": "cn=nexus,ou=services,dc=example,dc=test",
    "bind_password": "DirectorySecret!2026",
    "clear_bind_password": False,
    "user_filter": "(&(objectClass=person)(uid={username}))",
    "name_attribute": "displayName",
    "email_attribute": "mail",
    "auto_provision": True,
}


def test_ldap_settings_are_admin_only_and_do_not_expose_secrets(client):
    assert register(client).status_code == 201
    assert client.get("/api/admin/ldap").status_code == 403
    assert client.put("/api/admin/ldap", json=LDAP_CONFIG).status_code == 403
    assert client.post("/api/admin/ldap/test").status_code == 403

    client.post("/api/auth/logout")
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    default = client.get("/api/admin/ldap")
    assert default.status_code == 200
    assert default.json()["enabled"] is False
    assert default.json()["bind_password_configured"] is False
    assert "bind_password" not in default.json()

    saved = client.put("/api/admin/ldap", json=LDAP_CONFIG)
    assert saved.status_code == 200
    assert saved.json()["enabled"] is True
    assert saved.json()["bind_password_configured"] is True
    assert "bind_password" not in saved.json()
    assert "DirectorySecret" not in saved.text

    fetched = client.get("/api/admin/ldap")
    assert fetched.json()["url"] == LDAP_CONFIG["url"]
    assert fetched.json()["user_filter"] == LDAP_CONFIG["user_filter"]
    assert "bind_password" not in fetched.json()


def test_admin_can_test_ldap_connection(client, app):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    assert client.put("/api/admin/ldap", json=LDAP_CONFIG).status_code == 200

    response = client.post("/api/admin/ldap/test")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert app.state.fake_ldap.test_calls[-1]["ldap_url"] == LDAP_CONFIG["url"]


def test_ldap_login_provisions_and_respects_disabled_shadow_user(client, app):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    assert client.put("/api/admin/ldap", json=LDAP_CONFIG).status_code == 200
    client.post("/api/auth/logout")
    app.state.fake_ldap.identities["mnovak"] = {
        "_password": "LdapPass!2026",
        "username": "mnovak",
        "name": "Marta Novak",
        "email": "marta.novak@example.test",
        "dn": "uid=mnovak,ou=people,dc=example,dc=test",
    }

    authenticated = client.post(
        "/api/auth/login",
        json={"identifier": "mnovak", "password": "LdapPass!2026"},
    )
    assert authenticated.status_code == 200
    assert authenticated.json()["user"]["auth_source"] == "ldap"
    assert authenticated.json()["user"]["role"] == "user"

    ldap_user = app.state.store.get_user_by_identifier("mnovak")
    app.state.store.update_user(ldap_user["id"], is_active=False)
    client.cookies.clear()
    denied = client.post(
        "/api/auth/login",
        json={"identifier": "mnovak", "password": "LdapPass!2026"},
    )
    assert denied.status_code == 403


def test_ldap_cannot_take_over_an_existing_local_username(client, app):
    app.state.store.create_local_user(
        name="existing", password="ExistingPass2026", role="user"
    )
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    assert client.put("/api/admin/ldap", json=LDAP_CONFIG).status_code == 200
    client.post("/api/auth/logout")
    app.state.fake_ldap.identities["existing"] = {
        "_password": "LdapPass!2026",
        "username": "existing",
        "name": "LDAP Existing",
        "email": "ldap-existing@example.test",
        "dn": "uid=existing,ou=people,dc=example,dc=test",
    }

    response = client.post(
        "/api/auth/login",
        json={"identifier": "existing", "password": "LdapPass!2026"},
    )

    assert response.status_code == 401
    assert app.state.fake_ldap.auth_calls == []
