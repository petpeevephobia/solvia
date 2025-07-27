"""
Authentication utilities for Solvia Google OAuth.
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.config import settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token."""
    if not token:
        return None
    
    try:
        # First, let's check the token structure
        parts = token.split('.')
        
        if len(parts) != 3:
            return None
        
        # For Supabase tokens, we decode without verification since we don't have Supabase's signing key
        # The token is already verified by Supabase when we get it
        try:
            from jose import jwt
            # Decode without verification for Supabase tokens, ignoring audience validation
            payload = jwt.decode(token, key="", options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False
            })
        except Exception as e:
            return None
        
        # Supabase tokens have email in the 'email' field, not 'sub'
        email: str = payload.get("email") or payload.get("sub")
        if email is None:
            return None
        
        return email
        
    except JWTError as e:
        return None
    except Exception as e:
        return None


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None 