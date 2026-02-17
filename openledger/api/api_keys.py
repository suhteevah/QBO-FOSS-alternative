"""
API Key Management Endpoints

Allows authenticated users to create, list, and revoke long-lived API keys
for programmatic / mobile access. Keys work across all platforms:
Android, iOS, web, CLI.

Key lifecycle:
  1. User authenticates with JWT (web login)
  2. POST /api/keys/ → returns raw key ONCE
  3. Client stores key securely (EncryptedSharedPreferences on Android,
     Keychain on iOS, etc.)
  4. All subsequent requests use X-API-Key header
  5. DELETE /api/keys/{id} → soft-revokes key
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.auth import generate_api_key, get_current_user
from openledger.config import settings
from openledger.database import get_db
from openledger.models import APIKey, User
from openledger.schemas import APIKeyCreate, APIKeyCreateResponse, APIKeyResponse

router = APIRouter()


@router.post("/", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    data: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key. The raw key is returned ONCE and cannot be retrieved again.

    The `platform` field tracks what client type created this key (android, ios, web, cli).
    The `device_info` field is an optional human-readable device identifier.
    """
    # Validate platform
    valid_platforms = {"android", "ios", "web", "cli"}
    if data.platform not in valid_platforms:
        raise HTTPException(
            status_code=422,
            detail=f"platform must be one of: {sorted(valid_platforms)}",
        )

    raw_key, key_hash, key_prefix = generate_api_key()

    # Calculate expiry
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=data.expires_in_days)
    elif settings.api_key_default_expiry_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.api_key_default_expiry_days)

    api_key = APIKey(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        name=data.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        platform=data.platform,
        device_info=data.device_info,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.flush()

    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=key_prefix,
        raw_key=raw_key,
        platform=api_key.platform,
        device_info=api_key.device_info,
        expires_at=expires_at,
        created_at=api_key.created_at,
    )


@router.get("/", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all API keys for the current user (no raw keys — only prefixes).
    Useful for device management UI showing all connected Android/iOS/web clients.
    """
    result = await db.execute(
        select(APIKey)
        .where(
            APIKey.user_id == current_user.id,
            APIKey.is_revoked == False,  # noqa: E712
        )
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()
    return keys


@router.delete("/{key_id}", status_code=200)
async def revoke_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke (soft-delete) an API key. The key immediately stops working.
    Works for any platform — Android, iOS, web, or CLI keys.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    if api_key.is_revoked:
        raise HTTPException(status_code=400, detail="API key is already revoked")

    api_key.is_revoked = True
    return {
        "id": str(api_key.id),
        "name": api_key.name,
        "platform": api_key.platform,
        "revoked": True,
    }
