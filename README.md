# OpenLedger

**A FOSS alternative to QuickBooks Online — GAAP-compliant, AI-augmented bookkeeping platform.**

OpenLedger is designed as a managed bookkeeping backend: the software handles 90% of transaction categorization, reconciliation, and reporting automatically using AI (Claude Sonnet), while human accountants review and approve via audit logs.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│  Dashboard │ Transactions │ Reports │ Receipt Upload │
└──────────────────────┬──────────────────────────────┘
                       │ REST / WebSocket
┌──────────────────────▼──────────────────────────────┐
│                 FastAPI Backend                       │
│                                                      │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────┐ │
│  │ Transaction  │ │ AI Query     │ │ Receipt OCR   │ │
│  │ Engine       │ │ Tokenizer    │ │ Pipeline      │ │
│  └──────┬──────┘ └──────┬───────┘ └───────┬───────┘ │
│         │               │                 │          │
│  ┌──────▼───────────────▼─────────────────▼───────┐ │
│  │           Double-Entry Ledger Core              │ │
│  │         (GAAP-Compliant Engine)                 │ │
│  └──────────────────┬─────────────────────────────┘ │
└─────────────────────┼───────────────────────────────┘
                      │
        ┌─────────────▼─────────────┐
        │     PostgreSQL Database    │
        │  Ledger │ Audit │ Blobs   │
        └───────────────────────────┘
```

## Core Modules

| Module | Description | Status |
|--------|-------------|--------|
| `ledger/` | Double-entry bookkeeping engine, chart of accounts, journal entries | 🔨 Scaffold |
| `transactions/` | Bank CSV/XLSX import, auto-categorization, reconciliation | 🔨 Scaffold |
| `ai/` | Sonnet query tokenization, NL→ledger query, classification | 🔨 Scaffold |
| `ocr/` | Receipt scanning via Tesseract + Sonnet vision fallback | 🔨 Scaffold |
| `reports/` | P&L, balance sheet, cash flow, trial balance generators | 🔨 Scaffold |
| `audit/` | Accountant review queue, approval workflow, change logs | 🔨 Scaffold |

## Tech Stack

- **Backend:** Python 3.12+ / FastAPI
- **Database:** PostgreSQL 16 + SQLAlchemy / Alembic
- **AI:** Anthropic Claude Sonnet API (classification, NL queries, OCR enhancement)
- **OCR:** Tesseract + PIL/Pillow (with Sonnet vision fallback)
- **Spreadsheets:** openpyxl, pandas
- **Frontend:** React + Tailwind (future)
- **Auth:** JWT + role-based (admin, accountant, client)

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourorg/openledger.git
cd openledger

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
cp .env.example .env
# Edit .env with your PostgreSQL and Anthropic API credentials
alembic upgrade head

# Seed chart of accounts
python -m openledger.cli seed-accounts

# Run development server
uvicorn openledger.main:app --reload
```

## Configuration

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/openledger
ANTHROPIC_API_KEY=sk-ant-...
SONNET_MODEL=claude-sonnet-4-20250514
OCR_ENGINE=tesseract          # or "sonnet-vision"
ACCOUNTING_BASIS=accrual      # or "cash"
DEFAULT_FISCAL_YEAR_START=01  # January
```

## GAAP Compliance

OpenLedger enforces:
- **Double-entry bookkeeping** — every transaction has balanced debits and credits
- **Accrual & cash basis** — configurable per organization
- **Period closing** — locked periods prevent retroactive changes
- **Audit trail** — every mutation logged with user, timestamp, and before/after state
- **Chart of accounts** — standard GAAP account hierarchy (assets, liabilities, equity, revenue, expenses)
- **Materiality thresholds** — configurable for AI auto-approval vs. human review

## Monetization Model (Managed Service)

| Tier | Price | Includes |
|------|-------|----------|
| Solo | $49-99/mo | AI categorization, basic reports, quarterly accountant review |
| Small Biz | $149-299/mo | Full reconciliation, monthly review, receipt OCR, NL queries |
| Self-Hosted | Free (FOSS) | Community support, BYO accountant |

## License

AGPL-3.0 — Free to use and modify; derivative SaaS must open-source.

---

---

## Support This Project

If you find this project useful, consider buying me a coffee! Your support helps me keep building and sharing open-source tools.

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?logo=paypal)](https://www.paypal.me/baal_hosting)

**PayPal:** [baal_hosting@live.com](https://paypal.me/baal_hosting)

Every donation, no matter how small, is greatly appreciated and motivates continued development. Thank you!
