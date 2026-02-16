# OpenLedger v2 Roadmap

## What v1 Shipped

| Module | Status |
|--------|--------|
| Package structure, config, database | Done |
| Alembic migrations (10 tables, all indexes/constraints) | Done |
| JWT auth + bcrypt + role-based middleware (admin/accountant/client) | Done |
| User management (invite, list, role change, deactivate) | Done |
| Chart of accounts CRUD | Done |
| Journal entry creation with double-entry validation | Done |
| Bank CSV/XLSX import with dedup | Done |
| AI transaction classification (Sonnet) | Done |
| AI natural language → SQL queries | Done |
| Receipt OCR (Tesseract + Sonnet Vision) | Done |
| P&L, Balance Sheet, Trial Balance reports | Done |
| Reconciliation engine (auto-match scoring + manual match) | Done |
| Audit logging | Done |

---

## v2 — Three Phases

### Phase 1: Complete the Pipelines (Core Business Logic)

The v1 services work individually but aren't wired end-to-end. Phase 1 closes every gap between import → classify → create entry → reconcile.

#### 1.1 Bank Import → Journal Entry Pipeline
**Problem:** Bank transactions get imported and classified by AI, but nothing automatically creates journal entries from them.

**Build:**
- `POST /api/transactions/classify` — run AI classification on unclassified bank transactions, populate `suggested_account_id`, `ai_category`, `ai_confidence`
- `POST /api/transactions/create-entries` — take classified transactions above a confidence threshold and auto-generate balanced journal entries (debit expense/asset, credit cash)
- `POST /api/transactions/{id}/create-entry` — single transaction manual entry creation with account override
- Background task option: auto-classify + auto-create on import completion

#### 1.2 Receipt → Journal Entry Pipeline
**Problem:** OCR extracts merchant, date, total, tax, line items — but it dead-ends at a `Receipt` record.

**Build:**
- `POST /api/receipts/{id}/create-entry` — convert receipt data into a journal entry, mapping merchant to expense account via AI
- `POST /api/receipts/{id}/classify` — run AI classification on receipt to suggest accounts before entry creation
- Auto-link: set `journal_entry.receipt_id` so receipts are attached to their entries

#### 1.3 Period Management
**Problem:** `AccountingPeriod` model exists, `LedgerEngine._validate_period_open()` checks it, but there are zero API endpoints to manage periods.

**Build:**
- `POST /api/periods` — create period (name, start_date, end_date)
- `GET /api/periods` — list all periods with status
- `POST /api/periods/{id}/close` — close period (validates all entries approved, generates closing entries that zero out revenue/expense into retained earnings)
- `POST /api/periods/{id}/reopen` — admin-only with audit trail
- `GET /api/periods/{id}/readiness` — pre-close checklist (unapproved entries, unreconciled transactions in date range)

#### 1.4 Proper Reversing Entries
**Problem:** `void_entry()` sets status to VOIDED but doesn't create a GAAP-compliant reversing entry.

**Build:**
- When voiding, auto-create a new entry that swaps debits↔credits
- Link via `reversing_entry_id` field (add to model)
- Original stays as VOIDED, reversal is AUTO_APPROVED

#### 1.5 Organization Settings
**Problem:** Materiality threshold is hardcoded at $50. OCR engine, AI model, fiscal year — all config but not org-configurable via API.

**Build:**
- `OrganizationSettings` model (or add columns to Organization): `materiality_threshold_usd`, `ai_confidence_threshold`, `auto_create_entries`
- `GET/PATCH /api/org/settings` — admin-only
- Refactor `LedgerEngine` and `ReconciliationEngine` to read org settings

---

### Phase 2: New Data Models (A/R, A/P, Banking)

#### 2.1 Vendor & Customer Models
**Why:** A/R aging and A/P aging reports are meaningless without knowing who owes you and who you owe.

**Build:**
- `Vendor` model: name, email, address, tax_id, default_expense_account_id
- `Customer` model: name, email, address, tax_id, default_revenue_account_id
- Link to `BankTransaction.vendor_id` and `JournalEntry` context
- `GET/POST /api/vendors`, `GET/POST /api/customers`

#### 2.2 Bank Account Model
**Why:** System imports bank transactions but has no concept of *which* bank account they came from.

**Build:**
- `BankAccount` model: institution_name, account_type (checking/savings/credit), last_four, linked_account_id (maps to chart of accounts Cash entry)
- `BankTransaction.bank_account_id` FK
- `GET/POST /api/bank-accounts`
- Import endpoint accepts `bank_account_id` parameter

#### 2.3 Invoice & Bill Models
**Why:** Accrual accounting requires tracking revenue earned (invoices) and expenses incurred (bills) before cash moves.

**Build:**
- `Invoice` model: customer_id, issue_date, due_date, line_items, status (draft/sent/paid/overdue)
- `Bill` model: vendor_id, issue_date, due_date, line_items, status (pending/paid/overdue)
- Auto-create journal entries on invoice send (DR: A/R, CR: Revenue) and bill receipt (DR: Expense, CR: A/P)
- Payment recording reverses the A/R or A/P entry

#### 2.4 Tax Code System
**Why:** Every expense and revenue account needs a tax treatment for year-end reporting.

**Build:**
- `TaxCode` model: code, description, rate, type (income/sales/payroll)
- Link to `Account.tax_code_id`
- Tax summary report generator

---

### Phase 3: Advanced Reports & Analytics

#### 3.1 Cash Flow Statement
- Indirect method: start from net income, adjust for non-cash items
- Categorize: operating, investing, financing activities
- `POST /api/reports/cash-flow`

#### 3.2 A/R and A/P Aging Reports
- Requires Vendor/Customer models from Phase 2
- Bucket by: current, 30, 60, 90, 120+ days
- `POST /api/reports/ar-aging`, `POST /api/reports/ap-aging`

#### 3.3 Expense Analysis
- Pivot table: expenses by category, by month, by vendor
- Comparison: this period vs. last period, vs. budget
- `POST /api/reports/expense-analysis`

#### 3.4 Dashboard KPIs
- `GET /api/dashboard/summary` — current month revenue, expenses, net income, cash position, reconciliation %, pending review count, AI API cost
- `GET /api/dashboard/trends?months=12` — monthly time series for charting

#### 3.5 AI Cost Dashboard
- `GET /api/ai/usage` — total tokens, cost by query_type, cost by month
- Budget alerts when AI spend crosses thresholds

#### 3.6 Reconciliation Report
- `POST /api/reports/reconciliation` — matched vs unmatched by date range, bank account, and amount band

---

## Infrastructure & Quality (Cross-Cutting)

### Testing
- `tests/test_ledger.py` — balance validation, period enforcement, approval flow
- `tests/test_importer.py` — CSV/XLSX parsing, dedup, column mapping
- `tests/test_reconciliation.py` — scoring algorithm, match/unmatch
- `tests/test_reports.py` — P&L, balance sheet math correctness
- `tests/test_auth.py` — JWT flow, role enforcement, edge cases
- `tests/conftest.py` — fixtures with test database, mock Anthropic client

### API Polish
- Pagination on all list endpoints (limit/offset/total pattern)
- Rate limiting (per-user, per-org)
- Request ID middleware for tracing
- Error response standardization (RFC 7807 problem details)
- OpenAPI examples on every endpoint

### Deployment
- `Dockerfile` + `docker-compose.yml` (app + postgres + redis)
- GitHub Actions CI (lint + test + build)
- Alembic auto-run on deploy
- Health check endpoint with DB connectivity test

### Multi-Tenancy Hardening
- Row-level security: every query MUST filter by `organization_id` — audit this
- Cross-org data leak prevention middleware
- Org-scoped API key support (for headless/API integrations)

---

## Priority Order

| Priority | Item | Impact | Effort |
|----------|------|--------|--------|
| P0 | Bank import → entry pipeline | Unblocks core workflow | Medium |
| P0 | Period management endpoints | GAAP compliance | Small |
| P0 | Test suite | Confidence for everything else | Medium |
| P1 | Receipt → entry pipeline | Completes OCR value prop | Small |
| P1 | Org settings API | Unlocks configurability | Small |
| P1 | Reversing entries | GAAP compliance | Small |
| P1 | Docker + CI | Deployability | Medium |
| P2 | Vendor/Customer models | Unlocks aging reports | Medium |
| P2 | Bank Account model | Proper multi-account reconciliation | Small |
| P2 | Dashboard KPIs | User-facing value | Medium |
| P2 | Cash flow statement | Completes financial statement suite | Medium |
| P3 | Invoice/Bill models | Full accrual accounting | Large |
| P3 | Tax code system | Year-end reporting | Medium |
| P3 | A/R and A/P aging | Requires Vendor/Customer | Medium |
| P3 | Rate limiting + API keys | Production hardening | Small |
