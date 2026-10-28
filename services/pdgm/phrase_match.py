"""Match referral wording to candidate primary-diagnosis codes, instantly.

Built for the referral readiness check, where a rep types what the referral
says ("CHF exacerbation", "s/p left TKA") and should not have to look the code
up elsewhere. Like ``services.pdgm.search``, results are *choices* for the
user to confirm against the documentation; nothing here selects a diagnosis.

Only codes that pass ``assess_primary_diagnosis`` are offered, so every choice
can actually be the primary. Matching is word-based and deterministic: every
core word of the phrase must appear in the code description; laterality,
acuity and similar words only rank results.
"""

import re
import threading
from itertools import groupby

from services.pdgm.eligibility import assess_primary_diagnosis
from services.pdgm.search import ALIASES as SEARCH_ALIASES

# Referral shorthand, applied after the shared search aliases. Search
# vocabulary only, mapped to CMS description wording.
REFERRAL_ALIASES = {
    'cva': 'cerebral infarction',
    'stroke': 'cerebral infarction',
    'total knee replacement': 'aftercare joint replacement',
    'total hip replacement': 'aftercare joint replacement',
    'knee replacement': 'aftercare joint replacement',
    'hip replacement': 'aftercare joint replacement',
    'shoulder replacement': 'aftercare joint replacement',
    'joint replacement': 'aftercare joint replacement',
    'arthroplasty': 'aftercare joint replacement',
    'tka': 'aftercare joint replacement',
    'tha': 'aftercare joint replacement',
    'tkr': 'aftercare joint replacement',
    'thr': 'aftercare joint replacement',
    'hip fracture': 'fracture femur',
    'hip fx': 'fracture femur',
    'fx': 'fracture',
    'sacrum': 'sacral',
    'pna': 'pneumonia',
    'esrd': 'end stage renal disease',
    'oa': 'osteoarthritis',
    'djd': 'osteoarthritis',
    'cad': 'atherosclerotic heart disease',
    'pvd': 'peripheral vascular disease',
    'pad': 'peripheral vascular disease',
    'dvt': 'deep vein thrombosis',
    'pe': 'pulmonary embolism',
    'ms': 'multiple sclerosis',
    'als': 'amyotrophic lateral sclerosis',
    'parkinsons': 'parkinson',
    'alzheimers': 'alzheimer',
    'diabetic': 'diabetes',
    'left side weakness': 'hemiplegia left',
    'right side weakness': 'hemiplegia right',
    'left sided weakness': 'hemiplegia left',
    'right sided weakness': 'hemiplegia right',
    'hemiparesis': 'hemiplegia',
    'surgical wound infection': 'infection following procedure',
    'wound infection': 'infection following procedure',
    'surgical site infection': 'infection following procedure',
    'leg': 'lower limb',
    'arm': 'upper limb',
}

# Description words for narrower or unrelated conditions. A code whose
# description has one the phrase didn't ask for ranks below the plain match
# ("hip fracture" should lead with a femur fracture, not a stress fracture).
NARROWING_WORDS = {
    'stress', 'pathological', 'osteoporosis', 'osteopor', 'sequela', 'neonatal',
    'newborn', 'pregnancy', 'childbirth', 'puerperium', 'obstetric',
    'obstetrical', 'postprocedural', 'rheumatic', 'presymptomatic', 'induced',
    'abuse', 'dependence', 'portal', 'resistant', 'gestational', 'congenital',
    'right', 'left', 'secondary', 'ocular', 'intracranial', 'benign',
    'neoplastic', 'physeal', 'periprosthetic', 'nonunion', 'malunion', 'delayed',
    'insertion', 'implant', 'salter', 'pulmonary', 'renovascular', 'sedative',
    'hypnotic', 'anxiolytic', 'alcohol', 'inhalant', 'opioid', 'cocaine',
    'cannabis', 'use',
}

# Newborn (P) and pregnancy (O) chapter codes are left out unless the phrase
# is about pregnancy or a newborn.
_EXCLUDED_CHAPTERS = 'OP'
_CHAPTER_WORDS = {'pregnancy', 'pregnant', 'postpartum', 'obstetric', 'obstetrical',
                  'newborn', 'neonatal', 'infant', 'puerperal', 'delivery'}


# Abbreviations used in the mapping's (CMS short) descriptions, expanded so
# typed words match: "Hemiplga following cerebral infrc ... left nondom side".
DESCRIPTION_ABBREVIATIONS = {
    'unsp': 'unspecified', 'oth': 'other', 'subs': 'subsequent', 'init': 'initial',
    'encntr': 'encounter', 'femr': 'femur', 'hemiplga': 'hemiplegia',
    'infrc': 'infarction', 'nondom': 'nondominant', 'dom': 'dominant',
    'dis': 'disease', 'w': 'with', 'malig': 'malignant', 'neoplm': 'neoplasm',
    'fx': 'fracture', 'path': 'pathological', 'clos': 'closed',
    'disp': 'displaced', 'displ': 'displaced', 'nondisp': 'nondisplaced',
    'humer': 'humerus', 'rad': 'radius', 'musc': 'muscle', 'tend': 'tendon',
    'inj': 'injury', 'athscl': 'atherosclerosis', 'cereb': 'cerebral',
    'hemorrh': 'hemorrhage', 'intcrn': 'intracranial', 'ulc': 'ulcer',
    'r': 'right', 'l': 'left', 'nk': 'neck', 'chr': 'chronic',
    'diab': 'diabetes', 'traum': 'traumatic', 'lacerat': 'laceration',
    'physl': 'physeal', 'insrt': 'insertion', 'implnt': 'implant', 'sltr': 'salter',
    'sedatv': 'sedative', 'hyp': 'hypnotic', 'anxiolytc': 'anxiolytic',
}

# Words that refine a match but are not required to appear in the description.
MODIFIERS = {
    'left', 'right', 'bilateral', 'acute', 'chronic', 'exacerbation', 'recent',
    'new', 'severe', 'mild', 'moderate', 'unspecified', 'with', 'without', 'of',
    'the', 'and', 'in', 'on', 'a', 'an', 'to', 'due', 'after', 'following',
    'status', 'post', 's', 'p', 'sp', 'hx', 'history', 'dx', 'diagnosis',
    'patient', 'pt', 'home', 'health', 'needs', 'need', 'for', 'from',
    'hospital', 'hospitalization', 'discharge', 'stage', 'type',
    # The mechanism of injury is an external cause, never the primary.
    'fall', 'fell', 'falls', 'mechanical',
}

# For an exacerbation, these description words are what CMS uses instead.
_EXACERBATION_WORDS = {'exacerbation', 'acute', 'decompensation'}

_lock = threading.Lock()
_index_cache = {}


def _stem(word):
    if len(word) > 4 and word.endswith('s') and not word.endswith(('ss', 'us', 'is')):
        return word[:-1]
    return word


def _tokens(text):
    return [_stem(w) for w in re.findall(r'[a-z0-9]+', text.lower())]


def _description_tokens(description):
    words = [DESCRIPTION_ABBREVIATIONS.get(w, w) for w in re.findall(r'[a-z0-9]+', description.lower())]
    return [_stem(w) for w in words], ' '.join(words)


def _apply_aliases(text):
    text = ' ' + ' '.join(re.findall(r"[a-z0-9/]+", text.lower().replace("'s", 's'))) + ' '
    text = text.replace('s/p', ' status post ').replace('/', ' ')
    for aliases in (SEARCH_ALIASES, REFERRAL_ALIASES):
        for alias in sorted(aliases, key=len, reverse=True):
            text = re.sub(r'\b' + re.escape(alias) + r'\b', aliases[alias], text)
    return text


def _index(data):
    """Tokenised descriptions of primary-eligible codes, cached per mapping."""
    key = id(data)
    with _lock:
        cached = _index_cache.get(key)
        if cached is not None and cached[0] is data:
            return cached[1]
    entries = []
    for code, row in data.items():
        if not assess_primary_diagnosis(row)['primary_eligibility']['eligible']:
            continue
        tokens, text = _description_tokens(row.get('description', ''))
        entries.append((code, row, set(tokens), text))
    with _lock:
        _index_cache[key] = (data, entries)
    return entries


def match_primary(phrase, data, limit=5):
    """Candidate primary diagnoses for a phrase: ``[{code, description, row}]``."""
    words = _tokens(_apply_aliases(phrase or ''))
    core = [w for w in words if w not in MODIFIERS]
    if not core:
        return []
    core_set = set(core)
    modifiers = set(words) - core_set
    wants_exacerbation = 'exacerbation' in modifiers
    allow_chapters = bool(_CHAPTER_WORDS & set(words))
    # A short phrase with no detail ("sepsis") is best matched by the
    # unspecified code first, with specific variants after it.
    vague = len(core_set) <= 2 and not (modifiers - {'with', 'of', 'the', 'and', 'a', 'an'})

    ranked = []
    for code, row, tokens, text in _index(data):
        if not core_set <= tokens:
            continue
        bonus = len(modifiers & tokens)
        if wants_exacerbation:
            if 'acute on chronic' in text:
                bonus += 3
            elif _EXACERBATION_WORDS & tokens:
                bonus += 2
        if vague and 'unspecified' in tokens:
            bonus += 1
        if code[0] in _EXCLUDED_CHAPTERS and not allow_chapters:
            continue
        narrowing = len((NARROWING_WORDS & tokens) - set(words))
        injury = code[0] in 'ST'
        # Home health treats injuries in the aftercare phase: prefer the
        # subsequent-encounter (7th character D) code over initial encounters.
        aftercare = not injury or code.endswith('D')
        ranked.append(((narrowing, -bonus, not aftercare, not text.startswith(core[0]), len(text), code),
                       code, row))
    ranked.sort(key=lambda item: item[0])

    # Show several code families before a second variant of any one family.
    picked, seen = [], set()
    for _, tier in groupby(ranked, key=lambda item: item[0][:3]):
        tier = list(tier)
        for item in tier:
            if item[1][:3] not in seen:
                seen.add(item[1][:3])
                picked.append(item)
        picked.extend(item for item in tier if item not in picked)
        if len(picked) >= limit:
            break

    return [{
        'code': code[:3] + '.' + code[3:] if len(code) > 3 else code,
        'description': row.get('description', ''),
        'row': row,
    } for _, code, row in picked[:limit]]
