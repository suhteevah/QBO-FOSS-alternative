"""Receipt OCR API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import Receipt, User
from openledger.schemas import (
    JournalEntryResponse,
    ReceiptClassifyResponse,
    ReceiptCreateEntryRequest,
    ReceiptResponse,
)
from openledger.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=list[ReceiptResponse])
async def list_receipts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all receipts for the current organization."""
    result = await db.execute(
        select(Receipt)
        .where(Receipt.organization_id == current_user.organization_id)
        .order_by(Receipt.created_at.desc())
        .limit(200)
    )
    return result.scalars().all()


@router.post("/upload", response_model=ReceiptResponse, status_code=201)
async def upload_receipt(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from openledger.ocr_service import OCRService

    content = await file.read()
    service = OCRService(current_user.organization_id)
    save_path = f"uploads/{current_user.organization_id}/{uuid.uuid4()}/{file.filename}"
    receipt = await service.process_receipt(content, file.content_type, current_user.id, save_path)
    db.add(receipt)
    await db.flush()
    await db.refresh(receipt)
    return receipt


@router.post(
    "/{receipt_id}/classify",
    response_model=ReceiptClassifyResponse,
)
async def classify_receipt(
    receipt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run AI classification on a receipt to suggest a chart of accounts category.

    Returns the suggested account, confidence score, and reasoning.
    """
    from openledger.receipt_pipeline import (
        ReceiptPipeline,
        ReceiptNotFoundError,
        ReceiptNotProcessedError,
    )

    pipeline = ReceiptPipeline(db, current_user.organization_id)
    try:
        result = await pipeline.classify_receipt(receipt_id)
    except ReceiptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ReceiptNotProcessedError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return result


@router.post(
    "/{receipt_id}/create-entry",
    response_model=JournalEntryResponse,
    status_code=201,
)
async def create_entry_from_receipt(
    receipt_id: uuid.UUID,
    data: ReceiptCreateEntryRequest = ReceiptCreateEntryRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a balanced journal entry from a processed receipt.

    If account_id is provided in the request body, it overrides AI classification.
    Otherwise the AI service determines the expense account automatically.

    The resulting entry debits the expense account (and optionally a tax account)
    and credits Cash for the total receipt amount.
    """
    from openledger.receipt_pipeline import (
        ReceiptPipeline,
        ReceiptNotFoundError,
        ReceiptNotProcessedError,
        ReceiptAlreadyLinkedError,
        ReceiptMissingDataError,
        AccountNotFoundError,
    )
    from openledger.ledger import LedgerError

    pipeline = ReceiptPipeline(db, current_user.organization_id)
    try:
        entry = await pipeline.create_entry_from_receipt(
            receipt_id=receipt_id,
            account_id=data.account_id,
            created_by=current_user.id,
        )
    except ReceiptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ReceiptNotProcessedError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ReceiptAlreadyLinkedError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ReceiptMissingDataError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LedgerError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return entry
