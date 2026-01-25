"""
Security API Endpoints
=======================

Handles email verification, two-factor authentication, and password reset.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.api.auth import get_current_user_id, get_password_hash, create_access_token
from app.config import settings
from app.schemas import (
    EmailVerifyRequest, ResendVerificationRequest, ForgotPasswordRequest,
    ResetPasswordRequest, TwoFASetupResponse, TwoFAVerifyRequest, 
    TwoFAEnableRequest, OTPRequest, UserResponse
)
from app.services.email_service import (
    send_verification_email, send_otp_email, send_password_reset_email,
    send_security_alert_email, generate_token, generate_otp
)
from app.services.otp_service import otp_service

router = APIRouter()


# ============================================================================
# Email Verification
# ============================================================================

@router.post("/security/verify-email")
async def verify_email(
    data: EmailVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify email with token from verification email."""
    result = await db.execute(
        text("""
            SELECT user_id, email, verification_expires 
            FROM users 
            WHERE verification_token = :token
        """),
        {"token": data.token}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Check if token expired
    if user.verification_expires and user.verification_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )
    
    # Mark email as verified
    await db.execute(
        text("""
            UPDATE users 
            SET email_verified = TRUE, 
                verification_token = NULL, 
                verification_expires = NULL
            WHERE user_id = :user_id
        """),
        {"user_id": str(user.user_id)}
    )
    await db.commit()
    
    return {"message": "Email verified successfully! You can now log in."}


@router.post("/security/resend-verification")
async def resend_verification(
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resend email verification link."""
    result = await db.execute(
        text("SELECT user_id, full_name, email_verified FROM users WHERE email = :email"),
        {"email": data.email}
    )
    user = result.first()
    
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If this email is registered, a verification link has been sent."}
    
    if user.email_verified:
        return {"message": "Email is already verified."}
    
    # Generate new token
    token = generate_token()
    expires = datetime.utcnow() + timedelta(hours=24)
    
    await db.execute(
        text("""
            UPDATE users 
            SET verification_token = :token, verification_expires = :expires
            WHERE user_id = :user_id
        """),
        {"token": token, "expires": expires, "user_id": str(user.user_id)}
    )
    await db.commit()
    
    # Send email
    await send_verification_email(data.email, token, user.full_name)
    
    return {"message": "If this email is registered, a verification link has been sent."}


# ============================================================================
# Password Reset
# ============================================================================

@router.post("/security/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset email."""
    result = await db.execute(
        text("SELECT user_id, full_name FROM users WHERE email = :email"),
        {"email": data.email}
    )
    user = result.first()
    
    if user:
        # Generate reset token
        token = generate_token()
        expires = datetime.utcnow() + timedelta(hours=1)
        
        await db.execute(
            text("""
                UPDATE users 
                SET reset_token = :token, reset_expires = :expires
                WHERE user_id = :user_id
            """),
            {"token": token, "expires": expires, "user_id": str(user.user_id)}
        )
        await db.commit()
        
        # Send email
        await send_password_reset_email(data.email, token, user.full_name)
    
    # Always return same message to prevent email enumeration
    return {"message": "If this email is registered, a password reset link has been sent."}


@router.post("/security/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password with token from email."""
    result = await db.execute(
        text("""
            SELECT user_id, email, reset_expires 
            FROM users 
            WHERE reset_token = :token
        """),
        {"token": data.token}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Check if token expired
    if user.reset_expires and user.reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )
    
    # Update password
    hashed_password = get_password_hash(data.new_password)
    
    await db.execute(
        text("""
            UPDATE users 
            SET password_hash = :password_hash,
                reset_token = NULL, 
                reset_expires = NULL
            WHERE user_id = :user_id
        """),
        {"password_hash": hashed_password, "user_id": str(user.user_id)}
    )
    await db.commit()
    
    # Send security alert
    await send_security_alert_email(
        user.email,
        "Password Changed",
        f"Your password was reset at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}."
    )
    
    return {"message": "Password reset successfully! You can now log in with your new password."}


# ============================================================================
# Two-Factor Authentication
# ============================================================================

@router.get("/security/2fa/setup", response_model=TwoFASetupResponse)
async def setup_2fa(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get QR code and backup codes for 2FA setup."""
    # Get user email
    result = await db.execute(
        text("SELECT email, totp_enabled FROM users WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.totp_enabled:
        raise HTTPException(
            status_code=400, 
            detail="2FA is already enabled. Disable it first to reconfigure."
        )
    
    # Generate new secret and backup codes
    secret = otp_service.generate_totp_secret()
    totp_uri = otp_service.generate_totp_uri(secret, user.email)
    qr_code = otp_service.generate_qr_code_base64(totp_uri)
    backup_codes = otp_service.generate_backup_codes()
    
    # Store temporarily (not enabled yet - user must verify first)
    await db.execute(
        text("""
            UPDATE users 
            SET totp_secret = :secret, backup_codes = :backup_codes
            WHERE user_id = :user_id
        """),
        {"secret": secret, "backup_codes": backup_codes, "user_id": user_id}
    )
    await db.commit()
    
    return TwoFASetupResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes
    )


@router.post("/security/2fa/enable")
async def enable_2fa(
    data: TwoFAEnableRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Enable 2FA after verifying the setup code."""
    result = await db.execute(
        text("SELECT email, totp_secret, totp_enabled FROM users WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    
    if data.method == "totp":
        # Verify TOTP code
        if not user.totp_secret:
            raise HTTPException(status_code=400, detail="Please run 2FA setup first")
        
        if not otp_service.verify_totp(user.totp_secret, data.code):
            raise HTTPException(status_code=400, detail="Invalid verification code")
    
    elif data.method == "email":
        # For email OTP, verify against stored OTP
        result = await db.execute(
            text("SELECT email_otp, email_otp_expires FROM users WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        otp_data = result.first()
        
        if not otp_data or otp_data.email_otp != data.code:
            raise HTTPException(status_code=400, detail="Invalid verification code")
        
        if otp_data.email_otp_expires and otp_data.email_otp_expires < datetime.utcnow():
            raise HTTPException(status_code=400, detail="OTP has expired")
    
    # Enable 2FA
    await db.execute(
        text("""
            UPDATE users 
            SET totp_enabled = TRUE, two_fa_method = :method,
                email_otp = NULL, email_otp_expires = NULL
            WHERE user_id = :user_id
        """),
        {"method": data.method, "user_id": user_id}
    )
    await db.commit()
    
    # Send security alert
    await send_security_alert_email(
        user.email,
        "Two-Factor Authentication Enabled",
        f"2FA has been enabled on your account using {data.method.upper()} method."
    )
    
    return {"message": "Two-factor authentication enabled successfully!"}


@router.post("/security/2fa/disable")
async def disable_2fa(
    data: TwoFAVerifyRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Disable 2FA (requires current 2FA code)."""
    result = await db.execute(
        text("SELECT email, totp_secret, totp_enabled, two_fa_method, backup_codes FROM users WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    user = result.first()
    
    if not user or not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    
    # Verify code
    valid = False
    if data.method == "totp" and user.totp_secret:
        valid = otp_service.verify_totp(user.totp_secret, data.code)
    elif data.method == "backup" and user.backup_codes:
        valid, _ = otp_service.verify_backup_code(user.backup_codes, data.code)
    
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Disable 2FA
    await db.execute(
        text("""
            UPDATE users 
            SET totp_enabled = FALSE, totp_secret = NULL, 
                backup_codes = NULL, two_fa_method = NULL
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    await db.commit()
    
    # Send security alert
    await send_security_alert_email(
        user.email,
        "Two-Factor Authentication Disabled",
        "2FA has been disabled on your account. If this wasn't you, please secure your account immediately."
    )
    
    return {"message": "Two-factor authentication disabled."}


@router.post("/security/2fa/send-otp")
async def send_email_otp(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Send OTP code via email for 2FA."""
    result = await db.execute(
        text("SELECT email, full_name FROM users WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate OTP
    otp = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=10)
    
    # Store OTP
    await db.execute(
        text("""
            UPDATE users 
            SET email_otp = :otp, email_otp_expires = :expires
            WHERE user_id = :user_id
        """),
        {"otp": otp, "expires": expires, "user_id": user_id}
    )
    await db.commit()
    
    # Send email
    await send_otp_email(user.email, otp, user.full_name)
    
    return {"message": "OTP sent to your email"}


@router.post("/security/2fa/verify")
async def verify_2fa_login(
    data: TwoFAVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify 2FA code during login.
    This is called after initial login returns requires_2fa=True.
    Requires temp_user_id from session/cookie.
    """
    # This would typically get user_id from a temporary session
    # For now, we'll require it in the request
    temp_user_id = request.headers.get("X-Temp-User-Id")
    
    if not temp_user_id:
        raise HTTPException(status_code=400, detail="Missing temporary user session")
    
    result = await db.execute(
        text("""
            SELECT user_id, email, totp_secret, two_fa_method, backup_codes, 
                   email_otp, email_otp_expires
            FROM users WHERE user_id = :user_id
        """),
        {"user_id": temp_user_id}
    )
    user = result.first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    valid = False
    
    if data.method == "totp" and user.totp_secret:
        valid = otp_service.verify_totp(user.totp_secret, data.code)
    
    elif data.method == "email":
        if user.email_otp == data.code:
            if user.email_otp_expires and user.email_otp_expires > datetime.utcnow():
                valid = True
    
    elif data.method == "backup" and user.backup_codes:
        valid, updated_codes = otp_service.verify_backup_code(user.backup_codes, data.code)
        if valid:
            # Update remaining backup codes
            await db.execute(
                text("UPDATE users SET backup_codes = :codes WHERE user_id = :user_id"),
                {"codes": updated_codes, "user_id": temp_user_id}
            )
    
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Clear OTP
    await db.execute(
        text("UPDATE users SET email_otp = NULL, email_otp_expires = NULL WHERE user_id = :user_id"),
        {"user_id": temp_user_id}
    )
    await db.commit()
    
    # Generate full access token
    access_token = create_access_token(
        data={"sub": temp_user_id},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "message": "2FA verification successful"
    }
