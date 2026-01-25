
import asyncio
import httpx
from datetime import datetime, timedelta
from jose import jwt
import random

# Configuration
API_URL = "http://127.0.0.1:8000/api/v1"
USER_ID = "0f1907ed-bd9b-4d6f-ae09-a9275e8f8ad8"
SECRET_KEY = "your-secret-key-change-this-in-production-min-32-chars-long"
ALGORITHM = "HS256"

def create_test_token(user_id):
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"sub": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def seed_data():
    token = create_test_token(USER_ID)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Generate 10 trades with varying profit
    profits = [10.5, 20.1, -5.0, 15.2, 30.5, -10.2, 5.5, 40.0, 25.5, 50.0]
    
    print(f"Seeding {len(profits)} trades for User {USER_ID}...")
    
    async with httpx.AsyncClient() as client:
        for i, profit in enumerate(profits):
            trade_data = {
                "symbol": "EURUSD",
                "order_type": 1, 
                "open_price": 1.1000,
                "close_price": 1.1050,
                "profit": profit,
                "opened_at": (datetime.now() - timedelta(days=10-i)).isoformat(),
                "closed_at": (datetime.now() - timedelta(days=10-i)).isoformat()
            }
            
            resp = await client.post(
                f"{API_URL}/masters/report-trade",
                json=trade_data,
                headers=headers
            )
            print(f"Trade {i+1}: Profit {profit} -> Status {resp.status_code}")

    print("\nSeeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_data())
