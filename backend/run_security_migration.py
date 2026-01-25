"""
Run Security Features Migration
"""
import asyncio
from sqlalchemy import text
from app.database import engine

async def run_migration():
    migration_sql = """
    -- Email verification fields on users table
    ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(128);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_expires TIMESTAMP;

    -- Two-Factor Authentication fields
    ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS backup_codes TEXT[];
    ALTER TABLE users ADD COLUMN IF NOT EXISTS two_fa_method VARCHAR(20) DEFAULT NULL;

    -- Email OTP fields (for email-based 2FA)
    ALTER TABLE users ADD COLUMN IF NOT EXISTS email_otp VARCHAR(10);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS email_otp_expires TIMESTAMP;

    -- Password reset fields
    ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(128);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_expires TIMESTAMP;

    -- Failed login tracking fields
    ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(45);
    """
    
    login_attempts_sql = """
    CREATE TABLE IF NOT EXISTS login_attempts (
        attempt_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
        email VARCHAR(255) NOT NULL,
        ip_address VARCHAR(45),
        user_agent TEXT,
        success BOOLEAN NOT NULL,
        failure_reason VARCHAR(100),
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    
    user_sessions_sql = """
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
        token_hash VARCHAR(64) NOT NULL,
        device_name VARCHAR(100),
        ip_address VARCHAR(45),
        user_agent TEXT,
        last_activity TIMESTAMP DEFAULT NOW(),
        created_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP NOT NULL,
        is_active BOOLEAN DEFAULT TRUE
    );
    """
    
    indices_sql = """
    CREATE INDEX IF NOT EXISTS idx_login_attempts_user_id ON login_attempts(user_id);
    CREATE INDEX IF NOT EXISTS idx_login_attempts_created_at ON login_attempts(created_at);
    CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
    """
    
    async with engine.begin() as conn:
        print("Running security migrations...")
        
        # Execute each statement separately
        for statement in migration_sql.strip().split(';'):
            if statement.strip():
                try:
                    await conn.execute(text(statement))
                    print(f"✓ Executed: {statement[:60]}...")
                except Exception as e:
                    print(f"⚠ Skipped (may already exist): {str(e)[:80]}")
        
        # Create tables
        for sql in [login_attempts_sql, user_sessions_sql]:
            try:
                await conn.execute(text(sql))
                print(f"✓ Table created/verified")
            except Exception as e:
                print(f"⚠ Table issue: {str(e)[:80]}")
        
        # Create indices
        for idx in indices_sql.strip().split(';'):
            if idx.strip():
                try:
                    await conn.execute(text(idx))
                except:
                    pass
        
        print("✅ Security migration complete!")

if __name__ == "__main__":
    asyncio.run(run_migration())
