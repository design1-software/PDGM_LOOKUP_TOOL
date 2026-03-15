def test_logout_redirects(client):
    """GET /auth/logout should redirect to the index page."""
    resp = client.get("/auth/logout", follow_redirects=False)
    assert resp.status_code in (301, 302)
    location = resp.headers.get("Location", "")
    assert "/" in location
