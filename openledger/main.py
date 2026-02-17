"""OpenLedger — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openledger.config import settings
from openledger.api import (
    accounts,
    api_keys,
    transactions,
    journal_entries,
    reports,
    receipts,
    ai_query,
    audit,
    auth,
    reconciliation,
    periods,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (SQLite demo) / run any init logic."""
    from openledger.database import async_engine
    from openledger.models import Base

    if settings.database_url.startswith("sqlite"):
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Seed demo chart of accounts if the database is brand new
        await _seed_demo_data_if_empty()

    yield


app = FastAPI(
    title="OpenLedger",
    description="FOSS GAAP-compliant AI-augmented bookkeeping platform",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    lifespan=lifespan,
)

# In debug mode, allow all origins for local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ──────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(api_keys.router, prefix="/api/keys", tags=["API Keys"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["Chart of Accounts"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(journal_entries.router, prefix="/api/journal", tags=["Journal Entries"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(receipts.router, prefix="/api/receipts", tags=["Receipts & OCR"])
app.include_router(ai_query.router, prefix="/api/ai", tags=["AI Query"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit Log"])
app.include_router(reconciliation.router, prefix="/api/reconciliation", tags=["Reconciliation"])
app.include_router(periods.router, prefix="/api/periods", tags=["Accounting Periods"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


# ── Demo Data Seeder ────────────────────────────────────────

async def _seed_demo_data_if_empty():
    """Populate a fresh SQLite DB with a sample chart of accounts."""
    import uuid
    from openledger.database import AsyncSessionLocal
    from openledger.models import Organization, Account, AccountType, AccountSubtype

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        count = (await session.execute(select(func.count()).select_from(Organization))).scalar()
        if count > 0:
            return  # Already seeded

        org = Organization(id=uuid.uuid4(), name="Demo Company")
        session.add(org)
        await session.flush()

        # Standard GAAP chart of accounts
        coa = [
            ("1000", "Cash", AccountType.ASSET, AccountSubtype.CASH, "debit"),
            ("1100", "Accounts Receivable", AccountType.ASSET, AccountSubtype.ACCOUNTS_RECEIVABLE, "debit"),
            ("1200", "Inventory", AccountType.ASSET, AccountSubtype.INVENTORY, "debit"),
            ("1300", "Prepaid Expenses", AccountType.ASSET, AccountSubtype.PREPAID, "debit"),
            ("1500", "Equipment", AccountType.ASSET, AccountSubtype.FIXED_ASSET, "debit"),
            ("1600", "Accumulated Depreciation", AccountType.CONTRA_ASSET, None, "credit"),
            ("2000", "Accounts Payable", AccountType.LIABILITY, AccountSubtype.ACCOUNTS_PAYABLE, "credit"),
            ("2100", "Credit Card Payable", AccountType.LIABILITY, AccountSubtype.CREDIT_CARD, "credit"),
            ("2200", "Accrued Liabilities", AccountType.LIABILITY, AccountSubtype.ACCRUED_LIABILITY, "credit"),
            ("2500", "Long-Term Loan", AccountType.LIABILITY, AccountSubtype.LONG_TERM_DEBT, "credit"),
            ("3000", "Owner's Equity", AccountType.EQUITY, AccountSubtype.OWNERS_EQUITY, "credit"),
            ("3100", "Retained Earnings", AccountType.EQUITY, AccountSubtype.RETAINED_EARNINGS, "credit"),
            ("4000", "Sales Revenue", AccountType.REVENUE, AccountSubtype.SALES, "credit"),
            ("4100", "Service Revenue", AccountType.REVENUE, AccountSubtype.SERVICE_REVENUE, "credit"),
            ("4200", "Other Income", AccountType.REVENUE, AccountSubtype.OTHER_INCOME, "credit"),
            ("4900", "Sales Returns & Allowances", AccountType.CONTRA_REVENUE, None, "debit"),
            ("5000", "Cost of Goods Sold", AccountType.EXPENSE, AccountSubtype.COST_OF_GOODS, "debit"),
            ("6000", "Rent Expense", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
            ("6100", "Utilities Expense", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
            ("6200", "Office Supplies", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
            ("6300", "Advertising Expense", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
            ("6400", "Insurance Expense", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
            ("6500", "Payroll Expense", AccountType.EXPENSE, AccountSubtype.PAYROLL, "debit"),
            ("7000", "Depreciation Expense", AccountType.EXPENSE, AccountSubtype.DEPRECIATION, "debit"),
            ("8000", "Interest Expense", AccountType.EXPENSE, AccountSubtype.OTHER_EXPENSE, "debit"),
            ("9000", "Income Tax Expense", AccountType.EXPENSE, AccountSubtype.TAX_EXPENSE, "debit"),
        ]

        for num, name, atype, subtype, normal in coa:
            session.add(Account(
                id=uuid.uuid4(),
                organization_id=org.id,
                account_number=num,
                name=name,
                account_type=atype,
                account_subtype=subtype,
                normal_balance=normal,
                is_system=True,
            ))

        await session.commit()
