def test_recert_get(client):
    resp = client.get("/recert")
    assert resp.status_code == 200
    assert b"Recert" in resp.data


def test_recert_post(client):
    resp = client.post("/recert", data={"soc_date": "2024-01-01", "episode_length": "60"})
    assert resp.status_code == 200


def test_recert_ics(client):
    resp = client.get("/recert/ics?soc=2024-01-01&length=60")
    assert resp.status_code == 200
    assert resp.mimetype == "text/calendar"
    assert b"BEGIN:VCALENDAR" in resp.data


def test_recert_email(client, monkeypatch):
    from app_core.extensions import mail
    monkeypatch.setattr(mail, "send", lambda msg: None)
    resp = client.post(
        "/recert/email",
        data={"soc_date": "2024-01-01", "episode_length": "60", "email": "test@example.com"},
    )
    assert resp.status_code == 302
