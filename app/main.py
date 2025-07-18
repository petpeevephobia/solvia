"""
Main FastAPI application for Solvia authentication system.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add project root to the Python path
# This is the directory that contains `app` and `core`
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))   

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from .auth.routes import router as auth_router, get_current_user
from .config import settings
from .database import db

# Import the analysis components
# from core.modules.business_analysis import BusinessAnalyzer


from dotenv import load_dotenv
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Solvia Authentication API - SEO on AI Autopilot",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create static directory if it doesn't exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Mount static files
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include auth routes
app.include_router(auth_router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Solvia Authentication API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "ui": "/ui",
        "dashboard": "/dashboard"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "solvia-auth"
    }

@app.get("/ui")
def serve_ui():
    return FileResponse("app/static/index.html")

@app.get("/dashboard")
async def serve_dashboard():
    """Serve the dashboard UI."""
    dashboard_file = os.path.join(static_dir, "dashboard.html")
    if os.path.exists(dashboard_file):
        return FileResponse(dashboard_file)
    else:
        return {
            "error": "Dashboard not found",
            "message": "Please ensure the dashboard files are in the static directory"
        }



@app.get("/setup")
async def serve_setup_wizard():
    """Serve the setup wizard UI."""
    setup_file = os.path.join(static_dir, "setup_wizard.html")
    if os.path.exists(setup_file):
        return FileResponse(setup_file)
    else:
        return {
            "error": "Setup wizard not found",
            "message": "Please ensure the setup wizard files are in the static directory"
        }

@app.get("/property-selection")
async def serve_property_selection(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    request: Request = None
):
    """Serve the property selection UI and handle OAuth callbacks."""
    
    # If this is an OAuth callback (has code parameter), handle it
    if code and state:
        
        if error:
            return FileResponse(os.path.join(static_dir, "property_selection.html"))
        
        try:
            # Import the Google OAuth handler
            from app.auth.google_oauth import GoogleOAuthHandler
            from app.database.supabase_db import SupabaseAuthDB
            
            # Initialize OAuth handler
            db = SupabaseAuthDB()
            google_oauth = GoogleOAuthHandler(db)
            
            # The state parameter contains the user's email
            user_email = state
            
            if not user_email:
                return FileResponse(os.path.join(static_dir, "property_selection.html"))
            
            # Handle the OAuth callback without JWT token (we'll store credentials using email)
            result = await google_oauth.handle_callback(code, user_email, jwt_token=None)
            
            # Serve the property selection page
            property_file = os.path.join(static_dir, "property_selection.html")
            if os.path.exists(property_file):
                return FileResponse(property_file)
            else:
                return {
                    "error": "Property selection page not found",
                    "message": "Please ensure the property selection files are in the static directory"
                }
                
        except Exception as e:
            # Still serve the page even if OAuth fails
            property_file = os.path.join(static_dir, "property_selection.html")
            if os.path.exists(property_file):
                return FileResponse(property_file)
            else:
                return {
                    "error": "Property selection page not found",
                    "message": "Please ensure the property selection files are in the static directory"
                }
    
    # Regular property selection page request (no OAuth callback)
    property_file = os.path.join(static_dir, "property_selection.html")
    if os.path.exists(property_file):
        return FileResponse(property_file)
    else:
        return {
            "error": "Property selection page not found",
            "message": "Please ensure the property selection files are in the static directory"
        }







@app.get("/api/health")
async def api_health():
    """API health check."""
    return {
        "status": "healthy",
        "service": "solvia-auth-api",
        "version": settings.APP_VERSION
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.get("/login")
def serve_login():
    return FileResponse("app/static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    ) 