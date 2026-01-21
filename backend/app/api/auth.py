from datetime import datetime, timedelta
from typing import Optional, Union, Any
import uuid
from jose import JWTError, jwt
import bcrypt  # Replaces passlib
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.schemas import UserRegister, UserLogin, Token, UserResponse

# Security scheme
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against the stored bcrypt hash.
    """
    # bcrypt requires bytes
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)

def get_password_hash(password: str) -> str:
    """
    Hashes a password using bcrypt.
    """
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    
    # Return as string for database storage
    return hashed_password.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validates JWT token and returns the user_id (sub).
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

# Router definition
router = APIRouter()

@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
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

