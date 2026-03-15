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
    return {"query": q}

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
