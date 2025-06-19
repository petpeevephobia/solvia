"""
User models and schemas for Solvia authentication system.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr


class UserCreate(UserBase):
    """Model for user registration."""
    password: str


class UserLogin(BaseModel):
    """Model for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Model for user response (without sensitive data)."""
    created_at: datetime
    last_login: Optional[datetime] = None
    is_verified: bool = False


class UserInDB(UserResponse):
    """Model for user in database (includes hashed password)."""
    password_hash: str
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None


class Token(BaseModel):
    """Model for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Model for token payload data."""
    email: Optional[str] = None


class PasswordReset(BaseModel):
    """Model for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Model for password reset confirmation."""
    token: str
    new_password: str


class EmailVerification(BaseModel):
    """Model for email verification."""
    token: str 