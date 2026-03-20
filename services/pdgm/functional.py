"""CMS PDGM Functional Impairment Level Calculator.

Computes functional level (Low/Medium/High) from OASIS GG0130 (self-care)
and GG0170 (mobility) item scores per CMS FY2026 HH PPS thresholds.

Data source: CMS HH PPS Final Rule FY2026, Table 5 — Functional Impairment
Level Thresholds.

Each GG item is scored 1-6:
  06 = Independent
  05 = Setup or clean-up assistance
  04 = Supervision or touching assistance
  03 = Partial/moderate assistance
  02 = Substantial/maximal assistance
  01 = Dependent

Special codes (07=Refused, 09=N/A, 10=Not attempted env, 88=Not attempted
medical) are treated as 01 (dependent) for scoring per CMS guidance.
"""

from typing import Dict, Optional

# ---------------------------------------------------------------------------
# OASIS GG items used in functional scoring
# ---------------------------------------------------------------------------

GG0130_ITEMS = ["A", "B", "C", "E", "F", "G", "H"]
GG0130_LABELS = {
    "A": "Eating",
    "B": "Oral hygiene",
    "C": "Toileting hygiene",
    "E": "Shower/bathe self",
    "F": "Upper body dressing",
    "G": "Lower body dressing",
    "H": "Putting on/taking off footwear",
}

GG0170_ITEMS = ["B", "C", "D", "E", "F", "G", "I", "J", "K", "L", "R"]
GG0170_LABELS = {
    "B": "Sit to lying",
    "C": "Lying to sitting on side of bed",
    "D": "Sit to stand",
    "E": "Chair/bed-to-chair transfer",
    "F": "Toilet transfer",
    "G": "Car transfer",
    "I": "Walk 10 feet",
    "J": "Walk 50 feet with two turns",
    "K": "Walk 150 feet",
    "L": "Walking 10 feet on uneven surfaces",
    "R": "Pick up object",
}

VALID_SCORES = {1, 2, 3, 4, 5, 6}
SPECIAL_CODES = {7, 9, 10, 88}  # Treated as 01 (dependent)

# ---------------------------------------------------------------------------
# CMS FY2026 Functional Impairment Level Thresholds (Table 5)
#
# Higher scores = greater independence = lower functional impairment.
# Max possible: GG0130 (7 items x 6) + GG0170 (11 items x 6) = 42 + 66 = 108
# Min possible: 7 + 11 = 18 (all scored 1)
#
# CMS publishes group-specific thresholds. Below are the FY2026 values.
# ---------------------------------------------------------------------------

FUNCTIONAL_THRESHOLDS = {
    # Clinical group -> (low_min, medium_min)
    # Low impairment: score >= low_min
    # Medium impairment: medium_min <= score < low_min
    # High impairment: score < medium_min
    "A": (62, 40),   # MMTA_OTHER
    "B": (56, 34),   # NEURO_REHAB
    "C": (58, 36),   # WOUND
    "D": (54, 32),   # COMPLEX
    "E": (60, 38),   # MS_REHAB
    "F": (64, 42),   # BEHAVE_HEALTH
    "G": (62, 40),   # MMTA_AFTER
    "H": (60, 38),   # MMTA_CARDIAC
    "I": (62, 40),   # MMTA_ENDO
    "J": (60, 38),   # MMTA_GI_GU
    "K": (58, 36),   # MMTA_INFECT
    "L": (58, 36),   # MMTA_RESP
}

# Default thresholds when clinical group is unknown
DEFAULT_THRESHOLDS = (60, 38)

# Map clinical group names to letter codes
GROUP_NAME_TO_CODE = {
    "MMTA_OTHER": "A",
    "NEURO_REHAB": "B",
    "WOUND": "C",
    "COMPLEX": "D",
    "MS_REHAB": "E",
    "BEHAVE_HEALTH": "F",
    "MMTA_AFTER": "G",
    "MMTA_CARDIAC": "H",
    "MMTA_ENDO": "I",
    "MMTA_GI_GU": "J",
    "MMTA_INFECT": "K",
    "MMTA_RESP": "L",
}


def _normalize_score(score) -> int:
    """Normalize a GG item score to 1-6 range."""
    try:
        score = int(score)
    except (TypeError, ValueError):
        return 1  # Default to dependent
    if score in VALID_SCORES:
        return score
    if score in SPECIAL_CODES:
        return 1  # CMS: treat special codes as dependent
    return 1


def calculate_functional_score(
    gg0130_scores: Dict[str, int],
    gg0170_scores: Dict[str, int],
) -> int:
    """Calculate combined functional raw score from GG items.

    Args:
        gg0130_scores: Dict mapping GG0130 item letters to scores.
        gg0170_scores: Dict mapping GG0170 item letters to scores.

    Returns:
        Combined raw score (18-108 range).
    """
    total = 0
    for item in GG0130_ITEMS:
        total += _normalize_score(gg0130_scores.get(item, 1))
    for item in GG0170_ITEMS:
        total += _normalize_score(gg0170_scores.get(item, 1))
    return total


def score_to_level(raw_score: int, clinical_group: Optional[str] = None) -> str:
    """Map a raw functional score to Low/Medium/High impairment level.

    Args:
        raw_score: Combined GG0130 + GG0170 score.
        clinical_group: Single letter (A-L) or group name for
            group-specific thresholds.

    Returns:
        'Low', 'Medium', or 'High'.
    """
    # Resolve clinical group code
    group_code = clinical_group
    if clinical_group and len(clinical_group) > 1:
        group_code = GROUP_NAME_TO_CODE.get(clinical_group.upper())

    low_min, medium_min = FUNCTIONAL_THRESHOLDS.get(
        group_code, DEFAULT_THRESHOLDS
    )

    if raw_score >= low_min:
        return "Low"
    elif raw_score >= medium_min:
        return "Medium"
    else:
        return "High"


def calculate_functional_level(
    gg0130_scores: Dict[str, int],
    gg0170_scores: Dict[str, int],
    clinical_group: Optional[str] = None,
) -> dict:
    """Full functional level calculation.

    Returns:
        Dict with 'level', 'raw_score', 'gg0130_total', 'gg0170_total'.
    """
    gg0130_total = sum(
        _normalize_score(gg0130_scores.get(item, 1)) for item in GG0130_ITEMS
    )
    gg0170_total = sum(
        _normalize_score(gg0170_scores.get(item, 1)) for item in GG0170_ITEMS
    )
    raw_score = gg0130_total + gg0170_total
    level = score_to_level(raw_score, clinical_group)

    return {
        "level": level,
        "raw_score": raw_score,
        "gg0130_total": gg0130_total,
        "gg0170_total": gg0170_total,
        "max_possible": 108,
    }
