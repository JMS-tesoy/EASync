
import asyncio
import logging
from sqlalchemy import text
from app.database import engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_trade_history_table():
    async with engine.begin() as conn:
        logger.info("Creating trade_history table...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trade_history (
                trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                master_id UUID REFERENCES users(user_id),
                symbol VARCHAR(20),
                order_type INT, -- 1=BUY, 2=SELL
                open_price DECIMAL,
                close_price DECIMAL,
                profit DECIMAL,
                opened_at TIMESTAMP DEFAULT NOW(),
                closed_at TIMESTAMP DEFAULT NOW()
            );
        """))
        logger.info("Table trade_history created successfully.")

if __name__ == "__main__":
    asyncio.run(create_trade_history_table())
