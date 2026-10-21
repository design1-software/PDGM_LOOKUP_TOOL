"""
Core PDGM lookup logic.

This module provides the CSV-driven PDGM lookup, Claude AI mapping,
follow-up question generation, and documentation/assessment helpers.
It is imported by blueprints — it does NOT create a Flask app.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timezone
from difflib import SequenceMatcher

import anthropic

from services.reimbursement_service import (
    ReimbursementService,
    ai_map_phrase_to_code_with_payment,
    extract_pdgm_code_from_response,
)
from enhanced_pdgm_functions import (
    get_candidate_codes_enhanced,
    get_fallback_followup,
    validate_pdgm_response,
    expand_with_medical_synonyms,
)
import enhanced_prompt_manager as prompt_manager

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# claude-sonnet-4-20250514 reached end-of-life on 2026-06-15 and now returns a
# 404, which broke every AI feature. claude-sonnet-5 is the documented
# replacement for it and stays in the same cost tier.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
AI_LOG_PATH = Path(os.getenv("AI_LOG_PATH", "ai_logs.jsonl"))


# ---------------------------------------------------------------------------
# ICD-10 helpers (also in services/pdgm/impl.py — kept here for direct use)
# ---------------------------------------------------------------------------

def normalize_icd10(code: str) -> str:
    if not isinstance(code, str):
        return ""
    return code.replace('.', '').replace(' ', '').upper()


def normalize_query(q: str) -> str:
    if not isinstance(q, str):
        return ""
    return q.lower().strip()


from services.pdgm.impl import load_icd10_map, CurrentDiagnosisMap, _get_map

# Read-only compatibility view; explicit historical requests pass their date.
icd10_data = CurrentDiagnosisMap()


def format_icd10(code: str) -> str:
    if len(code) > 3 and code[3] != '.':
        return code[:3] + '.' + code[3:]
    return code


def format_pdgm_group(name: str) -> str:
    if not name:
        return ''
    name = name.upper()
    if name.startswith('MMTA_'):
        rest = name[5:].replace('GI_GU', 'GI/GU').replace('_', ' ').title()
        return f"MMTA - {rest}"
    if name.endswith('_REHAB'):
        return name.replace('_', ' ').title()
    if name == 'BEHAVE_HEALTH':
        return 'Behavioral Health'
    if name == 'NO_GROUP':
        return 'No Group'
    return name.replace('_', ' ').title()


from services.pdgm.impl import search_icd10_codes


def get_candidate_codes(phrase, limit=15, service_date=None):
    return get_candidate_codes_enhanced(phrase, _get_map(service_date), limit)


def extract_icd10_codes(text: str):
    pattern = r"\b[A-TV-Z][0-9][0-9A-Z]{1,6}(?:\.[0-9A-Z]{1,4})?\b"
    return [normalize_icd10(c) for c in re.findall(pattern, text.upper())]


def validate_ai_output(text: str, service_date=None):
    codes = extract_icd10_codes(text)
    data = _get_map(service_date)
    mismatches = [c for c in codes if c not in data]
    return len(mismatches) == 0, mismatches


def parse_pdgm_details(text):
    """Extract core PDGM details from a response string or dict."""
    if isinstance(text, dict):
        return text
    details = {}
    for line in str(text).split("\n"):
        line = line.strip()
        low = line.lower()
        if low.startswith("focus of care:"):
            details["focus_of_care"] = line.split(":", 1)[1].strip()
        elif low.startswith("description:"):
            details["description"] = line.split(":", 1)[1].strip()
        elif low.startswith("comorbidity group:"):
            details["comorbidity_group"] = line.split(":", 1)[1].strip()
        if len(details) >= 4:
            break
    return details


def log_ai_interaction(model: str, query: str, response: str, mismatches=None):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "query": query,
        "response": response,
        "mismatches": mismatches or [],
    }
    try:
        with open(AI_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def is_valid_ai_response(response):
    if not response or not isinstance(response, str):
        return False
    error_indicators = [
        "none of the provided codes", "no valid pdgm", "cannot be selected",
        "no appropriate code", "openai error", "rate limit exceeded",
        "error:", "failed to", "unable to",
    ]
    if any(ind in response.lower() for ind in error_indicators):
        return False
    if not re.search(r"\b[A-TV-Z][0-9][0-9A-Z]{1,6}(?:\.[0-9A-Z]{1,4})?\b", response):
        return False
    required = ["focus of care:", "description:", "pdgm group:"]
    if not any(el in response.lower() for el in required):
        return False
    return True

# ---------------------------------------------------------------------------
# Anthropic client + AI functions
# ---------------------------------------------------------------------------
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


def _call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Helper to call Claude API.

    No `temperature`: claude-sonnet-5 rejects non-default sampling parameters
    with a 400 ("`temperature` is deprecated for this model"). Steer output
    through the prompt instead.

    Thinking is disabled and effort is low because these are short, structured
    generations. Thinking is on by default on this model and is billed against
    the same `max_tokens` as the response, so leaving it on would eat the
    budget on the smaller calls and truncate the answer.
    """
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
    )
    return "".join(
        block.text for block in resp.content if block.type == "text"
    ).strip()


def ai_map_phrase_to_code(phrase, service_date=None):
    if not client:
        return "Anthropic API key not configured."
    system_prompt = (
        "You are a Utilization Review and Coding Compliance Nurse with 20+ years of Home Health experience, certified in HCS-D, HCS-O, CCS, and Medicare billing. "
        "Given a clinical phrase, select only PDGM-valid ICD-10 code(s) from the provided list, recognizing synonymous phrasing, "
        "prioritizing compliant primary-diagnosis selection, and append one line beginning with \"Reason:\" that briefly states why each code was chosen. "
        "Do not determine or report billability or payment coverage. "
        "Respond for each match using this format:\n"
        "Focus of Care: <ICD10 no dot> <Description> <PDGM Code> <PDGM Group>  ICD-10: <ICD10 with dot>\n"
        "Description: <Description>\nPDGM Group: <PDGM Group>\nComorbidity Group: <Comorbidity Group>\n"
        "Primary Awarding: <Primary Awarding Flag>\nCode First: <Code First>\n"
        "Reason: <Brief explanation for code selection>\nSeparate multiple codes with a blank line. Never invent codes."
    )
    candidates = (get_candidate_codes(phrase, service_date=service_date)
                  if service_date is not None else get_candidate_codes(phrase))
    code_choices = "\n".join(
        f"{row['icd10_code']}|{row.get('description','')}|{row.get('pdgm_clinical_group_code','')}|"
        f"{row.get('pdgm_clinical_group_name','')}|{row.get('COMORBIDITY_GROUP','')}|"
        f"{row.get('PRIMARY_AWARDING_FLAG','')}|{row.get('CODE_FIRST','')}"
        for row in candidates
    )
    user_prompt = (
        f"Clinical input: '{phrase}'\n"
        "Codes list (ICD10|Description|PDGM Code|PDGM Group|Comorbidity Group|Primary Awarding|Code First):\n"
        f"{code_choices}\n"
        "Return the closest code(s) in the specified format."
    )

    try:
        text = _call_claude(system_prompt, user_prompt, max_tokens=500)
        valid, mismatches = validate_ai_output(text, service_date)
        log_ai_interaction(CLAUDE_MODEL, phrase, text, mismatches)
        return text
    except anthropic.RateLimitError:
        return "Rate limit exceeded. Please try again later."
    except anthropic.APIError as e:
        return f"AI error: {e}"


def ai_followup_question(phrase: str) -> str:
    fallback_response = get_fallback_followup(phrase)
    if fallback_response != "Could you provide more specific details about the condition, such as: acute vs chronic, location, severity, or any complications?":
        return fallback_response
    if not client:
        return fallback_response
    try:
        return _call_claude(
            "You are a medical coding specialist helping refine ICD-10 selection for home health PDGM coding. "
            "ALWAYS provide helpful follow-up questions with specific options. "
            # Replaces temperature=0.7, which this model rejects: ask for the
            # variation directly instead of sampling for it.
            "Vary your phrasing and the angle you ask from across responses rather than "
            "reusing a standard template.",
            f"Medical term: '{phrase}' - What follow-up questions would help specify this for accurate ICD-10 coding?",
            max_tokens=200,
        )
    except Exception:
        pass
    return fallback_response


# ---------------------------------------------------------------------------
# Documentation roadmap & OASIS assessment
# ---------------------------------------------------------------------------

def extract_pdgm_info_from_response(pdgm_response):
    lines = pdgm_response.split('\n')
    diagnosis = pdgm_group = None
    for line in lines:
        line = line.strip()
        if line.startswith('Focus of Care:'):
            parts = line.split()
            for part in parts:
                if '.' in part and len(part) >= 4:
                    diagnosis = part
                    break
        elif line.startswith('PDGM Group:'):
            pdgm_group = line.replace('PDGM Group:', '').strip()
    return diagnosis, pdgm_group


def ai_documentation_roadmap(diagnosis: str, pdgm_group: str, disciplines: list):
    if not client:
        return "Anthropic API key not configured."
    try:
        system_prompt = prompt_manager.build_system_prompt("roadmap", pdgm_group, diagnosis, disciplines)
        user_prompt = f"Diagnosis: {diagnosis}\nPDGM Group: {pdgm_group}\nDisciplines: {', '.join(disciplines)}"
        return _call_claude(system_prompt, user_prompt, max_tokens=1400)
    except Exception as e:
        return f"AI error: {e}"


def ai_sample_oasis_assessment(diagnosis: str, pdgm_group: str, disciplines: list = None):
    if not client:
        return "Anthropic API key not configured."
    try:
        system_prompt = prompt_manager.build_system_prompt("oasis", pdgm_group, diagnosis, disciplines or [])
        user_prompt = f"Diagnosis: {diagnosis}\nPDGM Group: {pdgm_group}"
        return _call_claude(system_prompt, user_prompt, max_tokens=1400)
    except Exception as e:
        return f"AI error: {e}"
