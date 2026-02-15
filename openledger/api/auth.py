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
    organization_id: uuid.UUID | None = None


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

    # Create or use existing organization
    if data.organization_id:
        org_result = await db.execute(
            select(Organization).where(Organization.id == data.organization_id)
        )
        org = org_result.scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
    else:
        org = Organization(name=data.organization_name or f"{data.email}'s Organization")
        db.add(org)
        await db.flush()

    user = User(
        organization_id=org.id,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole.ADMIN,  # First user is admin
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
