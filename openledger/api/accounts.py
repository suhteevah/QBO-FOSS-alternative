"""Chart of Accounts API endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import Account, AccountType
from openledger.schemas import AccountCreate, AccountResponse
from openledger.auth import get_current_user, require_roles
from openledger.models import User, UserRole
from openledger.ledger import NORMAL_BALANCE_MAP

router = APIRouter()


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Account)
        .where(Account.organization_id == current_user.organization_id, Account.is_active == True)
        .order_by(Account.account_number)
    )
    return result.scalars().all()


@router.post("/", response_model=AccountResponse, status_code=201)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    acct_type = AccountType(data.account_type)
    normal_balance = NORMAL_BALANCE_MAP.get(acct_type, "debit")

    account = Account(
        organization_id=current_user.organization_id,
        account_number=data.account_number,
        name=data.name,
        description=data.description,
        account_type=acct_type,
        account_subtype=data.account_subtype,
        parent_id=data.parent_id,
        normal_balance=normal_balance,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account
