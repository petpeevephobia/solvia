"""
User models and schemas for Solvia Google OAuth authentication.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """Model for user response from Google OAuth."""
    id: str
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    created_at: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    """Model for Google OAuth authorization request."""
    state: Optional[str] = None


class GoogleCallbackRequest(BaseModel):
    """Model for Google OAuth callback."""
    code: str


class TokenResponse(BaseModel):
    """Model for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: float


class TokenData(BaseModel):
    """Model for token payload data."""
    email: Optional[str] = None 