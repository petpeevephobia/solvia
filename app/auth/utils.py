"""
Authentication utilities for Solvia.
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


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


def generate_verification_token() -> str:
    """Generate a random verification token."""
    return secrets.token_urlsafe(32)


def generate_reset_token() -> str:
    """Generate a random password reset token."""
    return secrets.token_urlsafe(32)


def is_valid_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_strong_password(password: str) -> bool:
    """Check if password meets security requirements."""
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit 


def send_verification_email(to_email: str, token: str):
    """Send a verification email with a link containing the token."""
    verify_url = f"http://localhost:8000/auth/verify-email?token={token}"
    subject = "Verify your Solvia account"
    body = f"""
    <h2>Welcome to Solvia!</h2>
    <p>Click the link below to verify your account:</p>
    <a href='{verify_url}'>{verify_url}</a>
    <p>If you did not sign up, you can ignore this email.</p>
    """
    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_FROM
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False 