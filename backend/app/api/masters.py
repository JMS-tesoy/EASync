from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List
from datetime import datetime

from app.database import get_db
from app.schemas import MasterProfileCreate, MasterProfileResponse
from app.api.auth import get_current_user_id

router = APIRouter()

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
        created_at=profile.created_at
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
    
    return [
        MasterProfileResponse(
            user_id=str(p.user_id),
            display_name=p.display_name,
            strategy_name=p.strategy_name,
            monthly_fee=p.monthly_fee,
            bio=p.bio,
            win_rate=p.win_rate,
            total_signals=p.total_signals,
            avg_profit=p.avg_profit,
            verified=p.verified,
            created_at=p.created_at
        ) for p in profiles
    ]

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
        created_at=profile.created_at
    )
