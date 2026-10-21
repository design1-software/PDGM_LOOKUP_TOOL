"""Actionable guidance must reflect mapping evidence without inventing a diagnosis."""

import pytest

from services.pdgm.eligibility import assess_primary_diagnosis


@pytest.mark.parametrize('value', ['1', '10', '110', 166])
def test_nonzero_code_first_entries_trigger_review_without_blanket_rejection(value):
    result = assess_primary_diagnosis({'pdgm_clinical_group_code': 'C', 'CODE_FIRST': value})
    assert result['primary_eligibility']['eligible'] is True
    assert result['primary_eligibility']['blocking_codes'] == []
    flag = result['flags'][0]
    assert flag['code'] == 'CODE_FIRST'
    assert flag['type'] == 'warning'
    assert 'alone does not prohibit primary use' in flag['explanation']
    assert 'If the instruction applies' in flag['next_step']


@pytest.mark.parametrize('value', ['0', 0, '', None])
def test_empty_or_zero_code_first_does_not_create_a_sequencing_warning(value):
    result = assess_primary_diagnosis({'pdgm_clinical_group_code': 'I', 'CODE_FIRST': value})
    assert result['flags'] == []


@pytest.mark.parametrize('code,flag_code', [
    ('D631', 'CODE_FIRST'),
    ('A400', 'CODE_FIRST'),
    ('L89153', 'CODE_FIRST'),
    ('M6281', 'NO_CLINICAL_GROUP'),
    ('B950', 'UNACCEPTABLE_PDX'),
    ('V0001XA', 'ECOI'),
    ('F50019', 'UNSPECIFIED_PDX'),
])
def test_lookup_and_hipps_share_actionable_guidance(client, code, flag_code):
    lookup = client.post('/api/lookup', json={'query': code}).get_json()
    response = client.post('/api/hipps', json={'primary_icd10': code})
    hipps = response.get_json()
    assert lookup['flags'] == hipps['flags']
    assert flag_code in {flag['code'] for flag in lookup['flags']}
    for flag in lookup['flags']:
        assert flag['explanation']
        assert flag['next_step']
    assert response.status_code == (200 if lookup['primary_eligibility']['eligible'] else 400)


def test_unresolved_lookup_guidance_does_not_call_the_code_invalid(client, monkeypatch):
    from services.pdgm import rules_engine

    monkeypatch.setattr(rules_engine, 'map_phrase_to_code', lambda _: None)
    lookup = client.post('/api/lookup', json={'query': 'ZZZZZ'}).get_json()
    rejected = client.post('/api/hipps', json={'primary_icd10': 'ZZZZZ'}).get_json()
    flag = lookup['flags'][0]
    assert lookup['flags'] == rejected['flags']
    assert flag['code'] == 'CODE_NOT_FOUND'
    assert 'does not establish' in flag['explanation']
    assert 'Do not substitute an unconfirmed diagnosis' in flag['next_step']
    assert 'payment_range' not in lookup


def test_missing_group_guidance_does_not_invent_an_underlying_cause():
    flag = assess_primary_diagnosis({'pdgm_clinical_group_code': 'NA'})['flags'][0]
    assert flag['code'] == 'NO_CLINICAL_GROUP'
    assert 'code itself is invalid' in flag['explanation']
    assert 'service date' in flag['next_step']
    assert 'do not choose a replacement solely for payment' in flag['next_step']


def test_legacy_direct_lookup_includes_sequencing_explanation_and_action(client, app, monkeypatch):
    from flask import template_rendered
    import blueprints.main.routes as routes

    monkeypatch.setattr(routes, 'ai_followup_question', lambda _: '')
    contexts = []

    def capture(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(capture, app):
        response = client.post('/', data={'query': 'D631'})
    assert response.status_code == 200
    text = contexts[-1]['result']['Text']
    assert 'Code First: Review sequencing instructions below' in text
    assert 'What this means:' in text
    assert 'Next step:' in text
    assert 'Code First: 10' not in text
