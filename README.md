# PDGM Lookup Tool

A Flask-based web application that maps ICD-10 diagnosis codes to PDGM (Patient-Driven Groupings Model) clinical groups for Medicare home health reimbursement. Combines a 74,000+ row authoritative CSV dataset with OpenAI-powered intelligent fallback to deliver compliant, accurate results in real time.

---

## Features

### 1. PDGM Code Lookup
- Enter an ICD-10 code (e.g., `I10`) or a clinical phrase (e.g., "congestive heart failure")
- **Direct CSV match**: instant lookup against the official PDGM diagnosis mapping
- **AI fallback**: when no exact code match is found, OpenAI maps the phrase to the best candidate code(s) from the CSV, validated before returning
- Returns: clinical group, comorbidity group, primary awarding flag, code-first sequencing, billable status, and a clinical rationale

### 2. Reimbursement Estimation
- Provide an optional ZIP code and visit count alongside any lookup
- Calculates estimated Medicare payment using the $1,901.12 national base rate, PDGM case-mix multipliers (A-L), and state-level wage index adjustments
- Detects Low-Utilization Payment Arrangement (LUPA) when visit counts fall below thresholds and recalculates to per-visit rates
- Includes late-episode timing adjustment (5% reduction)

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
- An OpenAI API key (for AI features; CSV lookups work without it)

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
export OPENAI_API_KEY="sk-your-key-here"    # optional for AI features
export FLASK_SECRET_KEY="change-me"

# Run
flask --app wsgi:app run
```

The app starts at `http://127.0.0.1:5000` with a SQLite database (`pdgm_dev.db`). No external services required.

### Run Tests

```bash
pip install pytest
OPENAI_API_KEY=test pytest tests/ -v
```

All 17 tests pass in ~1.5 seconds using in-memory SQLite and stubbed OpenAI.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | For AI features | - | OpenAI API key |
| `FLASK_SECRET_KEY` | Production | `dev-secret-change-me` | Session signing key |
| `DATABASE_URL` | Production | `sqlite:///pdgm_dev.db` | PostgreSQL connection string |
| `OPENAI_MODEL` | No | `gpt-4-turbo` | Primary OpenAI model |
| `FALLBACK_MODEL` | No | `gpt-4` | Fallback model when primary fails validation |
| `MAIL_SERVER` | For email | `smtp.gmail.com` | SMTP server |
| `MAIL_PORT` | For email | `587` | SMTP port |
| `MAIL_USE_TLS` | For email | `True` | Enable TLS |
| `MAIL_USERNAME` | For email | - | SMTP username |
| `MAIL_PASSWORD` | For email | - | SMTP password |
| `PDGM_CSV_PATH` | No | `./CCFTF_pdgm_diagnosis_mapping.csv` | Path to PDGM mapping CSV |
| `EXCLUDED_XLSX_PATH` | No | `./section111excludedicd10-jan2025_0.xlsx` | Section 111 exclusion list |

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
| `/api/lookup` | POST | `{"query": "I10"}` | Lookup by ICD-10 code or clinical phrase |
| `/api/roadmap` | POST | `{"diagnosis": "...", "pdgm_group": "...", "disciplines": ["SN"]}` | Generate documentation roadmap |
| `/api/assessment` | POST | `{"diagnosis": "...", "pdgm_group": "..."}` | Generate sample OASIS assessment |

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
  -e OPENAI_API_KEY=sk-your-key \
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

Set the required environment variables (`OPENAI_API_KEY`, `DATABASE_URL`, `FLASK_SECRET_KEY`) on your hosting platform.

---

## Data Sources

### PDGM Diagnosis Mapping CSV
`CCFTF_pdgm_diagnosis_mapping.csv` — 74,261 rows with 7 columns:

| Column | Example | Description |
|--------|---------|-------------|
| `icd10_code` | `I10` | ICD-10 code (no dots) |
| `description` | `Essential (primary) hypertension` | Clinical description |
| `pdgm_clinical_group_code` | `H` | Single-letter group code (A-L) |
| `pdgm_clinical_group_name` | `MMTA_CARDIAC` | Full PDGM group name |
| `PRIMARY_AWARDING_FLAG` | `0` | Can be primary diagnosis (0/1) |
| `COMORBIDITY_GROUP` | `No_group` | Comorbidity classification |
| `CODE_FIRST` | `0` | Must be sequenced first (0/1) |

### PDGM Clinical Groups

| Code | Group Name | Multiplier | Description |
|------|-----------|------------|-------------|
| A | MMTA_OTHER | 1.00 | Medical management, other |
| B | NEURO_REHAB | 1.05 | Neurological rehabilitation |
| C | WOUND | 0.98 | Wound care |
| D | COMPLEX | 1.10 | Complex nursing / acute care |
| E | MS_REHAB | 1.02 | Musculoskeletal rehabilitation |
| F | BEHAVE_HEALTH | 0.97 | Behavioral health |
| G | MMTA_AFTER | 1.00 | Post-surgical MMTA |
| H | MMTA_CARDIAC | 1.03 | Cardiac MMTA |
| I | MMTA_ENDO | 1.00 | Endocrine MMTA |
| J | MMTA_GI_GU | 1.01 | GI/GU MMTA |
| K | MMTA_INFECT | 0.95 | Infectious disease MMTA |
| L | MMTA_RESP | 1.04 | Respiratory MMTA |

### Section 111 Exclusions
`section111excludedicd10-jan2025_0.xlsx` — Codes excluded from primary diagnosis selection per CMS Section 111 reporting requirements.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Flask 2.x with Blueprints |
| Database | SQLite (dev) / PostgreSQL (prod) via SQLAlchemy |
| AI | OpenAI API (gpt-4-turbo with gpt-4 fallback) |
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
│   ├── reimbursement_service.py    # Payment calculations
│   └── pdgm/
│       ├── impl.py                 # CSV loading, normalization, parsing
│       ├── repository.py           # Data access layer
│       └── rules_engine.py         # Lookup orchestration
├── schemas/pdgm.py                 # Request validation
├── enhanced_pdgm_functions.py      # Medical synonyms, candidate matching
├── enhanced_prompt_manager.py      # AI prompt template management
├── prompts/                        # Prompt template files
├── templates/                      # Jinja2 HTML templates
├── static/                         # CSS, JS, icons
├── tests/                          # 17 pytest tests
├── CCFTF_pdgm_diagnosis_mapping.csv   # 74K ICD-10 to PDGM mappings
├── section111excludedicd10-jan2025_0.xlsx  # Exclusion list
├── requirements.txt                # Python dependencies (15 packages)
├── Dockerfile                      # Production container
└── ARCHITECTURE.md                 # Architecture documentation
```

---

## License

Proprietary - ClearChoiceFTF / ReferralMate
