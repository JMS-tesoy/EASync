from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Optional
from decimal import Decimal

from app.database import get_db
from app.api.auth import get_current_user_id

router = APIRouter()


@router.get("/overview")
async def get_overview_metrics(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overview metrics for master trader analytics.
    Returns: total/active subscribers, revenue, win rate, profit, total trades
    """
    # Verify user is a master
    master_check = await db.execute(
        text("SELECT monthly_fee FROM master_profiles WHERE user_id = :uid"),
        {"uid": user_id}
    )
    master = master_check.first()
    if not master:
        raise HTTPException(status_code=403, detail="Only masters can access analytics")
    
    # Get subscriber counts
    sub_result = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_subscribers,
                COUNT(*) FILTER (WHERE is_active = TRUE) as active_subscribers
            FROM subscriptions 
            WHERE master_id = :uid
        """),
        {"uid": user_id}
    )
    sub_data = sub_result.first()
    
    # Calculate monthly revenue
    monthly_revenue = float(master.monthly_fee) * (sub_data.active_subscribers or 0)
    
    # Get trade statistics
    trade_result = await db.execute(
        text("""
            SELECT 
                COUNT(*) as total_trades,
                COUNT(*) FILTER (WHERE profit > 0) as winning_trades,
                SUM(profit) as total_profit
            FROM trade_history 
            WHERE master_id = :uid
        """),
        {"uid": user_id}
    )
    trade_data = trade_result.first()
    
    total_trades = trade_data.total_trades or 0
    winning_trades = trade_data.winning_trades or 0
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        "total_subscribers": sub_data.total_subscribers or 0,
        "active_subscribers": sub_data.active_subscribers or 0,
        "monthly_revenue": round(monthly_revenue, 2),
        "win_rate": round(win_rate, 1),
        "total_profit": float(trade_data.total_profit or 0),
        "total_trades": total_trades
    }


@router.get("/subscriber-growth")
async def get_subscriber_growth(
    months: int = Query(default=6, ge=1, le=12),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscriber growth over time.
    Returns monthly subscriber counts for the specified time range.
    """
    # Verify user is a master
    master_check = await db.execute(
        text("SELECT 1 FROM master_profiles WHERE user_id = :uid"),
        {"uid": user_id}
    )
    if not master_check.first():
        raise HTTPException(status_code=403, detail="Only masters can access analytics")
    
    # Get subscriber growth data
    result = await db.execute(
        text(f"""
            WITH months_series AS (
                SELECT generate_series(
                    date_trunc('month', NOW() - INTERVAL '{months} months'),
                    date_trunc('month', NOW()),
                    '1 month'::interval
                ) AS month
            )
            SELECT 
                TO_CHAR(m.month, 'Mon') as label,
                COUNT(s.subscription_id) as count
            FROM months_series m
            LEFT JOIN subscriptions s ON 
                date_trunc('month', s.created_at) <= m.month 
                AND s.master_id = :uid
            GROUP BY m.month
            ORDER BY m.month
        """),
        {"uid": user_id}
    )
    
    rows = result.all()
    return {
        "labels": [row.label for row in rows],
        "data": [row.count for row in rows]
    }


@router.get("/revenue-trend")
async def get_revenue_trend(
    months: int = Query(default=6, ge=1, le=12),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get revenue trend over time.
    Returns monthly revenue for the specified time range.
    """
    # Verify user is a master and get monthly fee
    master_result = await db.execute(
        text("SELECT monthly_fee FROM master_profiles WHERE user_id = :uid"),
        {"uid": user_id}
    )
    master = master_result.first()
    if not master:
        raise HTTPException(status_code=403, detail="Only masters can access analytics")
    
    monthly_fee = float(master.monthly_fee)
    
    # Get active subscribers per month
    result = await db.execute(
        text(f"""
            WITH months_series AS (
                SELECT generate_series(
                    date_trunc('month', NOW() - INTERVAL '{months} months'),
                    date_trunc('month', NOW()),
                    '1 month'::interval
                ) AS month
            )
            SELECT 
                TO_CHAR(m.month, 'Mon') as label,
                COUNT(s.subscription_id) as subscriber_count
            FROM months_series m
            LEFT JOIN subscriptions s ON 
                date_trunc('month', s.created_at) <= m.month 
                AND s.master_id = :uid
                AND s.is_active = TRUE
            GROUP BY m.month
            ORDER BY m.month
        """),
        {"uid": user_id}
    )
    
    rows = result.all()
    return {
        "labels": [row.label for row in rows],
        "data": [round(row.subscriber_count * monthly_fee, 2) for row in rows]
    }


@router.get("/performance")
async def get_performance_data(
    months: int = Query(default=6, ge=1, le=12),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trading performance data including profit timeline, win rate trend, and trade distribution.
    """
    # Verify user is a master
    master_check = await db.execute(
        text("SELECT 1 FROM master_profiles WHERE user_id = :uid"),
        {"uid": user_id}
    )
    if not master_check.first():
        raise HTTPException(status_code=403, detail="Only masters can access analytics")
    
    # Get profit timeline (cumulative)
    profit_result = await db.execute(
        text(f"""
            WITH months_series AS (
                SELECT generate_series(
                    date_trunc('month', NOW() - INTERVAL '{months} months'),
                    date_trunc('month', NOW()),
                    '1 month'::interval
                ) AS month
            )
            SELECT 
                TO_CHAR(m.month, 'Mon') as label,
                COALESCE(SUM(t.profit), 0) as monthly_profit
            FROM months_series m
            LEFT JOIN trade_history t ON 
                date_trunc('month', t.closed_at) = m.month 
                AND t.master_id = :uid
            GROUP BY m.month
            ORDER BY m.month
        """),
        {"uid": user_id}
    )
    
    profit_rows = profit_result.all()
    cumulative_profit = 0
    profit_timeline = []
    labels = []
    
    for row in profit_rows:
        cumulative_profit += float(row.monthly_profit)
        profit_timeline.append(round(cumulative_profit, 2))
        labels.append(row.label)
    
    # Get win rate trend
    winrate_result = await db.execute(
        text(f"""
            WITH months_series AS (
                SELECT generate_series(
                    date_trunc('month', NOW() - INTERVAL '{months} months'),
                    date_trunc('month', NOW()),
                    '1 month'::interval
                ) AS month
            )
            SELECT 
                COUNT(*) FILTER (WHERE t.profit > 0)::float / NULLIF(COUNT(t.trade_id), 0) * 100 as win_rate
            FROM months_series m
            LEFT JOIN trade_history t ON 
                date_trunc('month', t.closed_at) = m.month 
                AND t.master_id = :uid
            GROUP BY m.month
            ORDER BY m.month
        """),
        {"uid": user_id}
    )
    
    win_rate_trend = [round(row.win_rate or 0, 1) for row in winrate_result.all()]
    
    # Get trade distribution (overall)
    distribution_result = await db.execute(
        text("""
            SELECT 
                COUNT(*) FILTER (WHERE profit > 0) as wins,
                COUNT(*) FILTER (WHERE profit <= 0) as losses
            FROM trade_history 
            WHERE master_id = :uid
        """),
        {"uid": user_id}
    )
    
    dist = distribution_result.first()
    
    return {
        "profit_timeline": {
            "labels": labels,
            "data": profit_timeline
        },
        "win_rate_trend": {
            "labels": labels,
            "data": win_rate_trend
        },
        "trade_distribution": {
            "wins": dist.wins or 0,
            "losses": dist.losses or 0
        }
    }


@router.get("/recent-trades")
async def get_recent_trades(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent trades for the master trader.
    """
    # Verify user is a master
    master_check = await db.execute(
        text("SELECT 1 FROM master_profiles WHERE user_id = :uid"),
        {"uid": user_id}
    )
    if not master_check.first():
        raise HTTPException(status_code=403, detail="Only masters can access analytics")
    
    result = await db.execute(
        text("""
            SELECT 
                trade_id,
                symbol,
                order_type,
                open_price,
                close_price,
                profit,
                opened_at,
                closed_at
            FROM trade_history 
            WHERE master_id = :uid
            ORDER BY closed_at DESC
            LIMIT :limit
        """),
        {"uid": user_id, "limit": limit}
    )
    
    trades = result.all()
    return [
        {
            "trade_id": str(t.trade_id),
            "symbol": t.symbol,
            "type": "BUY" if t.order_type == 1 else "SELL",
            "open_price": float(t.open_price),
            "close_price": float(t.close_price),
            "profit": float(t.profit),
            "opened_at": t.opened_at.isoformat(),
            "closed_at": t.closed_at.isoformat()
        }
        for t in trades
    ]
