"""
OTP Service for Two-Factor Authentication
==========================================

Handles both TOTP (Time-based OTP via authenticator apps) and 
email-based OTP for flexible 2FA options.
"""

import pyotp
import secrets
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64
from typing import Tuple, List, Optional
from datetime import datetime, timedelta


class OTPService:
    """
    Service for managing OTP/TOTP authentication.
    """
    
    @staticmethod
    def generate_totp_secret() -> str:
        """
        Generate a new TOTP secret for authenticator app setup.
        Returns a base32-encoded secret.
        """
        return pyotp.random_base32()
    
    @staticmethod
    def generate_totp_uri(secret: str, email: str, issuer: str = "EA Sync") -> str:
        """
        Generate the otpauth:// URI for QR code generation.
        This URI is used by authenticator apps like Google Authenticator.
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    @staticmethod
    def generate_qr_code_base64(totp_uri: str) -> str:
        """
        Generate a QR code image as base64-encoded PNG.
        Returns a data URI suitable for <img src="...">
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
        """
        Verify a TOTP code against the secret.
        
        Args:
            secret: The user's TOTP secret
            code: The 6-digit code from the authenticator app
            valid_window: Number of 30-second windows to check (default 1 = +/- 30 seconds)
        
        Returns:
            True if the code is valid, False otherwise
        """
        if not secret or not code:
            return False
            
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=valid_window)
        except Exception as e:
            print(f"[OTP Service] TOTP verification error: {e}")
            return False
    
    @staticmethod
    def generate_backup_codes(count: int = 8) -> List[str]:
        """
        Generate single-use backup codes for account recovery.
        Each code is 8 characters long.
        """
        codes = []
        for _ in range(count):
            # Generate format: XXXX-XXXX
            part1 = secrets.token_hex(2).upper()
            part2 = secrets.token_hex(2).upper()
            codes.append(f"{part1}-{part2}")
        return codes
    
    @staticmethod
    def generate_email_otp(length: int = 6) -> str:
        """
        Generate a numeric OTP code for email-based 2FA.
        """
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    @staticmethod
    def get_otp_expiry(minutes: int = 10) -> datetime:
        """
        Get the expiry timestamp for an email OTP.
        """
        return datetime.utcnow() + timedelta(minutes=minutes)
    
    @staticmethod
    def is_otp_expired(expiry: datetime) -> bool:
        """
        Check if an OTP has expired.
        """
        return datetime.utcnow() > expiry
    
    @staticmethod
    def verify_backup_code(stored_codes: List[str], provided_code: str) -> Tuple[bool, List[str]]:
        """
        Verify a backup code and return updated list with the used code removed.
        
        Args:
            stored_codes: List of remaining backup codes
            provided_code: The code provided by the user
        
        Returns:
            Tuple of (is_valid, updated_codes_list)
        """
        # Normalize the code (remove dashes, uppercase)
        normalized = provided_code.replace("-", "").upper()
        
        for i, code in enumerate(stored_codes):
            stored_normalized = code.replace("-", "").upper()
            if normalized == stored_normalized:
                # Remove the used code
                updated = stored_codes[:i] + stored_codes[i+1:]
                return True, updated
        
        return False, stored_codes


# Singleton instance for convenience
otp_service = OTPService()
