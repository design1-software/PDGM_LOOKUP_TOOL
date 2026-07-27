"""HIPPS generation and case-mix lookup against the real CY 2026 CMS table."""

import importlib
import sys
from pathlib import Path

import pytest


def _import(module):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    importlib.invalidate_caches()
    return importlib.import_module(module)


def test_generates_real_cms_hipps_format():
    """Real codes look like 1KC11, not the retired A1111 encoding."""
    hipps = _import("services.pdgm.hipps")
    code = hipps.generate_hipps_code(
        clinical_group="K", admission_source=1, episode_timing=1,
        functional_level="High", comorbidity_adjustment="None",
    )
    assert code == "1KC11"


def test_every_combination_resolves_against_cms():
    """All 4 x 12 x 3 x 3 codes must exist in the CMS table -- no gaps, no fallback."""
    hipps = _import("services.pdgm.hipps")
    seen = set()
    for group in "ABCDEFGHIJKL":
        for source in (1, 2):
            for timing in (1, 2):
                for level in ("Low", "Medium", "High"):
                    for comorbidity in ("None", "Low", "High"):
                        code = hipps.generate_hipps_code(
                            clinical_group=group, admission_source=source,
                            episode_timing=timing, functional_level=level,
                            comorbidity_adjustment=comorbidity,
                        )
                        assert hipps.get_case_mix_weight(code) > 0
                        assert hipps.get_lupa_threshold(code) in (2, 3, 4, 5)
                        seen.add(code)
    assert len(seen) == 432


def test_unknown_code_raises_instead_of_returning_one():
    """The old get_case_mix_weight returned 1.0 for anything unrecognised."""
    hipps = _import("services.pdgm.hipps")
    with pytest.raises(KeyError):
        hipps.get_case_mix_weight("A1111")
    with pytest.raises(KeyError):
        hipps.get_case_mix_weight("ZZZZZ")


def test_retired_encoding_is_not_decodable():
    hipps = _import("services.pdgm.hipps")
    assert "error" in hipps.decode_hipps("A1111")


def test_decode_round_trips_generate():
    hipps = _import("services.pdgm.hipps")
    code = hipps.generate_hipps_code(
        clinical_group="F", admission_source=2, episode_timing=2,
        functional_level="Medium", comorbidity_adjustment="High",
    )
    decoded = hipps.decode_hipps(code)
    assert decoded["clinical_group"] == "F"
    assert decoded["clinical_group_name"] == "Behavioral Health"
    assert decoded["admission_source"] == "Institutional"
    assert decoded["episode_timing"] == "Late"
    assert decoded["functional_level"] == "Medium"
    assert decoded["comorbidity_adjustment"] == 2


def test_invalid_inputs_raise_rather_than_default():
    hipps = _import("services.pdgm.hipps")
    base = dict(clinical_group="K", admission_source=1, episode_timing=1,
                functional_level="High", comorbidity_adjustment="None")
    for field, bad in [
        ("clinical_group", "Z"), ("admission_source", 3), ("episode_timing", 9),
        ("functional_level", "Severe"), ("comorbidity_adjustment", "Extreme"),
    ]:
        with pytest.raises(ValueError):
            hipps.generate_hipps_code(**dict(base, **{field: bad}))


def test_payment_requires_a_real_area_code():
    hipps = _import("services.pdgm.hipps")
    result = hipps.calculate_payment("1KC11", area_code="00000")
    assert result["estimated_payment"] is None
    assert any("area_code" in m for m in result["invalid_inputs"])


def test_payment_uses_real_wage_index():
    hipps = _import("services.pdgm.hipps")
    abilene = hipps.calculate_payment("1KC11", area_code="10180")
    san_francisco = hipps.calculate_payment("1KC11", area_code="41884")
    assert abilene["wage_index"] == 0.9287
    assert san_francisco["wage_index"] == 1.7522
    assert san_francisco["estimated_payment"] > abilene["estimated_payment"]
