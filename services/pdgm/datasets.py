"""Verified CMS diagnosis releases selected by claim From date.

The April baseline plus small release overlays reconstruct each CMS table in
every field. Checksums and row counts fail closed instead of serving guessed data.
"""
import csv
from datetime import date, datetime
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data/cms/diagnoses'


class DiagnosisDateError(ValueError):
    pass


class DiagnosisDataError(RuntimeError):
    pass


def today():
    return datetime.now(ZoneInfo('America/Chicago')).date()


@lru_cache(maxsize=1)
def manifest():
    return json.loads((DATA_DIR / 'manifest.json').read_text())


def select_release(service_date=None):
    if service_date is None or service_date == '':
        selected_date = today()
    elif type(service_date) is date:
        selected_date = service_date
    else:
        try:
            if not isinstance(service_date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', service_date):
                raise ValueError
            selected_date = date.fromisoformat(service_date)
        except ValueError:
            raise DiagnosisDateError('service_date must be a valid YYYY-MM-DD claim From date') from None
    for release in manifest()['releases']:
        if release['effective_from'] <= selected_date.isoformat() <= release['effective_through']:
            return selected_date, release
    raise DiagnosisDateError('No verified diagnosis mapping for this claim From date. '
                             'Supported dates: 2026-01-01 through 2026-12-31.')


def _checked_bytes(path, expected):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != expected:
        raise DiagnosisDataError(f'Diagnosis data checksum mismatch: {path.name}')
    return content


def _read_csv(path, expected):
    _checked_bytes(path, expected)
    with path.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    mapping = {row['icd10_code']: row for row in rows}
    if len(mapping) != len(rows):
        raise DiagnosisDataError('Duplicate diagnosis code in data file')
    return mapping


@lru_cache(maxsize=1)
def _baseline():
    config = manifest()
    path = Path(os.getenv('PDGM_CSV_PATH') or ROOT / config['base_path'])
    return _read_csv(path, config['base_sha256'])


@lru_cache(maxsize=3)
def _load_version(version):
    release = next(r for r in manifest()['releases'] if r['version'] == version)
    rows = _baseline().copy()
    for code in release['deleted_codes']:
        if code not in rows:
            raise DiagnosisDataError('Release deletion does not match baseline')
        del rows[code]
    rows.update(_read_csv(DATA_DIR / release['overlay_path'], release['overlay_sha256']))
    canonical = json.dumps([rows[code] for code in sorted(rows)], sort_keys=True,
                           separators=(',', ':'), ensure_ascii=True).encode()
    if len(rows) != release['row_count'] or hashlib.sha256(canonical).hexdigest() != release['canonical_sha256']:
        raise DiagnosisDataError('Reconstructed diagnosis table does not match verified CMS release')
    return rows


def load_release(service_date=None):
    _, release = select_release(service_date)
    return _load_version(release['version'])


def diagnosis_metadata(service_date=None):
    selected_date, release = select_release(service_date)
    return {
        'service_date': selected_date.isoformat(),
        'grouper_version': release['version'],
        'effective_from': release['effective_from'],
        'effective_through': release['effective_through'],
        'verified_on': manifest()['verified_on'],
        'source_url': release['source_url'],
        'row_count': release['row_count'],
    }
