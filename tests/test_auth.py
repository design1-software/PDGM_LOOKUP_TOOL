def test_capture_lead(client):
    """POST /api/capture-lead should create a lead and set session."""
    resp = client.post("/api/capture-lead", json={"name": "Test User", "email": "test@example.com"})
    assert resp.status_code == 200
    data = resp.json
    assert data["success"] is True
    
    with client.session_transaction() as session:
        assert session.get("lead_captured") is True
        assert session.get("lead_email") == "test@example.com"
