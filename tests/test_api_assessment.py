def test_api_assessment(client, monkeypatch):
    import app as app_module

    def fake_ai(diagnosis, pdgm_group):
        return "ASSESS"

    monkeypatch.setattr(app_module, "ai_sample_oasis_assessment", fake_ai)
    resp = client.post(
        "/api/assessment",
        json={"diagnosis": "E11.65", "pdgm_group": "MMTA"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["assessment"] == "ASSESS"
