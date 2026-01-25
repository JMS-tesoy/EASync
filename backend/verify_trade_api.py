
import asyncio
import httpx
from datetime import datetime, timedelta
from jose import jwt

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

async def test_report_trade():
    token = create_test_token(USER_ID)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Report a trade
    trade_data = {
        "symbol": "EURUSD",
        "order_type": 1, # BUY
        "open_price": 1.1000,
        "close_price": 1.1050,
        "profit": 50.00, # $50 profit
        "opened_at": datetime.now().isoformat(),
        "closed_at": datetime.now().isoformat()
    }
    
    print(f"Reporting trade for User {USER_ID}...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}/masters/report-trade",
            json=trade_data,
            headers=headers
        )
        print(f"Report Status: {resp.status_code}")
        print(f"Response: {resp.json()}")

        if resp.status_code != 200:
            print("Failed to report trade.")
            return

        # 2. Check profile for history
        print("\nChecking master profile...")
        resp = await client.get(f"{API_URL}/masters/{USER_ID}")
        data = resp.json()
        print(f"Performance History: {data.get('performance_history')}")
        
        if data.get('performance_history'):
            print("✅ Verification SUCCESS: History updated.")
        else:
            print("❌ Verification FAILED: History empty.")

if __name__ == "__main__":
    asyncio.run(test_report_trade())
