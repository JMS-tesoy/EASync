import asyncio
from sqlalchemy import text
from app.database import engine

async def init_master_profiles():
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS master_profiles (
                user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                display_name VARCHAR(255) NOT NULL,
                strategy_name VARCHAR(255) NOT NULL,
                monthly_fee DECIMAL(18, 2) NOT NULL DEFAULT 0.00,
                bio TEXT,
                win_rate DECIMAL(5, 2) DEFAULT 0.00,
                total_signals INTEGER DEFAULT 0,
                avg_profit DECIMAL(5, 2) DEFAULT 0.00,
                verified BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """))
    print("✅ master_profiles table created successfully")

if __name__ == "__main__":
    import os
    import sys
    # Add project root to path
    sys.path.append(os.getcwd())
    asyncio.run(init_master_profiles())
