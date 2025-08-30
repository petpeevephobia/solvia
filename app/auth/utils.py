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
        
        # Try to verify as our custom JWT token first (created by create_access_token)
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            # Our tokens have email in 'sub' field
            email: str = payload.get("sub")
            if email:
                return email
        except JWTError:
            # If verification fails, this might be a Supabase token
            pass
        except Exception:
            pass
        
        # If custom token verification failed, try Supabase token format
        try:
            # Decode without verification for Supabase tokens
            payload = jwt.decode(token, key="", options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False
            })
            # Supabase tokens have email in the 'email' field, not 'sub'
            email: str = payload.get("email") or payload.get("sub")
            if email:
                return email
        except Exception:
            pass
        
        return None
        
    except JWTError:
        return None
    except Exception:
        return None


def verify_gsc_credentials(user_email: str) -> bool:
    """
    Verify that user has valid (non-expired) GSC credentials.
    
    Args:
        user_email: User's email address
        
    Returns:
        True if GSC credentials are valid and not expired
    """
    try:
        from app.database.supabase_db import SupabaseAuthDB
        
        db = SupabaseAuthDB()
        
        # Get GSC credentials using service role (bypasses RLS)
        response = db.service_supabase.table('gsc_connections').select('*').eq('email', user_email).execute()
        
        if not response.data:
            return False
            
        credentials = response.data[0]
        
        # Check if we have access token
        if not credentials.get('access_token'):
            return False
            
        # Check if token is expired
        expires_at_str = credentials.get('expires_at')
        if expires_at_str:
            from datetime import datetime
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            now = datetime.now(expires_at.tzinfo)
            
            if now > expires_at:
                # Token is expired - check if we have refresh token
                if not credentials.get('refresh_token'):
                    return False  # Expired and can't refresh
                    
                # TODO: Attempt token refresh here
                # For now, consider expired tokens as invalid
                return False
                
        return True
        
    except Exception as e:
        print(f"[AUTH ERROR] Failed to verify GSC credentials: {e}")
        return False


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