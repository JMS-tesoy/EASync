"""
Protection Events API
=====================

Log and query protection events from EAs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas import ProtectionEventCreate, ProtectionEventResponse
from app.auth import get_current_user_id

router = APIRouter()


@router.post("/protection-events", response_model=ProtectionEventResponse, status_code=status.HTTP_201_CREATED)
async def create_protection_event(
    event_data: ProtectionEventCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Log a protection event from EA.
    
    This endpoint is called by the ExecutionGuard when a signal is rejected.
    No authentication required (uses subscription_id for validation).
    """
    # Verify subscription exists
    result = await db.execute(
        text("""
            SELECT subscriber_id FROM subscriptions
            WHERE subscription_id = :subscription_id
        """),
        {"subscription_id": str(event_data.subscription_id)}
    )
    
    subscription = result.first()
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    user_id = subscription.subscriber_id
    
    # Insert protection event
    result = await db.execute(
        text("""
            INSERT INTO protection_logs (
                subscription_id, user_id, signal_sequence,
                signal_generated_at, server_arrival_time,
                reason, latency_ms, current_state
            ) VALUES (
                :subscription_id, :user_id, :signal_sequence,
                :signal_generated_at, :server_arrival_time,
                :reason::protection_event_reason, :latency_ms, :current_state
            )
            RETURNING event_id, event_time
        """),
        {
            "subscription_id": str(event_data.subscription_id),
            "user_id": str(user_id),
            "signal_sequence": event_data.signal_sequence,
            "signal_generated_at": event_data.signal_generated_at,
            "server_arrival_time": event_data.server_arrival_time,
            "reason": event_data.reason,
            "latency_ms": event_data.latency_ms,
            "current_state": event_data.current_state
        }
    )
    
    event = result.first()
    await db.commit()
    
    return ProtectionEventResponse(
        event_id=str(event.event_id),
        subscription_id=str(event_data.subscription_id),
        user_id=str(user_id),
        signal_sequence=event_data.signal_sequence,
        reason=event_data.reason,
        latency_ms=event_data.latency_ms,
        event_time=event.event_time
    )


@router.get("/protection-events", response_model=List[ProtectionEventResponse])
async def get_protection_events(
    subscription_id: Optional[str] = None,
    hours: int = 24,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get protection events for current user.
    
    Query parameters:
    - subscription_id: Filter by specific subscription (optional)
    - hours: Time window in hours (default: 24)
    - limit: Maximum number of events to return (default: 100)
    """
    # Build query
    if subscription_id:
        # Verify subscription belongs to user
        result = await db.execute(
            text("""
                SELECT subscription_id FROM subscriptions
                WHERE subscription_id = :subscription_id
                  AND subscriber_id = :user_id
            """),
            {"subscription_id": subscription_id, "user_id": user_id}
        )
        
        if not result.first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        # Query events for specific subscription
        result = await db.execute(
            text("""
                SELECT 
                    event_id, subscription_id, user_id, signal_sequence,
                    reason, latency_ms, event_time
                FROM protection_logs
                WHERE subscription_id = :subscription_id
                  AND event_time > NOW() - INTERVAL '1 hour' * :hours
                ORDER BY event_time DESC
                LIMIT :limit
            """),
            {"subscription_id": subscription_id, "hours": hours, "limit": limit}
        )
    else:
        # Query all events for user
        result = await db.execute(
            text("""
                SELECT 
                    event_id, subscription_id, user_id, signal_sequence,
                    reason, latency_ms, event_time
                FROM protection_logs
                WHERE user_id = :user_id
                  AND event_time > NOW() - INTERVAL '1 hour' * :hours
                ORDER BY event_time DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "hours": hours, "limit": limit}
        )
    
    events = []
    for row in result:
        events.append(ProtectionEventResponse(
            event_id=str(row.event_id),
            subscription_id=str(row.subscription_id),
            user_id=str(row.user_id),
            signal_sequence=row.signal_sequence,
            reason=row.reason,
            latency_ms=row.latency_ms,
            event_time=row.event_time
        ))
    
    return events


@router.get("/protection-events/summary")
async def get_protection_summary(
    hours: int = 24,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of protection events (grouped by reason).
    """
    result = await db.execute(
        text("""
            SELECT 
                reason,
                COUNT(*) as count,
                AVG(latency_ms) as avg_latency_ms
            FROM protection_logs
            WHERE user_id = :user_id
              AND event_time > NOW() - INTERVAL '1 hour' * :hours
            GROUP BY reason
            ORDER BY count DESC
        """),
        {"user_id": user_id, "hours": hours}
    )
    
    summary = []
    for row in result:
        summary.append({
            "reason": row.reason,
            "count": row.count,
            "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else 0
        })
    
    return {
        "time_window_hours": hours,
        "events_by_reason": summary
    }
