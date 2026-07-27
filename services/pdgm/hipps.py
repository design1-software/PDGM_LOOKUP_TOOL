"""CMS PDGM HIPPS code generation and case-mix lookup, backed by CMS source data.

Weights, LUPA thresholds and wage index values are read at runtime from the CY
2026 CMS files under ``data/cms/cy2026/`` via ``services.cms_data``. Nothing in
this module is estimated.

HIPPS code structure (CY 2026, derived from the CMS case-mix file itself):

  Position 1: Admission source AND timing combined
              1 = Early/Community, 2 = Early/Institutional,
              3 = Late/Community,  4 = Late/Institutional
  Position 2: Clinical group, A-L
  Position 3: Functional impairment level, A = Low, B = Medium, C = High
  Position 4: Comorbidity adjustment, 1 = none, 2 = single, 3 = interaction
  Position 5: Always 1

Total: 4 x 12 x 3 x 3 = 432 codes, matching the CMS table exactly.

NOTE: this replaces an earlier encoding in this module that placed the clinical
group first and split admission source and timing into separate positions
(e.g. ``A1111``). That format does not exist in CMS's system -- codes built that
way cannot be billed or reconciled against CMS tables. Real codes look like
``1KC11``. The weight table it carried was likewise generated rather than
transcribed: only 20 of its 367 distinct values appeared anywhere in the real
CMS table, and most of its comorbidity steps were a constant additive delta.
"""

from services import cms_data
from services.reimbursement_service import ReimbursementService

CLINICAL_GROUPS = set(cms_data.CLINICAL_GROUPS)
CLINICAL_GROUP_NAMES = dict(cms_data.CLINICAL_GROUPS)

# Inputs accepted by generate_hipps_code, kept as-is for API compatibility.
FUNCTIONAL_LEVELS = ("Low", "Medium", "High")
COMORBIDITY_INPUTS = {"None": 0, "Low": 1, "High": 2}
ADMISSION_DECODE = {1: "Community", 2: "Institutional"}
TIMING_DECODE = {1: "Early", 2: "Late"}

# Position 1 of the HIPPS code, keyed by (episode_timing, admission_source).
_TIMING_SOURCE_TO_POSITION = {
    (1, 1): "1",  # Early, Community
    (1, 2): "2",  # Early, Institutional
    (2, 1): "3",  # Late,  Community
    (2, 2): "4",  # Late,  Institutional
}
_POSITION_TO_CMS_TIMING = {
    "1": "Early - Community",
    "2": "Early - Institutional",
    "3": "Late - Community",
    "4": "Late - Institutional",
}
_FUNCTIONAL_TO_POSITION = {"Low": "A", "Medium": "B", "High": "C"}
_POSITION_TO_FUNCTIONAL = {v: k for k, v in _FUNCTIONAL_TO_POSITION.items()}
_COMORBIDITY_TO_POSITION = {0: "1", 1: "2", 2: "3"}
_POSITION_TO_COMORBIDITY = {v: k for k, v in _COMORBIDITY_TO_POSITION.items()}

# Retained so callers can still translate the retired encoding if they need to.
LEGACY_FUNCTIONAL_LEVEL_MAP = {"Low": "1", "Medium": "2", "High": "3"}
LEGACY_COMORBIDITY_MAP = {"None": "1", "Low": "2", "High": "3"}


def generate_hipps_code(clinical_group, admission_source, episode_timing,
                        functional_level, comorbidity_adjustment):
    """Assemble a CY 2026 HIPPS code.

    Args:
        clinical_group: Letter A-L.
        admission_source: 1 (Community) or 2 (Institutional).
        episode_timing: 1 (Early) or 2 (Late).
        functional_level: 'Low', 'Medium' or 'High'.
        comorbidity_adjustment: 'None', 'Low' or 'High', or the integer 0, 1 or 2.

    Raises:
        ValueError: if any input is outside its domain. There are no defaults --
            a wrong HIPPS code produces a wrong payment.
    """
    group = (clinical_group or "").upper()
    if group not in CLINICAL_GROUPS:
        raise ValueError("Invalid clinical group: %r" % (clinical_group,))
    if admission_source not in (1, 2):
        raise ValueError("Invalid admission source: %r" % (admission_source,))
    if episode_timing not in (1, 2):
        raise ValueError("Invalid episode timing: %r" % (episode_timing,))

    functional_position = _FUNCTIONAL_TO_POSITION.get(functional_level)
    if functional_position is None:
        raise ValueError("Invalid functional level: %r" % (functional_level,))

    comorbidity = comorbidity_adjustment
    if isinstance(comorbidity, str):
        comorbidity = COMORBIDITY_INPUTS.get(comorbidity)
    comorbidity_position = _COMORBIDITY_TO_POSITION.get(comorbidity)
    if comorbidity_position is None:
        raise ValueError("Invalid comorbidity adjustment: %r" % (comorbidity_adjustment,))

    return "%s%s%s%s1" % (
        _TIMING_SOURCE_TO_POSITION[(episode_timing, admission_source)],
        group,
        functional_position,
        comorbidity_position,
    )


def _cell_for(hipps_code):
    """Look up the CMS row for a HIPPS code, or None if it isn't a real code."""
    code = (hipps_code or "").upper()
    if len(code) != 5:
        return None
    timing = _POSITION_TO_CMS_TIMING.get(code[0])
    functional = _POSITION_TO_FUNCTIONAL.get(code[2])
    comorbidity = _POSITION_TO_COMORBIDITY.get(code[3])
    if timing is None or functional is None or comorbidity is None:
        return None
    return cms_data.load_case_mix_table().get(
        (code[1], functional, timing, comorbidity)
    )


def get_case_mix_weight(hipps_code):
    """Return the CMS case-mix weight for a HIPPS code.

    Raises KeyError for codes CMS does not define. The previous implementation
    returned 1.0 for anything it didn't recognise, which silently turned a
    malformed code into a plausible-looking payment.
    """
    cell = _cell_for(hipps_code)
    if cell is None:
        raise KeyError("Not a CY 2026 HIPPS code: %r" % (hipps_code,))
    return cell["weight"]


def get_lupa_threshold(hipps_code):
    """Return the CMS LUPA visit threshold for a HIPPS code (2-5, varies)."""
    cell = _cell_for(hipps_code)
    if cell is None:
        raise KeyError("Not a CY 2026 HIPPS code: %r" % (hipps_code,))
    return cell["lupa_threshold"]


def decode_hipps(hipps_code):
    """Decode a HIPPS code into its PDGM dimensions."""
    code = (hipps_code or "").upper()
    cell = _cell_for(code)
    if cell is None:
        return {"error": "Not a CY 2026 HIPPS code: %r" % (hipps_code,)}
    timing = _POSITION_TO_CMS_TIMING[code[0]]
    episode_timing, admission_source = timing.split(" - ")
    return {
        "hipps_code": code,
        "clinical_group": code[1],
        "clinical_group_name": CLINICAL_GROUP_NAMES[code[1]],
        "admission_source": admission_source,
        "episode_timing": episode_timing,
        "functional_level": _POSITION_TO_FUNCTIONAL[code[2]],
        "comorbidity_adjustment": _POSITION_TO_COMORBIDITY[code[3]],
        "case_mix_weight": cell["weight"],
        "lupa_threshold": cell["lupa_threshold"],
    }


def calculate_payment(hipps_code, area_code=None, visits_by_discipline=None,
                      first_skilled_discipline=None, submitted_quality_data=True):
    """Calculate the CY 2026 payment for a HIPPS code in a given CMS area.

    ``area_code`` is a CBSA, statewide rural (999xx) or transition (50xxx) code
    from the CMS wage index file -- not a ZIP code. CMS keys the wage index on
    CBSA, and the CMS rate files contain no ZIP-to-CBSA mapping, so a bare ZIP
    cannot be resolved here without guessing.
    """
    decoded = decode_hipps(hipps_code)
    if "error" in decoded:
        return decoded

    service = ReimbursementService(submitted_quality_data=submitted_quality_data)
    return service.calculate_payment(
        clinical_group_code=decoded["clinical_group"],
        functional_level=decoded["functional_level"],
        admission_source_timing="%s - %s" % (
            decoded["episode_timing"], decoded["admission_source"],
        ),
        comorbidity_level=decoded["comorbidity_adjustment"],
        area_code=area_code,
        visits_by_discipline=visits_by_discipline,
        first_skilled_discipline=first_skilled_discipline,
    )
