"""Referral readiness check for account reps.

Answers "why home health, why now?" before a referral is sent to intake, by
checking the five things that most often send intake back to the referral
source: a primary diagnosis that groups under PDGM, a precipitating event, a
valid face-to-face encounter, homebound status, and a qualifying skilled need.

The rules are applied to every referral regardless of payer, the way agencies
that hold all referrals to Medicare standards work. Sources:

* Face-to-face: 42 CFR 424.22(a)(1)(v) — encounter no more than 90 days before
  or 30 days after the start of care, related to the primary reason for home
  care, performed by a physician or allowed practitioner. Telehealth counts.
* Homebound: Medicare Benefit Policy Manual, Ch. 7, 30.1.1 — Criterion One
  (either part) AND Criterion Two (both parts). Homebound status is confirmed
  by the clinician at the start-of-care visit, so it is informational here and
  never makes a referral "not ready" or adds a request to the referral source.
* Skilled need: 42 CFR 409.42(c) — intermittent skilled nursing, PT or SLP, or
  a continuing need for OT. OT alone cannot open a case; aide or MSW alone never
  qualifies.
* Admission source: an acute or post-acute inpatient stay in the 14 days before
  the start of care makes the period "institutional"; an observation stay or ED
  visit does not.

The primary diagnosis is judged by ``assess_primary_diagnosis`` against the
mapping release for the planned start-of-care date — the same assessment the
lookup and HIPPS calculator use — so the readiness check cannot disagree with
them.

Deterministic and AI-free on purpose: reps need an instant answer, and every
red flag has to be explainable to a physician's office. Nothing is stored.
"""

import re
from datetime import date, datetime

from services.cms_data import CLINICAL_GROUPS
from services.pdgm import datasets
from services.pdgm.eligibility import assess_primary_diagnosis
from services.pdgm.impl import normalize_icd10
from services.pdgm.phrase_match import match_primary

GREEN, YELLOW, RED = "green", "yellow", "red"
# Shown for education but excluded from the overall status and the message.
INFO = "info"

PHI_NOTICE = (
    "Do not enter patient names, dates of birth, MRNs or other identifiers. "
    "Describe the clinical situation only."
)

# Symptom-level and status diagnoses that reps hear most and that do not group.
# Every example code is asserted to fail ``assess_primary_diagnosis`` in
# tests/test_referral_readiness.py, so this table cannot drift from the data.
RED_FLAG_DIAGNOSES = [
    {
        "key": "weakness",
        "pattern": r"\b(weak(ness)?|debility|debilitated|decondition(ed|ing)?|failure to thrive|ftt|malaise|frail(ty)?)\b",
        "codes": ["M6281", "R531", "R54", "R627", "R5381"],
        "why": "Weakness, debility, deconditioning and failure to thrive are symptom codes. They do not group under PDGM, so they cannot be the primary diagnosis.",
        "ask": "What condition caused the weakness or decline? Please name the diagnosis being treated, for example the reason for the hospital stay (heart failure, COPD, pneumonia, sepsis), a stroke, a fracture or Parkinson's disease.",
    },
    {
        "key": "gait_falls",
        "pattern": r"\b(gait|unsteady|unsteadiness|difficulty walking|trouble walking|falls?|fall risk|balance)\b",
        "codes": ["R262", "R2689", "R2681", "R296", "Z9181"],
        "why": "Gait problems, unsteadiness and falls are symptoms. They do not group under PDGM.",
        "ask": "What is causing the gait problem or falls? Please name the underlying condition, for example osteoarthritis, neuropathy, after-effects of a stroke, Parkinson's disease or a fracture.",
    },
    {
        "key": "shortness_of_breath",
        "pattern": r"\b(sob|short(ness)? of breath|dyspnea)\b",
        "codes": ["R0602"],
        "why": "Shortness of breath is a symptom and does not group.",
        "ask": "What is causing the shortness of breath? Please name the diagnosis, for example heart failure, COPD or pneumonia.",
    },
    {
        "key": "edema",
        "pattern": r"\b(edema|swelling)\b",
        "codes": ["R600"],
        "why": "Edema is a symptom and does not group.",
        "ask": "What is causing the swelling? Please name the diagnosis, for example heart failure, venous insufficiency, lymphedema or kidney disease.",
    },
    {
        "key": "dizziness",
        "pattern": r"\b(dizz(y|iness)|lightheaded(ness)?)\b",
        "codes": ["R42"],
        "why": "Dizziness is a symptom and does not group.",
        "ask": "What is causing the dizziness? Please name the diagnosis if one has been made.",
    },
    {
        "key": "pain",
        "pattern": r"\b(pain|aches?)\b",
        "codes": ["R52"],
        "why": "Pain without a cause is a symptom code and does not group.",
        "ask": "Where is the pain and what is causing it? Please name the condition, for example osteoarthritis, a fracture, recovery from surgery or cancer.",
    },
    {
        "key": "cognitive",
        "pattern": r"\b(memory (loss|problems?)|forgetful(ness)?|confus(ed|ion)|cognitive decline)\b",
        "codes": ["R4181"],
        "why": "Memory loss and age-related cognitive decline are symptom codes and do not group.",
        "ask": "Has a specific diagnosis been made, such as Alzheimer's disease or another type of dementia? If so, please document it.",
    },
    {
        "key": "joint_status",
        "pattern": r"\b(s/?p|status post|history of|hx( of)?)\b.{0,30}\b(knee|hip|shoulder|joint)\b.{0,20}\b(replacement|arthroplasty|tka|tha)\b|\b(tka|tha)\b",
        "codes": ["Z96651"],
        "why": "\"Status post\" a joint replacement records that the joint is there; it does not group. Aftercare following the joint replacement surgery does.",
        "ask": "Please state that the patient needs aftercare following the joint replacement surgery, and include the date of surgery.",
    },
    {
        "key": "stroke_history",
        "pattern": r"\b(history of|hx( of)?|old|prior|past)\b.{0,15}\b(stroke|cva|tia)\b",
        "codes": ["Z8673"],
        "why": "A history of stroke with no lasting effects does not group.",
        "ask": "Does the patient have lasting effects from the stroke, such as weakness on one side, speech or swallowing problems? Please name them; those are what home health treats.",
    },
    {
        "key": "generic_aftercare",
        "pattern": r"\b(follow[- ]?up|post[- ]?hospital|after hospital|hospital follow|general aftercare)\b",
        "codes": ["Z09", "Z5189"],
        "why": "A general follow-up or aftercare visit does not group. The diagnosis being treated does.",
        "ask": "What was the hospital stay or recent treatment for? Please name the diagnosis home health will be treating.",
    },
    {
        "key": "bedbound",
        "pattern": r"\b(bed ?bound|bedridden|bed confine(d|ment))\b",
        "codes": ["Z7401"],
        "why": "Being bedbound is a status, not a diagnosis, and does not group.",
        "ask": "What condition has left the patient bedbound? Please name the diagnosis.",
    },
]

_CAUSE_CONNECTOR = re.compile(
    r"\b(due to|secondary to|caused by|because of|from|r/t|related to|d/t|after|following)\b"
)

EVENTS = {
    "hospital_discharge": "Hospital discharge (inpatient stay)",
    "post_acute_discharge": "SNF, rehab or LTCH discharge",
    "observation_or_ed": "ED visit or observation stay",
    "new_diagnosis": "New diagnosis",
    "exacerbation": "Worsening of a condition",
    "medication_change": "New or changed medications",
    "surgery": "Recent surgery",
    "fall_or_injury": "Recent fall or injury",
    "functional_decline": "Decline in function at home",
    "none": "Nothing recent / not sure",
}
_INSTITUTIONAL_EVENTS = {"hospital_discharge", "post_acute_discharge"}

PRACTITIONERS = {
    "physician": "Physician (MD/DO)",
    "np": "Nurse practitioner",
    "pa": "Physician assistant",
    "cns": "Clinical nurse specialist",
    "cnm": "Certified nurse-midwife",
    "other": "Other / not sure",
}

HOMEBOUND_C1 = {
    "device": "Needs a cane, walker, wheelchair or crutches to leave home",
    "assistance": "Needs another person's help to leave home",
    "transport": "Needs special transportation",
    "contraindicated": "Leaving home is medically inadvisable",
}
HOMEBOUND_C2 = {
    "normal_inability": "Normally unable to leave home",
    "taxing_effort": "Leaving home takes considerable and taxing effort",
}

SERVICES = {
    "sn": "Skilled nursing",
    "pt": "Physical therapy",
    "slp": "Speech therapy",
    "ot": "Occupational therapy",
    "aide": "Home health aide",
    "msw": "Social worker",
}
_QUALIFYING_SERVICES = {"sn", "pt", "slp"}

# Phrases that are commonly offered as the homebound reason and do not meet the
# definition on their own.
_WEAK_HOMEBOUND = re.compile(
    r"\b(elderly|old age|lives alone|doesn'?t drive|does not drive|no car|no transportation|no ride)\b"
)


def _parse_date(value):
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v]
    return [v for v in str(value).split(",") if v]


def _check(key, title, status, findings, asks):
    return {"key": key, "title": title, "status": status, "findings": findings, "asks": asks}


_FLAG_ASKS = {
    "ECOI": "What injury or condition resulted from the fall or accident? Please name it; an external cause cannot be the primary diagnosis.",
    "MANIFESTATION": "What is the underlying condition that caused this? It has to be documented and listed first.",
    "UNACCEPTABLE_PDX": "This diagnosis cannot be the main reason for home health. What condition is home health being ordered to treat? Please name it in the referral.",
    "NO_CLINICAL_GROUP": "This diagnosis cannot be the main reason for home health. What condition is home health being ordered to treat? Please name it in the referral.",
}
_UNSPECIFIED_ASK = (
    "Can the note be more specific about the main diagnosis, for example the type, "
    "site, side, whether it is acute or chronic, and any complications, where known?"
)


def check_diagnosis(text, icd10_code, icd10_data, data_error=None):
    """``icd10_data`` is the mapping for the start-of-care date, or None when
    that date has no verified release (``data_error`` says why)."""
    title = "Why home health: primary diagnosis"
    text = (text or "").strip()
    code = normalize_icd10(icd10_code)

    if code:
        shown = (icd10_code or "").strip().upper()
        if icd10_data is None:
            return _check("diagnosis", title, YELLOW,
                          ["%s could not be checked: %s" % (shown, data_error)],
                          [])
        row = icd10_data.get(code)
        assessment = assess_primary_diagnosis(row)
        flags = assessment["flags"]
        if not row:
            return _check("diagnosis", title, YELLOW,
                          ["%s was not found in the PDGM mapping for this start-of-care date. "
                           "Check the code for typos; intake will confirm it." % shown],
                          [])
        description = row.get("description", "")

        if assessment["primary_eligibility"]["eligible"]:
            group = CLINICAL_GROUPS.get(row.get("pdgm_clinical_group_code"), "")
            findings = ["%s (%s) groups to PDGM clinical group %s." % (shown, description, group)]
            status, asks = GREEN, []
            for flag in flags:
                if flag["code"] == "UNSPECIFIED_PDX":
                    status = YELLOW
                    findings.append("This is an unspecified code. It groups, but intake may need more detail.")
                    asks.append(_UNSPECIFIED_ASK)
                else:
                    findings.append("Intake will review: %s." % flag["message"].rstrip("."))
            return _check("diagnosis", title, status, findings, asks)

        findings = ["%s (%s) cannot be the primary diagnosis." % (shown, description)]
        findings += [f["explanation"] for f in flags if f["type"] == "error"]
        asks = []
        for flag in RED_FLAG_DIAGNOSES:
            if code in flag["codes"]:
                asks.append(flag["ask"])
                break
        else:
            blocking = assessment["primary_eligibility"]["blocking_codes"]
            asks.append(next((_FLAG_ASKS[c] for c in blocking if c in _FLAG_ASKS),
                             _FLAG_ASKS["NO_CLINICAL_GROUP"]))
        return _check("diagnosis", title, RED, findings, asks)

    if not text:
        return _check("diagnosis", title, RED,
                      ["No reason for home health was given."],
                      ["What condition is home health being ordered to treat?"])

    lowered = text.lower()
    choices = _code_choices(text, icd10_data)
    if choices:
        # Never auto-selected: the rep confirms which one the documentation supports.
        check = _check("diagnosis", title, YELLOW,
                       ["Possible primary diagnosis codes for \"%s\". Each one groups under PDGM. "
                        "Tap the one that matches the doctor's documentation." % text],
                       [])
        check["choices"] = choices
        return check

    matched = [f for f in RED_FLAG_DIAGNOSES if re.search(f["pattern"], lowered)]
    if not matched:
        # Words alone can't prove the diagnosis groups, so never green without a code.
        return _check("diagnosis", title, YELLOW,
                      ["No matching primary diagnosis code was found for \"%s\". The condition may not "
                       "group under PDGM as a primary, or may be worded differently. Try other wording, "
                       "or check it in the PDGM Lookup." % text],
                      ["What is the ICD-10 code for the main diagnosis home health will treat?"])

    findings = [f["why"] for f in matched]
    asks = [f["ask"] for f in matched]
    if _CAUSE_CONNECTOR.search(lowered):
        findings.append("A cause appears to be named. Make sure the physician's note lists that cause as the diagnosis being treated, not the symptom.")
        return _check("diagnosis", title, YELLOW, findings, asks)
    return _check("diagnosis", title, RED, findings, asks)


def _code_choices(text, icd10_data, limit=5):
    """Grouping candidates for referral wording, or for the cause it names."""
    if icd10_data is None:
        return []
    found = match_primary(text, icd10_data, limit=limit)
    if not found:
        # "weakness due to CHF exacerbation": match the named cause.
        parts = _CAUSE_CONNECTOR.split(text.lower(), maxsplit=1)
        if len(parts) == 3:
            found = match_primary(parts[2], icd10_data, limit=limit)
    return [{
        "code": c["code"],
        "description": c["description"],
        "group": CLINICAL_GROUPS.get(c["row"].get("pdgm_clinical_group_code"), ""),
    } for c in found]


def check_event(event, event_date, soc):
    title = "Why now: what changed"
    event = event or ""
    if event not in EVENTS or event == "none":
        return _check("event", title, RED,
                      ["No recent event or change in condition was given, so there is no answer to \"why now?\"."],
                      ["What changed recently that makes home health needed now? For example a hospital stay, a new diagnosis, a worsening condition, new medications or a fall."])

    findings = ["Precipitating event: %s." % EVENTS[event]]
    status = GREEN
    asks = []
    happened = _parse_date(event_date)
    if happened and soc:
        days_before = (soc - happened).days
        if days_before < 0:
            findings.append("The event date is after the planned start of care. Check the dates.")
            status = YELLOW
        elif days_before > 90:
            findings.append("The event was %d days before the planned start of care. Ask what has changed since then." % days_before)
            asks.append("The event we have is more than 90 days old. Has anything changed recently, such as a worsening condition or new medications?")
            status = YELLOW
        if event in _INSTITUTIONAL_EVENTS and 0 <= days_before <= 14:
            findings.append("Discharged within 14 days of the start of care, so the period is institutional.")
        elif event in _INSTITUTIONAL_EVENTS:
            findings.append("Discharged more than 14 days before the start of care, so the period is community.")
    elif event in _INSTITUTIONAL_EVENTS:
        findings.append("Add the discharge date: a discharge within 14 days of the start of care makes the period institutional.")
    if event == "observation_or_ed":
        findings.append("An ED visit or observation stay is a valid reason for \"why now\", but it does not count as an institutional admission.")
    return _check("event", title, status, findings, asks)


def check_face_to_face(f2f_date, practitioner, related, soc):
    title = "Face-to-face encounter"
    findings, asks = [], []
    status = GREEN

    encounter = _parse_date(f2f_date)
    if not encounter:
        return _check("f2f", title, RED,
                      ["No face-to-face encounter date was given."],
                      ["When did the physician or practitioner last see the patient (in person or by telehealth)? Please send the visit note."])
    if soc:
        delta = (soc - encounter).days
        if delta > 90:
            findings.append("The encounter was %d days before the planned start of care. It must be no more than 90." % delta)
            asks.append("The last visit is more than 90 days before the start of care. The patient needs a new face-to-face visit (in person or telehealth) related to the reason for home health.")
            status = RED
        elif delta < -30:
            findings.append("The encounter is more than 30 days after the planned start of care. It must be within 30.")
            status = RED
        elif delta < 0:
            findings.append("The encounter is planned %d days after the start of care. That is allowed up to 30 days; make sure it happens." % -delta)
            status = YELLOW
        else:
            findings.append("Encounter %d days before the planned start of care, within the 90-day window." % delta)

    if practitioner not in PRACTITIONERS:
        findings.append("Who performed the encounter was not given.")
        asks.append("Who saw the patient for the face-to-face visit (physician, NP, PA, CNS or nurse-midwife)?")
        status = RED if status == RED else YELLOW
    elif practitioner == "other":
        findings.append("The encounter must be done by a physician, NP, PA, CNS or certified nurse-midwife. Intake should confirm this one.")
        asks.append("Please confirm the credentials of the practitioner who saw the patient for the face-to-face visit.")
        status = RED if status == RED else YELLOW
    else:
        findings.append("Performed by: %s." % PRACTITIONERS[practitioner])

    if related == "no":
        findings.append("The visit was not about the reason for home health. The encounter must be related to the primary reason for home care.")
        asks.append("The face-to-face note needs to address the condition home health will treat. Can the practitioner add that, or see the patient for it?")
        status = RED
    elif related != "yes":
        findings.append("Confirm the visit note addresses the reason for home health.")
        asks.append("Does the face-to-face visit note address the condition home health will treat?")
        status = RED if status == RED else YELLOW
    return _check("f2f", title, status, findings, asks)


def check_homebound(c1, c2, notes):
    title = "Homebound status"
    c1 = [v for v in _as_list(c1) if v in HOMEBOUND_C1]
    c2 = [v for v in _as_list(c2) if v in HOMEBOUND_C2]
    findings = []
    if c1:
        findings.append("Criterion One indicators noted: %s." % "; ".join(HOMEBOUND_C1[v] for v in c1))
    if c2:
        findings.append("Criterion Two indicators noted: %s." % "; ".join(HOMEBOUND_C2[v].lower() for v in c2))
    if notes and _WEAK_HOMEBOUND.search(notes.lower()):
        findings.append("Age, living alone or not driving do not make a patient homebound on their own.")
    findings += [
        "Confirmed by the clinician at the start-of-care visit. If the patient is not homebound, they will not be admitted.",
        "What the clinician looks for: Criterion One, needing a device, another person's help or special "
        "transportation to leave home, or leaving being medically inadvisable; and Criterion Two, both a normal "
        "inability to leave home and leaving taking considerable and taxing effort.",
    ]
    return _check("homebound", title, INFO, findings, [])


def check_skilled_need(services, reason):
    title = "Skilled need"
    services = [v for v in _as_list(services) if v in SERVICES]
    findings, asks = [], []
    if not services:
        return _check("skilled", title, RED,
                      ["No services were selected."],
                      ["Which services is the patient being referred for (skilled nursing, physical therapy, speech therapy, occupational therapy)?"])

    names = ", ".join(SERVICES[v] for v in services)
    if _QUALIFYING_SERVICES.intersection(services):
        status = GREEN
        findings.append("Qualifying skilled service: %s." % names)
    elif "ot" in services:
        status = RED
        findings.append("Occupational therapy alone cannot open a home health case. It only qualifies as a continuing need after skilled nursing, PT or speech therapy.")
        asks.append("Does the patient also need skilled nursing, physical therapy or speech therapy? Occupational therapy alone cannot start home health.")
    else:
        status = RED
        findings.append("An aide or social worker alone does not qualify for home health. The patient needs skilled nursing, PT or speech therapy.")
        asks.append("What skilled care does the patient need, for example nursing for medication changes, wound care or disease teaching, or physical therapy?")

    if status == GREEN and not (reason or "").strip():
        status = YELLOW
        findings.append("Add what the skilled care is for, for example teaching a new medication, wound care, or therapy after a fall.")
        asks.append("What will the nurse or therapist be doing for the patient? For example teaching new medications, wound care, monitoring after a hospital stay, or strength and gait training.")
    return _check("skilled", title, status, findings, asks)


def evaluate(data, today=None):
    """Run every check on a referral. ``data`` is a dict (form or JSON body).

    The start of care stands in for the claim From date when choosing the
    diagnosis mapping release.
    """
    from services.pdgm.repository import get_icd10_map

    get = data.get
    today = today or datasets.today()
    soc = _parse_date(get("soc_date")) or today

    icd10_data, data_error, diagnosis_data = None, None, None
    try:
        diagnosis_data = datasets.diagnosis_metadata(soc.isoformat())
        icd10_data = get_icd10_map(soc.isoformat())
    except datasets.DiagnosisDateError as exc:
        data_error = str(exc)
    except datasets.DiagnosisDataError:
        data_error = "diagnosis data verification failed"

    checks = [
        # A tapped code choice takes precedence over the typed code field.
        check_diagnosis(get("diagnosis"), get("icd10_choice") or get("icd10_code"), icd10_data, data_error),
        check_event(get("event"), get("event_date"), soc),
        check_face_to_face(get("f2f_date"), get("f2f_practitioner"), get("f2f_related"), soc),
        check_homebound(_multi(data, "homebound_c1"), _multi(data, "homebound_c2"), get("homebound_notes")),
        check_skilled_need(_multi(data, "services"), get("skilled_reason")),
    ]

    statuses = [c["status"] for c in checks if c["status"] != INFO]
    if RED in statuses:
        overall = RED
    elif YELLOW in statuses:
        overall = YELLOW
    else:
        overall = GREEN

    asks = [ask for c in checks for ask in c["asks"]]
    message = compose_message(asks)
    return {
        "overall": overall,
        "overall_label": OVERALL_LABELS[overall],
        "soc_date": soc.isoformat(),
        "diagnosis_data": diagnosis_data,
        "checks": checks,
        "asks": asks,
        "message": message,
        "summary": compose_summary(overall, checks, message, soc),
    }


def _multi(data, key):
    getlist = getattr(data, "getlist", None)
    if callable(getlist):
        return getlist(key)
    return data.get(key)


OVERALL_LABELS = {
    GREEN: "Ready to send to intake",
    YELLOW: "Almost ready: confirm the items below",
    RED: "Not ready: get the items below from the referral source",
}
STATUS_LABELS = {GREEN: "OK", YELLOW: "CHECK", RED: "MISSING", INFO: "AT SOC VISIT"}


def compose_summary(overall, checks, message, soc):
    """The whole result as plain text, for sharing with a rep."""
    lines = ["REFERRAL READINESS CHECK (pdgmlookup.com)",
             "Planned start of care: %s" % soc.isoformat(),
             "Result: %s" % OVERALL_LABELS[overall], ""]
    for c in checks:
        lines.append("[%s] %s" % (STATUS_LABELS[c["status"]], c["title"]))
        lines += ["  - %s" % f for f in c["findings"]]
        lines += ["    > %s %s (%s)" % (ch["code"], ch["description"], ch["group"]) for ch in c.get("choices", [])]
        lines.append("")
    if message:
        lines += ["MESSAGE FOR THE REFERRAL SOURCE", message, ""]
    lines.append("Intake makes the final decision on every referral.")
    return "\n".join(lines)


def compose_message(asks):
    """A note the rep can paste into a text or email to the referral source."""
    if not asks:
        return ""
    lines = ["To complete this home health referral, could you please send or add to the notes:", ""]
    lines += ["%d. %s" % (i, ask) for i, ask in enumerate(asks, 1)]
    lines += ["", "Thank you!"]
    return "\n".join(lines)
