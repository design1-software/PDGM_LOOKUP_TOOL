"""CY 2026 Home Health PPS payment calculation.

Every constant below is transcribed from a primary CMS source and cited inline.
Nothing is estimated. The previous version of this module used invented case-mix
multipliers, 18 hardcoded ZIP-prefix wage index guesses, and four hardcoded LUPA
thresholds; all of that is gone.

Sources
-------
* CR 14304 / Transmittal R13488CP, "Home Health Prospective Payment System (HH
  PPS) Rate Update for Calendar Year (CY) 2026", Tables 1-5 and 7.
* CY 2026 HH PPS final rule (CMS-1828-F), 90 FR 55342 (December 2, 2025), for
  the labor-related share and the order of operations in ``calculate_payment``.
* Per-group case-mix weights, LUPA thresholds and wage index values are read at
  runtime from the CMS files under ``data/cms/cy2026/`` via ``services.cms_data``.

Scope
-----
This computes the case-mix and wage-adjusted 30-day period payment, and LUPA
per-visit payments. It does NOT compute outlier payments (which require visit
minutes), partial-period adjustments, or the dNPWT device add-on.
"""

from datetime import datetime

from services import cms_data
from services.cms_data import (  # re-exported for callers building input forms
    ADMISSION_SOURCE_TIMINGS,
    CLINICAL_GROUPS,
    COMORBIDITY_LEVELS,
    FUNCTIONAL_LEVELS,
)

# Transmittal R13488CP, Tables 1 and 2: national, standardized 30-day period
# payment amount, after the permanent (0.98977) and temporary (0.97000)
# adjustment factors.
NATIONAL_30_DAY_RATE = 2038.22           # HHAs that submitted quality data
NATIONAL_30_DAY_RATE_NO_QUALITY = 1998.41  # HHAs that did not

# 90 FR 55405-55406: "for CY 2024 and subsequent years, the labor-related share
# will be 74.9 percent, and the non-labor-related share will be 25.1 percent."
LABOR_SHARE = 0.749
NON_LABOR_SHARE = 0.251

# Transmittal R13488CP, Tables 3 and 4: national per-visit payment amounts.
PER_VISIT_RATES = {
    "Home Health Aide": 80.12,
    "Medical Social Services": 283.64,
    "Occupational Therapy": 194.74,
    "Physical Therapy": 193.42,
    "Skilled Nursing": 176.96,
    "Speech-Language Pathology": 210.25,
}
PER_VISIT_RATES_NO_QUALITY = {
    "Home Health Aide": 78.55,
    "Medical Social Services": 278.10,
    "Occupational Therapy": 190.94,
    "Physical Therapy": 189.64,
    "Skilled Nursing": 173.51,
    "Speech-Language Pathology": 206.14,
}

# Transmittal R13488CP, Table 7. Applied to the first skilled visit of a LUPA
# period that is the only period, or the initial period in a sequence of
# adjacent periods. Note these are the CY 2025-onward values; the older
# 1.8451 / 1.6700 / 1.6266 factors are superseded.
LUPA_ADD_ON_FACTORS = {
    "Skilled Nursing": 1.7200,
    "Physical Therapy": 1.6225,
    "Speech-Language Pathology": 1.6696,
    "Occupational Therapy": 1.7238,
}

# Display abbreviations. The CMS names above stay the canonical keys for the
# rate tables; these are what clinicians actually use on a plan of care.
DISCIPLINE_LABELS = {
    "Skilled Nursing": "SN",
    "Physical Therapy": "PT",
    "Occupational Therapy": "OT",
    "Speech-Language Pathology": "ST",
    "Home Health Aide": "HHA",
    "Medical Social Services": "SW",
}

PAYMENT_YEAR = 2026

DISCLAIMER = (
    "Estimate based on the CY 2026 HH PPS final rule (CMS-1828-F) and CR 14304. "
    "Does not include outlier payments, partial-period adjustments, dNPWT, or "
    "value-based purchasing adjustments. Not a guarantee of payment."
)


class ReimbursementService:
    """Computes CY 2026 30-day period and LUPA payments from explicit inputs.

    Unlike the previous implementation, this class does not guess. If an input
    needed to identify the HIPPS case-mix group is missing, ``calculate_payment``
    returns an error naming the missing fields rather than substituting a
    default.
    """

    def __init__(self, submitted_quality_data=True):
        self.submitted_quality_data = submitted_quality_data
        self.base_rate = (
            NATIONAL_30_DAY_RATE if submitted_quality_data else NATIONAL_30_DAY_RATE_NO_QUALITY
        )
        self.per_visit_rates = (
            PER_VISIT_RATES if submitted_quality_data else PER_VISIT_RATES_NO_QUALITY
        )

    # -- inputs -----------------------------------------------------------

    @staticmethod
    def input_options():
        """Everything a caller needs to build a complete input form."""
        return {
            "clinical_groups": dict(CLINICAL_GROUPS),
            "functional_levels": list(FUNCTIONAL_LEVELS),
            "admission_source_timings": list(ADMISSION_SOURCE_TIMINGS),
            "comorbidity_levels": list(COMORBIDITY_LEVELS),
            "disciplines": sorted(PER_VISIT_RATES),
            "discipline_labels": dict(DISCIPLINE_LABELS),
        }

    def _validate(self, clinical_group_code, functional_level,
                  admission_source_timing, comorbidity_level, area_code):
        missing, invalid = [], []

        if not clinical_group_code:
            missing.append("clinical_group_code")
        elif clinical_group_code not in CLINICAL_GROUPS:
            invalid.append(
                "clinical_group_code must be one of %s" % ", ".join(sorted(CLINICAL_GROUPS))
            )

        if not functional_level:
            missing.append("functional_level")
        elif functional_level not in FUNCTIONAL_LEVELS:
            invalid.append("functional_level must be one of %s" % ", ".join(FUNCTIONAL_LEVELS))

        if not admission_source_timing:
            missing.append("admission_source_timing")
        elif admission_source_timing not in ADMISSION_SOURCE_TIMINGS:
            invalid.append(
                "admission_source_timing must be one of %s"
                % ", ".join(ADMISSION_SOURCE_TIMINGS)
            )

        if comorbidity_level is None:
            missing.append("comorbidity_level")
        elif comorbidity_level not in COMORBIDITY_LEVELS:
            invalid.append("comorbidity_level must be 0, 1 or 2")

        if not area_code:
            missing.append("area_code")
        else:
            try:
                cms_data.get_wage_index(area_code)
            except KeyError:
                invalid.append(
                    "area_code %r is not a CY 2026 CBSA, statewide rural, or "
                    "transition code" % area_code
                )
        return missing, invalid

    # -- calculation ------------------------------------------------------

    def calculate_payment(self, clinical_group_code=None, functional_level=None,
                          admission_source_timing=None, comorbidity_level=None,
                          area_code=None, visits_by_discipline=None,
                          first_skilled_discipline=None,
                          is_initial_or_only_period=True):
        """Return the CY 2026 payment for one 30-day period.

        All five case-mix/geography inputs are required. ``visits_by_discipline``
        is optional; supply it to determine LUPA status and, when the period is a
        LUPA, the per-visit payment.
        """
        missing, invalid = self._validate(
            clinical_group_code, functional_level, admission_source_timing,
            comorbidity_level, area_code,
        )
        if missing or invalid:
            return {
                "error": "Cannot calculate payment: incomplete or invalid inputs.",
                "missing_inputs": missing,
                "invalid_inputs": invalid,
                "estimated_payment": None,
                "help": (
                    "A PDGM payment is determined by clinical group, functional "
                    "impairment level, admission source and timing, comorbidity "
                    "adjustment, and the wage index of the site of service. A "
                    "diagnosis code alone identifies only the clinical group."
                ),
            }

        cell = cms_data.load_case_mix_table()[
            (clinical_group_code, functional_level, admission_source_timing, comorbidity_level)
        ]
        area = cms_data.load_wage_index()[str(area_code).strip()]
        wage_index = area["wage_index"]

        # 90 FR 55405-55406, in this order: case-mix adjust, split labor /
        # non-labor, wage-adjust the labor portion, recombine.
        case_mix_adjusted = self.base_rate * cell["weight"]
        labor_portion = case_mix_adjusted * LABOR_SHARE * wage_index
        non_labor_portion = case_mix_adjusted * NON_LABOR_SHARE
        period_payment = labor_portion + non_labor_portion

        result = {
            "hipps_code": cell["hipps"],
            "clinical_group": cell["clinical_group"],
            "clinical_group_code": clinical_group_code,
            "functional_level": functional_level,
            "admission_source_timing": admission_source_timing,
            "comorbidity_level": comorbidity_level,
            "case_mix_weight": cell["weight"],
            "lupa_threshold": cell["lupa_threshold"],
            "area_code": area["code"],
            "area_name": area["name"],
            "wage_index": wage_index,
            "national_base_rate": self.base_rate,
            "labor_share": LABOR_SHARE,
            "submitted_quality_data": self.submitted_quality_data,
            "period_payment": round(period_payment, 2),
            "estimated_payment": round(period_payment, 2),
            "is_lupa": False,
            "payment_year": PAYMENT_YEAR,
            "calculation_date": datetime.now().strftime("%Y-%m-%d"),
            "disclaimer": DISCLAIMER,
        }

        if visits_by_discipline:
            result.update(
                self._apply_lupa(
                    visits_by_discipline, cell["lupa_threshold"], wage_index,
                    first_skilled_discipline, is_initial_or_only_period,
                )
            )
        return result

    def _apply_lupa(self, visits_by_discipline, threshold, wage_index,
                    first_skilled_discipline, is_initial_or_only_period):
        unknown = [d for d in visits_by_discipline if d not in self.per_visit_rates]
        if unknown:
            return {
                "lupa_error": "Unknown discipline(s): %s. Expected: %s"
                % (", ".join(sorted(unknown)), ", ".join(sorted(self.per_visit_rates))),
            }

        total_visits = sum(int(v) for v in visits_by_discipline.values())
        if total_visits >= threshold:
            return {"total_visits": total_visits, "is_lupa": False}

        # LUPA: pay per visit instead of the full period amount. Per-visit
        # amounts are wage-adjusted on the same labor / non-labor split.
        lupa_total = 0.0
        breakdown = {}
        for discipline, visits in visits_by_discipline.items():
            visits = int(visits)
            if visits <= 0:
                continue
            rate = self.per_visit_rates[discipline]
            adjusted = rate * LABOR_SHARE * wage_index + rate * NON_LABOR_SHARE
            line_total = adjusted * visits
            breakdown[discipline] = {
                "visits": visits,
                "national_rate": rate,
                "wage_adjusted_rate": round(adjusted, 2),
                "subtotal": round(line_total, 2),
            }
            lupa_total += line_total

        add_on = 0.0
        if is_initial_or_only_period and first_skilled_discipline in LUPA_ADD_ON_FACTORS:
            rate = self.per_visit_rates[first_skilled_discipline]
            adjusted = rate * LABOR_SHARE * wage_index + rate * NON_LABOR_SHARE
            factor = LUPA_ADD_ON_FACTORS[first_skilled_discipline]
            # The add-on pays the first visit at the factor, i.e. an extra
            # (factor - 1) x the per-visit amount on top of the visit itself.
            add_on = adjusted * (factor - 1)
            lupa_total += add_on

        return {
            "is_lupa": True,
            "total_visits": total_visits,
            "lupa_threshold": threshold,
            "lupa_visit_breakdown": breakdown,
            "lupa_add_on_discipline": first_skilled_discipline if add_on else None,
            "lupa_add_on_amount": round(add_on, 2) if add_on else 0.0,
            "estimated_payment": round(lupa_total, 2),
            "lupa_note": (
                "Visit count (%d) is below the LUPA threshold (%d) for this "
                "HIPPS group, so the period is paid per visit rather than as a "
                "full 30-day period." % (total_visits, threshold)
            ),
        }

    def payment_range(self, clinical_group_code, area_code, comorbidity_level=None):
        """Floor / ceiling across every functional level and admission timing.

        Useful when only the diagnosis and location are known, which is the
        common case for a code-lookup tool. Returns the span of possible payments
        rather than implying a single number is knowable.
        """
        missing, invalid = self._validate(
            clinical_group_code, FUNCTIONAL_LEVELS[0], ADMISSION_SOURCE_TIMINGS[0],
            0 if comorbidity_level is None else comorbidity_level, area_code,
        )
        if missing or invalid:
            return {"error": "Invalid inputs.", "missing_inputs": missing,
                    "invalid_inputs": invalid}

        comorbidity_levels = (
            COMORBIDITY_LEVELS if comorbidity_level is None else (comorbidity_level,)
        )
        outcomes = []
        for level in FUNCTIONAL_LEVELS:
            for timing in ADMISSION_SOURCE_TIMINGS:
                for comorbidity in comorbidity_levels:
                    outcomes.append(
                        self.calculate_payment(
                            clinical_group_code, level, timing, comorbidity, area_code
                        )
                    )
        payments = [o["period_payment"] for o in outcomes]
        lowest = min(outcomes, key=lambda o: o["period_payment"])
        highest = max(outcomes, key=lambda o: o["period_payment"])
        return {
            "clinical_group_code": clinical_group_code,
            "clinical_group": CLINICAL_GROUPS[clinical_group_code],
            "area_code": lowest["area_code"],
            "area_name": lowest["area_name"],
            "wage_index": lowest["wage_index"],
            "combinations": len(outcomes),
            "min_payment": round(min(payments), 2),
            "max_payment": round(max(payments), 2),
            "min_hipps": lowest["hipps_code"],
            "max_hipps": highest["hipps_code"],
            "lupa_thresholds": sorted({o["lupa_threshold"] for o in outcomes}),
            "payment_year": PAYMENT_YEAR,
            "disclaimer": DISCLAIMER,
        }


def format_payment_lines(pay):
    """Render a payment result as display lines, or None if it isn't payable.

    Returns None when the calculator reported missing/invalid inputs, so callers
    simply omit the section rather than showing a partial or guessed figure.
    """
    if not pay or pay.get("error") or not pay.get("estimated_payment"):
        return None

    lines = [
        "",
        "CY %d ESTIMATED REIMBURSEMENT:" % pay["payment_year"],
        "HIPPS Code: %s (%s, %s function, %s, comorbidity %d)" % (
            pay["hipps_code"], pay["clinical_group"], pay["functional_level"].lower(),
            pay["admission_source_timing"], pay["comorbidity_level"],
        ),
        "Payment Amount: ${:,.2f}".format(pay["estimated_payment"]),
        "National 30-Day Rate: ${:,.2f}".format(pay["national_base_rate"]),
        "Case-Mix Weight: {:.4f}".format(pay["case_mix_weight"]),
        "Wage Index: {:.4f} ({})".format(pay["wage_index"], pay["area_name"]),
        "LUPA Threshold: {} visits".format(pay["lupa_threshold"]),
    ]
    if pay.get("is_lupa"):
        lines.append("⚠️ " + pay["lupa_note"])
        if pay.get("lupa_add_on_amount"):
            discipline = pay["lupa_add_on_discipline"]
            lines.append(
                "LUPA add-on ({}): ${:,.2f}".format(
                    DISCIPLINE_LABELS.get(discipline, discipline), pay["lupa_add_on_amount"]
                )
            )
    lines.append("")
    lines.append(pay["disclaimer"])
    return lines


def format_payment_range_lines(rng):
    """Render a floor/ceiling range as display lines, or None if unusable.

    Shown when the user supplied a location but not the full case-mix picture:
    the diagnosis fixes the clinical group, so the payment is bounded even
    though it isn't determined.
    """
    if not rng or rng.get("error"):
        return None
    return [
        "",
        "CY %d ESTIMATED REIMBURSEMENT RANGE:" % rng["payment_year"],
        "${:,.2f} - ${:,.2f}".format(rng["min_payment"], rng["max_payment"]),
        "Clinical Group: %s" % rng["clinical_group"],
        "Wage Index: {:.4f} ({})".format(rng["wage_index"], rng["area_name"]),
        "LUPA Threshold: {} visits".format(
            " or ".join(str(t) for t in rng["lupa_thresholds"])
        ),
        "Range spans %d combinations (%s to %s)." % (
            rng["combinations"], rng["min_hipps"], rng["max_hipps"],
        ),
        "A diagnosis identifies the clinical group only. Add the functional "
        "level, admission source and timing, and comorbidity adjustment for an "
        "exact HIPPS code and payment.",
        "",
        rng["disclaimer"],
    ]


def discipline_field_name(discipline):
    """Form field name carrying the visit count for a discipline."""
    return "visits_" + discipline.lower().replace(" ", "_").replace("-", "_")


def parse_payment_inputs(source):
    """Pull PDGM payment inputs out of a Flask form or a JSON dict.

    Returns a kwargs dict for ``ReimbursementService.calculate_payment`` minus
    ``clinical_group_code``, which the caller supplies from the diagnosis lookup.
    Absent or unparseable values come back as None so the calculator reports them
    as missing rather than silently defaulting.
    """
    def text(key):
        value = source.get(key)
        return value.strip() if isinstance(value, str) else value

    comorbidity = text("comorbidity_level")
    try:
        comorbidity = int(comorbidity) if comorbidity not in (None, "") else None
    except (TypeError, ValueError):
        comorbidity = None

    visits = source.get("visits_by_discipline")
    if not isinstance(visits, dict):
        visits = {}
        for discipline in PER_VISIT_RATES:
            raw = text(discipline_field_name(discipline))
            try:
                count = int(raw) if raw not in (None, "") else 0
            except (TypeError, ValueError):
                count = 0
            if count > 0:
                visits[discipline] = count

    first_skilled = text("first_skilled_discipline") or None
    initial = text("is_initial_or_only_period")
    if isinstance(initial, str):
        initial = initial.lower() not in ("false", "0", "no", "")

    return {
        "functional_level": text("functional_level") or None,
        "admission_source_timing": text("admission_source_timing") or None,
        "comorbidity_level": comorbidity,
        "area_code": text("area_code") or None,
        "visits_by_discipline": visits or None,
        "first_skilled_discipline": first_skilled,
        "is_initial_or_only_period": True if initial is None else bool(initial),
    }


def extract_pdgm_code_from_response(ai_response):
    """Extract a PDGM clinical group name from AI text, for usage tracking.

    Deliberately does not match bare single letters. The previous version matched
    ``\\b[A-L]\\b``, so any stray capital letter in prose ("vitamin D", a bulleted
    "C.") was read as a clinical group.
    """
    import re

    patterns = (
        # Real 5-character HIPPS codes, e.g. 1KC11.
        r"[1-4][A-L][A-C][1-3]1",
        # Legacy pseudo-codes still produced by some prompts.
        r"MMTA\d{2}", r"SURG\d{2}", r"BEHAV\d{2}", r"COMPLEX\d{2}",
        # Clinical group names as they appear in the diagnosis CSV.
        r"BEHAVE_HEALTH", r"COMPLEX", r"MMTA_AFTER", r"MMTA_CARDIAC",
        r"MMTA_ENDO", r"MMTA_GI_GU", r"MMTA_INFECT", r"MMTA_OTHER",
        r"MMTA_RESP", r"MS_REHAB", r"NEURO_REHAB", r"WOUND",
    )
    match = re.search(r"\b(%s)\b" % "|".join(patterns), ai_response or "")
    return match.group(1) if match else None


def ai_map_phrase_to_code_with_payment(ai_map_func, phrase, *args, **kwargs):
    """Return the AI mapping response unchanged.

    Payment figures are no longer appended to free-text AI output. A payment
    requires the functional level, admission source and timing, and comorbidity
    adjustment, none of which can be recovered from a diagnosis phrase. Callers
    that want a payment should use ``ReimbursementService.calculate_payment``
    with explicit inputs, or ``payment_range`` for a floor/ceiling.

    The signature keeps ``*args``/``**kwargs`` so existing call sites that still
    pass a ZIP code and visit count keep working.
    """
    return ai_map_func(phrase)
