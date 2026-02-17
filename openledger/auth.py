"""
JWT + API Key Authentication & Role-Based Access Control

Provides:
- Password hashing (bcrypt)
- JWT token creation/validation
- API key generation/validation (SHA-256 hashed, ol_ prefixed)
- Unified FastAPI dependency: accepts EITHER JWT Bearer OR X-API-Key header
- Role-based access control

API key auth is designed platform-aware from day one so Android, iOS,
web, and CLI clients all use the same X-API-Key header mechanism.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
import jwt
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.config import settings
from openledger.database import get_db
from openledger.models import APIKey, User, UserRole

# ── Auth Schemes (both use auto_error=False so neither raises 401 alone) ──

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ── Password Utilities ─────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT Utilities ──────────────────────────────────────────

def create_access_token(
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "org": str(organization_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── API Key Utilities ──────────────────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        (raw_key, key_hash, key_prefix)
        - raw_key: The full key to show the user ONCE (e.g. ol_abc123...)
        - key_hash: SHA-256 hex digest to store in DB
        - key_prefix: First 11 chars for display (e.g. ol_abc1234)
    """
    random_part = secrets.token_urlsafe(48)
    raw_key = f"ol_{random_part}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:11]
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hash of the raw API key for storage."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


async def _get_user_from_api_key(
    raw_key: str,
    db: AsyncSession,
) -> Optional[User]:
    """
    Validate an API key and return its associated User.
    Returns None if the key is invalid, expired, or revoked.
    Updates last_used_at on success.
    """
    key_hash = hash_api_key(raw_key)

    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_revoked == False,  # noqa: E712
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        return None

    # Check expiry
    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        return None

    # Update last_used_at (fire-and-forget — don't block the request)
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    # Load the user
    user_result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = user_result.scalar_one_or_none()
    return user


# ── Unified Auth Dependency ────────────────────────────────

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Unified authentication dependency.

    Accepts EITHER:
    - Authorization: Bearer <jwt_token>
    - X-API-Key: ol_<key>

    API key is checked first (cheaper than JWT decode).
    This means every existing endpoint gets dual-auth automatically
    with ZERO changes to route files.

    Works identically for Android, iOS, web, and CLI clients.
    """
    # Try API key first (mobile/programmatic clients)
    if api_key:
        user = await _get_user_from_api_key(api_key, db)
        if user:
            if not user.is_active:
                raise HTTPException(status_code=403, detail="User account is disabled")
            return user
        # If api_key was provided but invalid, fall through to JWT
        # (don't error yet — maybe they also sent a Bearer token)

    # Try JWT (web frontend / Swagger)
    if token:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User account is disabled")
        return user

    # Neither auth method provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either 'Authorization: Bearer <jwt>' or 'X-API-Key: ol_...' header.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(*allowed_roles: UserRole):
    """
    Returns a dependency that enforces the user has one of the specified roles.

    Usage:
        @router.post("/admin-only")
        async def admin_endpoint(user: User = Depends(require_roles(UserRole.ADMIN))):
            ...
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker
