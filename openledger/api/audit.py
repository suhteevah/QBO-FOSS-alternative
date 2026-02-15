"""Audit Log API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import AuditLog, User, UserRole
from openledger.schemas import AuditLogResponse
from openledger.auth import require_roles

router = APIRouter()


@router.get("/", response_model=list[AuditLogResponse])
async def list_audit_logs(
    entity_type: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT)),
):
    query = (
        select(AuditLog)
        .where(AuditLog.organization_id == current_user.organization_id)
    )
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    query = query.order_by(AuditLog.created_at.desc()).limit(min(limit, 500))

    result = await db.execute(query)
    return result.scalars().all()
