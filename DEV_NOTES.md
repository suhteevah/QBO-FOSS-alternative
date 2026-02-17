# OpenLedger — Developer Notes & Technical Decisions

> **Repo:** https://github.com/suhteevah/QBO-FOSS-alternative
> **Last Updated:** 2026-02-16

---

## Table of Contents
1. [Secrets Audit Results](#secrets-audit-results)
2. [Security Decisions](#security-decisions)
3. [Architecture Decisions](#architecture-decisions)
4. [Known Issues & Tech Debt](#known-issues--tech-debt)
5. [Resumption Guide (Next Developer Session)](#resumption-guide)

---

## Secrets Audit Results

### Full Forensic Scan (2026-02-16)

Scanned entire codebase AND full git history for secrets.

#### Patterns Searched
| Pattern | Result |
|---------|--------|
| `sk-ant-` (Anthropic API keys) | **CLEAN** — only placeholder `sk-ant-...` in old `.env.example` |
| `sk-proj-` (OpenAI keys) | **CLEAN** |
| `AKIA` (AWS access keys) | **CLEAN** |
| `AIza` (Google API keys) | **CLEAN** |
| `ghp_` / `gho_` (GitHub tokens) | **CLEAN** |
| `glpat-` (GitLab tokens) | **CLEAN** |
| `xox[bpas]-` (Slack tokens) | **CLEAN** |
| SSH private keys (`-----BEGIN`) | **CLEAN** |
| PGP private keys | **CLEAN** |
| Hardcoded `password=` assignments | **CLEAN** — only `hashed_password` (bcrypt) |
| Committed `.env` files | **CLEAN** — only `.env.example` with placeholders |

#### Findings Addressed
| Finding | Severity | Action |
|---------|----------|--------|
| `sk-ant-...` placeholder in git history (.env.example) | Low | Already fixed in current version |
| Personal email `baal_hosting@live.com` in git history README | Privacy | Cannot remove from history without force-push; noted |
| `files.zip` committed (redundant archive) | Cleanup | Removed via `git rm --cached` |
| 8 root-level `.py` files tracked (pre-restructure copies) | Cleanup | Removed via `git rm --cached` |

#### Files NOT Tracked (verified)
- `.env` — **NOT in git** ✓
- `*.db` — **NOT in git** ✓ (gitignored)
- `node_modules/` — **NOT in git** ✓
- `.venv/` — **NOT in git** ✓

---

## Security Decisions

### 1. JWT Configuration
- **Algorithm:** HS256 (symmetric)
- **Expiry:** 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Decision:** HS256 is fine for single-server deployment. Switch to RS256 if distributing token validation across services.

### 2. Password Hashing
- **Library:** bcrypt via `bcrypt` package
- **Cost factor:** Default (12 rounds)
- **Decision:** Industry standard. No plaintext passwords anywhere.

### 3. CORS Policy
- **Debug mode:** `allow_origins=["*"]` (for local dev)
- **Production:** `allow_origins=["http://localhost:3000"]` only
- **Decision:** Lock down in production. If deploying behind a domain, update to actual domain.

### 4. Startup Guard
```python
if not settings.debug and settings.secret_key in ("change-me-in-production", "dev-secret-change-in-production"):
    raise RuntimeError("CRITICAL: SECRET_KEY is still set to the default value.")
```
- **Decision:** App refuses to start in production with default key. This prevents accidental deployment with weak secrets.

### 5. Swagger Docs
- **Debug mode:** Available at `/docs`
- **Production:** Disabled (`docs_url=None`)
- **Decision:** Prevents information leakage about API structure in production.

### 6. Database Credentials
- **Docker mode:** PostgreSQL password required via `POSTGRES_PASSWORD` env var
- **Dev mode:** SQLite with no password (file-based)
- **Decision:** Docker compose uses `${POSTGRES_PASSWORD:?err}` syntax to fail fast if not set.

---

## Architecture Decisions

### 1. Dual Database Support (PostgreSQL + SQLite)
**Why:** PostgreSQL for production, SQLite for zero-config demo/development.

**How:**
- `config.py` defaults to SQLite path
- `database.py` creates async engine from `DATABASE_URL`
- `main.py` auto-creates tables + seeds data when SQLite detected
- Docker compose overrides `DATABASE_URL` to point to PostgreSQL

**Trade-off:** SQLite doesn't support concurrent writes well. Fine for demo, not for production.

### 2. Package Structure (`openledger/`)
**Why:** Original flat structure had all `.py` at root. Restructured into proper Python package.

**Result:**
```
openledger/
├── __init__.py
├── main.py, config.py, database.py
├── models.py, schemas.py, auth.py
├── ledger.py, ai_service.py, ocr_service.py
├── importer.py, cli.py
├── reconciliation_engine.py, report_engine.py
├── receipt_pipeline.py, transaction_pipeline.py, period_service.py
└── api/ (route modules)
```

### 3. Monorepo (Backend + Frontend)
**Why:** Simplifies deployment (single `docker compose up`), single repo to manage.

**Structure:**
- Root: Python backend
- `frontend/`: React app
- Each has its own `Dockerfile`

### 4. Alembic Migrations
**Why:** Production schema changes need to be tracked and reversible.

**Files:**
- `001_initial_schema.py` — all 10+ tables, indexes, constraints
- `002_add_indexes_constraints_updated_at.py` — additional indexes

**Note:** When using SQLite in dev mode, tables are auto-created via `Base.metadata.create_all()` — Alembic is only needed for PostgreSQL migrations.

### 5. Demo Data Seeder
**Why:** New users should see a working app immediately, not empty screens.

**Seeds 26 GAAP-standard accounts:**
- Assets: Cash, A/R, Inventory, Prepaid, Equipment, Accumulated Depreciation
- Liabilities: A/P, Credit Card, Accrued Liabilities, Long-Term Loan
- Equity: Owner's Equity, Retained Earnings
- Revenue: Sales, Service, Other Income, Sales Returns
- Expenses: COGS, Rent, Utilities, Supplies, Advertising, Insurance, Payroll, Depreciation, Interest, Tax

---

## Known Issues & Tech Debt

### Must Fix
| Issue | Priority | Notes |
|-------|----------|-------|
| No test suite | P0 | Need pytest + fixtures with test DB |
| Personal email in git history | Low | `baal_hosting@live.com` in old README commit |
| DocSync `.md` files cluttering repo | Low | Gitignored but still on disk |

### Nice to Have
| Issue | Priority | Notes |
|-------|----------|-------|
| Rate limiting not implemented | P1 | Add per-user/per-org limits |
| No request ID middleware | P2 | For log tracing |
| No pagination on list endpoints | P2 | Need limit/offset/total |
| No CI/CD pipeline | P1 | Need GitHub Actions |
| README is DocSync auto-generated | P2 | Should be real README with badges |

### Won't Fix (by design)
| Issue | Reason |
|-------|--------|
| SQLite concurrent write limitations | Use PostgreSQL for production |
| CORS `*` in debug mode | Intentional for local development |
| No HTTPS | Handled by reverse proxy (nginx/Cloudflare) in production |

---

## Resumption Guide

### If continuing in a new Claude session, here's what to know:

**Project location:** `J:\QBO FOSS alternative\` (Windows) or wherever cloned

**Key entry points:**
- Backend: `openledger/main.py` → FastAPI app
- Frontend: `frontend/src/App.tsx` → React routes
- Config: `openledger/config.py` → all env var settings
- Models: `openledger/models.py` → all SQLAlchemy models
- Docker: `docker-compose.yml` → 3-service stack

**Current branch:** `main` (only branch)

**Last commit:** `ae21685` — Auto-install Docker in bootstrap scripts

**What's been done (v1 complete):**
- ✅ Full backend (FastAPI + SQLAlchemy + Alembic)
- ✅ JWT auth with role-based access
- ✅ 10 API route modules
- ✅ AI classification + NL query (Anthropic Claude)
- ✅ OCR (Tesseract + Vision)
- ✅ Bank import with dedup
- ✅ Double-entry ledger engine
- ✅ Reconciliation engine
- ✅ Report engine (P&L, Balance Sheet, Trial Balance)
- ✅ React frontend (10 pages)
- ✅ Docker production setup
- ✅ SQLite dev/demo mode
- ✅ One-click installers (6 scripts)
- ✅ One-shot bootstrap (2 scripts with Docker auto-install)
- ✅ Security audit (74 issues fixed)
- ✅ Secrets audit (clean)
- ✅ Git hygiene (.gitignore hardened, stale files removed)

**What's next (from V2_ROADMAP.md):**
1. **P0:** Test suite (pytest)
2. **P1:** Receipt → entry pipeline polish
3. **P1:** Org settings API
4. **P1:** GitHub Actions CI
5. **P2:** Vendor/Customer models
6. **P2:** Dashboard KPIs API
7. **P2:** Cash Flow Statement

**How to run locally (dev mode):**
```bash
cd "J:\QBO FOSS alternative"
.\start.ps1   # Windows
# or
./start.sh    # Linux/macOS
```
Frontend: http://localhost:3000
API: http://localhost:8000
