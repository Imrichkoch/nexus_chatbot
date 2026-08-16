def test_spa_shell_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert '<html lang="en">' in response.text
    assert "NexusChat" in response.text
    assert 'id="auth-view"' in response.text
    assert 'id="chat-view"' in response.text
    assert 'id="admin-view"' in response.text
    assert 'id="infra-source-switcher"' in response.text
    assert 'data-infra-source="live"' in response.text
    assert 'id="admin-user-create-form"' in response.text
    assert 'id="admin-user-role"' in response.text
    assert 'id="admin-user-password-generate"' in response.text
    assert 'id="admin-user-password-copy"' in response.text
    assert 'id="admin-user-email"' not in response.text
    assert 'name="identifier"' in response.text
    assert "crypto.getRandomValues" in client.get("/assets/app.js").text
    assert 'assets/app.js?v=20260816a' in response.text
    assert 'assets/styles.css?v=20260810b' in response.text
    assert 'id="settings-dirty-bar"' in response.text
    assert 'id="settings-dirty-save"' in response.text
    assert "settingsDirty" in client.get("/assets/app.js").text
    assert 'id="rag-drop"' in response.text
    assert 'id="rag-file"' in response.text
    assert "multiple" in response.text
    assert 'class="language-switcher' in response.text
    assert 'data-language="en"' in response.text
    assert 'data-language="sk"' in response.text
    assert "nexus_language" in client.get("/assets/app.js").text
    assert "TRANSLATIONS" in client.get("/assets/app.js").text
    assert "RAG_MAX_FILES_PER_BATCH = 1000" in client.get("/assets/app.js").text
    assert "max 1000 at once" in client.get("/assets/app.js").text
    assert "50 MB/batch" in client.get("/assets/app.js").text
    assert "max 1000 naraz" in response.text
    assert "50 MB/dávka" in response.text


def test_security_headers_and_host_validation(client):
    response = client.get("/")

    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "object-src 'none'" in response.headers["content-security-policy"]
    assert "form-action 'self'" in response.headers["content-security-policy"]
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cache-control"] == "no-store"

    api_response = client.get("/api/auth/me")
    assert api_response.headers["cache-control"] == "no-store"

    asset_response = client.get("/assets/app.js")
    assert asset_response.headers["cache-control"] == "no-cache"

    rejected = client.get("/", headers={"host": "attacker.example"})
    assert rejected.status_code == 400
