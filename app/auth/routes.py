"""
Authentication routes for Solvia.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
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
from app.database import db
from app.config import settings
from app.auth.google_oauth import GoogleOAuthHandler, GSCDataFetcher, pagespeed_fetcher, mobile_fetcher, IndexingCrawlabilityFetcher, business_fetcher
import uuid

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

class KeywordMetricsResponse(BaseModel):
    total_keywords: int
    avg_position: float
    opportunities: int
    branded_keywords: int
    top_keywords: str
    keyword_insights: str
    last_updated: str

class DashboardDataResponse(BaseModel):
    user: Optional[UserResponse]

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# Initialize Google OAuth handler
google_oauth = GoogleOAuthHandler()
gsc_fetcher = GSCDataFetcher(google_oauth)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token."""
    from app.auth.utils import verify_token
    
    token = credentials.credentials
    print(f"[DEBUG] get_current_user called with token: {token[:20] if token else 'None'}...")
    
    email = verify_token(token)
    print(f"[DEBUG] Token verification result - email: {email}")
    
    if email is None:
        print(f"[DEBUG] Token validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """Register a new user."""
    # Validate password strength
    if not is_strong_password(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long and contain uppercase, lowercase, and digit"
        )
    
    # Check if user already exists
    existing_user = db.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Hash password and create user
    password_hash = get_password_hash(user.password)
    verification_token = generate_verification_token()
    
    success = db.create_user(user, password_hash, verification_token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    # Send verification email
    send_verification_email(user.email, verification_token)

    # Generate a user ID (since we don't store it in the current DB structure)
    user_id = str(uuid.uuid4())
    
    return UserResponse(
        id=user_id,
        email=user.email,
        message="User registered successfully. Please check your email to verify your account.",
        created_at=datetime.utcnow().isoformat()
    )


@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin):
    """Login user and return access token."""
    # Get user from database
    user = db.get_user_by_email(user_credentials.email)
    print(f"[DEBUG] User from DB: {user}")
    print(f"[DEBUG] Password to check: {user_credentials.password}")
    if user:
        print(f"[DEBUG] Stored hash: {user.password_hash}")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    is_valid = verify_password(user_credentials.password, user.password_hash)
    print(f"[DEBUG] Password valid: {is_valid}")
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email before logging in"
        )
    
    # Update last login
    db.update_last_login(user.email)
    
    # Create access token
    access_token_expires = timedelta(minutes=30)  # 30 minutes
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=access_token_expires.total_seconds()
    )


@router.post("/verify-email")
async def verify_email(verification: EmailVerification):
    """Verify user email with token."""
    # Find user with this verification token
    # Note: This is a simplified implementation
    # In production, you'd want to store tokens with expiration
    
    # For now, we'll need to search through users
    # This is not efficient for production - consider using a separate tokens sheet
    
    # TODO: Implement proper token verification
    # For now, return a placeholder response
    return {"message": "Email verification endpoint - implementation needed"}


@router.post("/forgot-password")
async def forgot_password(reset_request: PasswordReset):
    """Send password reset email."""
    user = db.get_user_by_email(reset_request.email)
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = generate_reset_token()
    success = db.set_reset_token(user.email, reset_token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process reset request"
        )
    
    # TODO: Send reset email
    return {
        "message": "If the email exists, a reset link has been sent",
        "reset_token": reset_token  # Remove this in production
    }


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
    # For now, return a placeholder response
    return {"message": "Password reset endpoint - implementation needed"}


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
        # Create a new access token
        access_token_expires = timedelta(minutes=30)
        new_access_token = create_access_token(data={"sub": current_user}, expires_delta=access_token_expires)
        
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
    print("[TOKEN DEBUG] /refresh-token endpoint called")
    
    try:
        # Get the token from the Authorization header
        auth_header = request.headers.get('Authorization')
        print(f"[TOKEN DEBUG] Authorization header: {auth_header[:30] if auth_header else 'None'}...")
        
        if not auth_header or not auth_header.startswith('Bearer '):
            print("[TOKEN DEBUG] Invalid authorization header format")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = auth_header.split(' ')[1]
        print(f"[TOKEN DEBUG] Extracted token: {token[:20]}...")
        
        # Manually verify the token (even if expired)
        from app.auth.utils import verify_token
        email = verify_token(token)
        print(f"[TOKEN DEBUG] verify_token result: {email}")
        
        if not email:
            print("[TOKEN DEBUG] Token verification failed, trying unverified decode...")
            # Try to decode the token manually to get the email even if expired
            try:
                from jose import jwt
                from app.config import settings
                # Decode without verification to get payload - jose requires a key parameter
                payload = jwt.decode(token, key="", options={"verify_signature": False})
                print(f"[TOKEN DEBUG] Unverified payload: {payload}")
                email = payload.get("sub")
                if not email:
                    print("[TOKEN DEBUG] No 'sub' field in unverified payload")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token"
                    )
                print(f"[TOKEN DEBUG] Extracted email from unverified payload: {email}")
            except Exception as e:
                print(f"[TOKEN DEBUG] Failed to decode unverified payload: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
        
        print(f"[TOKEN DEBUG] Final email for refresh: {email}")
        
        # Verify user exists
        user = db.get_user_by_email(email)
        print(f"[TOKEN DEBUG] User lookup result: {user is not None}")
        if not user:
            print(f"[TOKEN DEBUG] User not found in database: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create a new access token
        access_token_expires = timedelta(minutes=30)
        new_access_token = create_access_token(data={"sub": email}, expires_delta=access_token_expires)
        print(f"[TOKEN DEBUG] New token created: {new_access_token[:20]}...")
        
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=access_token_expires.total_seconds()
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[TOKEN DEBUG] Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: str = Depends(get_current_user)):
    """Get current user profile."""
    user = db.get_user_by_email(current_user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate a user ID (since we don't store it in the current DB structure)
    user_id = str(uuid.uuid4())
    
    return UserResponse(
        id=user_id,
        email=user.email,
        is_verified=user.is_verified,
        created_at=user.created_at if user.created_at else None
    )


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
        user = db.get_user_by_email(current_user)
        
        # Convert user data to response model if exists
        user_response = None
        if user:
            user_response = UserResponse(
                id=user.id,
                email=user.email,
                is_verified=user.is_verified,
                created_at=user.created_at
            )
        
        return DashboardDataResponse(
            user=user_response
        )
        
    except Exception as e:
        print(f"Error getting dashboard data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Google OAuth and Search Console Integration
@router.get("/google/authorize")
async def google_authorize(current_user: str = Depends(get_current_user)):
    """Generate Google OAuth authorization URL."""
    try:
        # The user's email is passed as the 'state' parameter to identify
        # the user upon callback.
        print(f"[DEBUG] /google/authorize called for user: '{current_user}'")
        auth_url = google_oauth.get_auth_url(state=current_user)
        
        return {
            "auth_url": auth_url,
            "message": "Redirect user to this URL to authorize Google Search Console access"
        }
    except Exception as e:
        print(f"Error generating Google auth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None
):
    """Handle Google OAuth callback and store credentials."""
    try:
        print(f"[DEBUG] Google callback received - code: {code[:20]}..., state from URL: '{state}', error: {error}")
        
        if error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google OAuth error: {error}"
            )
        
        # The state parameter MUST contain the user's email.
        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing state parameter with user information"
            )
        
        user_email = state
        
        # Handle OAuth callback
        result = await google_oauth.handle_callback(code, user_email)
        
        print(f"[DEBUG] OAuth callback result: {result}")
        
        # Redirect to setup wizard
        if result.get("success"):
            return RedirectResponse(url=f"/setup?oauth_success=true&user={user_email}")
        else:
            return RedirectResponse(url=f"/setup?oauth_error=true&user={user_email}")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error handling Google callback: {e}")
        return RedirectResponse(url="/setup?oauth_error=true")


@router.get("/google/callback/test")
async def google_callback_test():
    """Test endpoint to verify callback route is accessible."""
    return {"message": "Google callback route is working!"}


@router.get("/gsc/properties", response_model=list[GSCPropertyResponse])
async def get_gsc_properties(current_user: str = Depends(get_current_user)):
    """Get user's Google Search Console properties."""
    try:
        print(f"[DEBUG] get_gsc_properties called for user: {current_user}")
        
        # Get GSC properties
        properties = await google_oauth.get_gsc_properties(current_user)
        
        print(f"[DEBUG] Retrieved properties: {properties}")
        
        if not properties:
            print(f"[DEBUG] No properties found for user: {current_user}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Google Search Console properties found. Please make sure you have verified websites in GSC."
            )
        
        return properties
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching GSC properties: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch Google Search Console properties"
        )


@router.post("/gsc/select-property")
async def select_gsc_property(
    property_data: GSCPropertySelectRequest,
    current_user: str = Depends(get_current_user)
):
    """Select a GSC property and start collecting SEO data."""
    try:
        # Add website to user's profile
        website_url = property_data.property_url
        success = db.add_user_website(current_user, website_url)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to add website to profile"
            )
        
        # Fetch initial SEO metrics
        metrics = await gsc_fetcher.fetch_metrics(current_user, website_url)
        
        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch SEO metrics. Please ensure your website has data in Google Search Console."
            )
        
        return {
            "success": True,
            "message": "Website selected and SEO data collected successfully!",
            "website_url": website_url,
            "metrics": metrics
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error selecting GSC property: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to select property and collect data"
        )


@router.get("/gsc/metrics", response_model=GSCMetricsResponse)
async def get_gsc_metrics(current_user: str = Depends(get_current_user)):
    """Fetch GSC metrics for the selected property."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        print(f"[INFO] Loading GSC metrics for user '{current_user}' and property '{website_url}'")
        metrics = await gsc_fetcher.fetch_metrics(current_user, website_url)
        if not metrics or "summary" not in metrics:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch GSC metrics or data is empty."
            )
        summary = metrics.get('summary', {})
        print(f"[INFO] Visibility Performance: Impressions={summary.get('total_impressions')}, Clicks={summary.get('total_clicks')}, CTR={summary.get('avg_ctr')}, Avg Position={summary.get('avg_position')}")
        print(f"[INFO] Organic Traffic Trends: {metrics.get('time_series', {}).get('clicks', [])}")
        print(f"[INFO] Impressions Trends: {metrics.get('time_series', {}).get('impressions', [])}")
        return GSCMetricsResponse(
            summary=metrics.get('summary', {}),
            time_series=metrics.get('time_series', {}),
            last_updated=datetime.utcnow().isoformat(),
            website_url=website_url,
            start_date=metrics.get('start_date'),
            end_date=metrics.get('end_date')
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
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


@router.get("/pagespeed/metrics")
async def get_pagespeed_metrics(current_user: str = Depends(get_current_user)):
    """Fetch PageSpeed Insights data for the user's website."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        print(f"[DEBUG] Fetching PageSpeed data for user '{current_user}' and property '{website_url}'")
        
        # Fetch PageSpeed data
        psi_data = await pagespeed_fetcher.fetch_pagespeed_data(website_url)
        
        if not psi_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch PageSpeed data."
            )

        return psi_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching PageSpeed metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.get("/mobile/metrics")
async def get_mobile_metrics(current_user: str = Depends(get_current_user)):
    """Fetch mobile usability data for the user's website."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        print(f"[DEBUG] Fetching mobile data for user '{current_user}' and property '{website_url}'")
        
        # Fetch mobile data
        mobile_data = await mobile_fetcher.fetch_mobile_data(website_url)
        
        if not mobile_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch mobile data."
            )

        return mobile_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching mobile metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.get("/indexing/metrics")
async def get_indexing_metrics(current_user: str = Depends(get_current_user)):
    """Fetch indexing and crawlability data for the user's website."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        print(f"[DEBUG] Fetching indexing data for user '{current_user}' and property '{website_url}'")
        
        # Get user's GSC credentials
        credentials = google_oauth.get_credentials(current_user)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GSC credentials not found. Please authenticate with Google Search Console first."
            )
        
        # Create indexing fetcher and fetch data
        indexing_fetcher = IndexingCrawlabilityFetcher(credentials)
        indexing_data = indexing_fetcher.fetch_indexing_data(website_url)
        
        if not indexing_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch indexing data."
            )

        return indexing_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching indexing metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.get("/business/metrics")
async def get_business_metrics(current_user: str = Depends(get_current_user)):
    """Fetch business context and intelligence data for the user's website."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        print(f"[DEBUG] Fetching business context data for user '{current_user}' and property '{website_url}'")
        
        # Fetch business context data
        business_data = await business_fetcher.fetch_business_data(website_url)
        
        if not business_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch business context data."
            )

        return business_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching business metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )


@router.get("/keyword/metrics", response_model=KeywordMetricsResponse)
async def get_keyword_metrics(current_user: str = Depends(get_current_user)):
    """Fetch keyword performance data for the user's website."""
    try:
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )
        keyword_data = await gsc_fetcher.fetch_keyword_data(current_user, website_url)
        if not keyword_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch keyword data."
            )
        print(f"[INFO] Keyword Trends: Total={keyword_data.get('total_keywords')}, Avg Position={keyword_data.get('avg_position')}, Opportunities={keyword_data.get('opportunities')}, Branded={keyword_data.get('branded_keywords')}")
        return KeywordMetricsResponse(
            total_keywords=keyword_data.get('total_keywords', 0),
            avg_position=keyword_data.get('avg_position', 0.0),
            opportunities=keyword_data.get('opportunities', 0),
            branded_keywords=keyword_data.get('branded_keywords', 0),
            top_keywords=keyword_data.get('top_keywords', ""),
            keyword_insights=keyword_data.get('keyword_insights', ""),
            last_updated=datetime.utcnow().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        ) 