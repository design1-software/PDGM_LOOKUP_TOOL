"""Deterministic search suggestions, never a clinical diagnosis assignment."""
import re
from itertools import groupby

# Search vocabulary only. These expansions produce choices for documentation
# review; they must never be used to auto-select or establish a diagnosis.
ALIASES = {
    'chf': 'heart failure',
    'congestive heart failure': 'heart failure',
    'high blood pressure': 'hypertension',
    'htn': 'hypertension',
    'heart attack': 'myocardial infarction',
    'afib': 'atrial fibrillation',
    'a fib': 'atrial fibrillation',
    'copd': 'chronic obstructive pulmonary disease',
    'dm': 'diabetes mellitus',
    'dm2': 'type 2 diabetes mellitus',
    'dm1': 'type 1 diabetes mellitus',
    'type two diabetes': 'type 2 diabetes mellitus',
    'lower back pain': 'low back pain',
    'uti': 'urinary tract infection',
    'ckd': 'chronic kidney disease',
    'gerd': 'gastro esophageal reflux disease',
    'acid reflux': 'gastro esophageal reflux disease',
}


def words(text):
    return re.findall(r'[a-z0-9]+', text.lower())


def search_rows(query, data, limit=10):
    term = ' '.join(words(query))
    if not term or limit <= 0:
        return []
    norm = query.replace('.', '').replace(' ', '').upper()
    code_search = bool(re.fullmatch(r'[A-Z][0-9][0-9A-Z]*', norm))
    if not code_search:
        for alias in sorted(ALIASES, key=len, reverse=True):
            term = re.sub(r'\b' + re.escape(alias) + r'\b', ALIASES[alias], term)
        tokens = set(term.split())
    ranked = []
    for code, row in data.items():
        description = row.get('description', '')
        if code_search:
            if not code.startswith(norm):
                continue
            rank = (code != norm, len(code), code)
        else:
            text = ' '.join(words(description))
            # Require all requested terms, including qualifiers and negations.
            # A broad match is preferable to inventing undocumented specifics.
            if not tokens.issubset(set(text.split())):
                continue
            qualifiers = re.findall(r'\btype [0-9]+\b', term)
            if any(qualifier not in text for qualifier in qualifiers):
                continue
            if 'without ' + term in text:
                continue
            rank = (text != term, term not in text,
                    len(tokens) > 1 and not text.startswith(term),
                    len(text), code)
        ranked.append((rank, code, description))
    ranked.sort(key=lambda item: item[0])
    if not code_search:
        # Broad terms should expose several code families instead of filling
        # the entire list with one family's many complication variants.
        diversified = []
        for _, tier in groupby(ranked, key=lambda item: item[0][:3]):
            seen, representatives, remaining = set(), [], []
            for item in tier:
                family = item[1][:3]
                if family in seen:
                    remaining.append(item)
                else:
                    seen.add(family)
                    representatives.append(item)
            diversified.extend(representatives + remaining)
        ranked = diversified
    return [{'code': code[:3] + '.' + code[3:] if len(code) > 3 else code,
             'description': description} for _, code, description in ranked[:limit]]
