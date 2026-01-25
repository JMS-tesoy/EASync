
import asyncio
from sqlalchemy import text
from app.database import engine

async def check_table():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trade_history');"))
        exists = result.scalar()
        print(f"Table 'trade_history' exists: {exists}")

if __name__ == "__main__":
    asyncio.run(check_table())
