"""OpenLedger — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openledger.config import settings
from openledger.api import (
    accounts,
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

app = FastAPI(
    title="OpenLedger",
    description="FOSS GAAP-compliant AI-augmented bookkeeping platform",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)

# In debug mode, allow all origins for local development.
# In production, nginx proxies everything so CORS is not needed,
# but set explicit origins if you deploy frontend and API on different domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routes ──────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
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
