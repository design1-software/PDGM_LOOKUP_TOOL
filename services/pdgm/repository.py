"""PDGM repository — data access layer."""

from .impl import normalize_icd10, load_icd10_map, search_icd10_codes, _get_map


def get_icd10_map():
    return _get_map()


def search_icd10(query, limit=10):
    return search_icd10_codes(query, limit)


def map_phrase_to_code(phrase):
    """Use AI to map a free-text phrase to an ICD-10 entry."""
    try:
        from app import ai_map_phrase_to_code
        return ai_map_phrase_to_code(phrase)
    except Exception:
        return None
