"""
Configuration settings for Solvia authentication system.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "Solvia Authentication"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "credentials.json"
    USERS_SHEET_ID: str = ""
    SESSIONS_SHEET_ID: str = ""
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    # PageSpeed Insights API
    PAGESPEED_API_KEY: str = os.getenv("PAGESPEED_API_KEY", "")
    
    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # JWT Settings
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Email Settings - Using Zoho SMTP
    EMAIL_ENABLED: bool = True  # Enable email functionality
    EMAIL_HOST: str = "smtp.zoho.com"  # Zoho SMTP server
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = "info@solvia.app"  # From .env SENDER_EMAIL
    EMAIL_PASSWORD: str = "BCbSE5cUDGnH"  # From .env APP_PASSWORD  
    EMAIL_FROM: str = "info@solvia.app"  # From .env SENDER_EMAIL
    EMAIL_USE_TLS: bool = True
    
    # Frontend URL for links in emails
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")
    
    # Security
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    RESET_TOKEN_EXPIRE_HOURS: int = 1
    
    # Rate Limiting
    LOGIN_ATTEMPTS_LIMIT: int = 5
    LOGIN_ATTEMPTS_WINDOW_MINUTES: int = 15
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }


# Create settings instance
settings = Settings() 