# OpenLedger — Full Build Session Log

> **Repo:** https://github.com/suhteevah/QBO-FOSS-alternative
> **Date:** February 14–16, 2026
> **Sessions:** 5 (context compacted multiple times)

---

## Table of Contents

1. [Session 1: Initial Build — Core Backend](#session-1-initial-build)
2. [Session 2: Package Restructure + React Frontend](#session-2-restructure--frontend)
3. [Session 3: Security Audit](#session-3-security-audit)
4. [Session 4: SQLite Support + Installers + Live Demo](#session-4-sqlite--installers--demo)
5. [Session 5: Secrets Audit + Bootstrap Scripts + Docker Auto-Install](#session-5-secrets--bootstrap--docker)
6. [All Commits (Chronological)](#all-commits)
7. [Current File Tree](#current-file-tree)

---

## Session 1: Initial Build

### What Was Built
Built the entire OpenLedger backend from scratch — a FOSS QuickBooks alternative using FastAPI + SQLAlchemy.

**Priority 1 — Alembic Migrations:**
- Created 2 migration files covering 10+ database tables
- All indexes, constraints, foreign keys
- Models: Organization, User, Account, JournalEntry, JournalLine, BankTransaction, Receipt, ReconciliationMatch, AuditLog, AccountingPeriod

**Priority 2 — JWT Authentication:**
- bcrypt password hashing
- JWT token generation/validation
- Role-based access control (admin / accountant / client)
- User management endpoints (invite, list, role change, deactivate)

**Priority 3 — Reports Engine:**
- Profit & Loss statement
- Balance Sheet
- Trial Balance
- All reports respect accounting period boundaries

**Priority 4 — Reconciliation Engine:**
- Auto-match scoring algorithm (amount, date proximity, description similarity)
- Manual match/unmatch endpoints
- Materiality threshold checks

### Other Modules
- Bank CSV/XLSX import with duplicate detection
- AI transaction classification (Anthropic Claude Sonnet)
- AI natural-language-to-SQL query engine
- Receipt OCR (Tesseract + Sonnet Vision)
- Full audit logging
- CLI tool for seeding data

---

## Session 2: Restructure + Frontend

### Package Restructure
Moved all root-level `.py` files into `openledger/` package:
- `openledger/__init__.py`
- `openledger/main.py`, `openledger/config.py`, `openledger/database.py`
- `openledger/models.py`, `openledger/schemas.py`
- `openledger/auth.py`, `openledger/ledger.py`
- `openledger/ai_service.py`, `openledger/ocr_service.py`
- `openledger/importer.py`, `openledger/cli.py`
- `openledger/reconciliation_engine.py`, `openledger/report_engine.py`
- `openledger/api/` — all route modules

### React Frontend (8 Pages)
Built complete React + TypeScript + Tailwind CSS frontend:

| Page | Route | Features |
|------|-------|----------|
| Login | `/login` | JWT auth, error handling |
| Register | `/register` | New user signup |
| Dashboard | `/` | KPI cards, recent transactions |
| Transactions | `/transactions` | Bank transaction list, CSV import |
| Journal | `/journal` | Journal entry creation, double-entry validation |
| Accounts | `/accounts` | Chart of accounts CRUD |
| Reconciliation | `/reconciliation` | Match/unmatch interface |
| Reports | `/reports` | P&L, Balance Sheet, Trial Balance generation |
| Receipts | `/receipts` | OCR upload, receipt list |
| Periods | `/periods` | Accounting period management |

### Docker Setup
- `Dockerfile` — Python 3.12 slim, multi-stage
- `frontend/Dockerfile` — Node build + nginx serve
- `docker-compose.yml` — 3-service stack (postgres, api, frontend)
- `.dockerignore` files for both

### Phase 1 Pipelines
- Transaction classification pipeline (`POST /api/transactions/classify`)
- Transaction → journal entry pipeline (`POST /api/transactions/create-entries`)
- Receipt → journal entry pipeline (`POST /api/receipts/{id}/create-entry`)
- Period management endpoints (create, list, close, reopen, readiness check)

---

## Session 3: Security Audit

### Findings: 74 Issues Total
- **14 Critical** — SQL injection risks, missing auth, secrets in code
- **27 High** — Missing rate limiting, CORS issues, weak JWT config
- **20 Medium** — Missing input validation, error information leakage
- **13 Low** — Logging improvements, code quality

### Fixes Applied
All 14 critical and 27 high severity issues were fixed in a single commit (`201e74e`):

- Parameterized all SQL queries (eliminated injection vectors)
- Added authentication to all unprotected endpoints
- Moved all secrets to environment variables
- Added rate limiting considerations
- Tightened CORS configuration
- Added input validation and size limits
- Sanitized error responses to prevent information leakage
- Added startup guard that refuses to run with default SECRET_KEY in production

---

## Session 4: SQLite + Installers + Demo

### SQLite Support
Added SQLite as a zero-config default for development/demo:
- `aiosqlite` async driver
- Auto-create tables on startup when using SQLite
- Auto-seed demo chart of accounts (26 GAAP-standard accounts)
- Config defaults to `sqlite+aiosqlite:///openledger.db`

### One-Click Installers
Created 6 installer/start scripts:

| Script | Purpose |
|--------|---------|
| `install.sh` | Production Docker install (Linux/macOS) |
| `install.ps1` | Production Docker install (Windows) |
| `install-dev.sh` | Dev/SQLite install — venv + npm (Linux/macOS) |
| `install-dev.ps1` | Dev/SQLite install — venv + npm (Windows) |
| `start.sh` | Start backend + frontend (Linux/macOS) |
| `start.ps1` | Start backend + frontend (Windows) |

### Live Demo
Ran the full app in the browser and verified all 8 pages:
- Registered a user, logged in
- Viewed dashboard with KPI cards
- Browsed chart of accounts (26 seeded accounts)
- Created journal entries with double-entry validation
- Navigated transactions, reports, reconciliation, receipts, periods
- All pages rendered correctly with Tailwind styling

---

## Session 5: Secrets Audit + Bootstrap + Docker Auto-Install

### Comprehensive Secrets Audit
Forensic-level scan of entire repo + git history:

**Searched for (all CLEAN):**
- Real API keys: `sk-ant-`, `sk-proj-`, `AKIA`, `AIza`, `ghp_`, `gho_`, `glpat-`, `xox[bpas]-`
- SSH/PGP private keys
- Hardcoded passwords
- GitHub tokens in history
- Committed `.env` files

**Found & Fixed:**
- Old `sk-ant-...` placeholder in historical `.env.example` (not a real key, already removed in current)
- Personal PayPal email in git history README (privacy concern, not security)
- `files.zip` committed (redundant source archive) — removed
- 8 root-level `.py` files still tracked (pre-restructure copies) — removed

**Cleanup (commit `e954c8c`):**
- `git rm --cached` on all 9 stale files
- Hardened `.gitignore` with:
  - Legacy root-level files
  - `*.tsbuildinfo`
  - DocSync auto-generated `.md` files
  - `docs/` directory
  - `*.db` database files
  - Windows reserved device names (`nul`, `con`, etc.)

### Bootstrap Scripts (commit `1addef6`)
Created one-shot installers for `curl | bash` and `irm | iex`:

**`bootstrap.sh`** (Linux/macOS):
```bash
curl -fsSL https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.sh | bash
```

**`bootstrap.ps1`** (Windows):
```powershell
irm https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.ps1 | iex
```

Both scripts:
1. Detect environment (Docker, Python 3.11+, Node.js 18+)
2. Auto-select best install mode
3. Clone repo
4. Run appropriate installer
5. Start app + open browser

### Docker Auto-Install (commit `ae21685`)
Updated bootstrap scripts to automatically install Docker when missing:

**Linux:** Official `get.docker.com` convenience script via `curl | sh`
**macOS:** `brew install --cask docker` (requires Homebrew)
**Windows:** `winget install Docker.DockerDesktop` → fallback to `choco install docker-desktop`

After install: starts Docker daemon, waits for it to be ready, then continues with production install path.

---

## All Commits

| Hash | Date | Message |
|------|------|---------|
| `b74b63c` | 2026-02-14 | Initial commit - uploaded via github-uploader-buildout |
| `8c3af7d` | 2026-02-15 | Initial commit - uploaded via github-uploader-buildout |
| `abadd6c` | 2026-02-16 | Initial commit - uploaded via github-uploader-buildout |
| `d8b0f59` | 2026-02-16 | Add v2 roadmap with three-phase plan |
| `ffa9094` | 2026-02-16 | Replace broken PayPal link with Ko-fi donation button |
| `b4af407` | 2026-02-16 | Add Phase 1 pipelines, period management, Docker, and React frontend |
| `87402ae` | 2026-02-16 | Resolve README.md merge conflict with remote DocSync update |
| `201e74e` | 2026-02-16 | Security audit: fix 14 critical + 27 high severity issues |
| `6191d95` | 2026-02-16 | Add SQLite support, one-click installers, and production Docker setup |
| `e954c8c` | 2026-02-16 | Remove stale root-level files and harden .gitignore |
| `1addef6` | 2026-02-16 | Add one-shot bootstrap installers for curl\|bash and irm\|iex |
| `ae21685` | 2026-02-16 | Auto-install Docker in bootstrap scripts when missing |

---

## Current File Tree

```
openledger/
├── __init__.py
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings (env vars)
├── database.py          # SQLAlchemy async engine + session
├── models.py            # 10+ SQLAlchemy ORM models
├── schemas.py           # Pydantic request/response schemas
├── auth.py              # JWT + bcrypt auth utilities
├── ledger.py            # Double-entry ledger engine
├── ai_service.py        # Anthropic Claude integration
├── ocr_service.py       # Tesseract + Vision OCR
├── importer.py          # CSV/XLSX bank import
├── cli.py               # CLI seeder tool
├── reconciliation_engine.py  # Auto-match scoring
├── report_engine.py     # P&L, Balance Sheet, Trial Balance
├── receipt_pipeline.py  # Receipt → journal entry
├── transaction_pipeline.py  # Transaction → journal entry
├── period_service.py    # Period close/reopen logic
└── api/
    ├── __init__.py
    ├── auth.py           # /api/auth/*
    ├── accounts.py       # /api/accounts/*
    ├── transactions.py   # /api/transactions/*
    ├── journal_entries.py # /api/journal/*
    ├── reports.py        # /api/reports/*
    ├── receipts.py       # /api/receipts/*
    ├── ai_query.py       # /api/ai/*
    ├── audit.py          # /api/audit/*
    ├── reconciliation.py # /api/reconciliation/*
    └── periods.py        # /api/periods/*

frontend/
├── src/
│   ├── App.tsx           # Routes + auth guards
│   ├── main.tsx          # React entry point
│   ├── index.css         # Tailwind imports
│   └── pages/            # Login, Register, Dashboard, etc.
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── Dockerfile            # Multi-stage Node build + nginx
└── nginx.conf

alembic/
├── env.py
├── script.py.mako
└── versions/
    ├── 001_initial_schema.py
    └── 002_add_indexes_constraints_updated_at.py

# Root files
├── bootstrap.sh          # One-shot curl|bash installer (with Docker auto-install)
├── bootstrap.ps1         # One-shot irm|iex installer (with Docker auto-install)
├── install.sh / .ps1     # Production Docker installers
├── install-dev.sh / .ps1 # Dev/SQLite installers
├── start.sh / .ps1       # App start scripts
├── docker-compose.yml    # 3-service stack (postgres + api + frontend)
├── Dockerfile            # Python 3.12 API container
├── requirements.txt      # Python dependencies
├── alembic.ini           # Migration config
├── .env.example          # Template env file
├── .gitignore            # Hardened ignores
├── V2_ROADMAP.md         # Three-phase roadmap
└── README.md             # Auto-generated by DocSync
```
