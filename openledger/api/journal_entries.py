"""Journal Entry API endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from openledger.database import get_db
from openledger.models import JournalEntry, User, UserRole
from openledger.schemas import JournalEntryCreate, JournalEntryResponse
from openledger.auth import get_current_user, require_roles
from openledger.ledger import LedgerEngine

router = APIRouter()


@router.post("/", response_model=JournalEntryResponse, status_code=201)
async def create_journal_entry(
    data: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = LedgerEngine(db, current_user.organization_id)
    entry = await engine.create_journal_entry(data, created_by=current_user.id)
    await db.flush()
    # Reload with line items
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.line_items))
        .where(JournalEntry.id == entry.id)
    )
    return result.scalar_one()


@router.get("/", response_model=list[JournalEntryResponse])
async def list_journal_entries(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.line_items))
        .where(JournalEntry.organization_id == current_user.organization_id)
    )
    if status:
        query = query.where(JournalEntry.status == status)
    query = query.order_by(JournalEntry.entry_date.desc()).limit(200)

    result = await db.execute(query)
    return result.scalars().unique().all()


@router.post("/{entry_id}/approve", response_model=JournalEntryResponse)
async def approve_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    engine = LedgerEngine(db, current_user.organization_id)
    entry = await engine.approve_entry(entry_id, current_user.id)
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.line_items))
        .where(JournalEntry.id == entry.id)
    )
    return result.scalar_one()


@router.post("/{entry_id}/void", response_model=JournalEntryResponse)
async def void_entry(
    entry_id: uuid.UUID,
    reason: str = "Voided",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    engine = LedgerEngine(db, current_user.organization_id)
    entry = await engine.void_entry(entry_id, current_user.id, reason)
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.line_items))
        .where(JournalEntry.id == entry.id)
    )
    return result.scalar_one()
