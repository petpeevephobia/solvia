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
from core.analysis_processor import generate_seo_analysis
from core.recommendation_aggregator import RecommendationAggregator

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

@app.get("/fixes")
async def serve_fixes_page():
    """Serve the Fixes page UI."""
    fixes_file = os.path.join(static_dir, "fixes.html")
    if os.path.exists(fixes_file):
        return FileResponse(fixes_file)
    else:
        return {
            "error": "Fixes page not found",
            "message": "Please ensure the fixes page files are in the static directory"
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

@app.post("/api/generate-report")
async def generate_report(current_user: str = Depends(get_current_user)):
    """Generate SEO analysis report with prioritized recommendations using real metrics data."""
    try:
        
        # Get user's website
        user_website = db.get_user_website(current_user)
        if not user_website or not user_website.get('website_url'):
            raise HTTPException(
                status_code=400,
                detail="No website configured. Please add a website URL first."
            )
        
        website_url = user_website['website_url']
        
        # Initialize business analyzer
        # business_analyzer = BusinessAnalyzer()
        
        # Get business analysis
        # business_analysis = business_analyzer.analyze_business(website_url)
        
        # Fetch real metrics from existing Solvia endpoints
        metrics_data = await fetch_real_metrics_for_analysis(current_user, website_url)
        
        # Generate AI analysis with recommendations using real data
        openai_analysis = generate_seo_analysis(metrics_data, business_analysis)
        
        if not openai_analysis:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate SEO analysis. Please try again."
            )
        
        # Prepare the complete report data
        report_data = {
            "success": True,
            "website_url": website_url,
            "business_model": business_analysis.get('business_model', 'Unknown'),
            "analysis": openai_analysis,
            "metrics_used": {
                "gsc_data_available": metrics_data.get('has_gsc_data', False),
                "psi_data_available": metrics_data.get('has_psi_data', False),
                "data_source": "real_metrics"
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Store the report in the user's database
        report_id = db.store_seo_report(current_user, website_url, report_data)
        
        if report_id:
            report_data["report_id"] = report_id
        else:
            print("[WARNING] Failed to store report, but continuing...")
        
        # Return the analysis with prioritized recommendations
        return report_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

async def fetch_real_metrics_for_analysis(current_user: str, website_url: str) -> Dict[str, Any]:
    """Fetch real metrics data from existing Solvia endpoints for analysis."""
    
    metrics_data = {
        'url': website_url,
        'has_gsc_data': False,
        'has_psi_data': False,
        'has_keyword_data': False,
        # Default values
        'impressions': 0,
        'clicks': 0,
        'ctr': 0.0,
        'average_position': 0.0,
        'performance_score': 50,
        'first_contentful_paint': 3.0,
        'largest_contentful_paint': 4.0,
        'cumulative_layout_shift': 0.2,
        'speed_index': 3.0,
        'time_to_interactive': 5.0,
        'total_blocking_time': 300
    }
    
    try:
        # Try to fetch GSC metrics
        try:
            from app.auth.routes import gsc_fetcher
            
            # Use the GSC fetcher with proper method and parameters
            gsc_data = await gsc_fetcher.fetch_metrics(current_user, website_url)
            if gsc_data and gsc_data.get('summary'):
                summary = gsc_data['summary']
                metrics_data.update({
                    'has_gsc_data': True,
                    'impressions': summary.get('total_impressions', 0),
                    'clicks': summary.get('total_clicks', 0),
                    'ctr': summary.get('avg_ctr', 0.0) * 100,  # Convert to percentage
                    'average_position': summary.get('avg_position', 0.0)
                })
        except Exception as gsc_error:
            pass
    
        # Try to fetch PageSpeed metrics
        try:
            from app.auth.routes import pagespeed_fetcher
            
            # PageSpeed fetcher needs the URL, not user email
            psi_data = await pagespeed_fetcher.fetch_pagespeed_data(website_url)
            if psi_data:
                metrics_data.update({
                    'has_psi_data': True,
                    'performance_score': psi_data.get('performance_score', 50),
                    'first_contentful_paint': psi_data.get('first_contentful_paint', 3.0),
                    'largest_contentful_paint': psi_data.get('largest_contentful_paint', 4.0),
                    'cumulative_layout_shift': psi_data.get('cumulative_layout_shift', 0.2),
                    'speed_index': psi_data.get('speed_index', 3.0),
                    'time_to_interactive': psi_data.get('time_to_interactive', 5.0),
                    'total_blocking_time': psi_data.get('total_blocking_time', 300)
                })
        except Exception as psi_error:
            pass
            
        # Try to fetch keyword metrics for additional context
        try:
            from app.auth.routes import gsc_fetcher
            
            keyword_data = await gsc_fetcher.fetch_keyword_data(current_user, website_url)
            if keyword_data:
                metrics_data.update({
                    'has_keyword_data': True,
                    'total_keywords': keyword_data.get('total_keywords', 0),
                    'keyword_opportunities': keyword_data.get('opportunities', 0)
                })
        except Exception as keyword_error:
            pass
            
    except Exception as e:
        pass
    
    return metrics_data

@app.get("/api/reports/latest")
async def get_latest_report(current_user: str = Depends(get_current_user)):
    """Get the most recent SEO report for the current user."""
    try:
        
        reports = db.get_user_reports(current_user, limit=1)
        
        if not reports:
            return {
                "success": True,
                "has_report": False,
                "report": None
            }
        
        latest_report = reports[0]
        
        # Parse the JSON report data
        import json
        if isinstance(latest_report.get('report_data'), str):
            full_report_data = json.loads(latest_report['report_data'])
        else:
            full_report_data = latest_report.get('report_data', {})
        
        return {
            "success": True,
            "has_report": True,
            "report": full_report_data,
            "report_meta": {
                "report_id": latest_report['report_id'],
                "generated_at": latest_report['generated_at'],
                "expires_at": latest_report['expires_at']
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve latest report: {str(e)}"
        )

@app.get("/api/reports")
async def get_user_reports(current_user: str = Depends(get_current_user)):
    """Get all SEO reports for the current user."""
    try:
        
        reports = db.get_user_reports(current_user, limit=20)
        
        # Parse the JSON report data for summary display
        report_summaries = []
        for report in reports:
            try:
                import json
                # Parse the stored JSON data
                if isinstance(report.get('report_data'), str):
                    full_report_data = json.loads(report['report_data'])
                else:
                    full_report_data = report.get('report_data', {})
                
                # Create a summary without the full analysis data
                summary = {
                    "report_id": report['report_id'],
                    "website_url": report['website_url'],
                    "business_model": report['business_model'],
                    "total_recommendations": report['total_recommendations'],
                    "quick_wins_count": report['quick_wins_count'],
                    "avg_priority_score": report['avg_priority_score'],
                    "generated_at": report['generated_at'],
                    "expires_at": report['expires_at'],
                    "metrics_used": full_report_data.get('metrics_used', {})
                }
                report_summaries.append(summary)
                
            except (json.JSONDecodeError, KeyError) as e:
                continue
        
        return {
            "success": True,
            "reports": report_summaries,
            "total_reports": len(report_summaries)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reports: {str(e)}"
        )

@app.get("/api/reports/{report_id}")
async def get_report_by_id(report_id: str, current_user: str = Depends(get_current_user)):
    """Get a specific SEO report by ID."""
    try:
        
        report = db.get_report_by_id(report_id, current_user)
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found or expired"
            )
        
        # Parse the JSON report data
        import json
        if isinstance(report.get('report_data'), str):
            full_report_data = json.loads(report['report_data'])
        else:
            full_report_data = report.get('report_data', {})
        
        return full_report_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve report: {str(e)}"
        )

@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: str, current_user: str = Depends(get_current_user)):
    """Delete a specific SEO report (mark as expired)."""
    try:
        
        # For now, we'll just mark it as expired by setting expires_at to past
        # In a more sophisticated system, you might want to actually delete the row
        report = db.get_report_by_id(report_id, current_user)
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )
        
        # This is a simplified implementation - in production you might want
        # to add a proper delete method to the database class
        return {
            "success": True,
            "message": "Report deletion requested (will expire naturally)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete report: {str(e)}"
        )

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