"""
Signal Distribution API
========================

HTTP polling endpoint for Signal Receiver EAs to fetch pending signals.
This bridges Redis Streams to MQL5-compatible HTTP/JSON format.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import redis.asyncio as redis
import json

from app.database import get_db
from app.config import settings

router = APIRouter()

# Redis connection pool
redis_pool = None

async def get_redis():
    """Get Redis connection from pool"""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.from_url(settings.redis_url, decode_responses=True)
    return redis_pool


class SignalResponse(BaseModel):
    """Signal data returned to Receiver EA"""
    subscription_id: str
    sequence_number: int
    generated_at: int  # Unix timestamp in milliseconds
    symbol: str
    order_type: int    # 1=BUY, 2=SELL, 3=CLOSE
    volume: float
    price: float
    stop_loss: float
    take_profit: float
    signature: str


class PollResponse(BaseModel):
    """Response for polling endpoint"""
    has_signals: bool
    signals: List[SignalResponse]
    last_sequence: int


@router.get("/signals/poll/{license_token}", response_model=PollResponse)
async def poll_signals(
    license_token: str,
    last_seq: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Poll for new signals since last_seq.
    
    Receiver EAs call this endpoint every 100-500ms to fetch pending signals.
    
    Args:
        license_token: The subscriber's license token
        last_seq: Last processed sequence number (receiver tracks this)
        limit: Maximum signals to return (default 10)
    
    Returns:
        List of signals with sequence > last_seq
    """
    # Validate license token and get subscription info
    result = await db.execute(
        text("""
            SELECT s.subscription_id, s.master_id, s.state, s.is_active
            FROM subscriptions s
            JOIN subscription_licenses sl ON s.subscription_id = sl.subscription_id
            WHERE sl.license_token = :token
              AND s.is_active = TRUE
        """),
        {"token": license_token}
    )
    
    subscription = result.first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive license token"
        )
    
    # Check if subscription is paused
    if subscription.state in ('PAUSED_USER', 'PAUSED_TOXIC', 'SUSPENDED_ADMIN'):
        return PollResponse(
            has_signals=False,
            signals=[],
            last_sequence=last_seq
        )
    
    # Fetch signals from Redis Stream
    redis_client = await get_redis()
    stream_key = f"signals:{subscription.master_id}"
    
    try:
        # Read signals from stream after last_seq
        # Using XREAD with consumer group for exactly-once delivery
        signals = []
        
        # Try to read from stream
        entries = await redis_client.xread(
            {stream_key: last_seq if last_seq > 0 else "0"},
            count=limit,
            block=0  # Non-blocking
        )
        
        if entries:
            for stream_name, messages in entries:
                for msg_id, data in messages:
                    try:
                        signal = SignalResponse(
                            subscription_id=data.get("subscription_id", ""),
                            sequence_number=int(data.get("sequence_number", 0)),
                            generated_at=int(data.get("generated_at", 0)),
                            symbol=data.get("symbol", ""),
                            order_type=int(data.get("order_type", 0)),
                            volume=float(data.get("volume", 0)),
                            price=float(data.get("price", 0)),
                            stop_loss=float(data.get("stop_loss", 0)),
                            take_profit=float(data.get("take_profit", 0)),
                            signature=data.get("signature", "")
                        )
                        signals.append(signal)
                    except Exception as e:
                        print(f"Error parsing signal: {e}")
                        continue
        
        # Get the highest sequence from returned signals
        new_last_seq = last_seq
        if signals:
            new_last_seq = max(s.sequence_number for s in signals)
        
        return PollResponse(
            has_signals=len(signals) > 0,
            signals=signals,
            last_sequence=new_last_seq
        )
        
    except Exception as e:
        print(f"Redis error: {e}")
        # Return empty response on Redis errors (fail gracefully)
        return PollResponse(
            has_signals=False,
            signals=[],
            last_sequence=last_seq
        )


@router.get("/signals/status/{license_token}")
async def get_signal_status(
    license_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription status for Receiver EA.
    
    Returns current state, connection info, and last signal time.
    """
    result = await db.execute(
        text("""
            SELECT 
                s.subscription_id,
                s.master_id,
                s.state,
                s.is_active,
                mp.display_name as master_name,
                s.created_at
            FROM subscriptions s
            JOIN subscription_licenses sl ON s.subscription_id = sl.subscription_id
            LEFT JOIN master_profiles mp ON s.master_id = mp.user_id
            WHERE sl.license_token = :token
        """),
        {"token": license_token}
    )
    
    subscription = result.first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid license token"
        )
    
    return {
        "subscription_id": str(subscription.subscription_id),
        "master_id": str(subscription.master_id),
        "master_name": subscription.master_name,
        "state": subscription.state,
        "is_active": subscription.is_active,
        "can_trade": subscription.state == "SYNCED" and subscription.is_active,
        "created_at": subscription.created_at.isoformat()
    }
