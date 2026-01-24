"""
Subscription Management API
============================

Create, manage, and monitor subscriptions.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
import uuid
import secrets
import hashlib

from app.database import get_db
from app.schemas import SubscriptionCreate, SubscriptionResponse, LicenseTokenResponse
from app.auth import get_current_user_id

router = APIRouter()


@router.post("/subscriptions", response_model=LicenseTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subscription to a master trader.
    
    Returns license token (shown only once).
    """
    # Verify master trader exists
    result = await db.execute(
        text("SELECT user_id FROM users WHERE user_id = :master_id"),
        {"master_id": str(subscription_data.master_id)}
    )
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master trader not found"
        )
    
    # Check if subscription already exists
    result = await db.execute(
        text("""
            SELECT subscription_id FROM subscriptions
            WHERE subscriber_id = :subscriber_id AND master_id = :master_id
              AND is_active = TRUE
        """),
        {"subscriber_id": user_id, "master_id": str(subscription_data.master_id)}
    )
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active subscription already exists"
        )
    
    # Generate subscription ID
    subscription_id = str(uuid.uuid4())
    
    # Create subscription
    await db.execute(
        text("""
            INSERT INTO subscriptions (
                subscription_id, subscriber_id, master_id,
                state, is_active, high_water_mark
            ) VALUES (
                :subscription_id, :subscriber_id, :master_id,
                'SYNCED', TRUE, 0
            )
        """),
        {
            "subscription_id": subscription_id,
            "subscriber_id": user_id,
            "master_id": str(subscription_data.master_id)
        }
    )
    
    # Generate license token (cryptographically secure)
    license_token = secrets.token_urlsafe(32)  # 43 characters, 256 bits
    
    # Hash token for storage
    token_hash = hashlib.sha256(license_token.encode()).hexdigest()
    
    # Store license token
    await db.execute(
        text("""
            INSERT INTO license_tokens (
                subscription_id, token_hash, is_active
            ) VALUES (
                :subscription_id, :token_hash, TRUE
            )
        """),
        {
            "subscription_id": subscription_id,
            "token_hash": token_hash
        }
    )
    
    await db.commit()
    
    return LicenseTokenResponse(
        subscription_id=subscription_id,
        license_token=license_token,
        expires_at=None  # No expiration by default
    )


@router.get("/subscriptions", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all subscriptions for the current user.
    """
    result = await db.execute(
        text("""
            SELECT 
                s.subscription_id, s.subscriber_id, s.master_id,
                s.state, s.is_active, s.created_at, s.paused_at, s.paused_reason,
                m.display_name as master_name
            FROM subscriptions s
            LEFT JOIN master_profiles m ON s.master_id = m.user_id
            WHERE s.subscriber_id = :user_id
            ORDER BY s.created_at DESC
        """),
        {"user_id": user_id}
    )
    
    subscriptions = []
    for row in result:
        subscriptions.append(SubscriptionResponse(
            subscription_id=str(row.subscription_id),
            subscriber_id=str(row.subscriber_id),
            master_id=str(row.master_id),
            master_name=row.master_name,
            state=row.state,
            is_active=row.is_active,
            created_at=row.created_at,
            paused_at=row.paused_at,
            paused_reason=row.paused_reason
        ))
    
    return subscriptions


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific subscription.
    """
    result = await db.execute(
        text("""
            SELECT 
                s.subscription_id, s.subscriber_id, s.master_id,
                s.state, s.is_active, s.created_at, s.paused_at, s.paused_reason,
                m.display_name as master_name
            FROM subscriptions s
            LEFT JOIN master_profiles m ON s.master_id = m.user_id
            WHERE s.subscription_id = :subscription_id
              AND s.subscriber_id = :user_id
        """),
        {"subscription_id": subscription_id, "user_id": user_id}
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    return SubscriptionResponse(
        subscription_id=str(row.subscription_id),
        subscriber_id=str(row.subscriber_id),
        master_id=str(row.master_id),
        master_name=row.master_name,
        state=row.state,
        is_active=row.is_active,
        created_at=row.created_at,
        paused_at=row.paused_at,
        paused_reason=row.paused_reason
    )


@router.post("/subscriptions/{subscription_id}/pause")
async def pause_subscription(
    subscription_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Pause a subscription (user-initiated).
    """
    # Verify ownership
    result = await db.execute(
        text("""
            SELECT subscription_id FROM subscriptions
            WHERE subscription_id = :subscription_id
              AND subscriber_id = :user_id
              AND is_active = TRUE
        """),
        {"subscription_id": subscription_id, "user_id": user_id}
    )
    
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active subscription not found"
        )
    
    # Pause subscription
    await db.execute(
        text("""
            UPDATE subscriptions
            SET state = 'PAUSED_USER',
                paused_at = NOW(),
                paused_reason = 'User requested pause',
                updated_at = NOW()
            WHERE subscription_id = :subscription_id
        """),
        {"subscription_id": subscription_id}
    )
    
    await db.commit()
    
    return {"message": "Subscription paused successfully"}


@router.post("/subscriptions/{subscription_id}/resume")
async def resume_subscription(
    subscription_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume a paused subscription.
    """
    # Verify ownership and paused state
    result = await db.execute(
        text("""
            SELECT subscription_id FROM subscriptions
            WHERE subscription_id = :subscription_id
              AND subscriber_id = :user_id
              AND state = 'PAUSED_USER'
        """),
        {"subscription_id": subscription_id, "user_id": user_id}
    )
    
    if not result.first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paused subscription not found"
        )
    
    # Resume subscription
    await db.execute(
        text("""
            UPDATE subscriptions
            SET state = 'SYNCED',
                paused_at = NULL,
                paused_reason = NULL,
                updated_at = NOW()
            WHERE subscription_id = :subscription_id
        """),
        {"subscription_id": subscription_id}
    )
    
    await db.commit()
    
    return {"message": "Subscription resumed successfully"}
