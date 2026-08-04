from conftest import login, register


def test_regular_user_cannot_access_admin(client):
    assert register(client).status_code == 201

    assert client.get("/api/admin/overview").status_code == 403
    assert client.get("/api/admin/users").status_code == 403


def test_admin_can_view_metrics_and_disable_user(client):
    assert register(client).status_code == 201
    client.post("/api/auth/logout")
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200

    users = client.get("/api/admin/users")
    assert users.status_code == 200
    target = next(user for user in users.json() if user["email"] == "user@example.test")

    updated = client.patch(
        f"/api/admin/users/{target['id']}",
        json={"is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    overview = client.get("/api/admin/overview").json()
    assert overview["users_total"] == 2
    assert overview["users_active"] == 1


def test_admin_can_create_user_and_admin_accounts(client):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200

    created_user = client.post(
        "/api/admin/users",
        json={
            "name": "Support User",
            "password": "SupportPass2026",
            "role": "user",
        },
    )
    created_admin = client.post(
        "/api/admin/users",
        json={
            "name": "Operations Admin",
            "password": "OperationsPass2026",
            "role": "admin",
        },
    )

    assert created_user.status_code == 201
    assert created_user.json()["role"] == "user"
    assert created_user.json()["username"] == "Support User"
    assert created_user.json()["email"] is None
    assert created_admin.status_code == 201
    assert created_admin.json()["role"] == "admin"
    assert "password_hash" not in created_admin.json()

    client.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"identifier": "Operations Admin", "password": "OperationsPass2026"},
    ).status_code == 200


def test_regular_user_cannot_create_accounts_and_admin_validates_input(client):
    assert register(client).status_code == 201
    payload = {
        "name": "Blocked Admin",
        "password": "BlockedPass2026",
        "role": "admin",
    }
    assert client.post("/api/admin/users", json=payload).status_code == 403

    client.post("/api/auth/logout")
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    payload["password"] = "weak"
    assert client.post("/api/admin/users", json=payload).status_code == 422
    payload["password"] = "BlockedPass2026"
    assert client.post("/api/admin/users", json=payload).status_code == 201
    assert client.post("/api/admin/users", json=payload).status_code == 409


def test_admin_cannot_disable_or_demote_self(client):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    me = client.get("/api/auth/me").json()["user"]

    disable = client.patch(
        f"/api/admin/users/{me['id']}",
        json={"is_active": False},
    )
    demote = client.patch(
        f"/api/admin/users/{me['id']}",
        json={"role": "user"},
    )

    assert disable.status_code == 400
    assert demote.status_code == 400


def test_admin_can_update_ai_settings_without_exposing_secrets(client):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200

    response = client.put(
        "/api/admin/settings",
        json={
            "model": "openai/gpt-5.6-terra",
            "system_prompt": "Odpovedaj presne, vecne a po slovensky.",
            "rag_enabled": True,
            "rag_max_chunks": 5,
            "infra_agent_enabled": True,
            "infra_agent_admin_only": True,
            "infra_live_enabled": True,
            "infra_model": "openai/gpt-5.6-terra",
            "data_agent_enabled": True,
            "data_agent_admin_only": False,
            "data_model": "openai/gpt-5.6-terra",
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "openai/gpt-5.6-terra"
    assert response.json()["rag_enabled"] is True
    assert response.json()["rag_max_chunks"] == 5
    assert response.json()["infra_agent_enabled"] is True
    assert response.json()["infra_agent_admin_only"] is True
    assert response.json()["infra_live_enabled"] is True
    assert response.json()["infra_model"] == "openai/gpt-5.6-terra"
    assert response.json()["data_agent_enabled"] is True
    assert response.json()["data_agent_admin_only"] is False
    assert response.json()["data_model"] == "openai/gpt-5.6-terra"
    assert "api_key" not in response.json()


def test_admin_gets_live_model_catalog_and_regular_user_does_not(client):
    assert register(client).status_code == 201
    assert client.get("/api/admin/models").status_code == 403
    client.post("/api/auth/logout")
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200

    response = client.get("/api/admin/models")

    assert response.status_code == 200
    assert response.json()["models"][0]["id"] == "openai/gpt-5.6-terra"
    assert response.json()["models"][0]["context_length"] == 400000


def test_admin_can_manage_rag_documents(client):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200

    created = client.post(
        "/api/admin/rag/documents",
        json={
            "name": "runbook.md",
            "content": "# Redis\nPri výpadku najprv over službu redis-server.",
        },
    )

    assert created.status_code == 201
    document = created.json()
    assert document["name"] == "runbook.md"
    assert document["chunk_count"] >= 1
    listing = client.get("/api/admin/rag/documents")
    assert listing.status_code == 200
    assert listing.json()["documents"][0]["name"] == "runbook.md"
    assert client.delete(f"/api/admin/rag/documents/{document['id']}").status_code == 204
    assert client.get("/api/admin/rag/documents").json()["documents"] == []


def test_rag_rejects_unsupported_or_oversized_documents(client):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200

    unsupported = client.post(
        "/api/admin/rag/documents",
        json={"name": "payload.exe", "content": "not executable"},
    )
    oversized = client.post(
        "/api/admin/rag/documents",
        json={"name": "huge.txt", "content": "x" * (10 * 1024 * 1024 + 1)},
    )

    assert unsupported.status_code == 422
    assert oversized.status_code == 413
