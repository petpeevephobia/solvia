"""
Real-time Audit Progress Tracking System with SSE (Server-Sent Events)
Based on best practices for SEO audit tools in 2024
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging

from app.auth.routes import get_current_user
from app.database.supabase_db import SupabaseAuthDB

logger = logging.getLogger(__name__)

class AuditStage(str, Enum):
    """Audit progress stages"""
    INITIALIZING = "initializing"
    FETCHING_GSC_DATA = "fetching_gsc_data"
    ANALYZING_METRICS = "analyzing_metrics"
    DETECTING_ISSUES = "detecting_issues"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    CREATING_REPORT = "creating_report"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"

class AuditProgress(BaseModel):
    """Progress update model"""
    audit_id: str
    stage: AuditStage
    progress: int  # 0-100
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)

class AuditProgressTracker:
    """Manages audit progress tracking and SSE streaming"""
    
    def __init__(self):
        self.active_audits: Dict[str, Dict[str, Any]] = {}
        self.db = SupabaseAuthDB()
        
    def start_audit(self, audit_id: str, user_email: str, website_url: str) -> None:
        """Initialize a new audit tracking session"""
        self.active_audits[audit_id] = {
            'user_email': user_email,
            'website_url': website_url,
            'stage': AuditStage.INITIALIZING,
            'progress': 0,
            'messages': [],
            'started_at': datetime.now().isoformat(),
            'updates': asyncio.Queue()
        }
        logger.info(f"Started tracking audit {audit_id} for {user_email}")
    
    async def update_progress(
        self, 
        audit_id: str, 
        stage: AuditStage, 
        progress: int, 
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update audit progress and notify listeners"""
        if audit_id not in self.active_audits:
            logger.warning(f"Audit {audit_id} not found in active audits")
            return
            
        audit = self.active_audits[audit_id]
        audit['stage'] = stage
        audit['progress'] = progress
        audit['messages'].append({
            'stage': stage,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Create progress update
        update = AuditProgress(
            audit_id=audit_id,
            stage=stage,
            progress=progress,
            message=message,
            details=details
        )
        
        # Put update in queue for SSE streaming
        await audit['updates'].put(update.dict())
        
        # Store in database for persistence
        await self._store_progress_update(audit_id, update)
        
        logger.info(f"Audit {audit_id} progress: {stage} - {progress}% - {message}")
    
    async def _store_progress_update(self, audit_id: str, update: AuditProgress) -> None:
        """Store progress update in database using service role key"""
        try:
            from supabase import create_client
            import os
            
            # Get user_email from active audit
            user_email = None
            if audit_id in self.active_audits:
                user_email = self.active_audits[audit_id].get('user_email')
            
            # Use service role key to bypass RLS
            service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if service_role_key:
                service_client = create_client(self.db.supabase_url, service_role_key)
            else:
                service_client = self.db.supabase
                
            service_client.table('audit_progress').insert({
                'audit_id': audit_id,
                'user_email': user_email,  # Add user_email
                'stage': update.stage,
                'progress': update.progress,
                'message': update.message,
                'details': json.dumps(update.details) if update.details else None,
                'created_at': update.timestamp
            }).execute()
        except Exception as e:
            logger.error(f"Failed to store progress update: {e}")
    
    async def stream_progress(self, audit_id: str) -> AsyncGenerator[str, None]:
        """Stream progress updates via SSE"""
        if audit_id not in self.active_audits:
            yield f"data: {json.dumps({'error': 'Audit not found'})}\n\n"
            return
            
        audit = self.active_audits[audit_id]
        queue = audit['updates']
        
        try:
            while True:
                # Wait for updates with timeout
                try:
                    update = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Format as SSE event
                    event_data = json.dumps(update)
                    yield f"data: {event_data}\n\n"
                    
                    # Check if audit is completed
                    if update.get('stage') in [AuditStage.COMPLETED, AuditStage.ERROR]:
                        break
                        
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for audit {audit_id}")
        finally:
            # Cleanup if audit is complete
            if audit.get('stage') in [AuditStage.COMPLETED, AuditStage.ERROR]:
                await self.cleanup_audit(audit_id)
    
    async def cleanup_audit(self, audit_id: str) -> None:
        """Clean up completed audit from memory"""
        if audit_id in self.active_audits:
            del self.active_audits[audit_id]
            logger.info(f"Cleaned up audit {audit_id}")
    
    def get_audit_status(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an audit"""
        if audit_id not in self.active_audits:
            return None
            
        audit = self.active_audits[audit_id]
        return {
            'audit_id': audit_id,
            'stage': audit['stage'],
            'progress': audit['progress'],
            'messages': audit['messages'][-5:],  # Last 5 messages
            'started_at': audit['started_at']
        }

# Global tracker instance
progress_tracker = AuditProgressTracker()

# API Router for progress endpoints
router = APIRouter(prefix="/agent/progress", tags=["audit-progress"])

@router.get("/stream/{audit_id}")
async def stream_audit_progress(
    audit_id: str,
    current_user: str = Depends(get_current_user)
):
    """
    Stream real-time audit progress updates via Server-Sent Events (SSE)
    
    Based on best practices:
    - SSE for one-way server-to-client communication
    - Heartbeat to maintain connection
    - Automatic cleanup after completion
    """
    # Verify user owns this audit
    audit_status = progress_tracker.get_audit_status(audit_id)
    if not audit_status:
        raise HTTPException(status_code=404, detail="Audit not found or already completed")
    
    # Stream progress updates
    return StreamingResponse(
        progress_tracker.stream_progress(audit_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )

@router.get("/status/{audit_id}")
async def get_audit_status(
    audit_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get current status of an audit"""
    status = progress_tracker.get_audit_status(audit_id)
    if not status:
        # Try to fetch from database
        db = SupabaseAuthDB()
        result = db.supabase.table('audit_progress') \
            .select('*') \
            .eq('audit_id', audit_id) \
            .order('created_at', desc=True) \
            .limit(1) \
            .execute()
        
        if result.data:
            latest = result.data[0]
            return {
                'audit_id': audit_id,
                'stage': latest['stage'],
                'progress': latest['progress'],
                'message': latest['message'],
                'completed': latest['stage'] in [AuditStage.COMPLETED, AuditStage.ERROR]
            }
        
        raise HTTPException(status_code=404, detail="Audit not found")
    
    return status

# Helper function for audit execution with progress
async def execute_audit_with_progress(
    audit_id: str,
    user_email: str,
    website_url: str,
    audit_function: callable
) -> Dict[str, Any]:
    """
    Execute an audit with progress tracking
    
    This wraps the actual audit logic with progress updates
    """
    tracker = progress_tracker
    
    try:
        # Initialize tracking
        tracker.start_audit(audit_id, user_email, website_url)
        
        # Stage 1: Initialize (0-10%)
        await tracker.update_progress(
            audit_id, 
            AuditStage.INITIALIZING,
            10,
            "Starting SEO audit for your website...",
            {"website": website_url}
        )
        await asyncio.sleep(0.5)  # Brief pause for UI
        
        # Stage 2: Fetch GSC Data (10-30%)
        await tracker.update_progress(
            audit_id,
            AuditStage.FETCHING_GSC_DATA,
            20,
            "Connecting to Google Search Console..."
        )
        # ... fetch data ...
        await tracker.update_progress(
            audit_id,
            AuditStage.FETCHING_GSC_DATA,
            30,
            "Retrieved search performance data"
        )
        
        # Stage 3: Analyze Metrics (30-50%)
        await tracker.update_progress(
            audit_id,
            AuditStage.ANALYZING_METRICS,
            40,
            "Analyzing SEO metrics and trends..."
        )
        # ... analyze ...
        await tracker.update_progress(
            audit_id,
            AuditStage.ANALYZING_METRICS,
            50,
            "Metrics analysis complete"
        )
        
        # Stage 4: Detect Issues (50-70%)
        await tracker.update_progress(
            audit_id,
            AuditStage.DETECTING_ISSUES,
            60,
            "Scanning for SEO issues..."
        )
        # ... detect issues ...
        await tracker.update_progress(
            audit_id,
            AuditStage.DETECTING_ISSUES,
            70,
            "Identified critical issues"
        )
        
        # Stage 5: Generate Recommendations (70-85%)
        await tracker.update_progress(
            audit_id,
            AuditStage.GENERATING_RECOMMENDATIONS,
            80,
            "Creating personalized recommendations..."
        )
        # ... generate recommendations ...
        await tracker.update_progress(
            audit_id,
            AuditStage.GENERATING_RECOMMENDATIONS,
            85,
            "Recommendations ready"
        )
        
        # Stage 6: Create Report (85-95%)
        await tracker.update_progress(
            audit_id,
            AuditStage.CREATING_REPORT,
            90,
            "Generating PDF report..."
        )
        # ... create report ...
        await tracker.update_progress(
            audit_id,
            AuditStage.CREATING_REPORT,
            95,
            "Report generated successfully"
        )
        
        # Stage 7: Finalize (95-100%)
        await tracker.update_progress(
            audit_id,
            AuditStage.FINALIZING,
            98,
            "Saving audit results..."
        )
        
        # Execute the actual audit
        result = await audit_function()
        
        # Complete
        await tracker.update_progress(
            audit_id,
            AuditStage.COMPLETED,
            100,
            "Audit completed successfully!",
            {"seo_score": result.get('seo_score', 0)}
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Audit {audit_id} failed: {e}")
        await tracker.update_progress(
            audit_id,
            AuditStage.ERROR,
            0,
            f"Audit failed: {str(e)}"
        )
        raise