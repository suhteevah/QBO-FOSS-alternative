"""
Bank Transaction Import & Pipeline API endpoints.

Provides:
- File import (CSV/XLSX)
- Transaction listing and retrieval
- AI classification of unprocessed transactions
- Journal entry creation from classified transactions
- Full pipeline (classify + create entries)
- Single transaction → journal entry conversion
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import BankTransaction, User, UserRole
from openledger.schemas import (
    BankImportResponse,
    BankTransactionResponse,
    ClassifyRequest,
    ClassifyResponse,
    CreateEntriesRequest,
    CreateEntriesResponse,
    SingleEntryRequest,
    SingleEntryResponse,
    ProcessBatchRequest,
    ProcessBatchResponse,
)
from openledger.auth import get_current_user, require_roles
from openledger.importer import TransactionImporter
from openledger.transaction_pipeline import TransactionPipeline, PipelineError

router = APIRouter()


# ── File Import ───────────────────────────────────────────────

@router.post("/import", response_model=BankImportResponse)
async def import_bank_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """Import a CSV or XLSX bank statement file."""
    content = await file.read()
    importer = TransactionImporter(db, current_user.organization_id)
    return await importer.import_file(content, file.filename)


# ── Transaction Listing ──────────────────────────────────────

@router.get("/", response_model=list[BankTransactionResponse])
async def list_transactions(
    reconciled: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List bank transactions with optional reconciled filter."""
    query = select(BankTransaction).where(
        BankTransaction.organization_id == current_user.organization_id
    )
    if reconciled is not None:
        query = query.where(BankTransaction.is_reconciled == reconciled)
    query = query.order_by(BankTransaction.transaction_date.desc()).limit(200)

    result = await db.execute(query)
    return result.scalars().all()


# ── Pipeline: Classify ────────────────────────────────────────

@router.post("/classify", response_model=ClassifyResponse)
async def classify_transactions(
    data: ClassifyRequest = ClassifyRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """
    Run AI classification on unprocessed bank transactions.

    Finds transactions where ai_category IS NULL and sends them through
    Claude Sonnet for automatic categorization against the chart of accounts.
    Each transaction is updated with suggested_account_id, ai_category,
    ai_confidence, and description_cleaned.
    """
    pipeline = TransactionPipeline(db, current_user.organization_id)
    try:
        result = await pipeline.classify_unprocessed(limit=data.limit)
        return result
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")


# ── Pipeline: Create Entries ──────────────────────────────────

@router.post("/create-entries", response_model=CreateEntriesResponse)
async def create_entries_from_classified(
    data: CreateEntriesRequest = CreateEntriesRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """
    Create journal entries from high-confidence classified transactions.

    Finds classified but un-reconciled transactions above the confidence
    threshold, creates balanced double-entry journal entries for each
    (debit expense / credit Cash for expenses; debit Cash / credit revenue
    for deposits), and links them to the bank transaction.
    """
    pipeline = TransactionPipeline(db, current_user.organization_id)
    try:
        result = await pipeline.create_entries_from_classified(
            confidence_threshold=data.confidence_threshold,
        )
        return result
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entry creation failed: {str(e)}")


# ── Pipeline: Single Transaction Entry ────────────────────────

@router.post("/{txn_id}/create-entry", response_model=SingleEntryResponse)
async def create_single_entry(
    txn_id: uuid.UUID,
    data: SingleEntryRequest = SingleEntryRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """
    Create a journal entry from a single bank transaction.

    Optionally accepts an account_id to override the AI-suggested account.
    If no account_id is provided, uses the AI-suggested account (the
    transaction must have been classified first, or an account_id must
    be supplied).
    """
    pipeline = TransactionPipeline(db, current_user.organization_id)
    try:
        result = await pipeline.create_entry_for_single(
            transaction_id=txn_id,
            account_id_override=data.account_id,
        )
        return result
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entry creation failed: {str(e)}")


# ── Pipeline: Full Process ────────────────────────────────────

@router.post("/process", response_model=ProcessBatchResponse)
async def process_transactions(
    data: ProcessBatchRequest = ProcessBatchRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    """
    Run the full transaction pipeline: classify unprocessed transactions,
    then create journal entries from high-confidence results.

    This is a convenience endpoint that combines /classify and /create-entries
    into a single call.
    """
    pipeline = TransactionPipeline(db, current_user.organization_id)
    try:
        result = await pipeline.process_batch(
            limit=data.limit,
            confidence_threshold=data.confidence_threshold,
        )
        return result
    except PipelineError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


# ── Transaction Detail ───────────────────────────────────────

@router.get("/{txn_id}", response_model=BankTransactionResponse)
async def get_transaction(
    txn_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single bank transaction by ID."""
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
