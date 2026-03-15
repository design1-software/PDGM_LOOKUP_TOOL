"""PDGM implementations — normalize, load, search, parse."""

import csv
import os
from pathlib import Path

_root = Path(__file__).resolve().parent.parent.parent
CSV_PATH = os.getenv("PDGM_CSV_PATH", str(_root / "CCFTF_pdgm_diagnosis_mapping.csv"))


def normalize_icd10(code: str) -> str:
    if not isinstance(code, str):
        return ""
    return code.replace('.', '').replace(' ', '').upper()


def load_icd10_map(csv_path=None):
    code_map = {}
    path = csv_path or CSV_PATH
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_map[normalize_icd10(row['icd10_code'])] = row
    return code_map


# Cache the loaded map at module level
_icd10_map = None


def _get_map():
    global _icd10_map
    if _icd10_map is None:
        _icd10_map = load_icd10_map()
    return _icd10_map


def format_icd10(code: str) -> str:
    if len(code) > 3 and code[3] != '.':
        return code[:3] + '.' + code[3:]
    return code


def search_icd10_codes(prefix: str, limit: int = 10):
    norm = normalize_icd10(prefix)
    data = _get_map()
    results = []
    for code in sorted(data):
        if code.startswith(norm):
            row = data[code]
            results.append({"code": format_icd10(row["icd10_code"]), "description": row.get("description", "")})
            if len(results) >= limit:
                break
    return results


def parse_pdgm_details(text) -> dict:
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
        elif low.startswith("billable:"):
            details["billable"] = line.split(":", 1)[1].strip()
        if len(details) >= 4:
            break
    return details
