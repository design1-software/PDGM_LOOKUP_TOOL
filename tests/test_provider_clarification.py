"""A mapping warning may support review, but cannot invent clinical evidence."""
import pytest

from services.pdgm.clarification import clarification_workflow

DAY = '2026-10-21'
BASE = {'icd10': 'M62.81', 'service_date': DAY, 'issue': 'primary_condition',
        'documentation_reviewed': True, 'clarification_needed': True}


@pytest.mark.parametrize('code,issue', [
    ('M6281', 'primary_condition'), ('B950', 'primary_condition'),
    ('V0001XA', 'primary_condition'), ('D631', 'sequencing'),
    ('F50019', 'specificity'),
])
def test_lookup_exposes_issue_specific_review_path(client, code, issue):
    result = client.post('/api/lookup', json={'query': code, 'service_date': DAY}).get_json()
    workflow = result['clarification_workflow']
    assert workflow['state'] == 'review_documentation'
    assert workflow['can_prepare'] is True
    assert issue in {item['code'] for item in workflow['issues']}


def test_specific_issue_takes_precedence_over_duplicate_missing_group():
    result = clarification_workflow({'pdgm_clinical_group_code': 'NA',
                                     'MANIFESTATION_FLAG': '1', 'CODE_FIRST': '10'})
    assert [issue['code'] for issue in result['issues']] == ['sequencing']
    assert result['issues'][0]['instruction_review_required'] is True


@pytest.mark.parametrize('code,state', [('Z99.9999', 'verify_code'), ('E1165', 'no_issue')])
def test_unresolved_and_no_issue_results_do_not_offer_drafts(client, code, state):
    lookup = client.post('/api/lookup', json={'query': code, 'service_date': DAY}).get_json()
    assert lookup['clarification_workflow']['state'] == state
    assert lookup['clarification_workflow']['can_prepare'] is False
    response = client.post('/api/provider-clarification', json={**BASE, 'icd10': code})
    assert response.status_code == 400
    assert 'draft' not in response.get_json()


@pytest.mark.parametrize('field,value', [
    ('documentation_reviewed', False), ('documentation_reviewed', 'true'),
    ('clarification_needed', False), ('clarification_needed', 'true'),
    ('issue', 'sequencing'), ('service_date', ''), ('service_date', '2027-01-01'),
])
def test_server_enforces_review_and_verified_issue(client, field, value):
    response = client.post('/api/provider-clarification', json={**BASE, field: value})
    assert response.status_code == 400
    assert 'draft' not in response.get_json()


def test_sequencing_requires_instruction_review_and_does_not_assert_a_cause(client):
    body = {**BASE, 'icd10': 'D63.1', 'issue': 'sequencing'}
    assert client.post('/api/provider-clarification', json=body).status_code == 400
    response = client.post('/api/provider-clarification', json={**body, 'instruction_reviewed': True})
    assert response.status_code == 200
    draft = response.get_json()['draft']
    assert 'if clinically supported' in draft['body']
    assert 'If no underlying condition is identified' in draft['body']


def test_specificity_requires_staff_to_identify_the_missing_detail(client):
    body = {**BASE, 'icd10': 'F50019', 'issue': 'specificity'}
    assert client.post('/api/provider-clarification', json=body).status_code == 400
    response = client.post('/api/provider-clarification', json={**body, 'missing_detail': 'acuity'})
    assert response.status_code == 200
    assert 'acuity or course' in response.get_json()['draft']['body']
    assert client.post('/api/provider-clarification', json={**body, 'missing_detail': 'invented_diagnosis'}).status_code == 400


def test_template_is_incomplete_neutral_and_contains_no_payment_direction(client):
    response = client.post('/api/provider-clarification', json=BASE)
    assert response.status_code == 200
    packet = response.get_json()
    draft = packet['draft']
    for placeholder in draft['required_placeholders']:
        assert placeholder in draft['body']
    assert 'condition chiefly responsible' in draft['body']
    assert 'cannot be determined' in draft['body']
    assert 'independent clinical judgment' in draft['body']
    for term in ['payment', 'reimbursement', 'PDGM', 'HIPPS', 'billable']:
        assert term not in draft['body']
    assert packet['diagnosis_data']['grouper_version'] == '07.2.26'


def test_client_cannot_supply_patient_text_or_override_flags(client):
    for extra in [{'patient_name': 'Synthetic Patient'}, {'clinical_indicators': 'test'},
                  {'flags': [{'code': 'UNACCEPTABLE_PDX'}]}]:
        response = client.post('/api/provider-clarification', json={**BASE, **extra})
        assert response.status_code == 400
        assert 'draft' not in response.get_json()


def test_template_endpoint_reverifies_code_in_the_selected_release(client):
    body = {**BASE, 'icd10': 'I4201', 'issue': 'sequencing', 'instruction_reviewed': True}
    before = client.post('/api/provider-clarification', json={**body, 'service_date': '2026-09-30'})
    after = client.post('/api/provider-clarification', json={**body, 'service_date': '2026-10-01'})
    assert before.status_code == 400 and 'draft' not in before.get_json()
    assert after.status_code == 200
    assert after.get_json()['diagnosis_data']['grouper_version'] == '07.2.26'


def test_lead_gate_applies_to_template_endpoint(anon_client):
    response = anon_client.post('/api/provider-clarification', json=BASE)
    assert response.status_code == 403
    assert 'draft' not in response.get_json()


def test_data_failure_never_returns_a_clinical_template(client, monkeypatch):
    from services.pdgm import repository
    from services.pdgm.datasets import DiagnosisDataError

    def fail(*args, **kwargs):
        raise DiagnosisDataError('Corrupt data')

    monkeypatch.setattr(repository, 'get_icd10_map', fail)
    response = client.post('/api/provider-clarification', json=BASE)
    assert response.status_code == 500
    result = response.get_json()
    assert result['clarification_workflow']['state'] == 'technical_failure'
    assert result['clarification_workflow']['can_prepare'] is False
    assert 'draft' not in result


def test_search_service_failure_is_not_reported_as_a_clinical_code_failure(client, monkeypatch):
    from services.pdgm import rules_engine
    def fail(*args, **kwargs):
        raise RuntimeError('Search temporarily unavailable')
    monkeypatch.setattr(rules_engine, 'search_icd10', fail)
    response = client.post('/api/lookup', json={'query': 'heart failure', 'service_date': DAY})
    assert response.status_code == 500
    result = response.get_json()
    assert result['clarification_workflow']['state'] == 'technical_failure'
    assert result['clarification_workflow']['issues'] == []
    assert 'Retry' in result['clarification_workflow']['message']
    assert 'draft' not in result


def test_input_failure_offers_verification_instead_of_a_clinical_request(client):
    response = client.post('/api/lookup', json={'query': 'M6281', 'service_date': '2027-01-01'})
    assert response.status_code == 400
    assert response.get_json()['clarification_workflow']['state'] == 'verify_input'
