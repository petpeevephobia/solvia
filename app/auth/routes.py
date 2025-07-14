"""
Authentication routes for Solvia.
"""
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
from app.auth.google_oauth import GoogleOAuthHandler, GSCDataFetcher, PageSpeedInsightsFetcher
import uuid
import json
from app.database.supabase_db import SupabaseAuthDB

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
pagespeed_fetcher = PageSpeedInsightsFetcher(db)

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
    
    # TODO: Implement proper token verification
    # For now, return a placeholder response
    return {"message": "Email verification endpoint - implementation needed"}


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
async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user information from Supabase Auth using access token."""
    access_token = credentials.credentials
    user_info = db.get_user(access_token)
    user_obj = user_info.get("user") if user_info else None
    if not user_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    # Convert user_obj to dict if needed
    if hasattr(user_obj, '__dict__'):
        user = user_obj.__dict__
    else:
        user = user_obj
    return UserResponse(
        id=user.get("id", str(uuid.uuid4())),
        email=user.get("email", ""),
        message="User information retrieved successfully",
        created_at=user.get("created_at", datetime.utcnow().isoformat())
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
async def google_authorize(request: Request):
    """Generate Google OAuth authorization URL."""
    try:
        # Try to get the current user, redirect to login if not authenticated
        credentials = request.headers.get("authorization")
        if not credentials or not credentials.lower().startswith("bearer "):
            return RedirectResponse(url="/ui", status_code=302)
        token = credentials.split(" ", 1)[1]
        from app.auth.utils import verify_token
        email = verify_token(token)
        if not email:
            return RedirectResponse(url="/ui", status_code=302)
        auth_url = google_oauth.get_auth_url(state=email)
        return {"auth_url": auth_url}
    except Exception as e:
        print(f"Error generating auth URL: {e}")
        return RedirectResponse(url="/ui", status_code=302)


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
        # The state parameter contains the user's email
        user_email = state
        
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User email not found in state parameter"
            )
        
        # Get JWT from Authorization header
        jwt_token = None
        if request:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                jwt_token = auth_header.split(" ", 1)[1]
        
        result = await google_oauth.handle_callback(code, user_email, jwt_token=jwt_token)
        
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


@router.get("/gsc/properties", response_model=list[GSCPropertyResponse])
async def get_gsc_properties(current_user: str = Depends(get_current_user)):
    """Get user's Google Search Console properties."""
    
    try:
        # Get GSC properties
        properties = await google_oauth.get_gsc_properties(current_user)
        
        if not properties:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Google Search Console properties found. Please make sure you have verified websites in GSC."
            )
        
        return properties
        
    except HTTPException:
        raise
    except Exception as e:
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

        metrics = await gsc_fetcher.fetch_metrics(current_user, website_url)
        if not metrics or "summary" not in metrics:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch GSC metrics or data is empty."
            )
        summary = metrics.get('summary', {})
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
async def cache_dashboard_data(request: Request, dashboard_data: dict, ai_insights: dict = None, current_user: str = Depends(get_current_user)):
    email = current_user
    user_jwt = request.headers.get("authorization", "").replace("Bearer ", "")
    db = SupabaseAuthDB(access_token=user_jwt)
    website_url = db.get_selected_gsc_property(email)
    if not website_url:
        return {"success": False, "message": "No website property selected for user."}
    # Optionally merge ai_insights into dashboard_data if provided
    if ai_insights:
        dashboard_data["ai_insights"] = ai_insights
    success = db.store_dashboard_cache(email, website_url, dashboard_data)
    if success:
        return {"success": True, "message": "Dashboard data cached successfully!"}
    else:
        return {"success": False, "message": "Failed to cache dashboard data"}


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


@router.get("/metadata/analysis")
async def get_metadata_analysis(current_user: str = Depends(get_current_user)):
    """Fetch metadata and image alt text analysis for the user's website."""
    try:
        # Get the selected property for the user
        website_url = db.get_selected_gsc_property(current_user)
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GSC property selected. Please select a property first."
            )

        from .metadata_analyzer import MetadataAnalyzer
        analyzer = MetadataAnalyzer()
        
        # Analyze the website
        analysis_result = await analyzer.analyze_website(website_url)
        
        if not analysis_result:
            # Fallback to demo data if analysis fails
            return {
                "meta_titles_optimized": 0,
                "meta_titles_total": 0,
                "meta_descriptions_optimized": 0,
                "meta_descriptions_total": 0,
                "image_alt_text_optimized": 0,
                "image_alt_text_total": 0,
                "h1_tags_optimized": 0,
                "h1_tags_total": 0,
                "meta_titles": 0,
                "meta_descriptions": 0,
                "image_alt_text": 0,
                "h1_tags": 0,
                "insights": ["Metadata analysis is currently unavailable. Please try again later."]
            }
        
        return analysis_result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching metadata analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
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
        from .benchmark_analyzer import benchmark_analyzer
        dashboard_metrics = {}
        try:
            print("[AI DEBUG] Step 1: Gathering latest SEO metrics...")
            gsc_metrics = await gsc_fetcher.fetch_metrics(current_user, website_url)
            if gsc_metrics:
                dashboard_metrics['summary'] = gsc_metrics.get('summary', {})
                dashboard_metrics['time_series'] = gsc_metrics.get('time_series', {})
            print("[AI DEBUG] Step 1 complete.")
        except Exception as e:
            print(f"[AI DEBUG] Failed to fetch GSC metrics: {e}")
        try:
            print("[AI DEBUG] Step 2: Analyzing site metadata and content...")
            from .metadata_analyzer import MetadataAnalyzer
            metadata_analyzer = MetadataAnalyzer()
            metadata_result = await metadata_analyzer.analyze_website(website_url)
            if metadata_result:
                dashboard_metrics['metadata'] = {
                    'meta_titles': metadata_result.get('meta_titles', 0),
                    'meta_descriptions': metadata_result.get('meta_descriptions', 0),
                    'image_alt_text': metadata_result.get('image_alt_text', 0),
                    'h1_tags': metadata_result.get('h1_tags', 0)
                }
            print("[AI DEBUG] Step 2 complete.")
        except Exception as e:
            print(f"[AI DEBUG] Failed to fetch metadata metrics: {e}")
        try:
            print("[AI DEBUG] Step 3: Evaluating engagement & UX signals...")
            psi_data = await pagespeed_fetcher.fetch_pagespeed_data(website_url)
            if psi_data:
                dashboard_metrics['ux'] = {
                    'performance_score': psi_data.get('performance_score', 0),
                    'lcp': psi_data.get('lcp', {}).get('value', 0),
                    'fcp': psi_data.get('fcp', {}).get('value', 0),
                    'cls': psi_data.get('cls', {}).get('value', 0)
                }
            print("[AI DEBUG] Step 3 complete.")
        except Exception as e:
            print(f"[AI DEBUG] Failed to fetch PageSpeed metrics: {e}")
        print("[AI DEBUG] Step 4: Aggregating AI insights...")
        insights = benchmark_analyzer.generate_ai_insights(dashboard_metrics, business_type="general")
        print("[AI DEBUG] Step 4 complete.")
        print("[AI DEBUG] Step 5: Summarizing recommendations and caching results...")
        dashboard_data = {"metrics": dashboard_metrics}
        dashboard_data["ai_insights"] = insights
        db.store_dashboard_cache(current_user, website_url, dashboard_data)
        print("[AI DEBUG] Step 5 complete. AI Overall Analysis generation finished.")
        return insights
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AI DEBUG] Error generating benchmark insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )





 