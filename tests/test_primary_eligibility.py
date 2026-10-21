"""Lookup and HIPPS must agree on primary-diagnosis restrictions."""

import pytest

from services.pdgm.eligibility import assess_primary_diagnosis


@pytest.mark.parametrize('code,blocking_code', [
    ('B950', 'UNACCEPTABLE_PDX'),
    ('D631', 'MANIFESTATION'),
    ('V0001XA', 'ECOI'),
    ('F50019', 'NO_CLINICAL_GROUP'),
    ('M6281', 'NO_CLINICAL_GROUP'),
])
def test_real_codes_have_matching_lookup_and_hipps_restrictions(client, code, blocking_code):
    lookup = client.post('/api/lookup', json={'query': code, 'area_code': '30780'})
    hipps = client.post('/api/hipps', json={'primary_icd10': code, 'area_code': '30780'})
    assert lookup.status_code == 200  # Keep the description and reasons visible.
    assert hipps.status_code == 400
    found, rejected = lookup.get_json(), hipps.get_json()
    assert found['primary_eligibility'] == rejected['primary_eligibility']
    assert found['flags'] == rejected['flags']
    assert blocking_code in rejected['primary_eligibility']['blocking_codes']
    assert rejected['primary_eligibility']['eligible'] is False
    assert 'hipps_code' not in rejected
    assert 'payment' not in rejected
    assert 'payment_range' not in found
    assert rejected['error']


@pytest.mark.parametrize('field,blocking_code', [
    ('UNACCEPTABLE_PDX', 'UNACCEPTABLE_PDX'),
    ('MANIFESTATION_FLAG', 'MANIFESTATION'),
    ('ECOI_FLAG', 'ECOI'),
])
def test_flags_block_hipps_even_if_a_clinical_group_exists(client, monkeypatch, field, blocking_code):
    from services.pdgm import impl, hipps

    # Isolate each restriction from the separate missing-group check.
    mapping = impl._get_map()
    row = dict(mapping['E1165'], **{field: '1'})
    monkeypatch.setattr(impl, '_icd10_map', {'E1165': row})

    def unexpected_calculation(**kwargs):
        pytest.fail('A blocked primary diagnosis reached HIPPS generation')

    monkeypatch.setattr(hipps, 'generate_hipps_code', unexpected_calculation)
    lookup = client.post('/api/lookup', json={'query': 'E11.65'}).get_json()
    response = client.post('/api/hipps', json={'primary_icd10': 'E1165'})
    assert response.status_code == 400
    rejected = response.get_json()
    assert rejected['flags'] == lookup['flags']
    assert rejected['primary_eligibility']['blocking_codes'] == [blocking_code]


def test_unspecified_warning_alone_does_not_block_a_mapped_code(client, monkeypatch):
    from services.pdgm import impl

    row = dict(impl._get_map()['E1165'], UNSPECIFIED_PDX='1')
    monkeypatch.setattr(impl, '_icd10_map', {'E1165': row})
    lookup = client.post('/api/lookup', json={'query': 'E1165'}).get_json()
    response = client.post('/api/hipps', json={'primary_icd10': 'E11.65'})
    assert response.status_code == 200
    calculated = response.get_json()
    assert calculated['primary_eligibility'] == lookup['primary_eligibility']
    assert calculated['primary_eligibility']['eligible'] is True
    assert calculated['flags'] == lookup['flags']
    assert calculated['flags'][0]['type'] == 'warning'
    assert calculated['hipps_code']


def test_valid_code_keeps_existing_hipps_and_payment(client):
    lookup = client.post('/api/lookup', json={'query': 'E11.65'}).get_json()
    response = client.post('/api/hipps', json={
        'primary_icd10': 'E1165', 'area_code': '30780',
        'gg0130': {'GG0130A': 1}, 'gg0170': {'GG0170A': 1},
    })
    assert response.status_code == 200
    calculated = response.get_json()
    assert calculated['primary_eligibility'] == lookup['primary_eligibility']
    assert calculated['primary_eligibility'] == {'eligible': True, 'blocking_codes': []}
    assert calculated['flags'] == lookup['flags'] == []
    assert calculated['hipps_code'] == '1IC11'
    assert calculated['payment']['estimated_payment'] > 0


def test_unknown_code_is_not_eligible_in_either_workflow(client, monkeypatch):
    from services.pdgm import rules_engine

    monkeypatch.setattr(rules_engine, 'map_phrase_to_code', lambda _: None)
    lookup = client.post('/api/lookup', json={'query': 'ZZZZZ'}).get_json()
    response = client.post('/api/hipps', json={'primary_icd10': 'ZZZZZ'})
    assert response.status_code == 400
    rejected = response.get_json()
    assert lookup['primary_eligibility'] == rejected['primary_eligibility']
    assert lookup['flags'] == rejected['flags']
    assert rejected['primary_eligibility']['blocking_codes'] == ['CODE_NOT_FOUND']


@pytest.mark.parametrize('group', ['', 'NA', 'Z', None])
def test_unassigned_or_unknown_group_blocks_primary(group):
    assessment = assess_primary_diagnosis({'pdgm_clinical_group_code': group})
    assert assessment['primary_eligibility']['blocking_codes'] == ['NO_CLINICAL_GROUP']


def test_primary_awarding_flag_is_not_a_restriction():
    assessment = assess_primary_diagnosis({
        'pdgm_clinical_group_code': 'I', 'PRIMARY_AWARDING_FLAG': '0',
    })
    assert assessment['primary_eligibility']['eligible'] is True


@pytest.mark.parametrize('code', ['B950', 'D631', 'V0001XA', 'M6281'])
def test_legacy_direct_lookup_uses_shared_reasons_without_payment(client, app, monkeypatch, code):
    from flask import template_rendered
    from services.pdgm.repository import get_icd10_map
    import blueprints.main.routes as routes

    monkeypatch.setattr(routes, 'ai_followup_question', lambda _: '')
    contexts = []

    def capture(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(capture, app):
        response = client.post('/', data={'query': code, 'area_code': '30780'})

    assert response.status_code == 200
    text = contexts[-1]['result']['Text']
    assessment = assess_primary_diagnosis(get_icd10_map()[code])
    for flag in assessment['flags']:
        assert flag['message'] in text
    assert '$' not in text
