"""Comorbidity adjustment follows the CY 2026 CMS low/high file."""

import csv
from pathlib import Path

import pytest

from services.pdgm import comorbidity

ROOT = Path(__file__).resolve().parents[1]


def test_cms_file_parses_completely():
    rules = comorbidity.load_rules()
    assert len(rules['low']) == 20
    assert len(rules['pairs']) == 98
    assert 'Heart_11' in rules['low']
    assert not any(d.startswith('=') for d in rules['descriptions'].values())


def test_every_cms_subgroup_exists_in_the_mapping():
    with open(ROOT / 'CCFTF_pdgm_diagnosis_mapping.csv', encoding='utf-8') as fh:
        mapped = {row['COMORBIDITY_GROUP'] for row in csv.DictReader(fh)}
    rules = comorbidity.load_rules()
    named = rules['low'] | {s for pair in rules['pairs'] for s in pair}
    assert named <= mapped


@pytest.mark.parametrize('secondaries,expected', [
    ([], 'None'),
    (['No_group'], 'None'),
    (['Heart_10'], 'Low'),                       # AFib: a single low subgroup
    (['Endocrine_3'], 'None'),                   # diabetes: interaction pairs only
    (['Heart_10', 'Skin_4'], 'High'),            # CMS interaction 57
    (['Behavioral_2', 'Circulatory_10'], 'High'),  # CMS interaction 1
    (['Heart_10', 'Heart_11'], 'Low'),           # two low subgroups, no pair
    (['Heart_11', 'Neoplasm_6'], 'High'),        # mapping spells it Neoplasm_, CMS Neoplasms
    (['Heart_11', 'Neoplasms_6'], 'High'),
])
def test_adjustment(secondaries, expected):
    assert comorbidity.determine_comorbidity_adjustment('No_group', secondaries) == expected


def test_primary_subgroup_never_counts():
    # Previously a primary in Heart_11 plus one secondary could form a "pair".
    assert comorbidity.determine_comorbidity_adjustment('Skin_4', ['Heart_10']) == 'Low'
    assert comorbidity.determine_comorbidity_adjustment('Heart_11', []) == 'None'


def test_explanation_names_the_interaction():
    detail = comorbidity.explain_comorbidity_adjustment(['Heart_10', 'Skin_4', 'Endocrine_3'])
    assert detail['adjustment'] == 'High'
    assert {'interaction': 57, 'subgroups': ['Heart_10', 'Skin_4']} in detail['interactions']
    assert detail['low_subgroups'] == ['Heart_10', 'Skin_4']


def test_comorbidity_check_endpoint(client):
    response = client.post('/api/comorbidity-check', json={
        'primary_icd10': 'I5023', 'secondary_icd10s': ['I4891', 'L89154'],
    })
    body = response.get_json()
    assert response.status_code == 200
    assert body['adjustment'] == 'High'
    assert body['interactions'][0]['subgroups'] == ['Heart_10', 'Skin_4']


def test_hipps_uses_cms_comorbidity(client):
    response = client.post('/api/hipps', json={
        'primary_icd10': 'I5023', 'secondary_icd10s': ['I4891'],
    })
    body = response.get_json()
    assert response.status_code == 200, body
    assert body['comorbidity_adjustment'] == 'Low'
    assert body['hipps_code'][3] == '2'
    assert body['comorbidity_detail']['low_subgroups'] == ['Heart_10']
