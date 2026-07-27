"""Substantive coverage for /api/lookup.

The existing test only asserted a 200 and the absence of an "error" key -- and
even that never ran, because the lead-capture gate 403'd it. These assert what
the endpoint actually returns.
"""


def test_lookup_returns_the_pdgm_mapping_for_a_code(client):
    data = client.post('/api/lookup', json={'query': 'A000'}).get_json()
    raw = data['raw']
    # `icd10` is the display form; `raw.icd10_code` is the undotted CSV key.
    assert data['icd10'] == 'A00.0'
    assert raw['icd10_code'] == 'A000'
    assert raw['description'].startswith('Cholera')
    assert raw['pdgm_clinical_group_code'] == 'K'
    assert raw['pdgm_clinical_group_name'] == 'MMTA_INFECT'


def test_lookup_normalises_a_dotted_code(client):
    """E11.65 and E1165 must resolve to the same row."""
    dotted = client.post('/api/lookup', json={'query': 'E11.65'}).get_json()
    undotted = client.post('/api/lookup', json={'query': 'E1165'}).get_json()
    assert dotted['icd10'] == undotted['icd10'] == 'E11.65'
    assert dotted['raw']['icd10_code'] == undotted['raw']['icd10_code'] == 'E1165'
    assert dotted['raw']['pdgm_clinical_group_code'] == 'I'
    assert dotted['raw']['pdgm_clinical_group_name'] == 'MMTA_ENDO'


def test_lookup_flags_a_code_barred_as_principal_diagnosis(client):
    """B950 has UNACCEPTABLE_PDX=1 -- one of only 1,603 codes that do."""
    data = client.post('/api/lookup', json={'query': 'B950'}).get_json()
    assert data['raw']['UNACCEPTABLE_PDX'] == '1'
    codes = {f['code'] for f in data.get('flags') or []}
    assert 'UNACCEPTABLE_PDX' in codes


def test_lookup_does_not_flag_an_acceptable_principal_diagnosis(client):
    """E11.65 is valid as a principal diagnosis and must not be flagged as not."""
    data = client.post('/api/lookup', json={'query': 'E11.65'}).get_json()
    assert data['raw']['UNACCEPTABLE_PDX'] == '0'
    codes = {f['code'] for f in data.get('flags') or []}
    assert 'UNACCEPTABLE_PDX' not in codes


def test_lookup_rejects_an_empty_query(client):
    assert client.post('/api/lookup', json={'query': ''}).status_code == 400


def test_lookup_handles_an_unknown_code_without_erroring(client):
    resp = client.post('/api/lookup', json={'query': 'ZZZZZ'})
    assert resp.status_code == 200
    assert resp.get_json() is not None
