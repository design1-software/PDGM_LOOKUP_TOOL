def test_api_lookup(client, monkeypatch):
    """POST /api/lookup with a valid ICD-10 code returns success."""
    resp = client.post("/api/lookup", json={"query": "A000"})
    assert resp.status_code == 200
    data = resp.get_json()
    # The rules engine returns a dict; just ensure no error key
    assert "error" not in data


def test_api_lookup_missing_query(client):
    """POST /api/lookup with empty query returns 400."""
    resp = client.post("/api/lookup", json={"query": ""})
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data
