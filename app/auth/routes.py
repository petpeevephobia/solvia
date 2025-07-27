"""
Google OAuth routes for Solvia.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from app.auth.models import (
    UserResponse, TokenResponse, GoogleAuthRequest, GoogleCallbackRequest
)
from app.auth.utils import create_access_token, verify_token
from app.database.supabase_db import SupabaseAuthDB
from app.config import settings
from app.auth.google_oauth import GoogleOAuthHandler
import uuid
import time

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize database and Google OAuth handler
db = SupabaseAuthDB()
google_oauth = GoogleOAuthHandler(db)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token."""
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user)):
    """Logout user and deactivate session."""
    try:
        # Deactivate user session in database
        await db.deactivate_session(current_user)
        
        return {
            "message": "Successfully logged out",
            "success": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )


@router.get("/me")
async def get_current_user(current_user: str = Depends(get_current_user)):
    """Get current user information from session."""
    try:
        # Get user session from database using email from JWT
        user_session = await db.get_user_session(current_user)
        
        if user_session:
            # Update last login timestamp
            await db.update_last_login(current_user)
        
            return {
                "email": user_session.get("email"),
                "name": user_session.get("name"),
                "picture": user_session.get("picture"),
                "last_login": user_session.get("last_login")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User session not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


# Google OAuth routes
@router.get("/google/authorize")
async def google_authorize(request: Request):
    """Generate Google OAuth authorization URL."""
    try:
        # Generate OAuth URL without requiring authentication first
        auth_url = google_oauth.get_auth_url(state="user_email")
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None
):
    """Handle Google OAuth callback."""
    
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
        # Handle the OAuth callback
        result = await google_oauth.handle_callback(code, "user_email")
        
        if result.get("success"):
            # Get user info from the result
            user_info = result.get("user_info", {})
            
            # Use a session-based email since we don't have userinfo scope
            user_email = f"user_{int(time.time())}@solvia.com"
            
            # Store user session in database
            await db.store_user_session(user_email, user_info)
            
            # Create a JWT token for the user
            jwt_token = create_access_token(
                data={"sub": user_email}, 
                expires_delta=timedelta(minutes=30)
            )
            
            # Redirect to dashboard page with the JWT token
            dashboard_url = f"/dashboard?access_token={jwt_token}"
            return RedirectResponse(url=dashboard_url, status_code=302)
        else:
            error_msg = result.get("error", "Unknown error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to complete OAuth process: {error_msg}"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete OAuth process"
        )


@router.get("/google/callback/test")
async def google_callback_test():
    """Test endpoint to verify callback route is accessible."""
    return {"message": "Google callback route is working!"}

 