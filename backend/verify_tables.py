
import asyncio
from sqlalchemy import text
from app.database import engine

async def list_tables():
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = result.fetchall()
        print("\n=== Current Tables in Database ===")
        for table in tables:
            print(f"- {table[0]}")
        print("==================================\n")

if __name__ == "__main__":
    asyncio.run(list_tables())
