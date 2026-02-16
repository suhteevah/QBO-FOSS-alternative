"""Financial Reports API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import User, UserRole
from openledger.schemas import ReportRequest, ReportResponse
from openledger.auth import get_current_user
from openledger.report_engine import ReportEngine

router = APIRouter()


@router.get("/")
async def list_report_types():
    return {
        "available_reports": [
            "profit_loss",
            "balance_sheet",
            "trial_balance",
        ]
    }


@router.post("/profit-loss", response_model=ReportResponse)
async def profit_and_loss(
    data: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a Profit & Loss (Income Statement) for the specified period."""
    if data.start_date > data.end_date:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")

    engine = ReportEngine(db, current_user.organization_id)
    return await engine.profit_and_loss(
        start_date=data.start_date,
        end_date=data.end_date,
        accounting_basis=data.accounting_basis or "accrual",
    )


@router.post("/balance-sheet", response_model=ReportResponse)
async def balance_sheet(
    data: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a Balance Sheet as of the end date."""
    engine = ReportEngine(db, current_user.organization_id)
    return await engine.balance_sheet(
        as_of=data.end_date,
        accounting_basis=data.accounting_basis or "accrual",
    )


@router.post("/trial-balance", response_model=ReportResponse)
async def trial_balance(
    data: ReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a Trial Balance as of the end date."""
    engine = ReportEngine(db, current_user.organization_id)
    return await engine.trial_balance(as_of=data.end_date)
