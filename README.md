# PDGM Lookup Tool

A Flask-based web application that maps ICD-10 diagnosis codes to PDGM (Patient-Driven Groupings Model) clinical groups for Medicare home health reimbursement. Combines a 74,000+ row authoritative CSV dataset with Claude-powered intelligent fallback to deliver compliant, accurate results in real time. Payment estimates are computed from the CY 2026 CMS Home Health PPS final rule.

---

## Features

### 1. PDGM Code Lookup
- Enter an ICD-10 code (e.g., `I10`) or a clinical phrase (e.g., "congestive heart failure")
- **Direct CSV match**: instant lookup against the official PDGM diagnosis mapping
- **AI fallback**: when no exact code match is found, Claude maps the phrase to the best candidate code(s) from the CSV, validated before returning
- Returns: clinical group, comorbidity group, code-first sequencing and a clinical rationale; lookup results do not establish billability or payment coverage

### 2. Reimbursement Estimation (CY 2026)
All figures come from the CY 2026 CMS Home Health PPS final rule (CMS-1828-F) and CR 14304, read at runtime from `data/cms/cy2026/`. Nothing is estimated — see [data/cms/cy2026/SOURCES.md](data/cms/cy2026/SOURCES.md) for provenance and the CY 2027 refresh procedure.

- **Payment range** on any lookup: pick a site of service and get the floor and ceiling for that diagnosis's clinical group. A diagnosis fixes the clinical group but not the functional level, admission source and timing, or comorbidity adjustment, so a single figure is not knowable from a code alone — the range spans all 36 combinations.
- **Exact payment** via `POST /api/hipps`: supply GG0130/GG0170 functional items, admission source, and episode timing, and the tool derives the real HIPPS code (e.g. `1KC11`), its CMS case-mix weight, and its LUPA threshold.
- **Geography**: 489 CMS wage index areas (417 urban CBSAs, 51 statewide rural, 21 transition codes), wage index 0.2719–1.8317. CMS keys the wage index on CBSA, not ZIP, and publishes no ZIP-to-CBSA mapping in the rate files, so the tool takes an `area_code` rather than guessing from a ZIP.
- **Payment math** follows 90 FR 55405: case-mix adjust the $2,038.22 national 30-day rate, split labor (74.9%) and non-labor (25.1%), wage-adjust the labor portion, recombine.
- **LUPA**: per-HIPPS thresholds (2–5 visits, varies by group), per-visit rates by discipline, and the CY 2025-onward add-on factors.

Not implemented: outlier payments, partial-period adjustments, dNPWT, and HHVBP adjustments.

### Shared Primary-Diagnosis Validation
`POST /api/lookup` and `POST /api/hipps` return the same `primary_eligibility`
assessment and diagnosis `flags` from the loaded mapping. Unacceptable principal,
manifestation, external-cause, missing-code, and missing/invalid clinical-group
conditions block HIPPS generation. An unspecified-code warning alone does not
block a code with an assigned clinical group. These checks do not establish
coverage, billability, or complete coding compliance.

Lookup keeps the diagnosis description and reasons visible but suppresses a
payment range for blocked primary diagnoses. HIPPS returns HTTP 400 with the
same reasons, without generating a HIPPS code or payment. The legacy direct-code
page uses the same assessment. The calculator button is disabled for blocked or
unverified results, and a new lookup clears any previous HIPPS/payment result.

### Actionable Diagnosis Alerts
Each diagnosis flag includes a plain-language `explanation` and `next_step`.
Lookup shows these inside the existing alert cards; HIPPS returns the same fields,
and legacy direct-code results include them as text. Unresolved results are labeled
“Diagnosis not verified,” and missing clinical groups are explained as a limitation
of the loaded mapping rather than proof that an ICD-10-CM code is invalid.

A nonzero `CODE_FIRST` entry (including values such as `10` or `110`) triggers a
sequencing-review warning. The mapping's numeric entry is not a replacement
ICD-10-CM code, and the application does not decode the corresponding instruction
or determine its applicability from patient documentation. It does not automatically
block every code-first entry; existing manifestation/primary-diagnosis restrictions
still apply. Review the applicable Tabular List and service-date instructions.
See [ICD-10-CM Official Guidelines, Section I.A.13](https://www.cms.gov/files/document/fy-2027-icd-10-cm-coding-guidelines.pdf)
for conditional sequencing instructions.

Guidance directs staff to review existing documentation before requesting provider
clarification and does not infer a replacement diagnosis. Provider-request generation,
changes to code-search fallback behavior, and diagnosis-data refresh are separate work.

### 3. Recertification Calculator
- Input a Start of Care (SOC) date and episode length (default 60 days)
- Calculates the recertification due date
- Export to calendar via `.ics` download (Outlook, Google Calendar, Apple Calendar)
- Send email reminders via SMTP

### 4. Documentation Roadmap & OASIS Assessment
- AI-generated discipline-specific documentation guidance (RN, PT, OT, SLP, HHA)
- Sample OASIS-E assessment generation with official CMS item numbers and terminology
- Uses structured prompt templates from `/prompts/` with PDGM-group-specific references

---

## Quick Start

### Prerequisites
- Python 3.11+
- An Anthropic API key (for AI features; CSV lookups and payment estimates work without it)

### Local Development

```bash
# Clone
git clone https://github.com/design1-software/PDGM_LOOKUP_TOOL.git
cd PDGM_LOOKUP_TOOL

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-your-key-here"   # optional for AI features
export FLASK_SECRET_KEY="change-me"

# Run
flask --app wsgi:app run
```

The app starts at `http://127.0.0.1:5000` with a SQLite database (`pdgm_dev.db`). No external services required.

### Run Tests

```bash
pip install pytest
pytest tests/ -q
```

All 55 tests pass in ~3 seconds using in-memory SQLite and a stubbed Anthropic client (see `tests/conftest.py`) — no API key needed.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | For AI features | - | Anthropic API key |
| `FLASK_SECRET_KEY` | Production | `dev-secret-change-me` | Session signing key |
| `DATABASE_URL` | Production | `sqlite:///pdgm_dev.db` | PostgreSQL connection string |
| `CLAUDE_MODEL` | No | `claude-sonnet-5` | Claude model ID. Set to `claude-opus-5` to trade cost for capability. |
| `AI_LOG_PATH` | No | `./ai_logs.jsonl` | Where AI interactions are logged |
| `MAIL_SERVER` | For email | `smtp.gmail.com` | SMTP server |
| `MAIL_PORT` | For email | `587` | SMTP port |
| `MAIL_USE_TLS` | For email | `True` | Enable TLS |
| `MAIL_USERNAME` | For email | - | SMTP username |
| `MAIL_PASSWORD` | For email | - | SMTP password |
| `PDGM_CSV_PATH` | No | `./CCFTF_pdgm_diagnosis_mapping.csv` | Path to PDGM mapping CSV |

---

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check. Returns `{"status": "ok"}` |
| `/version` | GET | Environment and version info |

### PDGM Lookup

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/api/lookup` | POST | `{"query": "I10", "area_code": "26300"}` | Lookup by ICD-10 code or clinical phrase. With `area_code`, also returns `payment_range`. |
| `/api/hipps` | POST | `{"primary_icd10": "...", "secondary_icd10s": [], "admission_source": 1, "episode_timing": 1, "gg0130": {}, "gg0170": {}, "area_code": "..."}` | Derive the real HIPPS code and its exact CY 2026 payment |
| `/api/compare` | POST | `{"code_a": "...", "code_b": "...", "area_code": "..."}` | Side-by-side diagnosis comparison |
| `/api/comorbidity-check` | POST | `{"primary_icd10": "...", "secondary_icd10s": [...]}` | Comorbidity adjustment without a full HIPPS calculation |
| `/api/roadmap` | POST | `{"diagnosis": "...", "pdgm_group": "...", "disciplines": ["SN"]}` | Generate documentation roadmap |
| `/api/assessment` | POST | `{"diagnosis": "...", "pdgm_group": "..."}` | Generate sample OASIS assessment |

### CMS Reference Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/wage-index-areas` | GET | All 489 CY 2026 wage index areas — the valid values for `area_code` |
| `/api/case-mix-weights` | GET | All 432 CMS case-mix weights and LUPA thresholds, keyed by HIPPS code |

> **`area_code`, not ZIP.** CMS keys the HH PPS wage index on CBSA and publishes no ZIP-to-CBSA mapping in the rate files, so these endpoints take a CBSA, statewide rural (`999xx`), or transition (`50xxx`) code. Passing a bare `zip_code` to `/api/hipps` returns a 400 explaining this rather than guessing.

> Most `/api/*` endpoints are behind the lead-capture gate and return 403 until the session has completed it. `/healthz` and `/version` are not gated.

### Web UI

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET/POST | Main lookup form with results display |
| `/recert` | GET/POST | Recertification date calculator |
| `/recert/ics` | GET | Download `.ics` calendar event |
| `/recert/email` | POST | Send recert reminder email |

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET/POST | User login |
| `/auth/register` | GET/POST | User registration |
| `/auth/logout` | GET | Logout |

---

## Example: API Lookup

**Request:**
```bash
curl -X POST http://localhost:5000/api/lookup \
  -H "Content-Type: application/json" \
  -d '{"query": "I10"}'
```

**Response:**
```json
{
  "icd10": "I10",
  "raw": {
    "icd10_code": "I10",
    "description": "Essential (primary) hypertension",
    "pdgm_clinical_group_code": "H",
    "pdgm_clinical_group_name": "MMTA_CARDIAC",
    "PRIMARY_AWARDING_FLAG": "0",
    "COMORBIDITY_GROUP": "No_group",
    "CODE_FIRST": "0"
  },
  "details": {
    "icd10_code": "I10",
    "description": "Essential (primary) hypertension",
    "pdgm_clinical_group_code": "H",
    "pdgm_clinical_group_name": "MMTA_CARDIAC"
  }
}
```

---

## Deployment

### Docker

The included Dockerfile is platform-agnostic and works with any container hosting provider (Railway, Render, Fly.io, AWS ECS, Azure Container Apps, DigitalOcean App Platform, etc.).

```bash
docker build -t pdgm-lookup .
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY=sk-ant-your-key \
  -e FLASK_SECRET_KEY=your-secret \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e PORT=8080 \
  pdgm-lookup
```

The image uses Python 3.11-slim with Gunicorn (2 workers, 2 threads, 120s timeout). Health check endpoint is `GET /healthz`.

### Without Docker

Any platform that supports Python WSGI apps can run this directly:

```bash
pip install -r requirements.txt
gunicorn wsgi:app --bind 0.0.0.0:8080 --workers 2 --threads 2
```

Set the required environment variables (`ANTHROPIC_API_KEY`, `DATABASE_URL`, `FLASK_SECRET_KEY`) on your hosting platform.

---

## Data Sources

### PDGM Diagnosis Mapping CSV
`CCFTF_pdgm_diagnosis_mapping.csv` — 74,719 rows built from the **CMS HH PDGM Grouper v07.1.26 (April 2026)** official `Diagnosis_Codes.txt` table. This is the latest available CMS data as of March 2026.

| Column | Example | Description |
|--------|---------|-------------|
| `icd10_code` | `I10` | ICD-10 code (no dots) |
| `description` | `Essential (primary) hypertension` | Clinical description |
| `pdgm_clinical_group_code` | `H` | Single-letter group code (A-L, or NA) |
| `pdgm_clinical_group_name` | `MMTA_CARDIAC` | Full PDGM group name |
| `PRIMARY_AWARDING_FLAG` | `0` | Present in the source data but not a usable signal — `0` on 74,718 of the 74,719 rows. Use `UNACCEPTABLE_PDX` for principal-diagnosis eligibility. |
| `COMORBIDITY_GROUP` | `No_group` | Comorbidity classification |
| `CODE_FIRST` | `0` | Must be sequenced first (0/1) |
| `SUBCHAPTER` | `I10-I16` | ICD-10 subchapter range |
| `MANIFESTATION_FLAG` | `0` | Manifestation code (0/1) |
| `ECOI_FLAG` | `0` | External cause of injury (0/1) |
| `UNACCEPTABLE_PDX` | `0` | Cannot be principal diagnosis (0/1) |
| `UNSPECIFIED_PDX` | `0` | Unspecified — more specific code preferred (0/1) |
| `PREDECESSOR_DX` | `` | Predecessor code (for split/replaced codes) |

### PDGM Clinical Groups

There is no single multiplier per clinical group. Each group's case-mix weight
depends on the full HIPPS combination — functional level, admission source and
timing, and comorbidity adjustment — so each spans a range of 36 CMS weights.
The letter is HIPPS position 2.

| Code | Group Name | CY 2026 weight range | LUPA thresholds | Description |
|------|-----------|----------------------|-----------------|-------------|
| A | MMTA_OTHER | 0.5823 – 1.5053 | 2, 3, 4 | Medical management, other |
| B | NEURO_REHAB | 0.6986 – 1.6798 | 2, 3, 4, 5 | Neurological rehabilitation |
| C | WOUND | 1.0048 – 1.9558 | 3, 4, 5 | Wound care |
| D | COMPLEX | 0.5624 – 1.4406 | 2, 3 | Complex nursing / acute care |
| E | MS_REHAB | 0.6081 – 1.5632 | 2, 3, 4, 5 | Musculoskeletal rehabilitation |
| F | BEHAVE_HEALTH | 0.5364 – 1.4837 | 2, 3, 4 | Behavioral health |
| G | MMTA_AFTER | 0.5738 – 1.5513 | 2, 3, 4 | Post-surgical MMTA |
| H | MMTA_CARDIAC | 0.5647 – 1.5053 | 2, 3, 4 | Cardiac MMTA |
| I | MMTA_ENDO | 0.8597 – 1.7193 | 3, 4, 5 | Endocrine MMTA |
| J | MMTA_GI_GU | 0.5587 – 1.5053 | 2, 3, 4 | GI/GU MMTA |
| K | MMTA_INFECT | 0.5828 – 1.5578 | 2, 3 | Infectious disease MMTA |
| L | MMTA_RESP | 0.5742 – 1.5166 | 2, 3, 4 | Respiratory MMTA |

Query `GET /api/case-mix-weights` for all 432 weights and thresholds keyed by HIPPS code.

### CY 2026 CMS Rate Data
`data/cms/cy2026/` — the CMS source files behind every payment figure, with full provenance in [SOURCES.md](data/cms/cy2026/SOURCES.md):

| File | Contents |
|------|----------|
| `case_mix_weights_lupa.csv` | All 432 HIPPS case-mix weights and LUPA thresholds |
| `wage_index.csv` | 489 wage index areas (urban CBSA, statewide rural, transition codes) |
| `comorbidity_interactions.xlsx` | Low/high comorbidity adjustment interactions |

Rate constants (the $2,038.22 national 30-day rate, per-visit amounts, LUPA add-on factors) are transcribed into `services/reimbursement_service.py` with inline citations to CR 14304 and 90 FR 55405.

### Section 111 Reference File (Not Used by the Application)
`section111_excluded_icd10_fy2026.xlsx` is retained as a reference only. Section 111 exclusions concern liability, no-fault, and workers’ compensation reporting, not home health billability or PDGM primary-diagnosis eligibility. The application does not load this file or pass its exclusions to AI. See [CMS ICD Code Lists](https://www.cms.gov/medicare/coordination-benefits-recovery/overview/icd-code-lists).

### Keeping Data Current
CMS updates PDGM groupings annually (October, with mid-year updates in January/April). To update:
1. Download the latest HH PDGM Grouper from [CMS Grouper Software](https://www.cms.gov/medicare/payment/prospective-payment-systems/home-health/home-health-grouper-software)
2. Extract `Diagnosis_Codes.txt` from the `tables/Versions/<latest>/RT/` folder inside the ZIP
3. Rebuild the CSV (tab-delimited source → comma-delimited with group name mapping)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Flask 2.x with Blueprints |
| Database | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy |
| AI | Anthropic Claude API (`claude-sonnet-5`) |
| Auth | Flask-Login |
| Caching | Flask-Caching (SimpleCache) |
| Email | Flask-Mail (SMTP) |
| Migrations | Flask-Migrate (Alembic) |
| Validation | Marshmallow |
| WSGI Server | Gunicorn |
| Container | Docker (python:3.11-slim) |
| Monitoring | Sentry SDK |

---

## Project Structure

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full architecture deep-dive.

```
.
├── app.py                          # Core PDGM logic module
├── wsgi.py                         # WSGI entrypoint
├── app_core/
│   ├── __init__.py                 # create_app() factory
│   ├── config.py                   # Dev/Prod/Test configs
│   ├── extensions.py               # Flask extensions
│   ├── errors.py                   # Error handlers
│   └── routes/auth.py              # Auth endpoints
├── blueprints/
│   ├── api/routes.py               # /healthz, /api/lookup, /api/roadmap, /api/assessment
│   ├── main/routes.py              # / (main lookup page)
│   └── recert/routes.py            # /recert calculator
├── models/
│   ├── user.py                     # User model (email, password)
│   └── oasis.py                    # OASIS-E assessment models
├── services/
│   ├── cms_data.py                 # Loaders for the CY 2026 CMS source files
│   ├── reimbursement_service.py    # CY 2026 payment calculations
│   └── pdgm/
│       ├── hipps.py                # HIPPS generation + CMS case-mix lookup
│       ├── comorbidity.py          # Comorbidity adjustment
│       ├── functional.py           # GG0130/GG0170 functional scoring
│       ├── impl.py                 # CSV loading, normalization, parsing
│       ├── repository.py           # Data access layer
│       └── rules_engine.py         # Lookup orchestration
├── schemas/pdgm.py                 # Request validation
├── enhanced_pdgm_functions.py      # Medical synonyms, candidate matching
├── enhanced_prompt_manager.py      # AI prompt template management
├── prompts/                        # Prompt template files
├── templates/                      # Jinja2 HTML templates
├── static/                         # CSS, JS, icons
├── tests/                          # 55 pytest tests
├── data/cms/cy2026/                # CMS CY 2026 rate data + SOURCES.md
├── CCFTF_pdgm_diagnosis_mapping.csv   # 74K ICD-10 to PDGM mappings
├── section111_excluded_icd10_fy2026.xlsx   # Unused Section 111 reference file
├── requirements.txt                # Python dependencies (15 packages)
├── Dockerfile                      # Production container
└── ARCHITECTURE.md                 # Architecture documentation
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
