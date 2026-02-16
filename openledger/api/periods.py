"""Accounting Period API endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import User, UserRole
from openledger.schemas import PeriodCreate, PeriodResponse, PeriodReadiness
from openledger.auth import get_current_user, require_roles
from openledger.period_service import (
    PeriodService,
    PeriodOverlapError,
    PeriodNotFoundError,
    PeriodAlreadyClosedError,
    PeriodAlreadyOpenError,
    PeriodError,
)

router = APIRouter()


@router.post("/", response_model=PeriodResponse, status_code=201)
async def create_period(
    data: PeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """Create a new accounting period with overlap validation."""
    service = PeriodService(db, current_user.organization_id)
    try:
        period = await service.create_period(
            name=data.name,
            start_date=data.start_date,
            end_date=data.end_date,
        )
        await db.flush()
        return period
    except PeriodOverlapError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/", response_model=list[PeriodResponse])
async def list_periods(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all accounting periods for the organization, ordered by start_date descending."""
    service = PeriodService(db, current_user.organization_id)
    return await service.list_periods()


@router.get("/{period_id}/readiness", response_model=PeriodReadiness)
async def get_period_readiness(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """
    Pre-close readiness check for a period.

    Returns counts of items that should be resolved before closing:
    unapproved journal entries, unreconciled bank transactions, and draft entries.
    """
    service = PeriodService(db, current_user.organization_id)
    try:
        return await service.get_readiness(period_id)
    except PeriodNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{period_id}/close", response_model=PeriodResponse)
async def close_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """
    Close an accounting period.

    Generates GAAP closing entries that zero out revenue and expense accounts
    and transfer the net income/loss to Retained Earnings (account 3200).
    """
    service = PeriodService(db, current_user.organization_id)
    try:
        return await service.close_period(period_id, current_user.id)
    except PeriodNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PeriodAlreadyClosedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PeriodError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/{period_id}/reopen", response_model=PeriodResponse)
async def reopen_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """
    Reopen a closed accounting period (admin only).

    Deletes the auto-generated closing entries and sets the period back to OPEN.
    """
    service = PeriodService(db, current_user.organization_id)
    try:
        return await service.reopen_period(period_id, current_user.id)
    except PeriodNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PeriodAlreadyOpenError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PeriodError as e:
        raise HTTPException(status_code=422, detail=str(e))
