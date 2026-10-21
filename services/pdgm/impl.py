"""PDGM implementations — normalize, load, search, parse."""

import csv
import os
from threading import RLock
from pathlib import Path
from collections.abc import Mapping
from .datasets import load_release, select_release

_root = Path(__file__).resolve().parent.parent.parent
CSV_PATH = os.getenv("PDGM_CSV_PATH", str(_root / "CCFTF_pdgm_diagnosis_mapping.csv"))


def normalize_icd10(code: str) -> str:
    if not isinstance(code, str):
        return ""
    return code.replace('.', '').replace(' ', '').upper()


def load_icd10_map(csv_path=None, service_date=None):
    if csv_path is None:
        return load_release(service_date)
    code_map = {}
    path = csv_path or CSV_PATH
    with open(path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code_map[normalize_icd10(row['icd10_code'])] = row
    return code_map


# Cache the loaded map at module level
_icd10_map = None
_default_version = None
_map_lock = RLock()


def _get_map(service_date=None):
    global _icd10_map, _default_version
    with _map_lock:
        if service_date is not None:
            _, selected = select_release(service_date)
            if _icd10_map is not None and _default_version == selected['version']:
                return _icd10_map
            return load_icd10_map(service_date=service_date)
        _, release = select_release()
        if _icd10_map is None or _default_version != release['version']:
            _icd10_map = load_icd10_map()
            _default_version = release['version']
        return _icd10_map


class CurrentDiagnosisMap(Mapping):
    """Compatibility view: do not freeze today's release at process startup."""
    def __getitem__(self, key):
        return _get_map()[key]

    def __iter__(self):
        return iter(_get_map())

    def __len__(self):
        return len(_get_map())


def format_icd10(code: str) -> str:
    if len(code) > 3 and code[3] != '.':
        return code[:3] + '.' + code[3:]
    return code


def search_icd10_codes(prefix: str, limit: int = 10, service_date=None):
    from .search import search_rows
    return search_rows(prefix, _get_map(service_date), limit)


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
        if len(details) >= 4:
            break
    return details
