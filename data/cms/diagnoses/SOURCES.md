# Verified 2026 PDGM diagnosis mappings

Verified against CMS packages on **2026-10-21**. The repository's existing
`CCFTF_pdgm_diagnosis_mapping.csv` matches the April 2026 diagnosis table in
every source field. It remains the baseline; release overlays reconstruct the
January and October tables without duplicating the full 74K-row CSV.

| Claim From date supported by this app | CMS HHGS release | Diagnosis rows |
|---|---|---:|
| 2026-01-01 through 2026-03-31 | 07.0.26 | 74,719 |
| 2026-04-01 through 2026-09-30 | 07.1.26 | 74,719 |
| 2026-10-01 through 2026-12-31 | 07.2.26 | 74,879 |

The October table adds 190 codes and removes 30 relative to April. Other fields
also change, including code-first references, descriptions, and subchapters.
January differs from April in code-first references, five unacceptable-primary
flags, and three clinical-group assignments. Use the selected table in full;
an additions-only update is insufficient.

Sources, linked from the [CMS HHGS page](https://www.cms.gov/medicare/payment/prospective-payment-systems/home-health/home-health-grouper-software):

- [January 2026 package, 07.0.26](https://www.cms.gov/files/zip/jan-2026-hh-pps-grouper-software-hh-pdgm-v07-0-26-posted-12-1-2025.zip), member `tables/Versions/07026/RT/Diagnosis_Codes.txt`.
- [April 2026 package, 07.1.26](https://www.cms.gov/files/zip/apr-2026-hh-pps-grouper-software-hh-pdgm-v07-1-26-posted-02-10-2026.zip), member `tables/Versions/07126/RT/Diagnosis_Codes.txt`.
- [October 2026 package, 07.2.26](https://www.cms.gov/files/zip/oct-2026-hh-pps-grouper-software-hh-pdgm-v07-2-26-posted-08-20-2026.zip), member `tables/Versions/07226/RT/Diagnosis_Codes.txt`.

`manifest.json` records full archive member paths and SHA-256 hashes for each
download, raw source table, baseline CSV, overlay, and reconstructed table.
The source tables are Windows-1252, tab-delimited. The build script renames
`DIAGNOSIS`, `DESCRIPTION`, and `CLINICAL_GROUP` to the app's existing field
names and retains the existing group display-name mapping. It preserves every
source field, including `PREDECESSOR_DX` and non-Boolean `CODE_FIRST` entries.
Overlays contain full changed/new rows; the manifest records deletions.

## Runtime behavior

`service_date` means the **claim period's From date**, not an individual visit
date or an assumed start-of-care date. Omitting it uses today's date in
America/Chicago and pins that date for the request. Results include the selected
date, grouper release, effective/supported interval, verification date, row count,
and CMS source URL under `diagnosis_data`.

Lookup, HIPPS primary/secondary diagnoses, live comorbidity checks, comparisons,
suggestions, AI candidates, and offline exports use the same date-selected
diagnosis release. An exact code absent from that release stays unresolved;
prefix search and AI must not silently substitute another code. Legacy lookup
and AI-cache keys include the date. Default-date lookups reselect the release
when the calendar crosses a boundary, without requiring a process restart.

Malformed dates and dates outside the bundled 2026 window return HTTP 400.
The December 31 limit is the app's supported window, not an assertion about
future CMS releases. Future dates require a verified refresh. Corrupt or
mismatched data raises a data error instead of silently using another table.
`PDGM_CSV_PATH`, if set, must point to the exact verified April baseline; an
unverified replacement is not treated as an official CMS mapping.

This change versions **diagnosis mapping data**. CY 2026 payment tables and the
rest of the app's grouper implementation remain separate; this is not a claim
that the app executes or reproduces the complete CMS Java grouper.

## Reproduce the verification

Download the three linked ZIP packages to a local directory, naming them
`07.0.26.zip`, `07.1.26.zip`, and `07.2.26.zip`, then run:

```bash
python scripts/build_diagnosis_releases.py --source-dir /path/to/zips
```

The script checks the package hashes, verifies the baseline against April in
every source field, and deterministically rebuilds the overlays and manifest.
Review future CMS effective dates and table changes, update source specifications
and supported intervals, rebuild, and run release-boundary tests before shipping
a refresh. Payment-year updates require their own validation.
