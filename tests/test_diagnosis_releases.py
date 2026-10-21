"""Release boundaries, verified contents, and one-date propagation."""
from datetime import date
import hashlib
import json

import pytest

from services.pdgm import datasets


@pytest.mark.parametrize('day,version,count', [
    ('2026-01-01', '07.0.26', 74719),
    ('2026-03-31', '07.0.26', 74719),
    ('2026-04-01', '07.1.26', 74719),
    ('2026-09-30', '07.1.26', 74719),
    ('2026-10-01', '07.2.26', 74879),
    ('2026-12-31', '07.2.26', 74879),
])
def test_verified_release_boundaries(day, version, count):
    rows = datasets.load_release(day)
    metadata = datasets.diagnosis_metadata(day)
    assert metadata['grouper_version'] == version
    assert metadata['service_date'] == day
    assert len(rows) == count == metadata['row_count']
    _, release = datasets.select_release(day)
    canonical = json.dumps([rows[c] for c in sorted(rows)], sort_keys=True,
                           separators=(',', ':'), ensure_ascii=True).encode()
    assert hashlib.sha256(canonical).hexdigest() == release['canonical_sha256']


@pytest.mark.parametrize('day', ['2025-12-31', '2027-01-01', '2026-02-30',
                                '20261001', 'nonsense', True, 20261001])
def test_unsupported_or_invalid_dates_fail_without_using_latest(day):
    with pytest.raises(datasets.DiagnosisDateError):
        datasets.load_release(day)


def test_april_change_is_not_applied_to_january():
    january = datasets.load_release('2026-03-31')['H40841']
    april = datasets.load_release('2026-04-01')['H40841']
    assert (january['pdgm_clinical_group_code'], january['UNACCEPTABLE_PDX']) == ('NA', '1')
    assert (april['pdgm_clinical_group_code'], april['UNACCEPTABLE_PDX']) == ('A', '0')


def test_october_additions_and_deletions_are_date_specific():
    september = datasets.load_release('2026-09-30')
    october = datasets.load_release('2026-10-01')
    assert len(october.keys() - september.keys()) == 190
    assert len(september.keys() - october.keys()) == 30
    assert 'D691' in september and 'D691' not in october
    assert 'D6911' not in september and 'D6911' in october


def test_checksum_failure_does_not_serve_an_overlay(tmp_path, monkeypatch):
    # Keep the verified manifest/baseline, corrupt only the staged overlay.
    datasets.manifest()
    (tmp_path / '07.2.26.csv').write_text('wrong data')
    monkeypatch.setattr(datasets, 'DATA_DIR', tmp_path)
    with pytest.raises(datasets.DiagnosisDataError, match='checksum mismatch'):
        datasets._load_version.__wrapped__('07.2.26')


def test_default_mapping_rolls_over_without_restarting_process(monkeypatch):
    from services.pdgm.impl import _get_map
    monkeypatch.setattr(datasets, 'today', lambda: date(2026, 9, 30))
    assert 'D691' in _get_map() and 'D6911' not in _get_map()
    monkeypatch.setattr(datasets, 'today', lambda: date(2026, 10, 1))
    assert 'D691' not in _get_map() and 'D6911' in _get_map()


@pytest.mark.parametrize('day,code,allowed', [
    ('2026-09-30', 'D691', True), ('2026-10-01', 'D691', False),
    ('2026-09-30', 'D6911', False), ('2026-10-01', 'D6911', True),
    ('2026-03-31', 'H40841', False), ('2026-04-01', 'H40841', True),
])
def test_lookup_and_hipps_agree_across_release_boundaries(client, monkeypatch, day, code, allowed):
    from services.pdgm import rules_engine

    def unexpected_fallback(*args, **kwargs):
        pytest.fail('An unavailable exact code was silently replaced')

    monkeypatch.setattr(rules_engine, 'search_icd10', unexpected_fallback)
    monkeypatch.setattr(rules_engine, 'map_phrase_to_code', unexpected_fallback)
    lookup = client.post('/api/lookup', json={'query': code, 'service_date': day}).get_json()
    response = client.post('/api/hipps', json={'primary_icd10': code, 'service_date': day})
    hipps = response.get_json()
    assert lookup['diagnosis_data'] == hipps['diagnosis_data']
    assert lookup['primary_eligibility']['eligible'] is allowed
    assert lookup['flags'] == hipps['flags']
    assert response.status_code == (200 if allowed else 400)


@pytest.mark.parametrize('endpoint,payload', [
    ('/api/lookup', {'query': 'E1165'}),
    ('/api/hipps', {'primary_icd10': 'E1165'}),
    ('/api/compare', {'code_a': 'E1165', 'code_b': 'I10'}),
    ('/api/comorbidity-check', {'primary_icd10': 'E1165', 'secondary_icd10s': []}),
])
def test_unsupported_date_rejected_by_each_diagnosis_api(client, endpoint, payload):
    response = client.post(endpoint, json={**payload, 'service_date': '2027-01-01'})
    assert response.status_code == 400
    assert 'Supported dates' in response.get_json()['error']


def test_secondary_diagnoses_use_same_release_as_primary(client):
    body = {'primary_icd10': 'E1165', 'secondary_icd10s': ['D6911']}
    for endpoint in ['/api/hipps', '/api/comorbidity-check']:
        assert client.post(endpoint, json={**body, 'service_date': '2026-09-30'}).status_code == 400
        response = client.post(endpoint, json={**body, 'service_date': '2026-10-01'})
        assert response.status_code == 200
        assert response.get_json()['diagnosis_data']['grouper_version'] == '07.2.26'


def test_suggestions_and_comparison_do_not_use_another_release(client):
    before = client.get('/api/suggest?q=D691&service_date=2026-09-30').get_json()
    after = client.get('/api/suggest?q=D691&service_date=2026-10-01').get_json()
    assert {r['code'] for r in before['suggestions']} == {'D69.1'}
    assert {r['code'] for r in after['suggestions']} == {'D69.11', 'D69.19'}
    comparison = client.post('/api/compare', json={
        'code_a': 'D691', 'code_b': 'D6911', 'service_date': '2026-09-30',
    }).get_json()
    assert comparison['a']['raw']['icd10_code'] == 'D691'
    assert comparison['b']['raw'] == {}
    assert comparison['diagnosis_data']['grouper_version'] == '07.1.26'


def test_offline_export_identifies_and_limits_its_release(client):
    result = client.get('/api/offline-data?service_date=2026-10-01').get_json()
    assert result['diagnosis_data']['grouper_version'] == '07.2.26'
    assert 'D6911' in result['data'] and 'D691' not in result['data']
    assert client.get('/api/offline-data?service_date=2027-01-01').status_code == 400


def test_legacy_lookup_caches_are_separated_by_date(client, app, monkeypatch):
    from flask import template_rendered
    import blueprints.main.routes as routes
    monkeypatch.setattr(routes, 'ai_followup_question', lambda _: '')
    contexts = []

    def capture(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(capture, app):
        before = client.post('/', data={'query': 'H40841', 'service_date': '2026-03-31'})
        after = client.post('/', data={'query': 'H40841', 'service_date': '2026-04-01'})
    assert before.status_code == after.status_code == 200
    assert 'Unacceptable PDx: Yes' in contexts[-2]['result']['Text']
    assert 'Unacceptable PDx: Yes' not in contexts[-1]['result']['Text']
    assert contexts[-2]['diagnosis_data']['grouper_version'] == '07.0.26'
    assert contexts[-1]['diagnosis_data']['grouper_version'] == '07.1.26'


def test_ai_candidates_and_validation_use_the_selected_release(monkeypatch, tmp_path):
    import app as core
    captured = []

    def fake_candidates(phrase, mapping, limit):
        captured.append(mapping)
        return [mapping['D691'] if 'D691' in mapping else mapping['D6911']]

    monkeypatch.setattr(core, 'get_candidate_codes_enhanced', fake_candidates)
    core.get_candidate_codes('platelet defect', service_date='2026-09-30')
    core.get_candidate_codes('platelet defect', service_date='2026-10-01')
    assert 'D691' in captured[0] and 'D6911' not in captured[0]
    assert 'D691' not in captured[1] and 'D6911' in captured[1]
    assert core.validate_ai_output('D69.11', '2026-09-30')[0] is False
    assert core.validate_ai_output('D69.11', '2026-10-01')[0] is True


def test_page_labels_date_as_claim_from_date(client):
    response = client.get('/?service_date=2026-04-01')
    assert response.status_code == 200
    assert b'Claim From date' in response.data
    assert b'value="2026-04-01"' in response.data


def test_comorbidity_check_does_not_report_no_adjustment_when_data_verification_fails(client, monkeypatch):
    from services.pdgm import repository

    def corrupted_data(*args, **kwargs):
        raise datasets.DiagnosisDataError('checksum mismatch')

    monkeypatch.setattr(repository, 'get_icd10_map', corrupted_data)
    response = client.post('/api/comorbidity-check', json={'primary_icd10': 'E1165'})
    assert response.status_code == 500
    assert response.get_json() == {'error': 'Diagnosis data verification failed'}
