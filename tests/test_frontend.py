def test_spa_shell_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "NexusChat" in response.text
    assert 'id="auth-view"' in response.text
    assert 'id="chat-view"' in response.text
    assert 'id="admin-view"' in response.text
    assert 'id="infra-source-switcher"' in response.text
    assert 'data-infra-source="live"' in response.text


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

    rejected = client.get("/", headers={"host": "attacker.example"})
    assert rejected.status_code == 400
