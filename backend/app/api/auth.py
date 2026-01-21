"""
Authentication API Endpoints
=============================

User registration, login, and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import uuid
from datetime import timedelta

from app.database import get_db
from app.schemas import UserRegister, UserLogin, Token, UserResponse
from app.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_id
)
from app.config import settings

router = APIRouter()


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    
    Creates user account and initializes wallet with $0 balance.
    """
    # Check if email already exists
    result = await db.execute(
        text("SELECT user_id FROM users WHERE email = :email"),
        {"email": user_data.email}
    )
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate user ID
    user_id = str(uuid.uuid4())
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Insert user
    await db.execute(
        text("""
            INSERT INTO users (user_id, email, password_hash, full_name, trust_score, is_active)
            VALUES (:user_id, :email, :password_hash, :full_name, 100, TRUE)
        """),
        {
            "user_id": user_id,
            "email": user_data.email,
            "password_hash": hashed_password,
            "full_name": user_data.full_name
        }
    )
    
    # Create wallet for user
    await db.execute(
        text("""
            INSERT INTO user_wallets (user_id, balance_usd, reserved_usd)
            VALUES (:user_id, 0, 0)
        """),
        {"user_id": user_id}
    )
    
    await db.commit()
    
    # Fetch created user
    result = await db.execute(
        text("""
            SELECT user_id, email, full_name, trust_score, is_active, created_at
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    user = result.first()
    
    return UserResponse(
        user_id=str(user.user_id),
        email=user.email,
        full_name=user.full_name,
        trust_score=user.trust_score,
        is_active=user.is_active,
        created_at=user.created_at
    )


@router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    """
    # Fetch user by email
    result = await db.execute(
        text("SELECT user_id, password_hash, is_active FROM users WHERE email = :email"),
        {"email": credentials.email}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.user_id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return Token(access_token=access_token)


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user's profile.
    """
    result = await db.execute(
        text("""
            SELECT user_id, email, full_name, trust_score, is_active, created_at
            FROM users
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        user_id=str(user.user_id),
        email=user.email,
        full_name=user.full_name,
        trust_score=user.trust_score,
        is_active=user.is_active,
        created_at=user.created_at
    )
