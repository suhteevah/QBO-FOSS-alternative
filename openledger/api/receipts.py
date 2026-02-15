"""Receipt OCR API endpoints."""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import User
from openledger.schemas import ReceiptResponse
from openledger.auth import get_current_user

router = APIRouter()


@router.post("/upload", response_model=ReceiptResponse, status_code=201)
async def upload_receipt(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from openledger.ocr_service import OCRService
    import uuid

    content = await file.read()
    service = OCRService(current_user.organization_id)
    save_path = f"uploads/{current_user.organization_id}/{uuid.uuid4()}/{file.filename}"
    receipt = await service.process_receipt(content, file.content_type, current_user.id, save_path)
    db.add(receipt)
    await db.flush()
    await db.refresh(receipt)
    return receipt
