"""Authentication API endpoints."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.database import get_db
from openledger.models import User, Organization, UserRole
from openledger.schemas import LoginRequest, TokenResponse
from openledger.auth import (
    verify_password, hash_password, create_access_token, get_current_user,
)

router = APIRouter()


class RegisterRequest(LoginRequest):
    full_name: str | None = None
    organization_name: str | None = None


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(user.id, user.organization_id, user.role.value)
    return TokenResponse(access_token=token, role=user.role.value)


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Password strength validation
    if len(data.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # Always create a new organization — users cannot join arbitrary orgs via registration.
    # To add users to an existing org, an admin must use the POST /users (invite) endpoint.
    org = Organization(name=data.organization_name or f"{data.email}'s Organization")
    db.add(org)
    await db.flush()

    # First user of a new org is always admin
    user = User(
        organization_id=org.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.flush()

    token = create_access_token(user.id, org.id, user.role.value)
    return TokenResponse(access_token=token, role=user.role.value)


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "organization_id": str(current_user.organization_id),
    }


# ── User Management (Admin-only) ──────────────────────────

from openledger.auth import require_roles
from pydantic import BaseModel


class InviteUserRequest(BaseModel):
    email: str
    full_name: str | None = None
    role: str = "client"
    password: str


class UpdateUserRoleRequest(BaseModel):
    role: str


@router.post("/users", status_code=201)
async def invite_user(
    data: InviteUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Admin creates a new user in their organization."""
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        organization_id=current_user.organization_id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole(data.role),
    )
    db.add(user)
    await db.flush()

    return {"id": str(user.id), "email": user.email, "role": user.role.value}


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """List all users in the current organization."""
    result = await db.execute(
        select(User).where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at)
    )
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_active": u.is_active,
        }
        for u in users
    ]


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: uuid.UUID,
    data: UpdateUserRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Change a user's role (admin-only)."""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = UserRole(data.role)
    return {"id": str(user.id), "role": user.role.value}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Deactivate a user account (admin-only)."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    return {"id": str(user.id), "is_active": False}
