"""Search offers dated choices and cannot silently assign a diagnosis."""
import pytest
from services.pdgm.impl import search_icd10_codes
from services.pdgm.search import search_rows


@pytest.mark.parametrize('phrase,description', [
    ('high blood pressure', 'hypertension'), ('CHF', 'heart failure'),
    ('AFIB', 'atrial fibrillation'), ('COPD', 'chronic obstructive pulmonary disease'),
    ('diabetes type 2 hyperglycemia', 'hyperglycemia'),
    ('lower back pain', 'low back pain'), ('GERD', 'reflux'),
    ('DM2', 'type 2 diabetes'),
])
def test_common_terms_return_options_from_verified_data(phrase, description):
    matches = search_icd10_codes(phrase, service_date='2026-10-21')
    assert matches
    assert all(description in item['description'].lower() for item in matches)


def test_ranking_is_deterministic_and_preserves_requested_details():
    rows = {'A001': {'description': 'Pain in right knee'},
            'A002': {'description': 'Pain in left knee'},
            'A003': {'description': 'Other pain in right knee'}}
    assert [r['code'] for r in search_rows('right knee pain', rows)] == ['A00.1', 'A00.3']
    assert search_rows('right knee pain', rows, limit=1)[0]['code'] == 'A00.1'
    assert search_rows('', rows) == []
    assert search_rows('knee', rows, limit=0) == []
    assert search_rows('kidney pain', rows) == []
    assert search_rows('pain without injury', {'A00': {'description': 'Pain with injury'}}) == []


def test_phrase_requires_choice_even_for_a_single_match(client, monkeypatch):
    import app as core
    monkeypatch.setattr(core, 'ai_map_phrase_to_code', lambda *a, **k: pytest.fail('Search called AI'))
    result = client.post('/api/lookup', json={'query': 'essential primary hypertension',
                         'service_date': '2026-10-21', 'area_code': '10180'}).get_json()
    assert result['selection_required'] is True
    assert result['candidates'] == [{'code': 'I10', 'description': 'Essential (primary) hypertension'}]
    assert result['diagnosis_data']['grouper_version'] == '07.2.26'
    for key in ['raw', 'icd10', 'primary_eligibility', 'flags', 'clarification_workflow', 'payment_range']:
        assert key not in result
    selected = client.post('/api/lookup', json={'query': result['candidates'][0]['code'],
                           'service_date': result['diagnosis_data']['service_date']}).get_json()
    assert selected['raw']['icd10_code'] == 'I10'
    assert selected['primary_eligibility']['eligible'] is True


def test_no_match_is_a_search_outcome_not_a_clinical_rejection(client):
    result = client.post('/api/lookup', json={'query': 'zzzzzzzzzzzz'}).get_json()
    assert result['selection_required'] is True
    assert result['candidates'] == []
    assert 'clarification_workflow' not in result
    assert 'primary_eligibility' not in result


def test_short_abbreviation_and_dated_autocomplete(client):
    assert client.get('/api/suggest?q=DM').get_json()['suggestions']
    for day, expected, absent in [('2026-09-30', 'D69.1', 'D69.11'),
                                 ('2026-10-01', 'D69.11', 'D69.1')]:
        result = client.get('/api/suggest', query_string={'q': 'D691', 'service_date': day}).get_json()
        codes = {r['code'] for r in result['suggestions']}
        assert expected in codes and absent not in codes
        assert result['diagnosis_data']['service_date'] == day
    assert client.get('/api/suggest', query_string={'q': 'x' * 501}).status_code == 400


def test_choice_list_keeps_codes_requiring_primary_review(client):
    result = client.post('/api/lookup', json={'query': 'muscle weakness generalized'}).get_json()
    assert any(c['code'] == 'M62.81' for c in result['candidates'])
    selected = client.post('/api/lookup', json={'query': 'M62.81'}).get_json()
    assert selected['primary_eligibility']['eligible'] is False
    assert 'NO_CLINICAL_GROUP' in {f['code'] for f in selected['flags']}


def test_legacy_form_also_requires_selection(client, monkeypatch):
    import blueprints.main.routes as routes
    monkeypatch.setattr(routes, 'get_cached_ai_response', lambda *a, **k: pytest.fail('Auto assigned'))
    response = client.post('/', data={'query': 'high blood pressure', 'service_date': '2026-10-21'})
    assert response.status_code == 200
    assert b'Choose a potential match' in response.data
    assert b'value="I10"' in response.data


def test_broad_search_exposes_multiple_families_instead_of_only_one_subtype():
    codes = {r['code'] for r in search_icd10_codes('diabetes', limit=25, service_date='2026-10-21')}
    assert any(code.startswith('E10.') for code in codes)
    assert any(code.startswith('E11.') for code in codes)
    assert 'I10' in {r['code'] for r in search_icd10_codes('high blood pressure', service_date='2026-10-21')}
    assert search_icd10_codes('heart failure', service_date='2026-10-21')[0]['code'] == 'I50.9'


def test_numbered_types_and_explicit_absence_do_not_match_a_different_condition():
    rows = {'E10A2': {'description': 'Type 1 diabetes mellitus, presymptomatic, Stage 2'},
            'E119': {'description': 'Type 2 diabetes mellitus without complications'},
            'I119': {'description': 'Hypertensive heart disease without heart failure'}}
    assert [r['code'] for r in search_rows('DM2', rows)] == ['E11.9']
    assert search_rows('CHF', rows) == []
