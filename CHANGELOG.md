# OpenLedger — Changelog

> **Repo:** https://github.com/suhteevah/QBO-FOSS-alternative

All notable changes to this project are documented in this file.

---

## [Unreleased]

### Next Up (from V2_ROADMAP.md)
- Test suite (pytest)
- Vendor & Customer models
- Bank Account model
- Invoice & Bill models
- Cash Flow Statement
- A/R and A/P Aging Reports
- Dashboard KPIs API
- GitHub Actions CI

---

## 2026-02-16

### ae21685 — Auto-install Docker in bootstrap scripts when missing
**Files changed:** `bootstrap.sh`, `bootstrap.ps1`

- `bootstrap.sh`: Added `install_docker()` function
  - Linux: Uses official `get.docker.com` convenience script
  - macOS: Installs Docker Desktop via Homebrew
  - Handles sudo, starts daemon, adds user to docker group
  - Waits for Docker to become ready before continuing
- `bootstrap.ps1`: Added `Install-Docker` function
  - Windows: Tries `winget install Docker.DockerDesktop` first
  - Fallback: `choco install docker-desktop`
  - Launches Docker Desktop, waits up to 90s for daemon
- Both scripts: If Docker mode requested and Docker missing → auto-install instead of error

---

### 1addef6 — Add one-shot bootstrap installers for curl|bash and irm|iex
**New files:** `bootstrap.sh`, `bootstrap.ps1`

- `bootstrap.sh`: One-liner install for Linux/macOS
  - `curl -fsSL URL | bash`
  - Auto-detects Docker, Python 3.11+, Node.js 18+
  - Selects best mode (docker/dev), clones repo, runs installer
  - Supports `OPENLEDGER_MODE` and `OPENLEDGER_DIR` env vars
- `bootstrap.ps1`: One-liner install for Windows
  - `irm URL | iex`
  - Same detection and mode selection logic

---

### e954c8c — Remove stale root-level files and harden .gitignore
**Files changed:** `.gitignore` + 9 files removed from tracking

- Removed from git tracking (via `git rm --cached`):
  - `ai_service.py`, `cli.py`, `importer.py`, `ledger.py`, `main.py`, `models.py`, `ocr_service.py`, `schemas.py` (pre-restructure duplicates)
  - `files.zip` (redundant source archive)
- Updated `.gitignore`:
  - Added legacy root-level file patterns
  - Added `*.tsbuildinfo`
  - Added DocSync auto-generated `.md` patterns
  - Added `docs/` directory
  - Added `*.db`, `*.db-journal`, `*.db-wal`
  - Added `uploads/`
  - Added Windows reserved device names (nul, con, prn, etc.)

---

### 6191d95 — Add SQLite support, one-click installers, and production Docker setup
**New files:** `install.sh`, `install.ps1`, `install-dev.sh`, `install-dev.ps1`, `start.sh`, `start.ps1`
**Modified:** `openledger/config.py`, `openledger/main.py`, `openledger/database.py`, `requirements.txt`

- Added `aiosqlite` as async SQLite driver
- `config.py`: Default `DATABASE_URL` now points to SQLite for zero-config dev
- `main.py`: Auto-creates tables on startup when using SQLite
- `main.py`: Auto-seeds 26 GAAP-standard chart of accounts for demo
- Startup guard: refuses to start with default `SECRET_KEY` in production
- Created 6 installer/start scripts for Docker and dev modes
- Created `.dockerignore` files for API and frontend

---

### 201e74e — Security audit: fix 14 critical + 27 high severity issues

- Fixed SQL injection risks (parameterized all queries)
- Added authentication to unprotected endpoints
- Moved all secrets to environment variables
- Tightened CORS (only `localhost:3000` in production)
- Disabled Swagger docs in production
- Added input validation and size limits
- Sanitized error responses
- Added bcrypt cost factor validation
- Added JWT expiry enforcement

---

### 87402ae — Resolve README.md merge conflict with remote DocSync update

- Resolved merge conflict between local README and DocSync auto-generated version

---

### b4af407 — Add Phase 1 pipelines, period management, Docker, and React frontend

**Major feature commit — largest in the project.**

Backend additions:
- `openledger/transaction_pipeline.py` — bank import → classify → create journal entries
- `openledger/receipt_pipeline.py` — OCR → classify → create journal entries
- `openledger/period_service.py` — period close/reopen with validation
- `openledger/api/periods.py` — full CRUD for accounting periods
- Updated all existing API routes with pipeline integration

Frontend (complete React app):
- 10 pages: Login, Register, Dashboard, Transactions, Journal, Accounts, Reconciliation, Reports, Receipts, Periods
- Auth context with JWT token management
- Tailwind CSS styling throughout
- `frontend/Dockerfile` — multi-stage build with nginx
- `frontend/nginx.conf` — SPA routing + API proxy

Docker:
- `Dockerfile` — Python 3.12 slim container
- `docker-compose.yml` — postgres + api + frontend services

---

### ffa9094 — Replace broken PayPal link with Ko-fi donation button
- Replaced non-working PayPal donation link with Ko-fi button in README

---

### d8b0f59 — Add v2 roadmap with three-phase plan
**New file:** `V2_ROADMAP.md`

- Phase 1: Complete pipelines (import→entry, receipt→entry, periods, reversing entries)
- Phase 2: New data models (Vendor, Customer, BankAccount, Invoice, Bill, TaxCode)
- Phase 3: Advanced reports (Cash Flow, A/R Aging, A/P Aging, Dashboard KPIs)
- Infrastructure: testing, CI, rate limiting, multi-tenancy hardening

---

### abadd6c / 8c3af7d / b74b63c — Initial commits
- Initial project upload via github-uploader-buildout
- Core models, services, and API structure
