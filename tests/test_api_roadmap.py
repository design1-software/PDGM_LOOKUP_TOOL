def test_api_roadmap(client, monkeypatch):
    import app as app_module

    captured = {}

    def fake_ai(diagnosis, pdgm_group, disciplines):
        captured["disciplines"] = disciplines
        return "DOC"

    monkeypatch.setattr(app_module, "ai_documentation_roadmap", fake_ai)
    resp = client.post(
        "/api/roadmap",
        json={
            "diagnosis": "E11.65",
            "pdgm_group": "MMTA",
            "disciplines": ["RN/LPN", "PT/OT"],
        },
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["roadmap"] == "DOC"
    assert captured["disciplines"] == ["RN/LPN", "PT/OT"]
