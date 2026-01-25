"""
Pydantic Schemas
================

Request and response models for API endpoints.
"""

from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional
from datetime import datetime
from decimal import Decimal


# ============================================================================
# Authentication Schemas
# ============================================================================

class UserRegister(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User information response"""
    user_id: str
    email: str
    full_name: Optional[str]
    trust_score: int
    is_active: bool
    created_at: datetime
    role: str = "user"  # "user" or "master"
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response with token and user data"""
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


# ============================================================================
# Subscription Schemas
# ============================================================================

class SubscriptionCreate(BaseModel):
    """Create subscription request"""
    master_id: UUID4


class SubscriptionResponse(BaseModel):
    """Subscription information response"""
    subscription_id: str
    subscriber_id: str
    master_id: str
    master_name: Optional[str] = None
    state: str
    is_active: bool
    created_at: datetime
    paused_at: Optional[datetime]
    paused_reason: Optional[str]
    
    class Config:
        from_attributes = True


class LicenseTokenResponse(BaseModel):
    """License token response (shown only once)"""
    subscription_id: str
    license_token: str
    expires_at: Optional[datetime]
    message: str = "Save this token - it won't be shown again"


# ============================================================================
# Wallet Schemas
# ============================================================================

class WalletResponse(BaseModel):
    """Wallet information response"""
    wallet_id: str
    user_id: str
    balance_usd: Decimal
    reserved_usd: Decimal
    lifetime_deposits: Decimal
    lifetime_fees: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True


class WalletDeposit(BaseModel):
    """Wallet deposit request"""
    amount_usd: Decimal = Field(..., gt=0, description="Amount to deposit (must be positive)")
    description: Optional[str] = "Wallet deposit"


class WalletWithdraw(BaseModel):
    """Wallet withdrawal request"""
    amount_usd: Decimal = Field(..., gt=0, description="Amount to withdraw (must be positive)")
    description: Optional[str] = "Wallet withdrawal"


class TransactionResponse(BaseModel):
    """Transaction/ledger entry response"""
    ledger_id: str
    entry_type: str
    amount_usd: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Protection Event Schemas
# ============================================================================

class ProtectionEventCreate(BaseModel):
    """Create protection event (from EA)"""
    subscription_id: UUID4
    signal_sequence: int
    signal_generated_at: datetime
    server_arrival_time: datetime
    reason: str
    latency_ms: int
    current_state: str
    metadata: Optional[dict] = None


class ProtectionEventResponse(BaseModel):
    """Protection event response"""
    event_id: str
    subscription_id: str
    user_id: str
    signal_sequence: int
    reason: str
    latency_ms: int
    event_time: datetime
    
    class Config:
        from_attributes = True
# ============================================================================
# Master Trader Schemas
# ============================================================================

class MasterProfileCreate(BaseModel):
    """Create or update master trader profile"""
    display_name: str = Field(..., min_length=3, max_length=100)
    strategy_name: str = Field(..., min_length=3, max_length=100)
    monthly_fee: Decimal = Field(Decimal("0.00"), ge=0)
    bio: Optional[str] = Field(None, max_length=1000)


class MasterProfileResponse(BaseModel):
    """Master trader profile information"""
    user_id: str
    display_name: str
    strategy_name: str
    monthly_fee: Decimal
    bio: Optional[str]
    win_rate: Decimal
    total_signals: int
    avg_profit: Decimal
    verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
