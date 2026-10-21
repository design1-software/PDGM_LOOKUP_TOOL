"""PDGM repository — data access layer."""

from .impl import normalize_icd10, load_icd10_map, search_icd10_codes, _get_map


class LookupUnavailable(RuntimeError):
    """A technical AI failure is not evidence of an unrecognized diagnosis."""


def get_icd10_map(service_date=None):
    return _get_map(service_date)


def search_icd10(query, limit=10, service_date=None):
    return search_icd10_codes(query, limit, service_date)


def map_phrase_to_code(phrase, service_date=None):
    """Use AI to map a free-text phrase to an ICD-10 entry."""
    try:
        from app import ai_map_phrase_to_code
        result = (ai_map_phrase_to_code(phrase, service_date=service_date)
                  if service_date is not None else ai_map_phrase_to_code(phrase))
        if isinstance(result, str) and result.startswith((
            'Anthropic API key not configured.', 'Rate limit exceeded.', 'AI error:',
        )):
            raise LookupUnavailable('AI-assisted lookup is temporarily unavailable')
        return result
    except LookupUnavailable:
        raise
    except Exception as e:
        raise LookupUnavailable('AI-assisted lookup is temporarily unavailable') from e
