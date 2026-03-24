"""PDGM rules engine — lookup orchestration."""

from typing import Any, Dict
from .repository import normalize_icd10, get_icd10_map, search_icd10, map_phrase_to_code
from .impl import parse_pdgm_details, format_icd10


def explain_pdgm_for_icd10(code: str) -> Dict[str, Any]:
    norm = normalize_icd10(code)
    mapping = get_icd10_map().get(norm, {})
    details = parse_pdgm_details(mapping)
    return {'icd10': format_icd10(norm), 'raw': mapping, 'details': details}


def lookup_pdgm(query: str) -> Dict[str, Any]:
    # If it looks like a code, try direct map
    if any(ch.isdigit() for ch in query) or len(query) <= 8:
        info = explain_pdgm_for_icd10(query)
        if info.get('raw'):
            return info

    # Search known codes
    hits = search_icd10(query)
    if hits:
        code = hits[0].get('code') or hits[0].get('ICD10') or hits[0].get('icd10')
        if code:
            return explain_pdgm_for_icd10(code)

    # AI mapping fallback
    mapped = map_phrase_to_code(query)
    if mapped and isinstance(mapped, str):
        # The AI returns a text response, not a dict — extract code from it
        import re
        match = re.search(r'\b[A-TV-Z][0-9][0-9A-Z]{1,6}\b', mapped)
        if match:
            return explain_pdgm_for_icd10(match.group(0))
        return {'icd10': None, 'raw': {}, 'details': {}, 'ai_response': mapped}

    return {'icd10': None, 'raw': {}, 'details': {}}
