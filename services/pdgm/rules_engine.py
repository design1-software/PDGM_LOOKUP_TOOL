"""PDGM rules engine — lookup orchestration."""

import re
from typing import Any, Dict
from .repository import normalize_icd10, get_icd10_map, search_icd10, map_phrase_to_code
from .impl import parse_pdgm_details, format_icd10


def explain_pdgm_for_icd10(code: str, service_date=None) -> Dict[str, Any]:
    norm = normalize_icd10(code)
    mapping = get_icd10_map(service_date).get(norm, {})
    details = parse_pdgm_details(mapping)
    return {'icd10': format_icd10(norm), 'raw': mapping, 'details': details}


def lookup_pdgm(query: str, service_date=None) -> Dict[str, Any]:
    # A code unavailable for this date must not become a different code through
    # prefix search or AI. This matters at release additions/deletions.
    normalized = normalize_icd10(query)
    if re.fullmatch(r'[A-Z][0-9][0-9A-Z]{1,5}', normalized):
        return explain_pdgm_for_icd10(normalized, service_date)

    # A phrase is a search, not authorization to assign its first match.
    return {'selection_required': True, 'query': query,
            'candidates': search_icd10(query, limit=25, service_date=service_date)}
