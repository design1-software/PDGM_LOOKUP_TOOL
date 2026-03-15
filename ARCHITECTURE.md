# Architecture

Detailed technical architecture of the PDGM Lookup Tool MVP.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Application Factory](#application-factory)
3. [Request Flow](#request-flow)
4. [File-by-File Reference](#file-by-file-reference)
5. [Data Models](#data-models)
6. [PDGM Lookup Pipeline](#pdgm-lookup-pipeline)
7. [OpenAI Integration](#openai-integration)
8. [Reimbursement Engine](#reimbursement-engine)
9. [Recertification Calculator](#recertification-calculator)
10. [Caching Strategy](#caching-strategy)
11. [Configuration](#configuration)
12. [Testing](#testing)
13. [Deployment](#deployment)

---

## System Overview

```
                    ┌─────────────────────────────────────┐
                    │           User / Client              │
                    └────────────┬────────────────────────┘
                                 │  HTTP
                    ┌────────────▼────────────────────────┐
                    │         Gunicorn (WSGI)              │
                    │         wsgi.py → create_app()       │
                    └────────────┬────────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐      ┌───────▼───────┐     ┌───────▼───────┐
   │  blueprints/ │      │  blueprints/  │     │  blueprints/  │
   │  main/       │      │  api/         │     │  recert/      │
   │  GET/POST /  │      │  /api/lookup  │     │  /recert      │
   └──────┬──────┘      │  /api/roadmap │     │  /recert/ics  │
          │              │  /api/assess. │     │  /recert/email│
          │              │  /healthz     │     └───────┬───────┘
          │              └───────┬───────┘             │
          │                      │                     │
          └──────────┬───────────┘                     │
                     │                                 │
          ┌──────────▼───────────────┐                 │
          │      app.py              │                 │
          │  (core PDGM logic)       │                 │
          │  - CSV loading           │                 │
          │  - OpenAI calls          │                 │
          │  - Normalization         │                 │
          │  - Validation            │                 │
          └────┬──────────┬──────────┘                 │
               │          │                            │
    ┌──────────▼──┐  ┌────▼──────────────┐   ┌────────▼─────────┐
    │ services/   │  │ OpenAI API        │   │ Flask-Mail       │
    │ pdgm/       │  │ gpt-4-turbo      │   │ (SMTP)           │
    │ reimburse.  │  │ gpt-4 (fallback) │   └──────────────────┘
    └──────┬──────┘  └─────────────────┘
           │
    ┌──────▼──────────────────┐
    │  Data Sources           │
    │  - PDGM CSV (74K rows)  │
    │  - Section 111 XLSX     │
    │  - SQLite / PostgreSQL  │
    └─────────────────────────┘
```

---

## Application Factory

**Location:** `app_core/__init__.py`

The `create_app(config=None)` function builds and configures the Flask application:

```
create_app(config)
  │
  ├─ 1. Create Flask instance
  │     - static_folder → project_root/static
  │     - template_folder → project_root/templates
  │
  ├─ 2. Load configuration
  │     ├─ config param provided → use it directly
  │     ├─ TESTING env → TestingConfig (in-memory SQLite)
  │     ├─ ENVIRONMENT=production → ProductionConfig (PostgreSQL)
  │     └─ default → DevelopmentConfig (file SQLite)
  │
  ├─ 3. Initialize extensions
  │     ├─ db (SQLAlchemy)
  │     ├─ migrate (Flask-Migrate)
  │     ├─ login_manager (Flask-Login)
  │     ├─ mail (Flask-Mail)
  │     └─ cache (Flask-Caching, SimpleCache)
  │
  ├─ 4. Register user_loader callback
  │
  ├─ 5. Create database tables (db.create_all)
  │
  ├─ 6. Register error handlers (404, 500 → JSON)
  │
  └─ 7. Register blueprints
        ├─ api_bp    → /healthz, /version, /api/*
        ├─ main_bp   → /
        ├─ recert_bp → /recert, /recert/ics, /recert/email
        └─ auth_bp   → /auth/login, /auth/register, /auth/logout
```

---

## Request Flow

### Web Form Lookup (POST /)

```
User submits form with query="heart failure", zip_code="10001", visit_count=3
  │
  ├─ normalize_icd10("heart failure") → "HEARTFAILURE"
  │
  ├─ CSV lookup: icd10_data.get("HEARTFAILURE") → None (not a code)
  │
  ├─ AI Fallback:
  │   ├─ expand_with_medical_synonyms("heart failure")
  │   │   → ["heart failure", "chf", "congestive heart failure", "cardiac failure"]
  │   │
  │   ├─ get_candidate_codes_enhanced() → top 15 scored matches from CSV
  │   │   (fuzzy match descriptions against all expanded terms)
  │   │
  │   ├─ Build system prompt (UR/Coding Compliance Nurse persona)
  │   ├─ Build user prompt (candidates + exclusions + clinical input)
  │   │
  │   ├─ Call OpenAI gpt-4-turbo (temp=0.1, max_tokens=350)
  │   │   → "Focus of Care: I5020 Systolic heart failure... ICD-10: I50.20..."
  │   │
  │   ├─ validate_ai_output() → check codes exist in CSV
  │   │   ├─ Valid → use response
  │   │   └─ Invalid → retry with gpt-4 fallback
  │   │
  │   └─ log_ai_interaction() → append to ai_logs.jsonl
  │
  ├─ ReimbursementService.calculate_payment("H", "10001", 3)
  │   ├─ base_rate = $1,901.12
  │   ├─ wage_index = 1.15 (NY prefix "10")
  │   ├─ labor = $1,901.12 * 0.687 * 1.15 = $1,501.47
  │   ├─ non_labor = $1,901.12 * 0.313 = $595.05
  │   ├─ adjusted_base = $2,096.52
  │   ├─ multiplier = 1.03 (MMTA_CARDIAC)
  │   ├─ payment = $2,159.42
  │   ├─ LUPA check: visit_count(3) < threshold(4) → LUPA!
  │   └─ LUPA payment = $150.00 * 3 = $450.00
  │
  ├─ ai_followup_question("heart failure")
  │   → "Would you like to specify: acute exacerbation, chronic systolic,
  │      chronic diastolic, or combined systolic/diastolic?"
  │
  └─ Render index.html with result, follow-up, reimbursement data
```

### API Lookup (POST /api/lookup)

```
JSON: {"query": "I10"}
  │
  ├─ validate_lookup_request() → {"query": "I10"}
  │
  ├─ services/pdgm/rules_engine.py → lookup_pdgm("I10")
  │   ├─ Has digits? Yes → try explain_pdgm_for_icd10("I10")
  │   │   ├─ normalize_icd10("I10") → "I10"
  │   │   ├─ get_icd10_map().get("I10") → CSV row found
  │   │   ├─ parse_pdgm_details(row) → structured dict
  │   │   └─ Return {icd10: "I10", raw: {...}, details: {...}}
  │   └─ (skip search + AI since direct match found)
  │
  └─ Return JSON response
```

---

## File-by-File Reference

### Root

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 335 | Core PDGM logic module. CSV loading, ICD-10 normalization, OpenAI client, AI mapping/follow-up/roadmap/assessment functions. Loads data at import time. |
| `wsgi.py` | 4 | WSGI entrypoint. Imports `create_app()` and creates `app`. |
| `enhanced_pdgm_functions.py` | 233 | Medical synonym dictionaries (37 abbreviations), context keyword extraction, enhanced candidate code scoring (SequenceMatcher fuzzy matching), predefined follow-up questions for 12 common conditions. |
| `enhanced_prompt_manager.py` | 82 | Loads prompt templates from `prompts/` directory. Builds system prompts with `{reference_block}` substitution. Graceful fallback if OASIS models unavailable. |

### App Core (`app_core/`)

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 56 | `create_app()` factory. Loads config, initializes 5 extensions, registers 4 blueprints, creates DB tables. |
| `config.py` | 39 | Three config classes. Dev: SQLite + DEBUG. Prod: PostgreSQL (auto-fixes `postgres://` URIs). Test: in-memory SQLite. Shared: SimpleCache, OPENAI/MAIL settings. |
| `extensions.py` | 10 | Declares `login_manager`, `mail`, `cache`, `migrate` as module-level singletons. |
| `errors.py` | 13 | Registers 404 (JSON) and 500 (JSON + logging) error handlers. |
| `logging.py` | 61 | `JsonRequestFormatter` for structured JSON logging. `setup_structured_logging()` adds request IDs and access logs. |
| `routes/auth.py` | 45 | Login (email+password), register, logout. Uses Flask-Login `login_user`/`logout_user`. |

### Blueprints (`blueprints/`)

| File | Routes | Purpose |
|------|--------|---------|
| `api/routes.py` | `GET /healthz`, `GET /version`, `POST /api/lookup`, `POST /api/roadmap`, `POST /api/assessment` | JSON API endpoints. Validates with `schemas/pdgm.py`. Lookup uses `services/pdgm/rules_engine.py`. Roadmap/assessment call `app.ai_documentation_roadmap` / `app.ai_sample_oasis_assessment`. |
| `main/routes.py` | `GET/POST /` | Main web form. Direct CSV lookup with `@cache.memoize` on code data. AI fallback with `cache.get/set` on responses (30 min TTL). Integrates reimbursement estimation. Renders `index.html`. |
| `recert/routes.py` | `GET/POST /recert`, `GET /recert/ics`, `POST /recert/email` | Recertification calculator. Date arithmetic via `timedelta`. ICS generation (RFC 5545). Email via Flask-Mail. |

### Models (`models/`)

| File | Models | Purpose |
|------|--------|---------|
| `user.py` | `User` | Minimal auth model: `id`, `email` (unique), `password_hash`, `created_at`. Werkzeug password hashing. Flask-Login `UserMixin`. |
| `oasis.py` | `OASISSection`, `OASISItem`, `OASISResponseOption`, `PDGMOASISMapping`, `OASISValidationRule` | OASIS-E assessment data models. Used by `enhanced_prompt_manager.py` for building assessment prompts. Tables auto-created but data population is optional. |

### Services (`services/`)

| File | Classes/Functions | Purpose |
|------|-------------------|---------|
| `reimbursement_service.py` | `ReimbursementService`, `extract_pdgm_code_from_response()`, `ai_map_phrase_to_code_with_payment()` | Medicare payment calculations. National base ($1,901.12), labor/non-labor split (68.7%/31.3%), wage index by ZIP, PDGM multipliers (A-L), LUPA detection, per-visit rate fallback. |
| `pdgm/impl.py` | `normalize_icd10()`, `load_icd10_map()`, `search_icd10_codes()`, `parse_pdgm_details()` | Low-level PDGM data functions. Module-level CSV cache via `_get_map()`. |
| `pdgm/repository.py` | `get_icd10_map()`, `search_icd10()`, `map_phrase_to_code()` | Data access layer. Delegates to `impl.py` for data, `app.py` for AI mapping. |
| `pdgm/rules_engine.py` | `explain_pdgm_for_icd10()`, `lookup_pdgm()` | Orchestration: try direct code match → search by prefix → AI fallback. Returns normalized `{icd10, raw, details}` payload. |

### Schemas (`schemas/`)

| File | Functions | Purpose |
|------|-----------|---------|
| `pdgm.py` | `validate_lookup_request()`, `validate_roadmap_request()`, `validate_assessment_request()` | Lightweight request validation using TypedDict definitions. Custom `ValidationError` exception (no external deps). |

---

## Data Models

### User (MVP)

```
┌─────────────────────────┐
│         users           │
├─────────────────────────┤
│ id          INTEGER PK  │
│ email       VARCHAR(120)│  UNIQUE, NOT NULL
│ password_hash VARCHAR   │
│ created_at  DATETIME    │  DEFAULT: now()
└─────────────────────────┘
```

### OASIS-E (Assessment Support)

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ OASISSection │◄────│   OASISItem      │◄────│ OASISResponseOption │
├──────────────┤     ├──────────────────┤     ├─────────────────────┤
│ id           │     │ id               │     │ id                  │
│ section_code │     │ item_number      │     │ item_id (FK)        │
│ title        │     │ title            │     │ code                │
│ description  │     │ intent           │     │ description         │
│ sort_order   │     │ section_id (FK)  │     │ coding_guidance     │
└──────────────┘     │ timepoints (JSON)│     │ sort_order          │
                     │ disciplines(JSON)│     └─────────────────────┘
                     │ assessment_method│
                     │ is_active        │     ┌─────────────────────┐
                     └─────────┬────────┘     │ OASISValidationRule │
                               │              ├─────────────────────┤
                     ┌─────────▼────────┐     │ id                  │
                     │ PDGMOASISMapping  │     │ rule_name           │
                     ├──────────────────┤     │ rule_type           │
                     │ id               │     │ primary_item_id(FK) │
                     │ pdgm_group       │     │ severity            │
                     │ oasis_item_id(FK)│     │ cms_edit_number     │
                     │ priority_level   │     └─────────────────────┘
                     │ typical_responses│
                     │ clinical_rational│
                     │ discipline_focus │
                     └──────────────────┘
```

---

## PDGM Lookup Pipeline

### Step 1: Normalization

```python
normalize_icd10("i10.1") → "I101"   # strip dots, spaces, uppercase
normalize_icd10("E11.01") → "E1101"
normalize_icd10("heart failure") → "HEARTFAILURE"  # not a valid code
```

### Step 2: Direct CSV Match

The CSV is loaded once at import time into `icd10_data` (dict of 74,261 entries keyed by normalized code). Exact O(1) lookup.

### Step 3: AI Fallback (when no direct match)

```
1. Synonym Expansion
   "CHF" → ["chf", "congestive heart failure", "heart failure", "cardiac failure"]

2. Context Keyword Extraction
   "CHF exacerbation" → ["acute", "acute on chronic", "with exacerbation"]

3. Candidate Code Scoring
   For each of 74,261 CSV rows:
     - Test expanded terms against description
     - Exact substring match → score 1.0
     - Fuzzy match (SequenceMatcher) → score 0.0-1.0
     - Context keyword boost → score * 1.5
     - Filter: score > 0.3
   Sort by score, return top 15

4. OpenAI Prompt Construction
   System: "You are a Utilization Review and Coding Compliance Nurse..."
   User: "Clinical input: 'CHF exacerbation'\nCodes list:\n[15 candidates]\n
          Codes excluded as primary: [Section 111 codes]\n"

5. Response Validation
   - Extract all ICD-10 codes from response via regex
   - Check each against icd10_data dict
   - If any mismatches → retry with fallback model (gpt-4)

6. Logging
   Every AI interaction logged to ai_logs.jsonl with timestamp,
   model, query, response, and any mismatches
```

---

## OpenAI Integration

### Models Used

| Function | Primary Model | Fallback | Temp | Max Tokens |
|----------|--------------|----------|------|-----------|
| `ai_map_phrase_to_code` | gpt-4-turbo | gpt-4 | 0.1 | 350 |
| `ai_followup_question` | gpt-4-turbo | predefined | 0.7 | 120 |
| `ai_documentation_roadmap` | gpt-4-turbo | - | 0.1 | 1,000 |
| `ai_sample_oasis_assessment` | gpt-4-turbo | - | 0.1 | 1,000 |

### Prompt Templates

Stored in `prompts/` directory:

- `roadmap_template.md` — Structure for discipline-specific documentation guidance
- `roadmap_reference.md` — PDGM-specific clinical content
- `oasis_template.md` — Structure for OASIS-E assessment examples
- `oasis_reference.md` — OASIS-specific reference content

Templates use `{reference_block}` placeholder, replaced at runtime with the appropriate reference content.

### Anti-Hallucination Guardrails

1. **Candidate constraint**: AI only sees 15 pre-selected codes from the CSV, not the full 74K set
2. **Post-validation**: extracted codes are checked against `icd10_data` dict
3. **Fallback retry**: if validation fails on primary model, retry with fallback
4. **Section 111 awareness**: excluded codes are passed to the AI prompt so it avoids selecting them as primary
5. **Logging**: every interaction is logged with mismatch details for QA review

---

## Reimbursement Engine

### Calculation Formula

```
IF zip_code provided:
    labor_portion    = national_base ($1,901.12) * 0.687 * wage_index
    non_labor_portion = national_base * 0.313
    adjusted_base    = labor_portion + non_labor_portion
ELSE:
    adjusted_base    = national_base

payment = adjusted_base * pdgm_multiplier

IF episode_timing == 'late':
    payment *= 0.95

IF visit_count < lupa_threshold:
    payment = per_visit_rate * visit_count    # LUPA override
```

### LUPA Thresholds

| PDGM Prefix | Threshold | Per-Visit Rate |
|-------------|-----------|---------------|
| MMTA | 4 visits | $150.00 |
| SURG | 2 visits | $160.00 |
| BEHAV | 7 visits | $140.00 |
| COMPLEX | 6 visits | $170.00 |
| Default | 4 visits | $145.00 |

### Wage Index (by ZIP prefix)

| ZIP Prefix | Region | Wage Index |
|-----------|--------|-----------|
| 10, 11 | NY | 1.15, 1.12 |
| 90-93 | CA | 1.20-1.14 |
| 60 | IL | 1.05 |
| 77 | TX (Houston) | 1.03 |
| 35 | AL | 0.85 |
| Default | - | 0.95 |

---

## Recertification Calculator

### Logic

```python
due_date = start_of_care_date + timedelta(days=episode_length)
# Standard episode: 60 days
# Missed recert = forced discharge + re-admission (billing reset)
```

### ICS Calendar Export (RFC 5545)

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ReferralMate//Recert//EN
BEGIN:VEVENT
DTSTART;VALUE=DATE:20240301
DTEND;VALUE=DATE:20240301
SUMMARY:Recert Due
DESCRIPTION:Recertification due
END:VEVENT
END:VCALENDAR
```

### Email Reminders

Uses Flask-Mail with SMTP. Sends plain text email with the due date to the specified recipient.

---

## Caching Strategy

### Layer 1: CSV Data (Application Lifetime)

```python
# Loaded once at import time (app.py module level)
icd10_data = load_icd10_map()      # dict of 74,261 entries
excluded_codes = load_excluded_codes()  # set of excluded codes
```

### Layer 2: Code Lookups (Flask-Caching)

```python
@cache.memoize(timeout=3600)  # 1 hour
def get_cached_icd10_data(code):
    return icd10_data.get(code)
```

### Layer 3: AI Responses (Flask-Caching)

```python
key = f"ai_response:{query.lower().strip()}"
cached = cache.get(key)
if cached:
    return cached
result = ai_map_phrase_to_code(query)
cache.set(key, result, timeout=1800)  # 30 minutes
```

All caching uses `SimpleCache` (in-process dictionary). No Redis or external cache required.

---

## Configuration

### Development (default)

```python
DEBUG = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///pdgm_dev.db'
CACHE_TYPE = 'SimpleCache'
CACHE_DEFAULT_TIMEOUT = 300
```

### Production

```python
DEBUG = False
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')  # PostgreSQL
CACHE_TYPE = 'SimpleCache'
SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
```

### Testing

```python
TESTING = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

### Environment Variable Summary

| Category | Variables |
|----------|----------|
| **Required (prod)** | `OPENAI_API_KEY`, `DATABASE_URL`, `FLASK_SECRET_KEY` |
| **AI Config** | `OPENAI_MODEL`, `FALLBACK_MODEL` |
| **Email** | `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD` |
| **Data Paths** | `PDGM_CSV_PATH`, `EXCLUDED_XLSX_PATH` |
| **Runtime** | `FLASK_ENV`, `ENVIRONMENT`, `PORT` |

---

## Testing

### Test Suite (17 tests)

```
tests/
├── conftest.py                 # Fixtures: app, client, db; OpenAI stub
├── test_api_lookup.py          # /api/lookup valid + missing query
├── test_api_roadmap.py         # /api/roadmap with mocked AI
├── test_api_assessment.py      # /api/assessment with mocked AI
├── test_normalization.py       # normalize_icd10, normalize_query, form POST
├── test_data_loading.py        # CSV + XLSX loading
├── test_reimbursement_service.py  # Payment calc + LUPA
├── test_recert.py              # GET/POST /recert, ICS, email
├── test_auth_logout.py         # /auth/logout redirect
└── test_prompt_building.py     # Template loading
```

### Test Configuration

- **Database**: in-memory SQLite (`sqlite:///:memory:`)
- **OpenAI**: stubbed at session scope — returns realistic dummy PDGM response
- **Fixtures**: `app` (creates full app), `client` (test client), `db` (creates tables, rollback on teardown)

### Running Tests

```bash
OPENAI_API_KEY=test pytest tests/ -v
# 17 passed in ~1.5s
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
# System deps: gcc, curl
# Install pip packages from requirements.txt
# Gunicorn: 2 workers, 2 threads, 120s timeout
# Health check: curl /healthz every 30s
# Entrypoint: gunicorn wsgi:app
```

### Gunicorn Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Workers | 2 | Fits 512MB container instances |
| Threads | 2 | Handles concurrent requests per worker |
| Timeout | 120s | Accommodates OpenAI response times |
| Keep-alive | 5s | Connection reuse |
| Max requests | 1,000 | Worker recycling to prevent memory leaks |
| Max requests jitter | 100 | Stagger worker restarts |
| Preload | Yes | Share CSV data across workers |

### Platform-Agnostic Deployment

The Dockerfile and Gunicorn config are platform-agnostic. Deploy to any container hosting provider by setting these environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (for AI) | OpenAI API key |
| `DATABASE_URL` | Yes (prod) | PostgreSQL connection string |
| `FLASK_SECRET_KEY` | Yes (prod) | Session signing key |
| `PORT` | Depends on host | Port to bind (default: 8080) |

For non-Docker deployments, run directly with Gunicorn:

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 2 --timeout 120
```

### Production Dependencies (15 packages)

```
flask, flask-sqlalchemy, flask-migrate, flask-login, flask-mail,
flask-caching, gunicorn, openai, openpyxl, marshmallow, werkzeug,
psycopg2-binary, python-dotenv, sentry-sdk[flask], email-validator
```

No Redis. No Supabase. No Celery. No pandas.
