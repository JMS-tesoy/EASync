"""
Configuration Management
========================

Loads configuration from environment variables using Pydantic Settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # JWT Authentication
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS - will be parsed as comma-separated string
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # Environment
    environment: str = "development"
    
    # Logging
    log_level: str = "INFO"
    
    # Email (Resend)
    resend_api_key: str = ""
    email_from: str = "EA Sync <noreply@easync.com>"
    
    # Frontend URL for email links
    frontend_url: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
