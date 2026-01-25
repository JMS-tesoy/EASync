"""
Direct Email Test Script
Run this to test if email sending works
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.config import settings
from app.services.email_service import send_password_reset_email, get_resend_client, get_sender

async def test_email():
    print("=" * 60)
    print("EMAIL SERVICE TEST")
    print("=" * 60)
    
    # Check config
    print(f"\n1. Checking config...")
    print(f"   RESEND_API_KEY: {settings.resend_api_key[:15]}..." if settings.resend_api_key else "   RESEND_API_KEY: NOT SET!")
    print(f"   EMAIL_FROM: {settings.email_from}")
    print(f"   FRONTEND_URL: {settings.frontend_url}")
    
    # Check client
    print(f"\n2. Testing get_resend_client()...")
    client = get_resend_client()
    if client:
        print("   ✓ Client created successfully")
    else:
        print("   ✗ Client is None - API key issue!")
        return
    
    # Test sender
    print(f"\n3. Testing get_sender()...")
    sender = get_sender()
    print(f"   Sender: {sender}")
    
    # Try to send email
    print(f"\n4. Attempting to send test email...")
    test_email = "testuser@example.com"
    test_token = "test-token-12345"
    
    result = await send_password_reset_email(test_email, test_token, "Test User")
    
    if result:
        print(f"   ✓ Email function returned True - check Resend dashboard!")
    else:
        print(f"   ✗ Email function returned False - check error above")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_email())
