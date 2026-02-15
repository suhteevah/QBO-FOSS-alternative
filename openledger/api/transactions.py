"""Bank Transaction Import API endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import BankTransaction, User, UserRole
from openledger.schemas import BankImportResponse, BankTransactionResponse
from openledger.auth import get_current_user, require_roles
from openledger.importer import TransactionImporter

router = APIRouter()


@router.post("/import", response_model=BankImportResponse)
async def import_bank_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    content = await file.read()
    importer = TransactionImporter(db, current_user.organization_id)
    return await importer.import_file(content, file.filename)


@router.get("/", response_model=list[BankTransactionResponse])
async def list_transactions(
    reconciled: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(BankTransaction).where(
        BankTransaction.organization_id == current_user.organization_id
    )
    if reconciled is not None:
        query = query.where(BankTransaction.is_reconciled == reconciled)
    query = query.order_by(BankTransaction.transaction_date.desc()).limit(200)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{txn_id}", response_model=BankTransactionResponse)
async def get_transaction(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BankTransaction).where(
            BankTransaction.id == txn_id,
            BankTransaction.organization_id == current_user.organization_id,
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
