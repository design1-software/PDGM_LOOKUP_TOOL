# Request/response schemas placeholder (use Marshmallow/Pydantic later if needed)
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

def _ensure_str(v, field):
    if not isinstance(v, str):
        raise ValidationError(f"{field} must be a string")
    if not v.strip():
        raise ValidationError(f"{field} cannot be empty")
    return v.strip()

def _ensure_list_str(v, field):
    if v is None:
        return []
    if not isinstance(v, list) or any(not isinstance(x, str) for x in v):
        raise ValidationError(f"{field} must be a list of strings")
    return [x.strip() for x in v if isinstance(x, str) and x.strip()]

def validate_lookup_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Body must be a JSON object")
    q = _ensure_str(payload.get("query", ""), "query")
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
    diagnosis = _ensure_str(payload.get("diagnosis",""), "diagnosis")
    pdgm_group = _ensure_str(payload.get("pdgm_group",""), "pdgm_group")
    disciplines = _ensure_list_str(payload.get("disciplines"), "disciplines")
    return {"diagnosis": diagnosis, "pdgm_group": pdgm_group, "disciplines": disciplines}

def validate_assessment_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Body must be a JSON object")
    diagnosis = _ensure_str(payload.get("diagnosis",""), "diagnosis")
    pdgm_group = _ensure_str(payload.get("pdgm_group",""), "pdgm_group")
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
