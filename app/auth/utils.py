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
    print(f"[GSC VERIFY] 🔍 Starting credential verification for {user_email}")

    try:
        from app.database.supabase_db import SupabaseAuthDB

        db = SupabaseAuthDB()

        # Get GSC credentials using service role (bypasses RLS)
        print(f"[GSC VERIFY] 📡 Querying database for credentials...")
        response = db.service_supabase.table('gsc_connections').select('*').eq('email', user_email).execute()

        if not response.data:
            print(f"[GSC VERIFY] ❌ No credentials found in database for {user_email}")
            return False

        credentials = response.data[0]
        print(f"[GSC VERIFY] ✅ Found credentials in database")
        print(f"[GSC VERIFY] 📊 Credential details:")
        print(f"[GSC VERIFY]   - Has access_token: {'Yes' if credentials.get('access_token') else 'No'}")
        print(f"[GSC VERIFY]   - Has refresh_token: {'Yes' if credentials.get('refresh_token') else 'No'}")
        print(f"[GSC VERIFY]   - Expires at: {credentials.get('expires_at')}")
        print(f"[GSC VERIFY]   - Last updated: {credentials.get('updated_at')}")

        # Check if we have access token
        if not credentials.get('access_token'):
            print(f"[GSC VERIFY] ❌ No access token found for {user_email}")
            return False

        # Check if token is expired
        expires_at_str = credentials.get('expires_at')
        if expires_at_str:
            from datetime import datetime
            print(f"[GSC VERIFY] ⏰ Checking token expiry...")

            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            now = datetime.now(expires_at.tzinfo)

            print(f"[GSC VERIFY]   - Token expires at: {expires_at}")
            print(f"[GSC VERIFY]   - Current time: {now}")
            print(f"[GSC VERIFY]   - Time difference: {(now - expires_at).total_seconds()} seconds")

            if now > expires_at:
                print(f"[GSC VERIFY] ⚠️ Token is EXPIRED! Starting refresh process...")

                # Token is expired - check if we have refresh token
                refresh_token = credentials.get('refresh_token')
                if not refresh_token or refresh_token == '':
                    print(f"[GSC REFRESH] ❌ No refresh token available for {user_email}, requiring re-auth")
                    return False  # Expired and can't refresh

                print(f"[GSC REFRESH] 🔄 Refresh token found, attempting automatic token refresh for {user_email}")
                try:
                    from google.oauth2.credentials import Credentials
                    from google.auth.transport.requests import Request
                    from app.config import settings

                    print(f"[GSC REFRESH] 🏗️ Creating credentials object for refresh...")
                    # Create credentials object for refresh
                    creds = Credentials(
                        token=credentials.get('access_token'),
                        refresh_token=refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=settings.GOOGLE_CLIENT_ID,
                        client_secret=settings.GOOGLE_CLIENT_SECRET
                    )

                    print(f"[GSC REFRESH] 📞 Calling Google OAuth refresh API...")
                    # Refresh the token
                    creds.refresh(Request())

                    print(f"[GSC REFRESH] ✅ Google refresh successful! New token received")
                    print(f"[GSC REFRESH] 📊 New credential details:")
                    print(f"[GSC REFRESH]   - New access_token: {'Yes' if creds.token else 'No'}")
                    print(f"[GSC REFRESH]   - New refresh_token: {'Yes' if creds.refresh_token else 'No'}")
                    print(f"[GSC REFRESH]   - New expiry: {creds.expiry}")

                    # Update database with new tokens
                    print(f"[GSC REFRESH] 💾 Updating database with new tokens...")
                    update_data = {
                        'access_token': creds.token,
                        'expires_at': creds.expiry.isoformat() if creds.expiry else None,
                        'updated_at': datetime.utcnow().isoformat()
                    }

                    # If we got a new refresh token, update it too
                    if creds.refresh_token:
                        update_data['refresh_token'] = creds.refresh_token
                        print(f"[GSC REFRESH] 🔄 Also updating refresh token")

                    db_response = db.service_supabase.table('gsc_connections').update(update_data).eq('email', user_email).execute()
                    print(f"[GSC REFRESH] 💾 Database update response: {db_response.data}")

                    # Clear the credentials cache in GoogleOAuthHandler so fresh tokens are fetched
                    print(f"[GSC REFRESH] 🧹 Clearing OAuth handler cache...")
                    try:
                        from app.auth.routes import google_oauth
                        google_oauth.clear_credentials_cache(user_email)
                        print(f"[GSC REFRESH] ✅ Cache cleared successfully")
                    except Exception as cache_clear_error:
                        print(f"[GSC REFRESH] ⚠️ Warning: Could not clear cache after refresh: {cache_clear_error}")

                    print(f"[GSC REFRESH] 🎉 ✅ Successfully refreshed tokens for {user_email}")
                    return True

                except Exception as refresh_error:
                    print(f"[GSC REFRESH] 💥 ❌ Token refresh failed for {user_email}: {refresh_error}")
                    import traceback
                    print(f"[GSC REFRESH] 📜 Full error traceback:")
                    traceback.print_exc()
                    return False
            else:
                print(f"[GSC VERIFY] ✅ Token is still valid (not expired)")

        else:
            print(f"[GSC VERIFY] ⚠️ No expiry time found, assuming token is valid")

        return True

    except Exception as e:
        print(f"[AUTH ERROR] 💥 Failed to verify GSC credentials: {e}")
        import traceback
        print(f"[AUTH ERROR] 📜 Full error traceback:")
        traceback.print_exc()
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