"""Reconciliation API endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import User, UserRole
from openledger.auth import get_current_user, require_roles
from openledger.reconciliation_engine import ReconciliationEngine

router = APIRouter()


class ReconcileRequest(BaseModel):
    bank_transaction_id: uuid.UUID
    journal_entry_id: uuid.UUID


# ── Match Suggestions ──────────────────────────────────────

@router.get("/suggestions")
async def get_match_suggestions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get auto-match suggestions for unreconciled bank transactions.

    Returns each unreconciled transaction paired with its top candidate
    journal entry matches, scored by amount/date/description similarity.
    """
    engine = ReconciliationEngine(db, current_user.organization_id)
    return await engine.find_matches(limit=min(limit, 200))


# ── Apply / Undo Reconciliation ────────────────────────────

@router.post("/match")
async def reconcile_transaction(
    data: ReconcileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """Link a bank transaction to a journal entry and mark it reconciled."""
    engine = ReconciliationEngine(db, current_user.organization_id)
    try:
        return await engine.reconcile(
            bank_transaction_id=data.bank_transaction_id,
            journal_entry_id=data.journal_entry_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/unmatch/{txn_id}")
async def unreconcile_transaction(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """Undo a reconciliation — unlink the bank transaction from its journal entry."""
    engine = ReconciliationEngine(db, current_user.organization_id)
    try:
        return await engine.unreconcile(
            bank_transaction_id=txn_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Summary ────────────────────────────────────────────────

@router.get("/summary")
async def reconciliation_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reconciliation statistics — total, reconciled, unreconciled counts and amounts."""
    engine = ReconciliationEngine(db, current_user.organization_id)
    return await engine.get_summary()
