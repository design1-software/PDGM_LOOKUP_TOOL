"""Reproduce the verified 2026 diagnosis overlays from CMS ZIP packages.

Usage: python scripts/build_diagnosis_releases.py --source-dir /path/to/zips
The directory must contain 07.0.26.zip, 07.1.26.zip, and 07.2.26.zip.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ('07.0.26', '07026', '2026-01-01', '2026-03-31',
     'jan-2026-hh-pps-grouper-software-hh-pdgm-v07-0-26-posted-12-1-2025.zip',
     '40cdaad09e83ec67d37ae041b59bdc2a9f9fd8b76638dd36702da0236f4628e7'),
    ('07.1.26', '07126', '2026-04-01', '2026-09-30',
     'apr-2026-hh-pps-grouper-software-hh-pdgm-v07-1-26-posted-02-10-2026.zip',
     '0c8c35996fea3be516c000afa5ae67dac64e25d9fb3123ce0f5e16d9f95bf0e7'),
    ('07.2.26', '07226', '2026-10-01', '2026-12-31',
     'oct-2026-hh-pps-grouper-software-hh-pdgm-v07-2-26-posted-08-20-2026.zip',
     'ff3efb8e4a09f5fb9d111df133129dc2e2dbfea829a39b4498e405b3cdcb7f26'),
)
RENAMES = {'DIAGNOSIS': 'icd10_code', 'DESCRIPTION': 'description',
           'CLINICAL_GROUP': 'pdgm_clinical_group_code'}


def digest(content):
    return hashlib.sha256(content).hexdigest()


def canonical_bytes(rows):
    return json.dumps([rows[code] for code in sorted(rows)], sort_keys=True,
                      separators=(',', ':'), ensure_ascii=True).encode()


def build(source_dir, output_dir):
    baseline_path = ROOT / 'CCFTF_pdgm_diagnosis_mapping.csv'
    with baseline_path.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        baseline = {row['icd10_code']: row for row in reader}
    groups = {row['pdgm_clinical_group_code']: row['pdgm_clinical_group_name']
              for row in baseline.values()}
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {'verified_on': '2026-10-21',
                'base_path': 'CCFTF_pdgm_diagnosis_mapping.csv',
                'base_release': '07.1.26',
                'base_sha256': digest(baseline_path.read_bytes()), 'releases': []}
    for version, token, start, end, filename, zip_sha in SOURCES:
        package = (source_dir / (version + '.zip')).read_bytes()
        if digest(package) != zip_sha:
            raise ValueError(f'CMS package checksum mismatch: {version}')
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            member = next(name for name in archive.namelist()
                          if name.endswith(f'/Versions/{token}/RT/Diagnosis_Codes.txt'))
            raw = archive.read(member)
        rows = {}
        for source in csv.DictReader(io.StringIO(raw.decode('cp1252')), delimiter='\t'):
            row = {RENAMES.get(key, key): value for key, value in source.items()}
            row['pdgm_clinical_group_name'] = groups[row['pdgm_clinical_group_code']]
            if row['icd10_code'] in rows:
                raise ValueError('Duplicate CMS diagnosis code')
            rows[row['icd10_code']] = row
        if version == '07.1.26' and rows != baseline:
            raise ValueError('Repository baseline does not match CMS April 2026 in every field')
        upserts = [rows[code] for code in sorted(rows) if rows[code] != baseline.get(code)]
        deleted = sorted(baseline.keys() - rows.keys())
        patch_path = output_dir / (version + '.csv')
        with patch_path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
            writer.writeheader()
            writer.writerows(upserts)
        manifest['releases'].append({
            'version': version, 'effective_from': start, 'effective_through': end,
            'row_count': len(rows), 'canonical_sha256': digest(canonical_bytes(rows)),
            'overlay_path': patch_path.name, 'overlay_sha256': digest(patch_path.read_bytes()),
            'deleted_codes': deleted, 'source_url': 'https://www.cms.gov/files/zip/' + filename,
            'package_sha256': zip_sha, 'source_member': member,
            'source_member_sha256': digest(raw),
        })
        print(f'{version}: {len(rows)} codes, {len(upserts)} overlays, {len(deleted)} deletions')
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data/cms/diagnoses')
    args = parser.parse_args()
    build(args.source_dir, args.output_dir)
