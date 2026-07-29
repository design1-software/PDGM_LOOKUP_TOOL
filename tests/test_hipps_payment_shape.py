"""The /api/hipps payment contract.

Returning a half-populated error object as `payment` crashed the browser
client while it formatted fields that were absent, surfacing to users as
"HIPPS calculation failed". `payment` must be either complete or null.
"""

GG = {"GG0130A": 1, "GG0170A": 1}
BASE = {"primary_icd10": "E1165", "secondary_icd10s": [],
        "admission_source": 1, "episode_timing": 1,
        "gg0130": GG, "gg0170": GG}

RENDERED_FIELDS = ("estimated_payment", "national_base_rate", "wage_index",
                   "area_name", "lupa_threshold", "is_lupa", "disclaimer")


def _authed(client):
    with client.session_transaction() as s:
        s['lead_captured'] = True
    return client


def test_payment_complete_when_area_given(client):
    r = _authed(client).post('/api/hipps', json={**BASE, "area_code": "30780"})
    assert r.status_code == 200
    body = r.get_json()
    assert body['hipps_code'] == '1IC11'
    payment = body['payment']
    for field in RENDERED_FIELDS:
        assert payment.get(field) is not None, f"client renders {field}"


def test_payment_is_null_not_partial_without_area(client):
    body = _authed(client).post('/api/hipps', json=BASE).get_json()
    assert body['payment'] is None
    assert body['payment_note']
    # the code and its dimensions never depend on geography
    assert body['hipps_code'] == '1IC11'
    assert body['dimensions']['case_mix_weight'] > 0


def test_zip_without_area_explains_rather_than_failing(client):
    body = _authed(client).post(
        '/api/hipps', json={**BASE, "zip_code": "72019"}).get_json()
    assert body['payment'] is None
    assert 'CBSA' in body['payment_note']
    assert body['hipps_code'] == '1IC11'


def test_bad_area_code_does_not_return_partial_payment(client):
    body = _authed(client).post(
        '/api/hipps', json={**BASE, "area_code": "00000"}).get_json()
    assert body['payment'] is None
    assert body['payment_note']
