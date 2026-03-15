import importlib
import sys
from pathlib import Path


def _import_service():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    importlib.invalidate_caches()
    return importlib.import_module("services.reimbursement_service")


def test_ai_map_letter_code():
    svc = _import_service()

    def stub_ai_map(_phrase):
        return "PDGM Code: A"

    text = svc.ai_map_phrase_to_code_with_payment(stub_ai_map, "test", zip_code="12345", visit_count=5)
    assert "ESTIMATED REIMBURSEMENT" in text


def test_lupa_calculation():
    mod = _import_service()
    svc = mod.ReimbursementService()
    info = svc.calculate_payment('MMTA01', zip_code='12345', visit_count=2)
    assert info['estimated_payment'] is not None
    assert not info.get('error')
