"""The lead-capture gate on the API surface.

These tests exist because the gate was previously only "covered" by accident:
the endpoint tests all 403'd, which looked like gate coverage but actually meant
none of the handlers were being exercised. Now `client` is past the gate, so the
gate needs its own tests or a regression that removed it would go unnoticed.
"""

import pytest

# Every route wrapped in @require_lead_capture, with a minimal valid body.
GATED_POST_ROUTES = [
    ('/api/lookup', {'query': 'A000'}),
    ('/api/roadmap', {'diagnosis': 'E11.65', 'pdgm_group': 'MMTA'}),
    ('/api/assessment', {'diagnosis': 'E11.65', 'pdgm_group': 'MMTA'}),
    ('/api/hipps', {'primary_icd10': 'A000', 'secondary_icd10s': [],
                    'admission_source': 1, 'episode_timing': 1,
                    'gg0130': {}, 'gg0170': {}}),
    ('/api/compare', {'code_a': 'A000', 'code_b': 'E1165'}),
]

GATED_GET_ROUTES = ['/api/offline-data']


@pytest.mark.parametrize('route,body', GATED_POST_ROUTES)
def test_gated_post_routes_reject_without_lead_capture(anon_client, route, body):
    resp = anon_client.post(route, json=body)
    assert resp.status_code == 403, route
    assert 'error' in resp.get_json()


@pytest.mark.parametrize('route', GATED_GET_ROUTES)
def test_gated_get_routes_reject_without_lead_capture(anon_client, route):
    resp = anon_client.get(route)
    assert resp.status_code == 403, route


@pytest.mark.parametrize('route,body', GATED_POST_ROUTES)
def test_gated_routes_pass_once_lead_is_captured(client, route, body):
    """The same requests must get past the gate for a captured lead.

    Asserts only that the gate opened -- the handler's own behaviour is covered
    by that endpoint's tests.
    """
    resp = client.post(route, json=body)
    assert resp.status_code != 403, route


def test_ungated_routes_need_no_lead_capture(anon_client):
    """Health and version must stay reachable for uptime checks."""
    assert anon_client.get('/healthz').status_code == 200
    assert anon_client.get('/version').status_code == 200
