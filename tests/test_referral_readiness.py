"""Referral readiness check: rules, shared primary-diagnosis assessment, routes."""

from datetime import date

import pytest

from services.pdgm import referral_readiness as rr
from services.pdgm.eligibility import assess_primary_diagnosis
from services.pdgm.repository import get_icd10_map

TODAY = date(2026, 10, 27)
SOC = '2026-10-28'


def ready_referral(**overrides):
    data = {
        'diagnosis': 'Acute on chronic systolic heart failure',
        'icd10_code': 'I50.23',
        'event': 'hospital_discharge',
        'event_date': '2026-10-20',
        'soc_date': SOC,
        'f2f_date': '2026-10-19',
        'f2f_practitioner': 'physician',
        'f2f_related': 'yes',
        'homebound_c1': ['device'],
        'homebound_c2': ['normal_inability', 'taxing_effort'],
        'services': ['sn', 'pt'],
        'skilled_reason': 'Teach new diuretic and daily weights',
    }
    data.update(overrides)
    return data


def run(**overrides):
    return rr.evaluate(ready_referral(**overrides), today=TODAY)


def by_key(result):
    return {c['key']: c for c in result['checks']}


def test_red_flag_codes_fail_the_shared_primary_assessment():
    mapping = get_icd10_map(SOC)
    for flag in rr.RED_FLAG_DIAGNOSES:
        for code in flag['codes']:
            assessment = assess_primary_diagnosis(mapping.get(code))
            assert mapping.get(code), code
            assert not assessment['primary_eligibility']['eligible'], code


def test_complete_referral_is_green():
    result = run()
    assert result['overall'] == rr.GREEN
    assert result['asks'] == [] and result['message'] == ''
    assert result['diagnosis_data']['service_date'] == SOC


def test_diagnosis_check_agrees_with_lookup_assessment():
    mapping = get_icd10_map(SOC)
    for code in ['I5023', 'M6281', 'W19XXXA', 'R2689', 'E1165']:
        eligible = assess_primary_diagnosis(mapping[code])['primary_eligibility']['eligible']
        status = by_key(run(icd10_code=code))['diagnosis']['status']
        assert (status != rr.RED) == eligible, code


def test_symptom_code_is_red_with_cause_question():
    dx = by_key(run(icd10_code='M62.81'))['diagnosis']
    assert dx['status'] == rr.RED
    assert any('What condition caused the weakness' in a for a in dx['asks'])


def test_external_cause_code_asks_for_the_injury():
    dx = by_key(run(icd10_code='W19.XXXA'))['diagnosis']
    assert dx['status'] == rr.RED
    assert any('What injury or condition resulted' in a for a in dx['asks'])


def test_symptom_text_is_red_and_named_cause_is_yellow():
    assert by_key(run(diagnosis='generalized weakness', icd10_code=''))['diagnosis']['status'] == rr.RED
    assert by_key(run(diagnosis='weakness due to CHF exacerbation', icd10_code=''))['diagnosis']['status'] == rr.YELLOW


def test_text_without_code_is_never_green():
    assert by_key(run(diagnosis='needs help at home', icd10_code=''))['diagnosis']['status'] == rr.YELLOW


def test_unknown_code_is_yellow():
    assert by_key(run(icd10_code='ZZZ999'))['diagnosis']['status'] == rr.YELLOW


def test_soc_outside_verified_releases_is_yellow_not_an_error():
    result = run(soc_date='2031-01-05', f2f_date='2031-01-01', event_date='2031-01-01')
    dx = by_key(result)['diagnosis']
    assert dx['status'] == rr.YELLOW
    assert 'could not be checked' in dx['findings'][0]
    assert result['diagnosis_data'] is None


def test_no_event_is_red():
    assert by_key(run(event='none'))['event']['status'] == rr.RED


def test_institutional_within_14_days():
    assert any('institutional' in f for f in by_key(run())['event']['findings'])
    assert any('community' in f for f in by_key(run(event_date='2026-09-01'))['event']['findings'])


@pytest.mark.parametrize('f2f_date,status', [
    ('2026-07-30', rr.GREEN),   # 90 days before SOC
    ('2026-07-29', rr.RED),     # 91 days before
    ('2026-11-20', rr.YELLOW),  # 23 days after SOC: allowed, pending
    ('2026-11-28', rr.RED),     # 31 days after
])
def test_face_to_face_window(f2f_date, status):
    assert by_key(run(f2f_date=f2f_date))['f2f']['status'] == status


def test_face_to_face_unrelated_is_red():
    assert by_key(run(f2f_related='no'))['f2f']['status'] == rr.RED


def test_homebound_is_informational_and_never_blocks():
    for overrides in ({'homebound_c1': [], 'homebound_c2': []},
                      {'homebound_c2': ['taxing_effort']},
                      {'homebound_notes': 'elderly, lives alone'}):
        result = run(**overrides)
        homebound = by_key(result)['homebound']
        assert homebound['status'] == rr.INFO
        assert homebound['asks'] == []
        assert result['overall'] == rr.GREEN
        assert any('start-of-care visit' in f for f in homebound['findings'])


def test_weak_homebound_reason_is_still_taught():
    findings = by_key(run(homebound_notes='elderly, lives alone'))['homebound']['findings']
    assert any('do not make a patient homebound' in f for f in findings)


@pytest.mark.parametrize('services,status', [
    (['ot'], rr.RED),
    (['aide', 'msw'], rr.RED),
    (['slp'], rr.GREEN),
    ([], rr.RED),
])
def test_skilled_need(services, status):
    assert by_key(run(services=services))['skilled']['status'] == status


def test_message_lists_every_ask():
    result = run(diagnosis='unsteady gait', icd10_code='', services=['ot'])
    assert result['overall'] == rr.RED
    for ask in result['asks']:
        assert ask in result['message']


def test_summary_has_every_check_and_the_message():
    result = run(diagnosis='unsteady gait', icd10_code='')
    summary = result['summary']
    assert result['overall_label'] in summary
    for check in result['checks']:
        assert check['title'] in summary
    assert '[AT SOC VISIT] Homebound status' in summary
    assert result['message'] in summary


def test_page_works_without_lead_capture(anon_client):
    response = anon_client.get('/referral-check')
    assert response.status_code == 200
    assert b'Referral Readiness Check' in response.data

    response = anon_client.post('/referral-check', data={
        'diagnosis': 'weakness', 'event': 'none', 'services': ['ot'],
    })
    assert response.status_code == 200
    assert b'Message for the referral source' in response.data


def test_api(anon_client):
    response = anon_client.post('/api/referral-check', json=ready_referral())
    assert response.status_code == 200
    assert response.get_json()['checks'][0]['key'] == 'diagnosis'
    assert anon_client.post('/api/referral-check', data='x').status_code == 400


def test_index_links_to_the_check(client):
    response = client.get('/')
    assert b'/referral-check' in response.data
