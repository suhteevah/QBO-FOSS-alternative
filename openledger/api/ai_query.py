"""AI Natural Language Query API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import User
from openledger.schemas import AIQueryRequest, AIQueryResponse
from openledger.auth import get_current_user
from openledger.ai_service import AIService

router = APIRouter()


@router.post("/query", response_model=AIQueryResponse)
async def natural_language_query(
    data: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AIService(db, current_user.organization_id)
    result = await service.natural_language_query(data.query, user_id=current_user.id)
    return result
