from conftest import login, register


def test_user_can_register_and_session_is_created(client):
    response = register(client)

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "user@example.test"
    assert response.json()["user"]["role"] == "user"
    assert "nexus_session=" in response.headers["set-cookie"]
    assert client.get("/api/auth/me").status_code == 200


def test_duplicate_email_and_weak_password_are_rejected(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409

    weak = register(client, email="weak@example.test", password="password")
    assert weak.status_code == 422
    assert "heslo" in weak.json()["detail"].lower()


def test_registration_rejects_a_whitespace_only_name(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "   ",
            "email": "blank-name@example.test",
            "password": "StrongPass!2026",
        },
    )

    assert response.status_code == 422
    assert "meno" in response.json()["detail"].lower()


def test_login_logout_and_invalid_credentials(client):
    assert register(client).status_code == 201
    client.post("/api/auth/logout")

    invalid = login(client, password="WrongPass!2026")
    assert invalid.status_code == 401

    assert login(client).status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_login_accepts_username_or_legacy_email(client, app):
    app.state.store.create_user(
        name="Named Login",
        username="Named Login",
        email="internal-login@nexus.invalid",
        password="NamedLoginPass2026",
    )

    by_name = client.post(
        "/api/auth/login",
        json={"identifier": "Named Login", "password": "NamedLoginPass2026"},
    )
    assert by_name.status_code == 200
    client.post("/api/auth/logout")

    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200


def test_disabled_user_cannot_log_in(client, app):
    assert register(client).status_code == 201
    user = app.state.store.get_user_by_email("user@example.test")
    app.state.store.update_user(user["id"], is_active=False)
    client.cookies.clear()

    assert login(client).status_code == 403
