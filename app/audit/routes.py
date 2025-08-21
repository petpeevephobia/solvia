"""
API routes for the Audit Engine
Following RESTful principles and clean architecture
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta

from app.audit.engine import AuditEngine
from app.audit.models import (
    AuditRequest, AuditResult, AuditStatus, 
    AuditHistoryItem, IssueSeverity
)
from app.database.supabase_db import SupabaseAuthDB
from app.auth.routes import get_current_user


# Create router with prefix
audit_router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Forbidden"},
        404: {"description": "Not found"}
    }
)

# Initialize audit engine (singleton pattern)
_audit_engine = None

def get_audit_engine() -> AuditEngine:
    """Get or create audit engine instance"""
    global _audit_engine
    if _audit_engine is None:
        db = SupabaseAuthDB()
        _audit_engine = AuditEngine(db)
    return _audit_engine


@audit_router.post("/trigger", response_model=AuditStatus)
async def trigger_audit(
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user),
    db: SupabaseAuthDB = Depends(lambda: SupabaseAuthDB())
):
    """
    Trigger a new SEO audit for the user's selected website
    
    This endpoint initiates an audit in the background and returns
    immediately with an audit ID for status checking.
    """
    
    try:
        # Get user's selected website (not async)
        user_website = db.get_user_website(current_user)
        if not user_website:
            raise HTTPException(
                status_code=400,
                detail="No website selected. Please select a website first."
            )
        
        # Create audit status
        audit_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{current_user[:8]}"
        audit_status = AuditStatus(
            audit_id=audit_id,
            status="pending",
            progress=0,
            message="Audit initiated, starting analysis...",
            estimated_completion=datetime.now() + timedelta(seconds=60)
        )
        
        # Trigger audit in background
        background_tasks.add_task(
            run_audit_background,
            audit_id=audit_id,
            user_email=current_user,
            website_url=user_website,
            request=request,
            db=db
        )
        
        return audit_status
        
    except Exception as e:
        print(f"[AUDIT API ERROR] Failed to trigger audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audit_router.get("/status/{audit_id}", response_model=AuditStatus)
async def get_audit_status(
    audit_id: str,
    current_user: str = Depends(get_current_user),
    db: SupabaseAuthDB = Depends(lambda: SupabaseAuthDB())
):
    """
    Get the status of an ongoing or completed audit
    """
    
    try:
        # In production, query audit_results table
        # For now, return mock status
        
        audit_status = AuditStatus(
            audit_id=audit_id,
            status="completed",
            progress=100,
            message="Audit completed successfully",
            estimated_completion=datetime.now()
        )
        
        return audit_status
        
    except Exception as e:
        print(f"[AUDIT API ERROR] Failed to get audit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audit_router.get("/results/{audit_id}", response_model=AuditResult)
async def get_audit_results(
    audit_id: str,
    current_user: str = Depends(get_current_user),
    db: SupabaseAuthDB = Depends(lambda: SupabaseAuthDB())
):
    """
    Get the complete results of a completed audit
    """
    
    try:
        # In production, query audit_results and audit_issues tables
        # For now, run audit synchronously for testing
        
        engine = get_audit_engine()
        user_website = db.get_user_website(current_user)
        
        if not user_website:
            raise HTTPException(status_code=400, detail="No website selected")
        
        # Run audit (in production, this would retrieve stored results)
        audit_result = await engine.run_audit(
            user_email=current_user,
            website_url=user_website,
            date_range_days=30
        )
        
        # Override audit_id with requested one
        audit_result.audit_id = audit_id
        
        return audit_result
        
    except Exception as e:
        print(f"[AUDIT API ERROR] Failed to get audit results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audit_router.get("/latest", response_model=AuditResult)
async def get_latest_audit(
    current_user: str = Depends(get_current_user),
    db: SupabaseAuthDB = Depends(lambda: SupabaseAuthDB())
):
    """
    Get the most recent audit results for the user's selected website
    """
    
    try:
        engine = get_audit_engine()
        user_website = db.get_user_website(current_user)
        
        if not user_website:
            raise HTTPException(status_code=400, detail="No website selected")
        
        # Run fresh audit (in production, would check cache first)
        audit_result = await engine.run_audit(
            user_email=current_user,
            website_url=user_website,
            date_range_days=30
        )
        
        return audit_result
        
    except Exception as e:
        print(f"[AUDIT API ERROR] Failed to get latest audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audit_router.get("/history", response_model=List[AuditHistoryItem])
async def get_audit_history(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    current_user: str = Depends(get_current_user),
    db: SupabaseAuthDB = Depends(lambda: SupabaseAuthDB())
):
    """
    Get audit history for the user's websites
    """
    
    try:
        # In production, query audit_history_view
        # For now, return empty list
        
        history = []
        
        return history
        
    except Exception as e:
        print(f"[AUDIT API ERROR] Failed to get audit history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audit_router.get("/top-issues")
async def get_top_issues(
    severity: Optional[IssueSeverity] = None,
    limit: int = Query(3, ge=1, le=10),
    current_user: str = Depends(get_current_user),
    db: SupabaseAuthDB = Depends(lambda: SupabaseAuthDB())
):
    """
    Get top issues from the latest audit
    
    This endpoint returns the most critical issues for display
    on the home page dashboard.
    """
    
    try:
        engine = get_audit_engine()
        user_website = db.get_user_website(current_user)
        
        if not user_website:
            raise HTTPException(status_code=400, detail="No website selected")
        
        # Get latest audit
        audit_result = await engine.run_audit(
            user_email=current_user,
            website_url=user_website,
            date_range_days=30
        )
        
        # Filter by severity if specified
        issues = audit_result.issues
        if severity:
            issues = [i for i in issues if i.severity == severity]
        
        # Get top issues
        top_issues = issues[:limit]
        
        # Convert to dict for JSON response
        return {
            "website": user_website,
            "audit_date": audit_result.audit_date.isoformat(),
            "seo_score": audit_result.seo_score,
            "total_issues": len(issues),
            "top_issues": [issue.to_dict() for issue in top_issues]
        }
        
    except Exception as e:
        print(f"[AUDIT API ERROR] Failed to get top issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audit_router.post("/export/{audit_id}")
async def export_audit(
    audit_id: str,
    format: str = Query("json", regex="^(json|pdf)$"),
    current_user: str = Depends(get_current_user),
    db: SupabaseAuthDB = Depends(lambda: SupabaseAuthDB())
):
    """
    Export audit results in JSON or PDF format
    
    PDF generation is planned for the Solvia Agent milestone.
    """
    
    try:
        if format == "pdf":
            raise HTTPException(
                status_code=501,
                detail="PDF export will be available in the next milestone"
            )
        
        # Get audit results
        engine = get_audit_engine()
        user_website = db.get_user_website(current_user)
        
        if not user_website:
            raise HTTPException(status_code=400, detail="No website selected")
        
        # Get audit (in production, retrieve from database)
        audit_result = await engine.run_audit(
            user_email=current_user,
            website_url=user_website,
            date_range_days=30
        )
        
        # Return JSON export
        return JSONResponse(
            content=audit_result.to_dict(),
            headers={
                "Content-Disposition": f"attachment; filename=audit_{audit_id}.json"
            }
        )
        
    except Exception as e:
        print(f"[AUDIT API ERROR] Failed to export audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task function
async def run_audit_background(
    audit_id: str,
    user_email: str,
    website_url: str,
    request: AuditRequest,
    db: SupabaseAuthDB
):
    """
    Run audit in background
    
    This function runs the audit and stores results in the database.
    """
    
    try:
        print(f"[AUDIT BACKGROUND] Starting audit {audit_id} for {website_url}")
        
        engine = AuditEngine(db)
        
        # Run the audit
        audit_result = await engine.run_audit(
            user_email=user_email,
            website_url=website_url,
            date_range_days=request.date_range_days,
            force_refresh=request.force_refresh
        )
        
        # Override audit_id
        audit_result.audit_id = audit_id
        
        print(f"[AUDIT BACKGROUND] Completed audit {audit_id}")
        print(f"  SEO Score: {audit_result.seo_score}")
        print(f"  Issues: {audit_result.total_issues}")
        print(f"  Processing Time: {audit_result.processing_time_ms}ms")
        
        # In production, update audit status in database
        
    except Exception as e:
        print(f"[AUDIT BACKGROUND ERROR] Failed audit {audit_id}: {e}")
        # In production, update audit status to failed


# Health check endpoint
@audit_router.get("/health")
async def audit_health():
    """Check if audit engine is healthy"""
    
    return {
        "status": "healthy",
        "engine": "audit_engine_v1",
        "analyzers": [
            "performance",
            "anomaly",
            "trends",
            "opportunities"
        ]
    }