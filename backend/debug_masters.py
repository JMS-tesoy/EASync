
import asyncio
import httpx

API_URL = "http://127.0.0.1:8000/api/v1"

async def debug_masters():
    async with httpx.AsyncClient() as client:
        print(f"Fetching {API_URL}/masters/ ...")
        resp = await client.get(f"{API_URL}/masters/")
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Error: {resp.text}")
        else:
            print("Success")
            data = resp.json()
            print(f"Loaded {len(data)} masters")

if __name__ == "__main__":
    asyncio.run(debug_masters())
