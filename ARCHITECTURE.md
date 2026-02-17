# OpenLedger — Architecture Reference

> **Repo:** https://github.com/suhteevah/QBO-FOSS-alternative

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | FastAPI | 0.115+ |
| **ORM** | SQLAlchemy (async) | 2.0+ |
| **Migrations** | Alembic | 1.14+ |
| **Auth** | PyJWT + bcrypt | JWT HS256 |
| **AI** | Anthropic Claude Sonnet | claude-sonnet-4-20250514 |
| **OCR** | Tesseract + Sonnet Vision | Configurable |
| **Frontend** | React 18 + TypeScript | Vite bundler |
| **Styling** | Tailwind CSS | PostCSS |
| **Database (prod)** | PostgreSQL 16 | asyncpg driver |
| **Database (dev)** | SQLite | aiosqlite driver |
| **Containerization** | Docker Compose | 3-service stack |
| **Web Server** | nginx | Frontend reverse proxy |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  React 18 + TypeScript + Tailwind CSS + Vite                │
│  ┌──────────┬────────────┬──────────┬──────────────────┐    │
│  │  Login   │ Dashboard  │ Reports  │  Reconciliation  │    │
│  │ Register │ Transactions│ Accounts │  Receipts/OCR   │    │
│  │          │ Journal    │ Periods  │                  │    │
│  └──────────┴────────────┴──────────┴──────────────────┘    │
│  nginx (port 3000) ──── Docker: frontend service            │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP /api/*
┌─────────────────────────┴───────────────────────────────────┐
│                     FASTAPI BACKEND                         │
│  uvicorn (port 8000) ──── Docker: api service               │
│                                                             │
│  ┌─── Auth Layer ────────────────────────────────────────┐  │
│  │  JWT tokens, bcrypt hashing, role middleware           │  │
│  │  Roles: admin | accountant | client                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── API Routes (/api/) ────────────────────────────────┐  │
│  │  /auth     — login, register, invite, roles           │  │
│  │  /accounts — chart of accounts CRUD                   │  │
│  │  /transactions — bank import, classify, create entries │  │
│  │  /journal  — journal entry CRUD, approve, void        │  │
│  │  /reports  — P&L, balance sheet, trial balance        │  │
│  │  /receipts — OCR upload, classify, create entries     │  │
│  │  /ai       — natural language query                   │  │
│  │  /audit    — audit log viewer                         │  │
│  │  /reconciliation — auto-match, manual match           │  │
│  │  /periods  — create, close, reopen, readiness         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── Business Logic Engines ────────────────────────────┐  │
│  │  LedgerEngine         — double-entry validation       │  │
│  │  ReconciliationEngine — auto-match scoring            │  │
│  │  ReportEngine         — financial statement generation │  │
│  │  AIService            — Claude classification/query   │  │
│  │  OCRService           — Tesseract + Vision            │  │
│  │  Importer             — CSV/XLSX bank import + dedup  │  │
│  │  TransactionPipeline  — import → classify → entry     │  │
│  │  ReceiptPipeline      — OCR → classify → entry        │  │
│  │  PeriodService        — close/reopen with validation  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ SQLAlchemy async
┌─────────────────────────┴───────────────────────────────────┐
│                       DATABASE                              │
│  Production: PostgreSQL 16 (Docker: db service)             │
│  Dev/Demo:   SQLite (zero-config, auto-seed)                │
│                                                             │
│  Tables: Organization, User, Account, JournalEntry,         │
│          JournalLine, BankTransaction, Receipt,              │
│          ReconciliationMatch, AuditLog, AccountingPeriod     │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Models

### Core Accounting
| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Organization` | Multi-tenant root | name, settings |
| `Account` | Chart of accounts | account_number, name, type, subtype, normal_balance |
| `JournalEntry` | Double-entry header | date, description, status (draft/approved/voided) |
| `JournalLine` | Debit/credit lines | account_id, debit, credit |
| `AccountingPeriod` | Fiscal periods | name, start_date, end_date, status (open/closed) |

### Banking & Transactions
| Model | Purpose | Key Fields |
|-------|---------|------------|
| `BankTransaction` | Imported bank data | date, description, amount, ai_category, ai_confidence |
| `ReconciliationMatch` | Bank↔entry matches | transaction_id, journal_entry_id, match_score |
| `Receipt` | OCR-parsed receipts | merchant, date, total, tax, line_items |

### Auth & Audit
| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` | Authentication | email, hashed_password, role, organization_id |
| `AuditLog` | Change tracking | user_id, action, entity_type, entity_id, changes |

### Account Types (GAAP)
```
ASSET, CONTRA_ASSET, LIABILITY, EQUITY, REVENUE, CONTRA_REVENUE, EXPENSE
```

### Account Subtypes
```
CASH, ACCOUNTS_RECEIVABLE, INVENTORY, PREPAID, FIXED_ASSET,
ACCOUNTS_PAYABLE, CREDIT_CARD, ACCRUED_LIABILITY, LONG_TERM_DEBT,
OWNERS_EQUITY, RETAINED_EARNINGS, SALES, SERVICE_REVENUE, OTHER_INCOME,
COST_OF_GOODS, OPERATING_EXPENSE, PAYROLL, DEPRECIATION, TAX_EXPENSE,
OTHER_EXPENSE
```

---

## API Endpoints

### Auth (`/api/auth`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Create new user |
| POST | `/login` | Get JWT token |
| POST | `/invite` | Admin invites user |
| GET | `/users` | List org users |
| PATCH | `/users/{id}/role` | Change user role |
| POST | `/users/{id}/deactivate` | Deactivate user |

### Accounts (`/api/accounts`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List chart of accounts |
| POST | `/` | Create account |
| PATCH | `/{id}` | Update account |

### Transactions (`/api/transactions`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List transactions |
| POST | `/import` | Import CSV/XLSX |
| POST | `/classify` | AI classify unclassified |
| POST | `/create-entries` | Auto-create journal entries |
| POST | `/{id}/create-entry` | Manual entry from transaction |

### Journal (`/api/journal`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List journal entries |
| POST | `/` | Create entry (validates balance) |
| POST | `/{id}/approve` | Approve entry |
| POST | `/{id}/void` | Void with reversing entry |

### Reports (`/api/reports`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/profit-loss` | P&L for date range |
| POST | `/balance-sheet` | Balance sheet at date |
| POST | `/trial-balance` | Trial balance at date |

### Reconciliation (`/api/reconciliation`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auto-match` | Run auto-matching |
| GET | `/unmatched` | List unmatched items |
| POST | `/match` | Manual match |
| POST | `/unmatch` | Remove match |

### Other
| Prefix | Endpoints |
|--------|-----------|
| `/api/receipts` | Upload, classify, create entry |
| `/api/ai` | Natural language query |
| `/api/audit` | Audit log viewer |
| `/api/periods` | Create, list, close, reopen, readiness |
| `/health` | Health check |

---

## Configuration

All config via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///openledger.db` | Async DB connection |
| `DATABASE_URL_SYNC` | `sqlite:///openledger.db` | Sync DB (Alembic) |
| `SECRET_KEY` | *(must set in prod)* | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token TTL |
| `ANTHROPIC_API_KEY` | *(empty)* | Claude API key |
| `SONNET_MODEL` | `claude-sonnet-4-20250514` | AI model |
| `OCR_ENGINE` | `tesseract` | OCR backend |
| `ACCOUNTING_BASIS` | `accrual` | Accrual or cash |
| `DEFAULT_FISCAL_YEAR_START` | `1` | January |
| `DEBUG` | `false` | Debug mode |

### Security Guards
- **Production refuses to start** if `SECRET_KEY` is still `"change-me-in-production"`
- **CORS** locked to `localhost:3000` in production, `*` only in debug mode
- **Swagger docs** (`/docs`) disabled in production

---

## Docker Services

```yaml
services:
  db:        # PostgreSQL 16 Alpine — port 5432
  api:       # Python 3.12 + FastAPI — port 8000
  frontend:  # Node build + nginx — port 3000
```

### Networks
- `backend` — db ↔ api
- `frontend` — api ↔ frontend

### Volumes
- `pgdata` — PostgreSQL persistent storage
