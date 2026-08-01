import json

from conftest import login, register
from nexus.ai import AIUnavailable


def test_user_can_create_conversation_and_receive_ai_reply(client, app):
    assert register(client).status_code == 201
    created = client.post("/api/conversations", json={"title": "Prvý chat"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    reply = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Vysvetli mi kvantové tunelovanie."},
    )

    assert reply.status_code == 201
    body = reply.json()
    assert body["assistant"]["content"] == "Testovacia odpoveď z Nexus AI."
    assert body["assistant"]["model"]
    assert app.state.fake_ai.calls[0]["messages"][-1]["content"].startswith("Vysvetli")

    detail = client.get(f"/api/conversations/{conversation_id}")
    assert [message["role"] for message in detail.json()["messages"]] == [
        "user",
        "assistant",
    ]


def test_users_cannot_access_each_others_conversations(client):
    assert register(client, email="first@example.test").status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "Súkromné"}
    ).json()["id"]
    client.post("/api/auth/logout")

    assert register(client, email="second@example.test").status_code == 201
    assert client.get(f"/api/conversations/{conversation_id}").status_code == 404
    assert (
        client.delete(f"/api/conversations/{conversation_id}").status_code == 404
    )


def test_conversation_histories_are_separated_by_agent_mode(client, app):
    assert register(client).status_code == 201
    app.state.store.update_settings(
        {"infra_agent_enabled": "1", "infra_agent_admin_only": "0"}
    )

    created = {
        mode: client.post(
            "/api/conversations",
            json={"title": f"{mode} workspace", "agent_mode": mode},
        ).json()
        for mode in ("general", "infra", "data")
    }

    for mode, conversation in created.items():
        response = client.get("/api/conversations", params={"agent_mode": mode})
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [conversation["id"]]
        assert response.json()[0]["agent_mode"] == mode


def test_message_agent_must_match_conversation_workspace(client):
    assert register(client).status_code == 201
    conversation = client.post(
        "/api/conversations",
        json={"title": "Nexus only", "agent_mode": "general"},
    ).json()

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"content": "Run a SQL report.", "agent_mode": "data"},
    )

    assert response.status_code == 409
    assert client.get(
        f"/api/conversations/{conversation['id']}"
    ).json()["messages"] == []


def test_empty_or_oversized_messages_are_rejected(client):
    assert register(client).status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "Validácia"}
    ).json()["id"]

    assert (
        client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "   "},
        ).status_code
        == 422
    )


def test_enabled_rag_injects_relevant_chunks_and_returns_sources(client, app):
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    client.put(
        "/api/admin/settings",
        json={
            "model": "openai/gpt-5.6-terra",
            "system_prompt": "Odpovedaj presne, vecne a po slovensky.",
            "rag_enabled": True,
            "rag_max_chunks": 4,
            "infra_agent_enabled": False,
            "infra_agent_admin_only": True,
            "infra_model": "openai/gpt-5.6-terra",
        },
    )
    client.post(
        "/api/admin/rag/documents",
        json={
            "name": "runbook.md",
            "content": "Redis cache beží ako služba redis-server. Pri výpadku over jej stav.",
        },
    )
    conversation_id = client.post(
        "/api/conversations", json={"title": "RAG"}
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Ako sa volá služba pre Redis cache?"},
    )

    assert response.status_code == 201
    call = app.state.fake_ai.calls[-1]
    assert "[KB:runbook.md#1]" in call["system_prompt"]
    assert "redis-server" in call["system_prompt"]
    assert response.json()["assistant"]["sources"][0]["document"] == "runbook.md"


def test_infra_agent_is_disabled_by_default(client):
    assert register(client).status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "Infra", "agent_mode": "infra"}
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Koľko RAM používa server?", "agent_mode": "infra"},
    )

    assert response.status_code == 403


def test_infra_agent_uses_read_only_snapshot_for_admin(client, app, tmp_path):
    snapshot_path = tmp_path / "infra-snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-24T12:00:00Z",
                "hostname": "vps-prod",
                "memory": {"used_mb": 2048, "total_mb": 8192},
                "services": [{"name": "nexuschat", "active": True}],
            }
        ),
        encoding="utf-8",
    )
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    client.put(
        "/api/admin/settings",
        json={
            "model": "openai/gpt-5.6-terra",
            "system_prompt": "Odpovedaj presne, vecne a po slovensky.",
            "rag_enabled": False,
            "rag_max_chunks": 4,
            "infra_agent_enabled": True,
            "infra_agent_admin_only": True,
            "infra_model": "openai/gpt-5.6-terra",
        },
    )
    conversation_id = client.post(
        "/api/conversations", json={"title": "Infra", "agent_mode": "infra"}
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Koľko RAM používa server?", "agent_mode": "infra"},
    )

    assert response.status_code == 201
    call = app.state.fake_ai.calls[-1]
    assert call["model"] == "openai/gpt-5.6-terra"
    assert "READ-ONLY" in call["system_prompt"]
    assert '"used_mb": 2048' in call["system_prompt"]
    assert "2026-07-24T12:00:00Z" in call["system_prompt"]


def test_admin_only_infra_agent_rejects_regular_user(client, app, tmp_path):
    (tmp_path / "infra-snapshot.json").write_text(
        '{"generated_at":"2026-07-24T12:00:00Z"}',
        encoding="utf-8",
    )
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    app.state.store.update_settings(
        {"infra_agent_enabled": "1", "infra_agent_admin_only": "1"}
    )
    client.post("/api/auth/logout")
    assert register(client).status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "Infra", "agent_mode": "infra"}
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Je Nexus online?", "agent_mode": "infra"},
    )

    assert response.status_code == 403


def test_admin_can_choose_live_infra_source(client, app):
    live_calls = []

    def collect_live():
        live_calls.append(True)
        return {
            "generated_at": "2026-07-26T14:30:00+00:00",
            "hostname": "live-vps",
            "memory": {"used_mb": 3072, "total_mb": 8192},
            "services": [{"name": "nexuschat", "active": True}],
            "scope": "sanitized_read_only",
            "collection_mode": "live",
        }

    app.state.live_infra_collector = collect_live
    app.state.store.update_settings(
        {
            "infra_agent_enabled": "1",
            "infra_agent_admin_only": "1",
            "infra_live_enabled": "1",
        }
    )
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    capabilities = client.get("/api/capabilities")
    assert capabilities.status_code == 200
    assert capabilities.json()["infra_live_available"] is True
    conversation_id = client.post(
        "/api/conversations",
        json={"title": "Live infra", "agent_mode": "infra"},
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "Aký je stav servera práve teraz?",
            "agent_mode": "infra",
            "infra_source": "live",
        },
    )

    assert response.status_code == 201
    assert live_calls == [True]
    assert '"collection_mode": "live"' in app.state.fake_ai.calls[-1]["system_prompt"]
    infra_source = next(
        source
        for source in response.json()["assistant"]["sources"]
        if source["type"] == "infra"
    )
    assert infra_source == {
        "type": "infra",
        "mode": "live",
        "generated_at": "2026-07-26T14:30:00+00:00",
    }


def test_live_infra_is_always_admin_only(client, app):
    live_calls = []
    app.state.live_infra_collector = lambda: live_calls.append(True)
    app.state.store.update_settings(
        {
            "infra_agent_enabled": "1",
            "infra_agent_admin_only": "0",
            "infra_live_enabled": "1",
        }
    )
    assert register(client).status_code == 201
    capabilities = client.get("/api/capabilities").json()
    assert capabilities["infra_agent_available"] is True
    assert capabilities["infra_live_available"] is False
    conversation_id = client.post(
        "/api/conversations",
        json={"title": "No live access", "agent_mode": "infra"},
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "Pozri server naživo.",
            "agent_mode": "infra",
            "infra_source": "live",
        },
    )

    assert response.status_code == 403
    assert live_calls == []
    assert client.get(
        f"/api/conversations/{conversation_id}"
    ).json()["messages"] == []


def test_snapshot_infra_response_is_labeled_with_source(client, app, tmp_path):
    (tmp_path / "infra-snapshot.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-26T14:00:00+00:00",
                "hostname": "snapshot-vps",
                "scope": "sanitized_read_only",
            }
        ),
        encoding="utf-8",
    )
    app.state.store.update_settings(
        {"infra_agent_enabled": "1", "infra_agent_admin_only": "1"}
    )
    assert login(client, "admin@example.test", "AdminPass!2026").status_code == 200
    conversation_id = client.post(
        "/api/conversations",
        json={"title": "Snapshot infra", "agent_mode": "infra"},
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "Čo bolo v poslednom snapshote?",
            "agent_mode": "infra",
            "infra_source": "snapshot",
        },
    )

    assert response.status_code == 201
    infra_source = next(
        source
        for source in response.json()["assistant"]["sources"]
        if source["type"] == "infra"
    )
    assert infra_source["mode"] == "snapshot"
    assert infra_source["generated_at"] == "2026-07-26T14:00:00+00:00"


def test_data_agent_turns_natural_language_into_sql_report(client, app):
    assert register(client).status_code == 201
    capabilities = client.get("/api/capabilities").json()
    assert capabilities["data_agent_available"] is True
    conversation_id = client.post(
        "/api/conversations",
        json={"title": "Data report", "agent_mode": "data"},
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "Sprav report tržieb podľa krajín.",
            "agent_mode": "data",
        },
    )

    assert response.status_code == 201
    assistant = response.json()["assistant"]
    assert assistant["content"].startswith("REPORT /")
    assert assistant["agent_mode"] == "data"
    assert assistant["sources"][0]["type"] == "sql"
    assert assistant["sources"][0]["row_count"] > 0
    assert "SELECT" in assistant["sources"][0]["query"]
    assert app.state.fake_ai.sql_calls[-1]["question"].startswith("Sprav report")
    assert app.state.fake_ai.report_calls[-1]["query_result"]["rows"]


def test_data_agent_accepts_direct_read_only_sql(client, app):
    assert register(client).status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "SQL", "agent_mode": "data"}
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "SELECT status, COUNT(*) AS total FROM orders GROUP BY status",
            "agent_mode": "data",
        },
    )

    assert response.status_code == 201
    assert app.state.fake_ai.sql_calls == []
    assert app.state.fake_ai.report_calls[-1]["sql"].startswith("SELECT status")


def test_data_agent_cannot_query_nexus_application_tables(client):
    assert register(client).status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "Isolation", "agent_mode": "data"}
    ).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={
            "content": "SELECT email, password_hash FROM users",
            "agent_mode": "data",
        },
    )

    assert response.status_code == 422
    detail = client.get(f"/api/conversations/{conversation_id}").json()
    assert detail["messages"] == []
    assert "syntetickej databáze" in response.json()["detail"]
    assert (
        client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "x" * 12001},
        ).status_code
        == 422
    )


def test_failed_ai_reply_does_not_persist_an_orphan_user_message(client, app):
    class UnavailableAI:
        def reply(self, **_kwargs):
            raise AIUnavailable("Model je dočasne nedostupný.")

    assert register(client).status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "Zlyhanie modelu"}
    ).json()["id"]
    app.state.ai_provider = UnavailableAI()

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Táto správa sa nemá uložiť bez odpovede."},
    )

    assert response.status_code == 503
    detail = client.get(f"/api/conversations/{conversation_id}").json()
    assert detail["messages"] == []


def test_empty_ai_reply_is_rejected_without_persisting_messages(client, app):
    class EmptyAI:
        def reply(self, **_kwargs):
            return {
                "text": "   ",
                "model": "test/empty",
                "input_tokens": 1,
                "output_tokens": 0,
            }

    assert register(client).status_code == 201
    conversation_id = client.post(
        "/api/conversations", json={"title": "Prázdna odpoveď"}
    ).json()["id"]
    app.state.ai_provider = EmptyAI()

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Odpovedz mi."},
    )

    assert response.status_code == 502
    assert client.get(f"/api/conversations/{conversation_id}").json()["messages"] == []
