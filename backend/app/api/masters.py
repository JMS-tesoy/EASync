from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from datetime import datetime

from app.database import get_db
from app.schemas import MasterProfileCreate, MasterProfileResponse, TradeReport
from app.api.auth import get_current_user_id

router = APIRouter()

async def get_performance_history(user_id: str, db: AsyncSession) -> List[float]:
    """
    Calculate monthly returns for the last 6 months.
    Returns a list of percentage returns, e.g. [2.5, -1.1, 5.0, ...].
    """
    # For now, we'll just mock this or return empty if no trades
    # In a real implementation, we would query the trade_history table
    # and aggregate profit by month.
    
    # Check if we have any trades
    result = await db.execute(
        text("SELECT profit, closed_at FROM trade_history WHERE master_id = :uid ORDER BY closed_at DESC LIMIT 100"),
        {"uid": user_id}
    )
    trades = result.fetchall()
    
    if not trades:
        return []
    
    # Simple accumulation for demo (just list the last few profits as 'monthly' for now)
    # real logic would filter by month
    history = []
    current_month_profit = 0.0
    
    # Mock logic: just take the last 6 trades profit as "history" for visual effect
    # pending a real monthly aggregation query
    vals = [float(t.profit) for t in trades[:6]]
    return list(reversed(vals))  # Oldest to newest


@router.post("/report-trade")
async def report_trade(
    trade: TradeReport,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Report a closed trade result from the Master EA.
    """
    # Verify user is a master
    master = await db.execute(
        text("SELECT verified FROM master_profiles WHERE user_id = :uid"),
        {"uid": user_id}
    )
    if not master.first():
         raise HTTPException(status_code=403, detail="Only masters can report trades")

    await db.execute(
        text("""
            INSERT INTO trade_history (
                master_id, symbol, order_type, open_price, close_price, 
                profit, opened_at, closed_at
            ) VALUES (
                :uid, :symbol, :type, :open, :close, 
                :profit, :opened, :closed
            )
        """),
        {
            "uid": user_id,
            "symbol": trade.symbol,
            "type": trade.order_type,
            "open": float(trade.open_price),
            "close": float(trade.close_price),
            "profit": float(trade.profit),
            "opened": trade.opened_at,
            "closed": trade.closed_at
        }
    )
    
    # Update master stats (win rate, avg profit, etc.)
    # simplistic update: increment total signals
    await db.execute(
        text("UPDATE master_profiles SET total_signals = total_signals + 1 WHERE user_id = :uid"),
        {"uid": user_id}
    )
    
    await db.commit()
    return {"status": "recorded", "trade_id": "new"}


@router.post("/profile", response_model=MasterProfileResponse)
async def create_master_profile(
    profile_data: MasterProfileCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update a master trader profile.
    Automatically promotes user to 'master' role if not already.
    """
    # Check if profile already exists
    result = await db.execute(
        text("SELECT * FROM master_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    existing_profile = result.first()
    
    if existing_profile:
        # Update existing profile
        await db.execute(
            text("""
                UPDATE master_profiles
                SET display_name = :display_name,
                    strategy_name = :strategy_name,
                    monthly_fee = :monthly_fee,
                    bio = :bio,
                    updated_at = NOW()
                WHERE user_id = :user_id
            """),
            {
                "user_id": user_id,
                "display_name": profile_data.display_name,
                "strategy_name": profile_data.strategy_name,
                "monthly_fee": float(profile_data.monthly_fee),
                "bio": profile_data.bio
            }
        )
    else:
        # Create new profile
        await db.execute(
            text("""
                INSERT INTO master_profiles (
                    user_id, display_name, strategy_name, monthly_fee, bio, verified
                ) VALUES (
                    :user_id, :display_name, :strategy_name, :monthly_fee, :bio, TRUE
                )
            """),
            {
                "user_id": user_id,
                "display_name": profile_data.display_name,
                "strategy_name": profile_data.strategy_name,
                "monthly_fee": float(profile_data.monthly_fee),
                "bio": profile_data.bio
            }
        )
        
        # Promote user to 'master' role
        await db.execute(
            text("UPDATE users SET role = 'master' WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
    
    await db.commit()
    
    # Fetch and return the profile
    result = await db.execute(
        text("SELECT * FROM master_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    profile = result.first()
    
    return MasterProfileResponse(
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        strategy_name=profile.strategy_name,
        monthly_fee=profile.monthly_fee,
        bio=profile.bio,
        win_rate=profile.win_rate,
        total_signals=profile.total_signals,
        avg_profit=profile.avg_profit,
        verified=profile.verified,
        created_at=profile.created_at,
        performance_history=await get_performance_history(user_id, db)
    )

@router.get("/", response_model=List[MasterProfileResponse])
async def list_masters(db: AsyncSession = Depends(get_db)):
    """
    List all verified master trader profiles for the marketplace.
    """
    result = await db.execute(
        text("SELECT * FROM master_profiles WHERE verified = TRUE ORDER BY created_at DESC")
    )
    profiles = result.all()
    
    response = []
    for p in profiles:
        history = await get_performance_history(str(p.user_id), db)
        response.append(MasterProfileResponse(
            user_id=str(p.user_id),
            display_name=p.display_name,
            strategy_name=p.strategy_name,
            monthly_fee=p.monthly_fee,
            bio=p.bio,
            win_rate=p.win_rate,
            total_signals=p.total_signals,
            avg_profit=p.avg_profit,
            verified=p.verified,
            created_at=p.created_at,
            performance_history=history
        ))
    
    return response

@router.get("/{user_id}", response_model=MasterProfileResponse)
async def get_master(user_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a specific master trader's profile.
    """
    result = await db.execute(
        text("SELECT * FROM master_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    profile = result.first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master profile not found"
        )
    
    return MasterProfileResponse(
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        strategy_name=profile.strategy_name,
        monthly_fee=profile.monthly_fee,
        bio=profile.bio,
        win_rate=profile.win_rate,
        total_signals=profile.total_signals,
        avg_profit=profile.avg_profit,
        verified=profile.verified,
        created_at=profile.created_at,
        performance_history=await get_performance_history(str(profile.user_id), db)
    )

@router.get("/profile/me", response_model=MasterProfileResponse)
async def get_my_master_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's master profile.
    """
    result = await db.execute(
        text("SELECT * FROM master_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    profile = result.first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master profile not found"
        )
    
    return MasterProfileResponse(
        user_id=str(profile.user_id),
        display_name=profile.display_name,
        strategy_name=profile.strategy_name,
        monthly_fee=profile.monthly_fee,
        bio=profile.bio,
        win_rate=profile.win_rate,
        total_signals=profile.total_signals,
        avg_profit=profile.avg_profit,
        verified=profile.verified,
        created_at=profile.created_at,
        performance_history=await get_performance_history(str(profile.user_id), db)
    )

@router.get("/my/subscribers")
async def get_my_subscribers(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    List all subscribers for the current master trader.
    """
    # Verify the user is actually a master
    master_check = await db.execute(
        text("SELECT verified FROM master_profiles WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    if not master_check.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only master traders can view their subscribers"
        )

    # Fetch subscribers with their email from users table
    result = await db.execute(
        text("""
            SELECT 
                s.subscription_id,
                u.email as subscriber_email,
                s.state,
                s.is_active,
                s.created_at
            FROM subscriptions s
            JOIN users u ON s.subscriber_id = u.user_id
            WHERE s.master_id = :user_id
            ORDER BY s.created_at DESC
        """),
        {"user_id": user_id}
    )
    subscribers = result.all()
    
    return [
        {
            "subscription_id": str(s.subscription_id),
            "email": s.subscriber_email,
            "state": s.state,
            "is_active": s.is_active,
            "created_at": s.created_at
        } for s in subscribers
    ]
