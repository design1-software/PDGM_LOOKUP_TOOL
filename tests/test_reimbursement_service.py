import importlib
import sys
from pathlib import Path


def _import_service():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    importlib.invalidate_caches()
    return importlib.import_module("services.reimbursement_service")


def _import_cms_data():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return importlib.import_module("services.cms_data")


# -- CMS source data ------------------------------------------------------


def test_case_mix_table_is_the_complete_cms_grid():
    """CMS publishes all 12 x 3 x 4 x 3 combinations; a gap means a parse bug."""
    table = _import_cms_data().load_case_mix_table()
    assert len(table) == 432
    assert table[("K", "High", "Early - Community", 0)]["hipps"] == "1KC11"


def test_wage_index_has_no_default():
    """Guessing a wage index is the bug this rebuild exists to fix."""
    cms_data = _import_cms_data()
    assert cms_data.get_wage_index("99901") == 0.6367
    try:
        cms_data.get_wage_index("00000")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown area code should raise, not return a default")


# -- payment calculation --------------------------------------------------


def test_payment_matches_cms_formula():
    """90 FR 55405: case-mix adjust, split 74.9/25.1, wage-adjust labor portion."""
    mod = _import_service()
    svc = mod.ReimbursementService()
    result = svc.calculate_payment(
        clinical_group_code="K",
        functional_level="High",
        admission_source_timing="Early - Community",
        comorbidity_level=0,
        area_code="10180",
    )
    expected = (
        mod.NATIONAL_30_DAY_RATE
        * result["case_mix_weight"]
        * (mod.LABOR_SHARE * result["wage_index"] + mod.NON_LABOR_SHARE)
    )
    assert result["hipps_code"] == "1KC11"
    assert result["period_payment"] == round(expected, 2)
    assert not result.get("error")


def test_incomplete_inputs_return_no_payment():
    """A diagnosis alone cannot identify a HIPPS group; refuse rather than guess."""
    mod = _import_service()
    result = mod.ReimbursementService().calculate_payment(clinical_group_code="K")
    assert result["estimated_payment"] is None
    assert result["error"]
    assert set(result["missing_inputs"]) == {
        "functional_level",
        "admission_source_timing",
        "comorbidity_level",
        "area_code",
    }


def test_invalid_area_code_is_rejected():
    mod = _import_service()
    result = mod.ReimbursementService().calculate_payment(
        clinical_group_code="K",
        functional_level="High",
        admission_source_timing="Early - Community",
        comorbidity_level=0,
        area_code="00000",
    )
    assert result["estimated_payment"] is None
    assert any("area_code" in message for message in result["invalid_inputs"])


def test_lupa_pays_per_visit_below_threshold():
    mod = _import_service()
    svc = mod.ReimbursementService()
    full = svc.calculate_payment(
        clinical_group_code="F",
        functional_level="High",
        admission_source_timing="Early - Community",
        comorbidity_level=0,
        area_code="10180",
    )
    lupa = svc.calculate_payment(
        clinical_group_code="F",
        functional_level="High",
        admission_source_timing="Early - Community",
        comorbidity_level=0,
        area_code="10180",
        visits_by_discipline={"Skilled Nursing": 1},
    )
    assert lupa["is_lupa"] is True
    assert lupa["total_visits"] < lupa["lupa_threshold"]
    assert lupa["estimated_payment"] < full["period_payment"]


def test_visits_at_threshold_pay_the_full_period():
    mod = _import_service()
    svc = mod.ReimbursementService()
    result = svc.calculate_payment(
        clinical_group_code="F",
        functional_level="High",
        admission_source_timing="Early - Community",
        comorbidity_level=0,
        area_code="10180",
        visits_by_discipline={"Skilled Nursing": 20},
    )
    assert result["is_lupa"] is False
    assert result["estimated_payment"] == result["period_payment"]


def test_lupa_thresholds_vary_by_hipps_group():
    """The old code returned a single hardcoded threshold for every group."""
    mod = _import_service()
    svc = mod.ReimbursementService()
    thresholds = set()
    for timing in mod.ADMISSION_SOURCE_TIMINGS:
        for level in mod.FUNCTIONAL_LEVELS:
            result = svc.calculate_payment(
                clinical_group_code="F",
                functional_level=level,
                admission_source_timing=timing,
                comorbidity_level=0,
                area_code="10180",
            )
            thresholds.add(result["lupa_threshold"])
    assert len(thresholds) > 1


def test_no_quality_data_pays_less():
    mod = _import_service()
    kwargs = dict(
        clinical_group_code="K",
        functional_level="High",
        admission_source_timing="Early - Community",
        comorbidity_level=0,
        area_code="10180",
    )
    submitted = mod.ReimbursementService(submitted_quality_data=True).calculate_payment(**kwargs)
    withheld = mod.ReimbursementService(submitted_quality_data=False).calculate_payment(**kwargs)
    assert withheld["period_payment"] < submitted["period_payment"]


def test_payment_range_spans_functional_levels_and_timings():
    mod = _import_service()
    result = mod.ReimbursementService().payment_range("E", "10180")
    assert result["combinations"] == 36
    assert result["min_payment"] < result["max_payment"]


# -- input parsing --------------------------------------------------------


def test_parse_payment_inputs_reads_flat_visit_fields():
    mod = _import_service()
    parsed = mod.parse_payment_inputs({
        "area_code": "10180",
        "functional_level": "High",
        "admission_source_timing": "Early - Community",
        "comorbidity_level": "2",
        "visits_skilled_nursing": "3",
        "visits_speech_language_pathology": "1",
        "visits_physical_therapy": "0",
    })
    assert parsed["comorbidity_level"] == 2
    assert parsed["visits_by_discipline"] == {
        "Skilled Nursing": 3,
        "Speech-Language Pathology": 1,
    }


def test_parse_payment_inputs_leaves_blanks_as_none():
    mod = _import_service()
    parsed = mod.parse_payment_inputs({"area_code": "  "})
    assert parsed["area_code"] is None
    assert parsed["functional_level"] is None
    assert parsed["comorbidity_level"] is None
    assert parsed["visits_by_discipline"] is None


# -- AI helpers -----------------------------------------------------------


def test_ai_mapping_no_longer_appends_payment():
    """Payment figures must not be derived from free-text AI output."""
    mod = _import_service()
    text = mod.ai_map_phrase_to_code_with_payment(
        lambda _phrase: "PDGM Code: A", "test", "12345", 5
    )
    assert "ESTIMATED REIMBURSEMENT" not in text
    assert text == "PDGM Code: A"


def test_extract_code_ignores_stray_capital_letters():
    """The old \\b[A-L]\\b pattern matched prose like "vitamin D"."""
    mod = _import_service()
    assert mod.extract_pdgm_code_from_response("Patient has vitamin D deficiency") is None
    assert mod.extract_pdgm_code_from_response("Refer to section C. for details") is None
    # Real codes and group names must still be extracted for usage tracking.
    assert mod.extract_pdgm_code_from_response("Group: MMTA_INFECT") == "MMTA_INFECT"
    assert mod.extract_pdgm_code_from_response("MMTA01 result") == "MMTA01"
    assert mod.extract_pdgm_code_from_response("HIPPS 1KC11 applies") == "1KC11"
