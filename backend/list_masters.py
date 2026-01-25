
import asyncio
from sqlalchemy import text
from app.database import engine

async def list_masters():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT user_id, display_name FROM master_profiles"))
        masters = result.fetchall()
        print("\n=== Master Profiles ===")
        for m in masters:
            print(f"ID: {m.user_id}, Name: {m.display_name}")
        print("=======================\n")

if __name__ == "__main__":
    asyncio.run(list_masters())
