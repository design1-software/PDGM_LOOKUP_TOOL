# Request/response schemas placeholder (use Marshmallow/Pydantic later if needed)
import re
from typing import TypedDict, List, Optional

class PDGMLookupRequest(TypedDict):
    query: str  # ICD-10 code or phrase

class PDGMLookupResponse(TypedDict):
    icd10: str
    pdgm_group: str
    clinical_group: str
    is_valid_primary: bool
    notes: Optional[str]


# ---- Lightweight validation helpers (no external deps) ----

class ValidationError(Exception):
    pass

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

def _ensure_str(v, field, max_length=500):
    if not isinstance(v, str):
        raise ValidationError(f"{field} must be a string")
    v = _CONTROL_CHARS.sub('', v).strip()
    if not v:
        raise ValidationError(f"{field} cannot be empty")
    if len(v) > max_length:
        raise ValidationError(f"{field} exceeds maximum length of {max_length} characters")
    return v

def _ensure_list_str(v, field, max_items=25):
    if v is None:
        return []
    if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
        raise ValidationError(f"{field} must be a list of strings")
    if len(v) > max_items:
        raise ValidationError(f"{field} cannot contain more than {max_items} entries")
    return [_CONTROL_CHARS.sub('', x).strip() for x in v if isinstance(x, str) and x.strip()]

def validate_lookup_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Body must be a JSON object")
    q = _ensure_str(payload.get("query", ""), "query", max_length=500)
    zip_code = payload.get("zip_code", "")
    if isinstance(zip_code, str):
        zip_code = zip_code.strip()
    else:
        zip_code = ""
    visit_count = payload.get("visit_count", "")
    try:
        visit_count = int(visit_count) if visit_count else None
    except (ValueError, TypeError):
        visit_count = None
    return {"query": q, "zip_code": zip_code, "visit_count": visit_count}

def validate_roadmap_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Body must be a JSON object")
    diagnosis = _ensure_str(payload.get("diagnosis",""), "diagnosis", max_length=200)
    pdgm_group = _ensure_str(payload.get("pdgm_group",""), "pdgm_group", max_length=100)
    disciplines = _ensure_list_str(payload.get("disciplines"), "disciplines")
    return {"diagnosis": diagnosis, "pdgm_group": pdgm_group, "disciplines": disciplines}

def validate_assessment_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Body must be a JSON object")
    diagnosis = _ensure_str(payload.get("diagnosis",""), "diagnosis", max_length=200)
    pdgm_group = _ensure_str(payload.get("pdgm_group",""), "pdgm_group", max_length=100)
    return {"diagnosis": diagnosis, "pdgm_group": pdgm_group}

def validate_hipps_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Body must be a JSON object")
    primary_icd10 = _ensure_str(payload.get("primary_icd10", ""), "primary_icd10")
    secondary_icd10s = _ensure_list_str(payload.get("secondary_icd10s"), "secondary_icd10s")
    admission_source = payload.get("admission_source", 1)
    try:
        admission_source = int(admission_source)
    except (ValueError, TypeError):
        admission_source = 1
    if admission_source not in (1, 2):
        admission_source = 1
    episode_timing = payload.get("episode_timing", 1)
    try:
        episode_timing = int(episode_timing)
    except (ValueError, TypeError):
        episode_timing = 1
    if episode_timing not in (1, 2):
        episode_timing = 1
    gg0130 = payload.get("gg0130", {})
    gg0170 = payload.get("gg0170", {})
    if not isinstance(gg0130, dict):
        gg0130 = {}
    if not isinstance(gg0170, dict):
        gg0170 = {}
    zip_code = payload.get("zip_code", "")
    if isinstance(zip_code, str):
        zip_code = zip_code.strip()
    else:
        zip_code = ""
    return {
        "primary_icd10": primary_icd10,
        "secondary_icd10s": secondary_icd10s,
        "admission_source": admission_source,
        "episode_timing": episode_timing,
        "gg0130": gg0130,
        "gg0170": gg0170,
        "zip_code": zip_code,
    }
