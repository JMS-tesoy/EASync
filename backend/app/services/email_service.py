"""
Email Service using Resend
==========================

Handles all email sending functionality including:
- Email verification
- Password reset
- OTP codes
- Security notifications
"""

import resend
import secrets
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings


# Configure Resend with API key from settings
# You'll need to set RESEND_API_KEY in your .env file
resend.api_key = getattr(settings, 'resend_api_key', None) or "re_placeholder_key"

# Default sender email (must be verified in Resend dashboard)
DEFAULT_SENDER = getattr(settings, 'email_from', 'noreply@easync.com')


def generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP code."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


async def send_verification_email(
    to_email: str,
    verification_token: str,
    user_name: Optional[str] = None
) -> bool:
    """
    Send email verification link to new user.
    """
    verification_url = f"{settings.frontend_url}/verify-email?token={verification_token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f23; color: #fff; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(102, 126, 234, 0.2); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .content {{ font-size: 16px; line-height: 1.6; color: rgba(255,255,255,0.8); }}
            .btn {{ display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; color: rgba(255,255,255,0.5); text-align: center; }}
            .code {{ background: rgba(102, 126, 234, 0.2); padding: 12px 20px; border-radius: 8px; font-family: monospace; font-size: 18px; letter-spacing: 2px; display: inline-block; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">EA Sync</div>
                <p style="color: rgba(255,255,255,0.6);">Trading Signal Platform</p>
            </div>
            <div class="content">
                <p>Hi{f' {user_name}' if user_name else ''},</p>
                <p>Welcome to EA Sync! Please verify your email address to activate your account and start trading.</p>
                <p style="text-align: center;">
                    <a href="{verification_url}" class="btn">Verify Email Address</a>
                </p>
                <p>Or copy and paste this link in your browser:</p>
                <p style="word-break: break-all; color: #667eea; font-size: 14px;">{verification_url}</p>
                <p style="color: rgba(255,255,255,0.5); font-size: 14px;">This link expires in 24 hours.</p>
            </div>
            <div class="footer">
                <p>If you didn't create an account, you can safely ignore this email.</p>
                <p>© 2026 EA Sync. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": DEFAULT_SENDER,
            "to": [to_email],
            "subject": "Verify your EA Sync account",
            "html": html_content
        }
        
        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[Email Service] Failed to send verification email: {e}")
        return False


async def send_otp_email(
    to_email: str,
    otp_code: str,
    user_name: Optional[str] = None
) -> bool:
    """
    Send OTP code for 2FA verification.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f23; color: #fff; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(102, 126, 234, 0.2); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .content {{ font-size: 16px; line-height: 1.6; color: rgba(255,255,255,0.8); text-align: center; }}
            .otp-code {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px 40px; border-radius: 12px; font-family: monospace; font-size: 32px; letter-spacing: 8px; display: inline-block; margin: 20px 0; font-weight: 700; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; color: rgba(255,255,255,0.5); text-align: center; }}
            .warning {{ background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 12px; margin-top: 20px; color: #fca5a5; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">EA Sync</div>
                <p style="color: rgba(255,255,255,0.6);">Two-Factor Authentication</p>
            </div>
            <div class="content">
                <p>Hi{f' {user_name}' if user_name else ''},</p>
                <p>Your verification code is:</p>
                <div class="otp-code">{otp_code}</div>
                <p style="color: rgba(255,255,255,0.5);">This code expires in 10 minutes.</p>
                <div class="warning">
                    ⚠️ Never share this code with anyone. EA Sync staff will never ask for your code.
                </div>
            </div>
            <div class="footer">
                <p>If you didn't request this code, please secure your account immediately.</p>
                <p>© 2026 EA Sync. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": DEFAULT_SENDER,
            "to": [to_email],
            "subject": f"Your EA Sync verification code: {otp_code}",
            "html": html_content
        }
        
        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[Email Service] Failed to send OTP email: {e}")
        return False


async def send_password_reset_email(
    to_email: str,
    reset_token: str,
    user_name: Optional[str] = None
) -> bool:
    """
    Send password reset link.
    """
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f23; color: #fff; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(102, 126, 234, 0.2); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .content {{ font-size: 16px; line-height: 1.6; color: rgba(255,255,255,0.8); }}
            .btn {{ display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; color: rgba(255,255,255,0.5); text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">EA Sync</div>
                <p style="color: rgba(255,255,255,0.6);">Password Reset</p>
            </div>
            <div class="content">
                <p>Hi{f' {user_name}' if user_name else ''},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p style="text-align: center;">
                    <a href="{reset_url}" class="btn">Reset Password</a>
                </p>
                <p>Or copy and paste this link in your browser:</p>
                <p style="word-break: break-all; color: #f59e0b; font-size: 14px;">{reset_url}</p>
                <p style="color: rgba(255,255,255,0.5); font-size: 14px;">This link expires in 1 hour.</p>
            </div>
            <div class="footer">
                <p>If you didn't request a password reset, you can safely ignore this email.</p>
                <p>© 2026 EA Sync. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": DEFAULT_SENDER,
            "to": [to_email],
            "subject": "Reset your EA Sync password",
            "html": html_content
        }
        
        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[Email Service] Failed to send password reset email: {e}")
        return False


async def send_security_alert_email(
    to_email: str,
    alert_type: str,
    details: str,
    user_name: Optional[str] = None
) -> bool:
    """
    Send security alert notification.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f23; color: #fff; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(239, 68, 68, 0.3); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ font-size: 28px; font-weight: 700; color: #ef4444; }}
            .content {{ font-size: 16px; line-height: 1.6; color: rgba(255,255,255,0.8); }}
            .alert-box {{ background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; padding: 16px; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 12px; color: rgba(255,255,255,0.5); text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo">⚠️ Security Alert</div>
            </div>
            <div class="content">
                <p>Hi{f' {user_name}' if user_name else ''},</p>
                <p>We detected {alert_type} on your EA Sync account:</p>
                <div class="alert-box">
                    <p style="margin: 0; color: #fca5a5;">{details}</p>
                </div>
                <p>If this was you, no action is needed. If you don't recognize this activity, please secure your account immediately.</p>
            </div>
            <div class="footer">
                <p>© 2026 EA Sync. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": DEFAULT_SENDER,
            "to": [to_email],
            "subject": f"Security Alert: {alert_type}",
            "html": html_content
        }
        
        email = resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[Email Service] Failed to send security alert: {e}")
        return False
