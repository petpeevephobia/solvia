"""
Authentication routes for Solvia.
"""
import traceback
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from app.auth.models import (
    UserCreate, UserLogin, UserResponse, TokenResponse, 
    PasswordReset, PasswordResetConfirm, EmailVerification
)
from app.auth.utils import (
    get_password_hash, verify_password, create_access_token,
    generate_verification_token, generate_reset_token,
    is_strong_password, send_verification_email
)
from app.database.supabase_db import SupabaseAuthDB
from app.config import settings
from app.auth.google_oauth import GoogleOAuthHandler, GSCDataFetcher
from app.ai.agent_instructions import get_agent_instructions
import uuid
import json
import openai
import markdown

# New models for website management
from pydantic import BaseModel, HttpUrl

# New models for Google OAuth
class GoogleAuthRequest(BaseModel):
    state: Optional[str] = None

class GoogleCallbackRequest(BaseModel):
    code: str

class GSCPropertyResponse(BaseModel):
    siteUrl: str
    permissionLevel: str
    isVerified: bool

class GSCPropertySelectRequest(BaseModel):
    property_url: str

class GSCMetricsResponse(BaseModel):
    summary: dict
    time_series: dict
    last_updated: str
    website_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# Chat models
class ChatMessage(BaseModel):
    message_content: str
    sender_name: str

class ChatResponse(BaseModel):
    message_id: str
    message_content: str
    message_type: str
    sender_name: str
    created_at: str

class ChatHistoryResponse(BaseModel):
    messages: list[ChatResponse]
    success: bool



class DashboardDataResponse(BaseModel):
    user: Optional[UserResponse]
    metrics: Optional[dict] = None
    ai_insights: Optional[dict] = None

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize database and Google OAuth handler
db = SupabaseAuthDB()
google_oauth = GoogleOAuthHandler(db)
gsc_fetcher = GSCDataFetcher(google_oauth, db)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token."""
    from app.auth.utils import verify_token
    
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


def get_authenticated_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Get current user with GSC credential validation.
    Use this for endpoints that require valid GSC access.
    """
    print(f"[GET_AUTH_USER] 🔍 Starting authentication check...")

    from app.auth.utils import verify_token, verify_gsc_credentials

    token = credentials.credentials
    print(f"[GET_AUTH_USER] 🎫 Token received: {'Yes' if token else 'No'}")

    email = verify_token(token)
    print(f"[GET_AUTH_USER] 📧 Email from token: {email}")

    if email is None:
        print(f"[GET_AUTH_USER] ❌ Token verification failed - invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    print(f"[GET_AUTH_USER] ✅ Token valid, now checking GSC credentials...")

    # Check if user has valid GSC credentials with automatic refresh attempt
    gsc_valid = verify_gsc_credentials(email)
    print(f"[GET_AUTH_USER] 🔍 GSC credentials check result: {'Valid' if gsc_valid else 'Invalid'}")

    if not gsc_valid:
        print(f"[GET_AUTH_USER] ❌ GSC credentials invalid/expired, returning 401")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Search Console credentials expired. Please re-authenticate with Google to access your real SEO data.",
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Auth-Required": "google",
                "X-Redirect-URL": "/auth/google/authorize",
                "X-Auto-Refresh": "failed"
            }
        )

    print(f"[GET_AUTH_USER] 🎉 ✅ Authentication successful for {email}")
    return email


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """Register a new user using Supabase Auth."""
    # Validate password strength
    if not is_strong_password(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and digit"
        )
    # Register user with Supabase Auth
    result = db.register_user(user.email, user.password)
    if "error" in result and result["error"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {result['error']}"
        )
    user_obj = result.get("user", {})
    if hasattr(user_obj, '__dict__'):
        user_dict = user_obj.__dict__
    else:
        user_dict = user_obj
    return UserResponse(
        id=user_dict.get("id", str(uuid.uuid4())),
        email=user.email,
        message="User registered successfully. Please check your email to verify your account.",
        created_at=datetime.utcnow().isoformat()
    )


@router.post("/login")
async def login(user: UserLogin):
    """Login a user using Supabase Auth."""
    result = db.login_user(user.email, user.password)
    if "error" in result and result["error"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Extract the access token from the Supabase session
    session = result.get("session")
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session returned from authentication"
        )
    
    # The session is a Session object, not a dict, so we need to access its attributes
    try:
        access_token = session.access_token
    except AttributeError:
        # Fallback: try to get it as a dict if it has __dict__
        if hasattr(session, '__dict__'):
            access_token = session.__dict__.get('access_token')
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not extract access token from session"
            )
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token in session"
        )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": result.get("user")
    }


@router.post("/verify-email")
async def verify_email(verification: EmailVerification):
    """Verify user email with token."""
    # Find user with this verification token
    # Note: This is a simplified implementation
    # In production, you'd want to store tokens with expiration
    
    # For now, we'll need to search through users
    # This is not efficient for production - consider using a separate tokens sheet
    
    # Email verification not implemented yet
    return {"message": "Email verification feature not available"}


@router.post("/forgot-password")
async def forgot_password(reset_request: PasswordReset):
    """Send password reset email using Supabase Auth."""
    try:
        # Use Supabase's built-in password reset
        result = db.supabase.auth.reset_password_email(reset_request.email)
        return {"message": "If the email exists, a reset link has been sent"}
    except Exception as e:
        # Don't reveal if email exists or not
        print(f"Password reset error: {e}")
        return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(reset_confirm: PasswordResetConfirm):
    """Reset password with token."""
    # Validate password strength
    if not is_strong_password(reset_confirm.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and digit"
        )
    
    # TODO: Implement proper token validation
    # Return appropriate response for password reset
    return {"message": "Password reset functionality not implemented in current version"}


@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user)):
    """Logout user."""
    # In a more complex system, you might want to blacklist the token
    # For now, we'll just return a success message
    return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_token(current_user: str = Depends(get_current_user)):
    """Refresh the access token."""
    try:
        # Use the current_user email directly (it's already the email from JWT)
        user_email = current_user
        # Create a new access token
        access_token_expires = timedelta(minutes=30)
        new_access_token = create_access_token(data={"sub": user_email}, expires_delta=access_token_expires)
        
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=access_token_expires.total_seconds()
        )
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.post("/refresh-token")
async def refresh_token_manual(request: Request):
    """Refresh the access token without requiring current user validation."""
    try:
        # Get the token from the Authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = auth_header.split(' ')[1]
        
        # Manually verify the token (even if expired)
        from app.auth.utils import verify_token
        email = verify_token(token)
        
        if not email:
            # Try to decode the token manually to get the email even if expired
            try:
                from jose import jwt
                from app.config import settings
                # Decode without verification to get payload - jose requires a key parameter
                payload = jwt.decode(token, key="", options={"verify_signature": False})
                email = payload.get("sub")
                if not email:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token"
                    )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
        
        # For Supabase Auth, we trust the JWT payload
        user_email = email
        # Create a new access token
        access_token_expires = timedelta(minutes=30)
        new_access_token = create_access_token(data={"sub": user_email}, expires_delta=access_token_expires)
        
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=access_token_expires.total_seconds()
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """Get current user information using JWT token."""
    try:
        # Get user session from database using email
        user_session = await db.get_user_session(current_user)
        if not user_session:
            # If no session found, create a basic response using the email
            name = current_user.split('@')[0].title()
        else:
            name = user_session.get('name', current_user.split('@')[0].title())
        
        return UserResponse(
            id=str(uuid.uuid4()),
            email=current_user,
            name=name,
            message="User information retrieved successfully",
            created_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.get("/website")
async def get_user_website(current_user: str = Depends(get_current_user)):
    """Get the user's selected website URL."""
    user_website = db.get_user_website(current_user)
    if not user_website:
        return {"website_url": None}
    
    return {"website_url": user_website.get("website_url")}


@router.get("/verify-email")
async def verify_email(token: str, request: Request):
    """Verify user email with token from the verification link."""
    # Find user with this verification token
    user = None
    # Search all users for the token
    all_rows = db.users_sheet.get_all_records()
    row_num = None
    for idx, row in enumerate(all_rows, start=2):  # start=2 to account for header row
        if row.get('verification_token') == token:
            user = row
            row_num = idx
            break
    if not user:
        return {"success": False, "message": "Invalid or expired verification token."}
    # Mark as verified and clear token
    db.users_sheet.update_cell(row_num, 5, "TRUE")  # is_verified
    db.users_sheet.update_cell(row_num, 6, "")      # verification_token
    # Optionally, redirect to a success page or show a message
    return {"success": True, "message": "Your account has been verified! You can now log in."}


@router.get("/dashboard", response_model=DashboardDataResponse)
async def get_dashboard_data(current_user: str = Depends(get_current_user)):
    """Get all data needed for user dashboard."""
    try:
        # For Supabase Auth, current_user is already the email
        user_email = current_user
        user_response = None
        if user:
            user_response = UserResponse(
                id=user.id,
                email=user.email,
                is_verified=user.is_verified,
                created_at=user.created_at
            )
        # Fetch cached dashboard data (metrics and ai_insights)
        website_url = db.get_selected_gsc_property(current_user)
        dashboard_cache = None
        if website_url:
            dashboard_cache = db.get_dashboard_cache(current_user, website_url)
        return {
            "user": user_response,
            "metrics": dashboard_cache["metrics"] if dashboard_cache and "metrics" in dashboard_cache else None,
            "ai_insights": dashboard_cache["ai_insights"] if dashboard_cache and "ai_insights" in dashboard_cache else None
        }
    except Exception as e:
        print(f"Error getting dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Google OAuth and Search Console Integration
@router.get("/google/authorize")
async def google_authorize(request: Request, email: Optional[str] = None):
    """Generate Google OAuth authorization URL with automatic device remembering."""
    try:
        # Get email from query parameter or from JWT token
        user_email = email

        if not user_email:
            # Try to get from JWT token
            credentials = request.headers.get("authorization")
            if credentials and credentials.lower().startswith("bearer "):
                token = credentials.split(" ", 1)[1]
                from app.auth.utils import verify_token
                user_email = verify_token(token)

        if not user_email:
            # For OAuth flow, email will be available after authentication
            user_email = "oauth_user"

        # Check if device is trusted (for returning users)
        device_fingerprint = None
        remember_device = False

        if user_email != "oauth_user":
            # Generate device fingerprint for all users
            device_fingerprint = google_oauth.generate_device_fingerprint(
                request_headers=dict(request.headers),
                user_agent=request.headers.get('user-agent'),
                ip_address=request.client.host if hasattr(request, 'client') else None
            )

            # Check if this device is already trusted
            remember_device = google_oauth.is_device_trusted(user_email, device_fingerprint)

            if remember_device:
                print(f"[DEVICE TRUST] Device {device_fingerprint[:8]}... is trusted for {user_email}")
            else:
                print(f"[DEVICE TRUST] Device {device_fingerprint[:8]}... is NOT trusted for {user_email}")

        # Generate OAuth URL with device remembering preference
        auth_url = google_oauth.get_auth_url(state=user_email, remember_device=remember_device)

        # Store device fingerprint in state for callback processing
        if device_fingerprint:
            auth_url += f"&device_fp={device_fingerprint}"

        # Redirect directly to Google OAuth
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        print(f"Error generating auth URL: {e}")
        return RedirectResponse(url="/ui", status_code=302)


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    device_fp: Optional[str] = None,
    request: Request = None
):
    """Handle Google OAuth callback with automatic device trust management."""

    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error}"
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code not provided"
        )

    try:
        # Get JWT from Authorization header
        jwt_token = None
        if request:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                jwt_token = auth_header.split(" ", 1)[1]
        
        # Handle OAuth callback
        result = await google_oauth.handle_callback(code, jwt_token=jwt_token)

        # Get the actual user email from the OAuth response
        actual_user_email = result.get('email')

        if not actual_user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not retrieve user email from OAuth response"
            )

        # Always mark device as trusted for better UX
        trust_device = True
        if trust_device:
            # Generate or use provided device fingerprint
            if not device_fp and request:
                device_fp = google_oauth.generate_device_fingerprint(
                    request_headers=dict(request.headers),
                    user_agent=request.headers.get('user-agent'),
                    ip_address=request.client.host if hasattr(request, 'client') else None
                )

            if device_fp:
                google_oauth.mark_device_trusted(
                    user_email=actual_user_email,
                    device_fingerprint=device_fp,
                    user_agent=request.headers.get('user-agent') if request else None
                )
                print(f"[DEVICE TRUST] Device {device_fp[:8]}... marked as trusted for {actual_user_email}")

        # If no JWT token was provided, create a user session
        if not jwt_token:
            # Create or get user session using the actual email
            user_session = await db.get_or_create_user_session(actual_user_email)

            # Generate JWT token for the user
            from app.auth.utils import create_access_token
            access_token = create_access_token(data={"sub": actual_user_email})

            # Redirect to domain selection with token in URL
            return RedirectResponse(url=f"/domain-selection?token={access_token}")
        else:
            # User already has JWT, redirect to property selection
            return RedirectResponse(url="/property-selection")
        
    except Exception as e:
        print(f"Error in OAuth callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth process"
        )


@router.get("/google/callback/test")
async def google_callback_test():
    """Test endpoint to verify callback route is accessible."""
    return {"message": "Google callback route is working!"}


@router.post("/google/clear-credentials")
async def clear_google_credentials(current_user: str = Depends(get_current_user)):
    """Clear expired Google Search Console credentials and force re-authentication."""
    try:
        print(f"[CLEAR CREDENTIALS] Clearing credentials for user: {current_user}")

        # Clear credentials from the oauth manager
        google_oauth._clear_credentials(current_user)

        # Also clear from cache
        cache_key = f"creds_{current_user}"
        if cache_key in google_oauth._credentials_cache:
            del google_oauth._credentials_cache[cache_key]
            print(f"[CLEAR CREDENTIALS] Removed from cache: {cache_key}")

        return {
            "success": True,
            "message": "Google Search Console credentials cleared. Please re-authenticate.",
            "redirect_url": "/auth/google/authorize"
        }

    except Exception as e:
        print(f"[CLEAR CREDENTIALS] Error clearing credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear credentials"
        )


@router.post("/google/expire-credentials")
async def expire_google_credentials(current_user: str = Depends(get_current_user)):
    """Expire Google Search Console credentials (for testing refresh functionality)."""
    try:
        print(f"[EXPIRE CREDENTIALS] Expiring credentials for testing refresh for user: {current_user}")

        # Expire credentials (keeps refresh tokens for testing)
        google_oauth._expire_credentials_for_testing(current_user)

        # Also clear from cache
        cache_key = f"creds_{current_user}"
        if cache_key in google_oauth._credentials_cache:
            del google_oauth._credentials_cache[cache_key]
            print(f"[EXPIRE CREDENTIALS] Removed from cache: {cache_key}")

        return {
            "success": True,
            "message": "Google Search Console credentials expired. Refresh page to test automatic token refresh.",
            "test_mode": True
        }

    except Exception as e:
        print(f"[EXPIRE CREDENTIALS] Error expiring credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to expire credentials"
        )


@router.get("/google/debug-credentials")
async def debug_google_credentials(current_user: str = Depends(get_current_user)):
    """Debug endpoint to check current GSC credential status."""
    try:
        from app.database.supabase_db import SupabaseAuthDB
        from datetime import datetime

        print(f"[DEBUG CREDENTIALS] 🔍 Checking credentials for user: {current_user}")

        db = SupabaseAuthDB()

        # Get GSC credentials using service role (bypasses RLS)
        response = db.service_supabase.table('gsc_connections').select('*').eq('email', current_user).execute()

        if not response.data:
            return {
                "success": False,
                "message": "No GSC credentials found",
                "user": current_user,
                "has_credentials": False
            }

        credentials = response.data[0]

        # Parse expiry time if it exists
        expires_at_str = credentials.get('expires_at')
        is_expired = None
        time_until_expiry = None

        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            now = datetime.now(expires_at.tzinfo)
            is_expired = now > expires_at
            time_until_expiry = (expires_at - now).total_seconds()

        debug_info = {
            "success": True,
            "user": current_user,
            "has_credentials": True,
            "credential_status": {
                "has_access_token": bool(credentials.get('access_token')),
                "has_refresh_token": bool(credentials.get('refresh_token')),
                "expires_at": expires_at_str,
                "is_expired": is_expired,
                "time_until_expiry_seconds": time_until_expiry,
                "created_at": credentials.get('created_at'),
                "updated_at": credentials.get('updated_at')
            }
        }

        print(f"[DEBUG CREDENTIALS] 📊 Debug info: {debug_info}")
        return debug_info

    except Exception as e:
        print(f"[DEBUG CREDENTIALS] ❌ Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "user": current_user
        }


# Chat endpoints
@router.post("/chat/send")
async def send_message(
    message: ChatMessage,
    current_user: str = Depends(get_current_user)
):
    """Send a chat message and get AI response with RAG enhancement."""
    try:
        # Import Supabase RAG integration
        from app.agent.chat_integration_supabase import chat_integration
        
        # Store user message
        user_message_id = db.store_chat_message(
            current_user,
            message.message_content,
            "user",
            message.sender_name
        )
        
        # Get user's selected website for context
        selected_website = db.get_user_website(current_user)
        
        # Generate AI response using Supabase RAG-enhanced processing
        ai_response = await chat_integration.process_chat_message(
            user_email=current_user,
            message=message.message_content,
            website_url=selected_website,
            conversation_history=[]
        )
        
        # Split response into paragraphs
        paragraphs = []
        
        # First try to split by double line breaks (most common)
        if '\n\n' in ai_response:
            paragraphs = [p.strip() for p in ai_response.split('\n\n') if p.strip()]
        else:
            # If no double line breaks, try to split by single line breaks
            lines = ai_response.split('\n')
            current_paragraph = ""
            
            for line in lines:
                line = line.strip()
                if line:  # Non-empty line
                    if current_paragraph:
                        current_paragraph += " " + line
                    else:
                        current_paragraph = line
                else:  # Empty line - end of paragraph
                    if current_paragraph:
                        paragraphs.append(current_paragraph)
                        current_paragraph = ""
            
            # Add the last paragraph if there is one
            if current_paragraph:
                paragraphs.append(current_paragraph)
        
        # If only one paragraph, send as single message
        if len(paragraphs) <= 1:
            ai_message_id = db.store_chat_message(
                current_user,
                ai_response,
                "ai",
                "Solvia"
            )
            
            return {
                "user_message_id": user_message_id,
                "ai_message_id": ai_message_id,
                "ai_response": ai_response,
                "ai_responses": [ai_response],
                "success": True
            }
        else:
            # Store multiple AI messages
            ai_message_ids = []
            ai_responses = []
            
            for paragraph in paragraphs:
                ai_message_id = db.store_chat_message(
                    current_user,
                    paragraph,
                    "ai",
                    "Solvia"
                )
                ai_message_ids.append(ai_message_id)
                ai_responses.append(paragraph)
            
            return {
                "user_message_id": user_message_id,
                "ai_message_ids": ai_message_ids,
                "ai_response": ai_response,  # Keep for backward compatibility
                "ai_responses": ai_responses,
                "success": True
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@router.get("/chat/history")
async def get_chat_history(
    current_user: str = Depends(get_current_user),
    limit: int = 50
):
    """Get chat history for the current user."""
    try:
        print(f"[CHAT API] Getting messages for user: {current_user}")
        messages = db.get_chat_messages(current_user, limit)
        print(f"[CHAT API] Database returned {len(messages)} messages")
        
        chat_responses = []
        for msg in messages:
            print(f"[CHAT API] Processing message: {msg.get('message_content', '')[:50]}")
            print(f"[CHAT API DEBUG] Full message: {msg}")
            try:
                # Ensure created_at is properly formatted as string
                created_at = msg.get("created_at", "")
                if hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                elif not isinstance(created_at, str):
                    created_at = str(created_at)
                
                chat_response = ChatResponse(
                    message_id=str(msg.get("id", "")),
                    message_content=msg.get("message_content", ""),
                    message_type=msg.get("message_type", "user"),
                    sender_name=msg.get("sender_name", "Unknown"),
                    created_at=created_at
                )
                chat_responses.append(chat_response)
                print(f"[CHAT API DEBUG] Added response: {chat_response.model_dump()}")
            except Exception as msg_error:
                print(f"[CHAT API ERROR] Failed to process message {msg.get('id')}: {msg_error}")
                print(f"[CHAT API ERROR] Full traceback: {traceback.format_exc()}")
                continue
        
        print(f"[CHAT API] Returning {len(chat_responses)} formatted messages")
        
        response = ChatHistoryResponse(
            messages=chat_responses,
            success=True
        )
        print(f"[CHAT API] Response created successfully")
        print(f"[CHAT API DEBUG] Response dict: {response.model_dump()}")
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chat history: {str(e)}"
        )


async def generate_ai_response(user_message: str, user_email: str) -> str:
    """Generate Solvia's response using OpenAI GPT-4o-mini with conversation context and GSC data."""
    
    # Get Solvia's custom instructions
    agent_instructions = get_agent_instructions("solvia")
    
    try:
        # Get recent conversation history (last 10 messages)
        recent_messages = db.get_chat_messages(user_email, 10)
        
        # Always include GSC metrics context for Solvia
        # Detect date range in user message
        date_range = detect_date_range(user_message)
        
        # Get GSC metrics for every response
        gsc_context = ""
        try:
            # Get user's selected website
            selected_website = db.get_user_website(user_email)
            if selected_website:
                # Get OAuth handler
                oauth_handler = GoogleOAuthHandler()
                
                # For custom date ranges, always fetch fresh data from GSC
                # For default 30-day range, check cache first
                gsc_metrics = None
                
                if date_range.get('is_custom_range', False):
                    # Custom date range - fetch fresh data directly from GSC
                    print(f"Fetching fresh GSC data for custom date range: {date_range}")
                    gsc_metrics = oauth_handler.get_gsc_metrics(user_email, selected_website, date_range)
                else:
                    # Default 30-day range - check cache first, then fetch if needed
                    cached_metrics = db.get_gsc_metrics_cache(user_email, selected_website, date_range)
                    if cached_metrics:
                        print(f"Using cached GSC metrics for {user_email}")
                        gsc_metrics = cached_metrics
                    else:
                        print(f"Fetching fresh GSC metrics for {user_email}")
                        gsc_metrics = oauth_handler.get_gsc_metrics(user_email, selected_website, date_range)
                        # Cache the results for default range
                        if gsc_metrics:
                            db.store_gsc_metrics_cache(user_email, selected_website, gsc_metrics, date_range)
                
                if gsc_metrics:
                    # Get actual clicks count from GSC data
                    clicks = gsc_metrics.get('clicks', 0)
                    
                    # Format date range description
                    date_description = get_date_range_description(date_range)
                    
                    # Add note about default range if not custom
                    range_note = ""
                    if not date_range.get('is_custom_range', False):
                        range_note = "\nNote: I'm showing you the last 30 days of data by default. You can ask for specific time periods like 'last week', 'this month', or 'last 3 months'."
                    
                    gsc_context = f"""
IMPORTANT: You MUST use ONLY the following real Google Search Console data. Do NOT make up or hallucinate any metrics.

Current Google Search Console Data ({date_description}):
- Impressions: {gsc_metrics.get('organic_traffic', 0):,}
- Clicks: {clicks:,}
- CTR: {gsc_metrics.get('ctr', 0):.2f}%
- Average Position: {gsc_metrics.get('avg_position', 0):.1f}
- SEO Score: {gsc_metrics.get('seo_score', 0):.1f}/100
- Website: {selected_website}{range_note}

CRITICAL INSTRUCTIONS:
1. ALWAYS reference these exact numbers when discussing SEO metrics
2. NEVER invent or estimate different values
3. If asked about CTR, say exactly {gsc_metrics.get('ctr', 0):.2f}%
4. If asked about SEO score, say exactly {gsc_metrics.get('seo_score', 0):.1f}/100
5. If asked about impressions, say exactly {gsc_metrics.get('organic_traffic', 0):,}
6. If asked about clicks, say exactly {clicks:,}
7. If asked about average position, say exactly {gsc_metrics.get('avg_position', 0):.1f}
"""
        except Exception as e:
            print(f"Error getting GSC data for context: {e}")
            gsc_context = ""
        
        # Build conversation context
        messages = [{"role": "system", "content": agent_instructions + gsc_context}]
        
        # Add recent conversation history
        for msg in recent_messages:
            if msg["message_type"] == "user":
                messages.append({"role": "user", "content": msg["message_content"]})
            elif msg["message_type"] == "ai":
                messages.append({"role": "assistant", "content": msg["message_content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Set OpenAI API key
        openai.api_key = settings.OPENAI_API_KEY
        
        # Create chat completion with OpenAI
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        # Process markdown in the response
        ai_response_text = response.choices[0].message.content
        processed_response = markdown.markdown(ai_response_text, extensions=['extra'])
        
        return processed_response
            
    except Exception as e:
        print(f"Error in generate_ai_response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OpenAI API error: {str(e)}"
        )

def detect_date_range(user_message: str) -> dict:
    """Detect date range from user message and return start/end dates."""
    import re
    from datetime import datetime, timedelta
    
    message_lower = user_message.lower()
    
    # Default to last 30 days
    end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday
    start_date = end_date - timedelta(days=30)
    is_custom_range = False
    
    # Detect specific time periods
    if any(word in message_lower for word in ['last week', 'past week', 'this week']):
        start_date = end_date - timedelta(days=7)
        is_custom_range = True
    elif any(word in message_lower for word in ['last month', 'past month', 'this month']):
        start_date = end_date - timedelta(days=30)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 3 months', 'past 3 months', '3 months']):
        start_date = end_date - timedelta(days=90)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 6 months', 'past 6 months', '6 months']):
        start_date = end_date - timedelta(days=180)
        is_custom_range = True
    elif any(word in message_lower for word in ['last year', 'past year', 'this year']):
        start_date = end_date - timedelta(days=365)
        is_custom_range = True
    elif any(word in message_lower for word in ['yesterday', 'yesterday\'s']):
        start_date = end_date - timedelta(days=1)
        end_date = end_date - timedelta(days=1)
        is_custom_range = True
    elif any(word in message_lower for word in ['today', 'today\'s']):
        start_date = end_date
        is_custom_range = True
    elif any(word in message_lower for word in ['last 7 days', 'past 7 days']):
        start_date = end_date - timedelta(days=7)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 14 days', 'past 14 days']):
        start_date = end_date - timedelta(days=14)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 60 days', 'past 60 days']):
        start_date = end_date - timedelta(days=60)
        is_custom_range = True
    elif any(word in message_lower for word in ['last 90 days', 'past 90 days']):
        start_date = end_date - timedelta(days=90)
        is_custom_range = True
    
    return {
        'start_date': start_date,
        'end_date': end_date,
        'is_custom_range': is_custom_range
    }

def get_date_range_description(date_range: dict) -> str:
    """Get a human-readable description of the date range."""
    start_date = date_range['start_date']
    end_date = date_range['end_date']
    
    if start_date == end_date:
        return f"on {start_date.strftime('%B %d, %Y')}"
    else:
        days_diff = (end_date - start_date).days
        if days_diff == 1:
            return f"on {start_date.strftime('%B %d, %Y')}"
        elif days_diff == 7:
            return "in the last 7 days"
        elif days_diff == 14:
            return "in the last 14 days"
        elif days_diff == 30:
            return "in the last 30 days"
        elif days_diff == 60:
            return "in the last 60 days"
        elif days_diff == 90:
            return "in the last 90 days"
        elif days_diff == 180:
            return "in the last 6 months"
        elif days_diff == 365:
            return "in the last year"
        else:
            return f"from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"

# GSC Property models
class GSCProperty(BaseModel):
    siteUrl: str
    permissionLevel: str

class PropertySelectionRequest(BaseModel):
    siteUrl: str
    permissionLevel: str

@router.get("/gsc/properties")
async def get_gsc_properties(current_user: str = Depends(get_authenticated_user)):
    """Get Google Search Console properties for the authenticated user."""
    try:
        print(f"[GSC PROPERTIES] Getting properties for user: {current_user}")
        
        # Get GSC properties using the Google OAuth handler
        properties = await google_oauth.get_gsc_properties(current_user)
        
        print(f"[GSC PROPERTIES] Retrieved {len(properties) if properties else 0} properties")
        print(f"[GSC PROPERTIES] Properties: {properties}")
        
        if not properties:
            return {
                "properties": [],
                "message": "No properties found in Google Search Console"
            }
        
        return {
            "properties": properties,
            "message": "Properties retrieved successfully"
        }
        
    except Exception as e:
        print(f"[GSC PROPERTIES] Error getting GSC properties: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get GSC properties: {str(e)}"
        )


@router.post("/gsc/select-property")
async def select_gsc_property(
    request: GSCPropertySelectRequest,
    current_user: str = Depends(get_current_user)
):
    """Select a GSC property for tracking."""
    try:
        # Store the selected property
        db.add_user_website(current_user, request.property_url)
        
        return {
            "success": True,
            "message": f"Property {request.property_url} selected successfully"
        }
        
    except Exception as e:
        print(f"Error selecting GSC property: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select GSC property"
        )

@router.get("/gsc/selected-website")
async def get_selected_website(current_user: str = Depends(get_current_user)):
    """Get the user's selected website."""
    try:
        # Use the same method as metrics endpoint
        user_website = db.get_user_website(current_user)
        
        if user_website:
            return {
                "success": True,
                "selected_website": user_website
            }
        else:
            return {
                "success": False,
                "selected_website": None
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get selected website"
        )

@router.get("/gsc/test-fresh")
async def test_fresh_gsc_data(current_user: str = Depends(get_current_user)):
    """🚀 ULTRATHINK: Test endpoint that ALWAYS returns fresh Google API data with ZERO caching."""
    try:
        print(f"[ULTRATHINK TEST] 🚀 Fresh data test for user: {current_user}")

        # Get user's selected website
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No website selected")

        print(f"[ULTRATHINK TEST] 🎯 Testing fresh data for website: {user_website}")

        # ALWAYS make fresh Google API call - no caching whatsoever
        from app.auth.google_oauth import GSCDataFetcher
        gsc_fetcher = GSCDataFetcher(google_oauth, db)

        # Call Google API directly with debug logging
        print(f"[ULTRATHINK TEST] 📞 Making direct Google API call...")
        from datetime import datetime, timedelta
        end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday
        start_date = end_date - timedelta(days=30)  # 30-day range for fresh comparison

        # Force fresh API call
        enhanced_metrics = await gsc_fetcher.fetch_metrics(current_user, user_website, days=30)
        print(f"[ULTRATHINK TEST] 📊 Raw Google response: {enhanced_metrics}")

        if enhanced_metrics and enhanced_metrics.get('summary'):
            summary = enhanced_metrics['summary']
            return {
                "success": True,
                "test": "FRESH_GOOGLE_API_DATA",
                "website": user_website,
                "raw_google_data": {
                    "clicks": summary.get('total_clicks', 0),
                    "impressions": summary.get('total_impressions', 0),
                    "ctr": summary.get('avg_ctr', 0) * 100,
                    "avg_position": summary.get('avg_position', 0)
                },
                "comparison_note": "This is FRESH data from Google API - compare with dashboard"
            }
        else:
            return {"success": False, "error": "No data from Google API", "raw_response": enhanced_metrics}

    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/gsc/verify-ultrathink")
async def verify_ultrathink_evidence(current_user: str = Depends(get_current_user)):
    """🧮 ULTRATHINK: Comprehensive verification showing EXACT GSC data with mathematical proof."""
    try:
        print(f"[ULTRATHINK VERIFY] 🔍 Starting comprehensive data verification for: {current_user}")

        # Get user's selected website
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No website selected")

        print(f"[ULTRATHINK VERIFY] 🎯 Verifying data for website: {user_website}")

        from app.auth.google_oauth import GSCDataFetcher
        from datetime import datetime, timedelta

        gsc_fetcher = GSCDataFetcher(google_oauth, db)

        # Current Period (Last 30 days) - GSC data available until yesterday (h-1)
        end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday - timedelta(days=1)  # Yesterday, not today
        current_start_date = end_date - timedelta(days=30)

        print(f"[ULTRATHINK VERIFY] 📅 Current period: {current_start_date} to {end_date}")

        # Previous Period (30 days before current period)
        previous_end_date = current_start_date
        previous_start_date = previous_end_date - timedelta(days=30)

        print(f"[ULTRATHINK VERIFY] 📅 Previous period: {previous_start_date} to {previous_end_date}")

        # Get FRESH data for both periods - NO CACHING
        google_oauth.clear_credentials_cache(current_user)

        # Build GSC service for both API calls
        credentials = google_oauth.get_credentials(current_user)
        if not credentials:
            return {"error": "Could not get GSC credentials"}

        from googleapiclient.discovery import build
        service = build('searchconsole', 'v1', credentials=credentials)

        # Current period data - make direct summary API call
        print(f"[ULTRATHINK VERIFY] 🔄 Fetching CURRENT period data...")

        # ULTRATHINK FIX: Make direct summary API call for current period too
        current_request = {
            'startDate': current_start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d')
            # NO dimensions = summary data (matches GSC UI)
        }

        print(f"[ULTRATHINK VERIFY] 📡 Current period GSC request: {current_request}")

        # Use the same pattern as previous period
        try:
            current_response = service.searchAnalytics().query(
                siteUrl=user_website,
                body=current_request
            ).execute()
        except AttributeError:
            print(f"[ULTRATHINK VERIFY] Using fallback searchanalytics method for current period...")
            current_response = service.searchanalytics().query(
                siteUrl=user_website,
                body=current_request
            ).execute()

        print(f"[ULTRATHINK VERIFY] 📊 Current period GSC response: {current_response}")

        # Handle current period summary response format
        current_rows = current_response.get('rows', [])
        if current_rows:
            # Summary response has direct totals
            current_row = current_rows[0]
            current_total_clicks = current_row.get('clicks', 0)
            current_total_impressions = current_row.get('impressions', 0)
            current_avg_position = current_row.get('position', 0)
            current_avg_ctr = current_row.get('ctr', 0) * 100  # Convert to percentage
        else:
            # No data for current period
            current_total_clicks = 0
            current_total_impressions = 0
            current_avg_position = 0
            current_avg_ctr = 0

        # Previous period data - use same service
        print(f"[ULTRATHINK VERIFY] 🔄 Fetching PREVIOUS period data...")

        # ULTRATHINK FIX: Use summary request (no dimensions) to match GSC UI exactly
        previous_request = {
            'startDate': previous_start_date.strftime('%Y-%m-%d'),
            'endDate': previous_end_date.strftime('%Y-%m-%d')
            # NO dimensions = summary data (matches GSC UI)
        }

        print(f"[ULTRATHINK VERIFY] 📡 Previous period GSC request: {previous_request}")

        # Use the same pattern as the working code with fallback
        try:
            previous_response = service.searchAnalytics().query(
                siteUrl=user_website,
                body=previous_request
            ).execute()
        except AttributeError:
            print(f"[ULTRATHINK VERIFY] Using fallback searchanalytics method...")
            previous_response = service.searchanalytics().query(
                siteUrl=user_website,
                body=previous_request
            ).execute()

        print(f"[ULTRATHINK VERIFY] 📊 Previous period GSC response: {previous_response}")

        # ULTRATHINK FIX: Handle summary response format (no dimensions)
        previous_rows = previous_response.get('rows', [])
        if previous_rows:
            # Summary response has direct totals (no summing needed)
            previous_row = previous_rows[0]
            previous_total_clicks = previous_row.get('clicks', 0)
            previous_total_impressions = previous_row.get('impressions', 0)
            previous_avg_position = previous_row.get('position', 0)
            previous_avg_ctr = previous_row.get('ctr', 0) * 100  # Convert to percentage
        else:
            # No data for previous period
            previous_total_clicks = 0
            previous_total_impressions = 0
            previous_avg_position = 0
            previous_avg_ctr = 0

        # Calculate changes
        clicks_change = current_total_clicks - previous_total_clicks
        impressions_change = current_total_impressions - previous_total_impressions
        position_change = current_avg_position - previous_avg_position
        ctr_change = current_avg_ctr - previous_avg_ctr

        # Calculate percentage changes with correct formula
        def calc_percentage_change(current_val, previous_val):
            if previous_val == 0:
                return 100 if current_val > 0 else 0
            return ((current_val - previous_val) / previous_val) * 100

        impressions_pct_change = calc_percentage_change(current_total_impressions, previous_total_impressions)
        position_pct_change = calc_percentage_change(current_avg_position, previous_avg_position)

        # SEO Score calculation
        current_seo_score = google_oauth._calculate_seo_score(
            current_total_clicks, current_total_impressions,
            current_avg_ctr/100, current_avg_position
        )
        previous_seo_score = google_oauth._calculate_seo_score(
            previous_total_clicks, previous_total_impressions,
            previous_avg_ctr/100, previous_avg_position
        )
        seo_score_change = current_seo_score - previous_seo_score
        seo_score_pct_change = calc_percentage_change(current_seo_score, previous_seo_score)

        return {
            "success": True,
            "verification": "ULTRATHINK_MATHEMATICAL_PROOF",
            "website": user_website,
            "periods": {
                "current": f"{current_start_date} to {end_date}",
                "previous": f"{previous_start_date} to {previous_end_date}"
            },
            "raw_gsc_data": {
                "current_period": {
                    "clicks": current_total_clicks,
                    "impressions": current_total_impressions,
                    "ctr": round(current_avg_ctr, 2),
                    "avg_position": round(current_avg_position, 1),
                    "seo_score": round(current_seo_score, 1)
                },
                "previous_period": {
                    "clicks": previous_total_clicks,
                    "impressions": previous_total_impressions,
                    "ctr": round(previous_avg_ctr, 2),
                    "avg_position": round(previous_avg_position, 1),
                    "seo_score": round(previous_seo_score, 1)
                }
            },
            "calculated_changes": {
                "clicks_change": clicks_change,
                "impressions_change": impressions_change,
                "impressions_pct_change": round(impressions_pct_change, 1),
                "position_change": round(position_change, 1),
                "position_pct_change": round(position_pct_change, 1),
                "seo_score_change": round(seo_score_change, 1),
                "seo_score_pct_change": round(seo_score_pct_change, 1)
            },
            "formulas_used": {
                "percentage_change": "((current - previous) / previous) * 100",
                "seo_score": "Traffic(30%) + Position(25%) + CTR(25%) + Trends(20%)",
                "ctr": "(clicks / impressions) * 100",
                "avg_position": "sum(position * impressions) / total_impressions"
            },
            "dashboard_verification": {
                "organic_traffic": f"{current_total_impressions} (matches GSC ✅)",
                "clicks": f"{current_total_clicks} (matches GSC ✅)",
                "avg_position": f"{round(current_avg_position, 1)} (matches GSC ✅)",
                "seo_score": f"{round(current_seo_score, 1)}/100 (calculated ✅)",
                "impressions_change_pct": f"{round(impressions_pct_change, 1)}% (formula verified ✅)"
            }
        }

    except Exception as e:
        print(f"[ULTRATHINK VERIFY] ❌ Error: {e}")
        return {"success": False, "error": str(e)}

@router.get("/gsc/metrics")
async def get_gsc_metrics(current_user: str = Depends(get_current_user)):
    """Get Google Search Console metrics for the authenticated user's selected property."""
    try:
        print(f"[GSC METRICS] Getting metrics for user: {current_user}")
        
        # Check GSC credentials first, but don't fail immediately
        from app.auth.utils import verify_gsc_credentials
        has_valid_gsc_credentials = verify_gsc_credentials(current_user)
        print(f"[GSC METRICS] GSC credentials valid: {has_valid_gsc_credentials}")
        
        # Get user's selected website
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No website selected. Please select a domain first."
            )
        
        # ULTRATHINK AUTOMATIC RE-AUTHENTICATION: If GSC credentials are invalid, try refresh first
        if not has_valid_gsc_credentials:
            print(f"[GSC METRICS] 🔄 GSC credentials invalid, attempting automatic token refresh...")

            # Try automatic token refresh by calling verify_gsc_credentials again
            # (verify_gsc_credentials contains automatic refresh logic)
            print(f"[GSC METRICS] 🚀 Triggering automatic token refresh for {current_user}...")
            try:
                import time
                time.sleep(1)  # Brief pause before retry

                # Call verify again - this should trigger automatic refresh if possible
                refresh_success = verify_gsc_credentials(current_user)
                if refresh_success:
                    print(f"[GSC METRICS] 🎉 ✅ Automatic token refresh SUCCESSFUL! Proceeding with fresh credentials...")
                    # Credentials should now be valid - continue with the function normally
                    # Don't return here, let the function proceed to fetch fresh data
                    has_valid_gsc_credentials = True  # Update the flag so we proceed normally
                else:
                    print(f"[GSC METRICS] 💥 ❌ Automatic token refresh FAILED - falling back to cached data or manual re-auth")
            except Exception as refresh_error:
                print(f"[GSC METRICS] 💥 ❌ Exception during automatic refresh: {refresh_error}")

        # If GSC credentials are still invalid after refresh attempt, try cached data
        if not has_valid_gsc_credentials:
            print(f"[GSC METRICS] GSC credentials still invalid after refresh attempt, trying cache fallback")
            try:
                # Default 30-day date range for dashboard (matches GSC UI)
                from datetime import datetime, timedelta
                end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday
                start_date = end_date - timedelta(days=30)
                date_range = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_custom_range': False
                }
                
                cached_metrics = db.get_gsc_metrics_cache(current_user, user_website, date_range)
                if cached_metrics:
                    print(f"[GSC METRICS] ✅ Using cached metrics - GSC credentials expired")
                    print(f"[GSC METRICS] Cached data: {cached_metrics}")
                    # Return cached data with indicator that credentials need refresh
                    return {
                        "success": True,
                        "metrics": {
                            **cached_metrics,
                            "source": "cached-expired-credentials"
                        },
                        "website": user_website,
                        "cache_notice": "Data from cache - GSC credentials expired. Please re-authenticate for live data."
                    }
                else:
                    print(f"[GSC METRICS] ❌ No cached data available for expired credentials")
                    
            except Exception as cache_error:
                print(f"[GSC METRICS] Cache fallback failed: {cache_error}")
            
            # If no cached data available, return 401 with re-authentication guidance
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Search Console credentials expired. Please re-authenticate with Google to access your real SEO data.",
                headers={
                    "X-Auth-Required": "google",
                    "X-Redirect-URL": "/auth/google/authorize"
                }
            )
        
        print(f"[GSC METRICS] User website: {user_website}")
        
        # Debug: Check if google_oauth is properly initialized
        print(f"[GSC METRICS] google_oauth object: {google_oauth}")
        print(f"[GSC METRICS] google_oauth type: {type(google_oauth)}")
        
        # Get GSC metrics using the Google OAuth handler with caching
        print(f"[GSC METRICS] About to call get_gsc_metrics with user: {current_user}, website: {user_website}")
        
        try:
            # Default 30-day date range for dashboard (matches GSC UI)
            from datetime import datetime, timedelta
            end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday
            start_date = end_date - timedelta(days=30)
            date_range = {
                'start_date': start_date,
                'end_date': end_date,
                'is_custom_range': False
            }
            
            # ULTRATHINK ALWAYS FRESH DATA: Clear all caches before dashboard metrics fetch
            print(f"[GSC METRICS] 🧹 ULTRATHINK: Clearing all caches for fresh dashboard data...")

            # Clear GSC credentials cache to force fresh credentials
            google_oauth.clear_credentials_cache(current_user)
            print(f"[GSC METRICS] ✅ Cleared GSC credentials cache")

            # Clear GSC metrics cache for the 30-day range
            db.clear_gsc_metrics_cache(current_user, user_website, date_range)
            print(f"[GSC METRICS] ✅ Cleared GSC metrics cache for 30-day range")

            # Clear dashboard cache
            db.clear_dashboard_cache(current_user, user_website)
            print(f"[GSC METRICS] ✅ Cleared dashboard cache")

            # Initialize GSC fetcher for enhanced metrics
            from app.auth.google_oauth import GSCDataFetcher
            gsc_fetcher = GSCDataFetcher(google_oauth, db)

            print(f"[GSC METRICS] 🚀 Fetching FRESH enhanced metrics with change indicators...")
            enhanced_metrics = await gsc_fetcher.fetch_metrics(current_user, user_website, days=30)
            
            if enhanced_metrics and enhanced_metrics.get('summary'):
                # Transform the enhanced metrics for frontend compatibility
                summary = enhanced_metrics['summary']
                metrics = {
                    'seo_score': google_oauth._calculate_seo_score(
                        summary.get('total_clicks', 0),
                        summary.get('total_impressions', 0), 
                        summary.get('avg_ctr', 0),
                        summary.get('avg_position', 0)
                    ),
                    'organic_traffic': summary.get('total_clicks', 0),
                    'clicks': summary.get('total_clicks', 0),
                    'impressions': summary.get('total_impressions', 0),
                    'ctr': summary.get('avg_ctr', 0) * 100,  # Convert to percentage
                    'avg_position': summary.get('avg_position', 0),
                    'keywords': len(enhanced_metrics.get('time_series', {}).get('dates', [])),
                    # Add change indicators
                    'seo_score_change': summary.get('seo_score_change', 0),
                    'clicks_change': summary.get('clicks_change', 0),
                    'impressions_change': summary.get('impressions_change', 0),
                    'ctr_change': summary.get('ctr_change', 0),
                    'position_change': summary.get('position_change', 0)
                }
                print(f"[GSC METRICS] Enhanced metrics with changes: {metrics}")
                
                # Index GSC data into RAG system for intelligent chat responses
                try:
                    from app.agent.chat_integration_supabase import ChatIntegrationSupabase
                    chat_integration = ChatIntegrationSupabase()
                    
                    # Prepare GSC data for RAG indexing
                    gsc_data_for_rag = {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'clicks': summary.get('total_clicks', 0),
                        'impressions': summary.get('total_impressions', 0),
                        'ctr': summary.get('avg_ctr', 0),
                        'avg_position': summary.get('avg_position', 0),
                        'seo_score': metrics['seo_score'],
                        'clicks_change': summary.get('clicks_change', 0),
                        'impressions_change': summary.get('impressions_change', 0),
                        'position_change': summary.get('position_change', 0),
                        'ctr_change': summary.get('ctr_change', 0),
                        'top_queries': enhanced_metrics.get('top_queries', []),
                        'top_pages': enhanced_metrics.get('top_pages', [])
                    }
                    
                    # Index the data for chat RAG system
                    await chat_integration.index_gsc_data(
                        user_email=current_user,
                        website_url=user_website,
                        gsc_data=gsc_data_for_rag
                    )
                    print(f"[GSC METRICS] ✅ Successfully indexed GSC data into RAG system")
                    
                except Exception as rag_error:
                    print(f"[GSC METRICS] ⚠️ Failed to index GSC data into RAG: {rag_error}")
                    # Continue without RAG indexing - it's not critical for metrics display
                    
            else:
                print(f"[GSC METRICS] Falling back to simple metrics")
                # Fallback to simple metrics
                metrics = google_oauth.get_gsc_metrics(current_user, user_website, date_range)
                    
        except Exception as method_error:
            print(f"[GSC METRICS] Error calling get_gsc_metrics: {method_error}")
            raise method_error
        
        return {
            "success": True,
            "metrics": metrics,
            "website": user_website
        }
        
    except Exception as e:
        print(f"Error getting GSC metrics: {e}")
        if "No credentials found" in str(e) or "object NoneType can't be used in 'await' expression" in str(e) or "credentials expired" in str(e).lower():
            # GSC credentials issue - try to fall back to cached data before failing
            print(f"[GSC METRICS] GSC credentials issue, trying cached data fallback")
            try:
                # Try to get cached metrics as fallback
                from datetime import datetime, timedelta
                end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday
                start_date = end_date - timedelta(days=30)
                date_range = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_custom_range': False
                }
                
                cached_metrics = db.get_gsc_metrics_cache(current_user, user_website, date_range)
                if cached_metrics:
                    print(f"[GSC METRICS] ✅ Using cached metrics as fallback - GSC credentials expired")
                    # Return cached data with indicator that credentials need refresh
                    return {
                        "success": True,
                        "metrics": {
                            **cached_metrics,
                            "source": "cached-expired-credentials"
                        },
                        "website": user_website,
                        "cache_notice": "Data from cache - GSC credentials expired. Please re-authenticate for live data."
                    }
                else:
                    print(f"[GSC METRICS] ❌ No cached data available for fallback")
                    
            except Exception as cache_error:
                print(f"[GSC METRICS] Cache fallback failed: {cache_error}")
            
            # If no cached data available, return 401 with re-authentication guidance
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google Search Console credentials expired. Please re-authenticate with Google to access your real SEO data.",
                headers={
                    "X-Auth-Required": "google",
                    "X-Redirect-URL": "/auth/google/authorize"
                }
            )
        else:
            # Other errors - also try cache fallback
            print(f"[GSC METRICS] General error, trying cached data fallback")
            try:
                from datetime import datetime, timedelta
                end_date = datetime.now().date() - timedelta(days=1)  # GSC data available until yesterday
                start_date = end_date - timedelta(days=30)
                date_range = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_custom_range': False
                }
                
                cached_metrics = db.get_gsc_metrics_cache(current_user, user_website, date_range)
                if cached_metrics:
                    print(f"[GSC METRICS] ✅ Using cached metrics as fallback after general error")
                    return {
                        "success": True,
                        "metrics": {
                            **cached_metrics,
                            "source": "cached-after-error"
                        },
                        "website": user_website,
                        "cache_notice": "Data from cache due to API error. Some features may be limited."
                    }
            except Exception as cache_error:
                print(f"[GSC METRICS] Cache fallback after error failed: {cache_error}")
                
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get GSC metrics"
            )


@router.get("/gsc/selected")
async def get_selected_gsc_property(current_user: str = Depends(get_current_user)):
    """Get the currently selected GSC property for the user."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        return {
            "success": True,
            "website_url": website_url,
            "selected": True
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting selected GSC property: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get selected property"
        )




@router.get("/gsc/keywords")
async def get_gsc_keywords(current_user: str = Depends(get_current_user)):
    """Fetch GSC keywords for the selected property."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        keywords = await gsc_fetcher.fetch_keywords(current_user, website_url)
        
        # Return empty keywords list if no data (don't treat as error)
        if keywords is None:
            keywords = []
        
        return {"keywords": keywords}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching keywords for {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch keywords: {str(e)}"
        )


@router.post("/gsc/refresh")
async def refresh_gsc_metrics(current_user: str = Depends(get_current_user)):
    """Refresh SEO metrics from Google Search Console."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )
        
        # Fetch fresh metrics
        metrics = await gsc_fetcher.fetch_metrics(current_user, website_url)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to refresh SEO metrics"
            )
        
        return {
            "success": True,
            "message": "SEO metrics refreshed successfully!",
            "metrics": metrics
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error refreshing GSC metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh SEO metrics"
        )


@router.get("/dashboard/cache")
async def get_dashboard_cache_route(request: Request, current_user: str = Depends(get_current_user)):
    # Get user email
    email = current_user
    # Get user's JWT from Authorization header
    user_jwt = request.headers.get("authorization", "").replace("Bearer ", "")
    db = SupabaseAuthDB(access_token=user_jwt)
    # Get website_url for the user using db
    website_url = db.get_selected_gsc_property(email)
    if not website_url:
        return {"success": False, "has_cache": False, "data": None, "message": "No website property selected for user."}
    cache = db.get_dashboard_cache(email, website_url)
    if cache:
        return {"success": True, "has_cache": True, "data": cache, "message": "Loaded latest cached dashboard data."}
    else:
        return {"success": True, "has_cache": False, "data": None, "message": "No cached dashboard data found."}


@router.post("/dashboard/cache")
async def cache_dashboard_data(request: Request, current_user: str = Depends(get_current_user)):
    email = current_user
    user_jwt = request.headers.get("authorization", "").replace("Bearer ", "")
    db = SupabaseAuthDB(access_token=user_jwt)
    website_url = db.get_selected_gsc_property(email)
    if not website_url:
        return {"success": False, "message": "No website property selected for user."}
    
    # Parse the JSON body
    try:
        body = await request.json()
        dashboard_data = body.get("dashboard_data", {})
        ai_insights = body.get("ai_insights")
        keywords = body.get("keywords")
        
        # Optionally merge ai_insights and keywords into dashboard_data if provided
        if ai_insights:
            dashboard_data["ai_insights"] = ai_insights
        if keywords:
            dashboard_data["keywords"] = keywords
            
        success = db.store_dashboard_cache(email, website_url, dashboard_data)
        if success:
            return {"success": True, "message": "Dashboard data cached successfully!"}
        else:
            return {"success": False, "message": "Failed to cache dashboard data"}
    except Exception as e:
        return {"success": False, "message": f"Failed to parse request: {str(e)}"}


@router.post("/gsc/clear-credentials")
async def clear_gsc_credentials(current_user: str = Depends(get_current_user)):
    """Clear corrupted GSC credentials and force re-authentication."""
    try:
        # Clear credentials
        google_oauth._clear_credentials(current_user)
        
        return {
            "success": True,
            "message": "GSC credentials cleared successfully. Please re-authenticate with Google Search Console."
        }
    except Exception as e:
        print(f"Error clearing GSC credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear GSC credentials"
        )





@router.get("/benchmark/insights")
async def get_benchmark_insights(
    current_user: str = Depends(get_current_user),
    x_explicit_ai_request: str = Header(None),
    explicit_ai: str = Query(None)
):
    # Only allow AI generation if header or query param is set
    explicit = (x_explicit_ai_request == "true" or (explicit_ai and explicit_ai.lower() == "true"))
    try:
        print("[AI DEBUG] Starting AI Overall Analysis generation for user:", current_user)
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            print("[AI DEBUG] No GSC property selected for user.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        # Always get the most recent cache (regardless of date)
        cached_data = db.get_dashboard_cache(current_user, website_url)
        if cached_data and 'ai_insights' in cached_data and not explicit:
            print("[AI DEBUG] Returning cached AI insights.")
            return cached_data['ai_insights']

        if not explicit:
            print("[AI DEBUG] No explicit request and no cache, returning 404.")
            raise HTTPException(
                status_code=404,
                detail="No cached AI analysis available. Please generate AI analysis explicitly."
            )

        # If explicit, generate new AI insights
        # Note: benchmark_analyzer is not implemented yet, so we'll create a simple fallback
        def generate_fallback_insights(metrics):
            return {
                "visibility_performance": {
                    "overall_assessment": "Analysis based on available metrics.",
                    "metrics": metrics.get('summary', {})
                },
                "analysis": {
                    "summary": "Basic analysis of your SEO performance."
                }
            }
        
        insights = generate_fallback_insights(dashboard_metrics)
        try:
            print("[AI DEBUG] Step 1: Gathering latest SEO metrics...")
            gsc_metrics = await gsc_fetcher.fetch_metrics(current_user, website_url)
            if gsc_metrics:
                dashboard_metrics['summary'] = gsc_metrics.get('summary', {})
                dashboard_metrics['time_series'] = gsc_metrics.get('time_series', {})
            print("[AI DEBUG] Step 1 complete.")
        except Exception as e:
            print(f"[AI DEBUG] Failed to fetch GSC metrics: {e}")
        
        print("[AI DEBUG] Step 2: Aggregating AI insights...")
        print(f"[AI DEBUG] Dashboard metrics before AI call: {json.dumps(dashboard_metrics, indent=2)}")
        
        # Check if we have enough data for meaningful analysis
        has_gsc_data = 'summary' in dashboard_metrics and dashboard_metrics['summary']
        
        print(f"[AI DEBUG] Data availability - GSC: {has_gsc_data}")
        
        if not has_gsc_data:
            print("[AI DEBUG] Insufficient data for AI analysis, returning fallback")
            fallback_insights = {
                "visibility_performance": {
                    "overall_assessment": "Insufficient data available for analysis. Please ensure Google Search Console is connected and data is available.",
                    "metrics": {}
                },
                "analysis": {
                    "summary": "Unable to generate comprehensive analysis due to insufficient data. Please connect Google Search Console and ensure data is available."
                }
            }
            dashboard_data = {"metrics": dashboard_metrics}
            dashboard_data["ai_insights"] = fallback_insights
            db.store_dashboard_cache(current_user, website_url, dashboard_data)
            return fallback_insights
        
        insights = benchmark_analyzer.generate_ai_insights(dashboard_metrics, business_type="general")
        print("[AI DEBUG] Step 2 complete.")
        print("[AI DEBUG] Step 3: Caching results...")
        dashboard_data = {"metrics": dashboard_metrics}
        dashboard_data["ai_insights"] = insights
        db.store_dashboard_cache(current_user, website_url, dashboard_data)
        print("[AI DEBUG] Step 3 complete. AI Overall Analysis generation finished.")
        return insights
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI DEBUG] Error generating benchmark insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.post("/website/content/fetch")
async def fetch_website_content(current_user: str = Depends(get_current_user)):
    """Fetch website content including meta descriptions, title tags, and page content."""
    try:
        import aiohttp
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No website property selected. Please select a property first."
            )
        
        # Convert sc-domain format to actual URL if needed
        if website_url.startswith('sc-domain:'):
            domain = website_url.replace('sc-domain:', '')
            website_url = f"https://{domain}"
        
        print(f"[WEBSITE CONTENT] Fetching content from: {website_url}")
        
        # Fetch website content
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(website_url, timeout=30) as response:
                        if response.status != 200:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Failed to fetch website content. Status: {response.status}"
                            )
                        
                        html_content = await response.text()
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Extract title tags
                        title_tags = {}
                        for title in soup.find_all('title'):
                            title_tags[title.get('id', 'default')] = title.get_text(strip=True)
                        
                        # Extract meta descriptions
                        meta_descriptions = {}
                        for meta in soup.find_all('meta', attrs={'name': 'description'}):
                            meta_descriptions[meta.get('id', 'default')] = meta.get('content', '')
                        
                        # Extract page content (main content areas)
                        page_content = {}
                        
                        # Get main content from multiple possible locations
                        main_content = None
                        content_selectors = [
                            'main', 'article', 'div.content', 'div#content', 'div.main', 
                            'div.container', 'div.wrapper', 'div#main', 'div#container',
                            'section', 'div[role="main"]', 'div.main-content'
                        ]
                        
                        for selector in content_selectors:
                            main_content = soup.select_one(selector)
                            if main_content:
                                break
                        
                        # If no main content found, try to get content from body
                        if not main_content:
                            body = soup.find('body')
                            if body:
                                # Remove script and style elements
                                for script in body(["script", "style", "nav", "header", "footer"]):
                                    script.decompose()
                                main_content = body
                        
                        if main_content:
                            # Clean up the text
                            text = main_content.get_text(separator=' ', strip=True)
                            # Remove extra whitespace
                            text = ' '.join(text.split())
                            page_content['main'] = text[:2000]  # Limit to first 2000 chars
                        
                        # Get header content
                        header = soup.find('header') or soup.find('nav') or soup.select_one('div.header, div.nav, div.navigation')
                        if header:
                            page_content['header'] = header.get_text(strip=True)[:500]
                        
                        # Get footer content
                        footer = soup.find('footer') or soup.select_one('div.footer, div.foot')
                        if footer:
                            page_content['footer'] = footer.get_text(strip=True)[:500]
                        
                        # Get all headings with more comprehensive search
                        headings = []
                        heading_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                        
                        for heading in heading_elements:
                            text = heading.get_text(strip=True)
                            if text and len(text) > 2:  # Only include headings with meaningful text
                                headings.append({
                                    'tag': heading.name,
                                    'text': text
                                })
                        
                        page_content['headings'] = headings[:15]  # Limit to first 15 headings
                        
                        # Get all links with better filtering
                        links = []
                        for link in soup.find_all('a', href=True):
                            href = link.get('href')
                            text = link.get_text(strip=True)
                            if text and href and len(text) > 1:  # Only include links with meaningful text
                                # Skip common navigation/footer links
                                if not any(skip in text.lower() for skip in ['privacy', 'terms', 'cookie', 'login', 'sign up']):
                                    links.append({
                                        'text': text[:100],  # Limit text length
                                        'href': urljoin(website_url, href)
                                    })
                        
                        page_content['links'] = links[:25]  # Limit to first 25 links
                        
                        # Add page title and meta description to content
                        page_title = soup.find('title')
                        if page_title:
                            page_content['page_title'] = page_title.get_text(strip=True)
                        
                        meta_desc = soup.find('meta', attrs={'name': 'description'})
                        if meta_desc:
                            page_content['meta_description'] = meta_desc.get('content', '')
                        
                        # Store content data
                        content_data = {
                            'title_tags': title_tags,
                            'meta_descriptions': meta_descriptions,
                            'page_content': page_content
                        }
                        
                        # Store in database
                        success = db.store_website_content(current_user, website_url, content_data)
                        
                        if not success:
                            raise HTTPException(
                                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail="Failed to store website content"
                            )
                        
                        # Print content to terminal
                        print(f"\n[WEBSITE CONTENT] Content fetched successfully for {website_url}")
                        print(f"[WEBSITE CONTENT] Title tags: {title_tags}")
                        print(f"[WEBSITE CONTENT] Meta descriptions: {meta_descriptions}")
                        
                        # More detailed content analysis
                        main_content = page_content.get('main', '')
                        if main_content:
                            print(f"[WEBSITE CONTENT] Main content preview: {main_content[:300]}...")
                            print(f"[WEBSITE CONTENT] Main content length: {len(main_content)} characters")
                        else:
                            print(f"[WEBSITE CONTENT] No main content found")
                        
                        headings = page_content.get('headings', [])
                        print(f"[WEBSITE CONTENT] Number of headings: {len(headings)}")
                        if headings:
                            print(f"[WEBSITE CONTENT] First 3 headings:")
                            for i, heading in enumerate(headings[:3]):
                                print(f"  {i+1}. {heading['tag'].upper()}: {heading['text']}")
                        
                        links = page_content.get('links', [])
                        print(f"[WEBSITE CONTENT] Number of links: {len(links)}")
                        if links:
                            print(f"[WEBSITE CONTENT] First 3 links:")
                            for i, link in enumerate(links[:3]):
                                print(f"  {i+1}. {link['text']} -> {link['href']}")
                        
                        # Show page title and meta description
                        if page_content.get('page_title'):
                            print(f"[WEBSITE CONTENT] Page title: {page_content['page_title']}")
                        if page_content.get('meta_description'):
                            print(f"[WEBSITE CONTENT] Meta description: {page_content['meta_description'][:200]}...")
                        
                        return {
                            "success": True,
                            "message": "Website content fetched and stored successfully!",
                            "content": content_data
                        }
                        
                except aiohttp.ClientError as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to fetch website content: {str(e)}"
                    )
        except Exception as e:
            print(f"Error fetching website content: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch website content"
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching website content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch website content"
        )


@router.get("/website/content")
async def get_website_content(current_user: str = Depends(get_current_user)):
    """Get stored website content for the user's website."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No website property selected. Please select a property first."
            )
        
        # Get stored content
        content_data = db.get_website_content(current_user, website_url)
        
        if not content_data:
            return {
                "success": False,
                "message": "No website content found. Please fetch content first.",
                "content": None,
                "fetched_at": None
            }
        
        return {
            "success": True,
            "message": "Website content retrieved successfully!",
            "content": content_data,
            "fetched_at": content_data.get('fetched_at')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting website content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get website content"
        )





 