"""Referral wording maps to sensible, primary-eligible candidate codes."""

import pytest

from services.pdgm.eligibility import assess_primary_diagnosis
from services.pdgm.phrase_match import match_primary
from services.pdgm.repository import get_icd10_map


@pytest.fixture(scope='module')
def mapping():
    return get_icd10_map('2026-11-03')


@pytest.mark.parametrize('phrase,expected_first', [
    ('CHF exacerbation', 'I50.23'),
    ('CHF', 'I50.9'),
    ('COPD exacerbation', 'J44.1'),
    ('pneumonia', 'J18.9'),
    ('sepsis', 'A41.9'),
    ('UTI', 'N39.0'),
    ('stroke', 'I63.9'),
    ('s/p left TKA', 'Z47.1'),
    ('knee replacement', 'Z47.1'),
    ('pressure ulcer sacrum stage 3', 'L89.153'),
    ('cellulitis left leg', 'L03.116'),
    ('afib', 'I48.91'),
    ('hypertension', 'I10'),
    ('pulmonary hypertension', 'I27.20'),
    ('diabetes', 'E11.9'),
    ('type 2 diabetes', 'E11.9'),
    ('diabetes and a foot sore', 'E11.621'),
    ('diabetic with foot sore', 'E11.621'),
    ('diabetic foot ulcer', 'E11.621'),
    ('type 1 diabetes foot ulcer', 'E10.621'),
    ('pressure sore sacrum stage 3', 'L89.153'),
])
def test_first_choice(mapping, phrase, expected_first):
    choices = match_primary(phrase, mapping)
    assert choices, phrase
    assert choices[0]['code'] == expected_first, [c['code'] for c in choices]


@pytest.mark.parametrize('phrase,family', [
    ('left hip fracture', 'S72'),
    ('fall with hip fracture', 'S72'),
    ('CVA with left side weakness', 'I69'),
    ('diabetic foot ulcer', 'E1'),
    ('parkinsons', 'G20'),
    ("Alzheimer's", 'G30'),
])
def test_first_choice_family(mapping, phrase, family):
    choices = match_primary(phrase, mapping)
    assert choices and choices[0]['code'].startswith(family), [c['code'] for c in choices]


def test_injuries_prefer_the_aftercare_encounter(mapping):
    assert match_primary('left hip fracture', mapping)[0]['code'].endswith('D')


def test_every_choice_can_be_a_primary(mapping):
    for phrase in ['CHF', 'dementia', 'hip fracture', 'sepsis', 'diabetes']:
        for choice in match_primary(phrase, mapping):
            assert assess_primary_diagnosis(choice['row'])['primary_eligibility']['eligible']


def test_obstetric_and_newborn_codes_only_when_asked(mapping):
    for phrase in ['sepsis', 'UTI', 'wound infection']:
        assert not any(c['code'][0] in 'OP' for c in match_primary(phrase, mapping)), phrase


def test_symptoms_and_non_grouping_conditions_offer_nothing(mapping):
    for phrase in ['generalized weakness', 'unsteady gait', 'end stage renal disease', 'needs help at home']:
        assert match_primary(phrase, mapping) == [], phrase


def test_pressure_and_non_pressure_ulcers_stay_apart(mapping):
    for phrase in ['bed sore', 'pressure ulcer', 'pressure sore heel']:
        codes = [c['code'] for c in match_primary(phrase, mapping)]
        assert codes and all(c.startswith('L89') for c in codes), (phrase, codes)
    codes = [c['code'] for c in match_primary('non pressure ulcer right foot', mapping)]
    assert codes and all(c.startswith('L97') for c in codes), codes


def test_sore_throat_is_not_an_ulcer(mapping):
    assert match_primary('sore throat', mapping) == []
