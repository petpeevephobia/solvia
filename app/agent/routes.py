"""
Agent routes for Solvia - Handles audit generation, PDF reports, and chat interactions
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import openai

from app.auth.routes import get_current_user, get_authenticated_user
from app.auth.google_oauth import GoogleOAuthHandler, GSCDataFetcher
from app.database.supabase_db import SupabaseAuthDB
from app.audit.engine import AuditEngine
from app.core.seo_scoring import SEOScoringEngine
from app.ai.agent_instructions import get_agent_instructions
from app.config import settings

# Helper functions for enhanced audit flow
def detect_industry_from_url(website_url: str) -> str:
    """Simple industry detection from website URL and content"""
    url_lower = website_url.lower()
    
    # E-commerce indicators
    if any(word in url_lower for word in ['shop', 'store', 'buy', 'cart', 'product']):
        return "e-commerce"
    
    # SaaS indicators  
    elif any(word in url_lower for word in ['saas', 'software', 'app', 'platform', 'tool']):
        return "saas"
    
    # Blog/content indicators
    elif any(word in url_lower for word in ['blog', 'news', 'article', 'content', 'media']):
        return "blog"
    
    # Local business indicators
    elif any(word in url_lower for word in ['local', 'restaurant', 'service', 'clinic', 'lawyer']):
        return "local_business"
    
    # Default
    return "default"

def merge_rag_insights(audit_result: Dict[str, Any], enhanced_issues: List) -> Dict[str, Any]:
    """Merge enhanced RAG insights with traditional audit results"""
    
    # Convert enhanced issues to audit format
    rag_issues = []
    for issue in enhanced_issues:
        rag_issue = {
            'title': issue.title,
            'description': issue.description, 
            'severity': issue.severity,
            'category': issue.category,
            'impact': issue.impact,
            'recommendation': issue.recommendation,
            'confidence_score': issue.confidence_score,
            'evidence_count': len(issue.evidence_chunks),
            'patterns_detected': len(issue.patterns_detected),
            'data_points': issue.data_points,
            'source': 'enhanced_rag',
            'priority_score': calculate_priority_score(issue)
        }
        rag_issues.append(rag_issue)
    
    # Merge with existing issues
    existing_issues = audit_result.issues if hasattr(audit_result, 'issues') else []
    
    # Convert existing issues to dict format and add source tag
    existing_issues_dict = []
    for issue in existing_issues:
        issue_dict = issue.to_dict() if hasattr(issue, 'to_dict') else issue
        issue_dict['source'] = 'audit_engine'
        issue_dict['priority_score'] = issue_dict.get('impact_score', 50)
        existing_issues_dict.append(issue_dict)
    
    # Combine and deduplicate
    all_issues = existing_issues_dict + rag_issues
    
    # Sort by priority and confidence
    all_issues.sort(key=lambda x: (
        {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.get('severity', 'low'), 3),
        -x.get('confidence_score', 0.5),
        -x.get('priority_score', 0)
    ))
    
    # Convert AuditResult to dict format
    audit_dict = audit_result.to_dict() if hasattr(audit_result, 'to_dict') else audit_result
    
    # Update audit result
    audit_dict['issues'] = all_issues[:10]  # Top 10 issues
    audit_dict['rag_enhanced'] = True
    audit_dict['enhanced_insights'] = {
        'total_rag_issues': len(rag_issues),
        'evidence_backed_issues': sum(1 for i in rag_issues if i['evidence_count'] > 0),
        'pattern_detected_issues': sum(1 for i in rag_issues if i['patterns_detected'] > 0),
        'high_confidence_issues': sum(1 for i in rag_issues if i['confidence_score'] > 0.8)
    }
    
    # Update summary with merged counts
    if 'summary' not in audit_dict:
        audit_dict['summary'] = {}
    
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for issue in audit_dict['issues']:
        severity = issue.get('severity', 'low')
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    audit_dict['summary'].update({
        'critical_issues': severity_counts['critical'],
        'high_issues': severity_counts['high'], 
        'medium_issues': severity_counts['medium'],
        'low_issues': severity_counts['low'],
        'total_issues': len(audit_dict['issues'])
    })
    
    return audit_dict

def calculate_priority_score(issue) -> float:
    """Calculate priority score for enhanced issues"""
    severity_weights = {
        'critical': 100,
        'high': 75,
        'medium': 50, 
        'low': 25
    }
    
    base_score = severity_weights.get(issue.severity, 25)
    confidence_bonus = issue.confidence_score * 20
    evidence_bonus = min(len(issue.evidence_chunks) * 5, 15)
    pattern_bonus = min(len(issue.patterns_detected) * 10, 20)
    
    return base_score + confidence_bonus + evidence_bonus + pattern_bonus

# Models for agent interactions
class AuditRequest(BaseModel):
    """Request model for triggering an audit"""
    date_range_days: int = 30
    report_format: str = "both"  # pdf, json, or both
    delivery_method: str = "email"  # email or download
    force_refresh: bool = False
    include_recommendations: bool = True
    
    # Optional fields that frontend might send
    prompt: Optional[str] = None
    website_url: Optional[str] = None
    date_range: Optional[int] = None  # Alternative field name
    
    def model_post_init(self, __context) -> None:
        # Handle alternative field names
        if self.date_range is not None and self.date_range_days == 30:
            self.date_range_days = self.date_range

class ChatMessage(BaseModel):
    """Chat message from user to agent"""
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    """Agent response to user"""
    message: str
    audit_triggered: bool = False
    audit_id: Optional[str] = None
    action_buttons: Optional[List[str]] = None

class AuditHistoryItem(BaseModel):
    """Single audit history item"""
    audit_id: str
    website_url: str
    seo_score: float
    created_at: str
    status: str
    critical_issues: int
    high_issues: int
    medium_issues: int
    total_issues: int
    pdf_url: Optional[str] = None
    json_data: Optional[Dict] = None

class AuditReportResponse(BaseModel):
    """Response after generating audit report"""
    audit_id: str
    status: str
    seo_score: float
    pdf_generated: bool
    email_sent: bool
    issues_count: Dict[str, int]
    top_issues: List[Dict[str, Any]]
    message: str

# Initialize router
router = APIRouter(prefix="/agent", tags=["agent"])

# Initialize services
db = SupabaseAuthDB()
google_oauth = GoogleOAuthHandler(db)
gsc_fetcher = GSCDataFetcher(google_oauth, db)
seo_engine = SEOScoringEngine()

# Configure OpenAI
openai.api_key = settings.OPENAI_API_KEY

@router.post("/trigger-audit", response_model=AuditReportResponse)
async def trigger_audit(
    request: AuditRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_authenticated_user)
):
    """
    Trigger a new SEO audit with real-time progress tracking.
    Enhanced with RAG analysis for intelligent insights.
    
    Features:
    1. Real-time progress via SSE
    2. RAG-powered issue analysis
    3. PDF report generation
    4. Intelligent recommendations
    """
    try:
        # Import progress tracker and ENHANCED RAG analyzer
        from app.agent.audit_progress import progress_tracker, execute_audit_with_progress
        from app.agent.rag_analyzer_enhanced import enhanced_rag_analyzer
        
        # Generate unique audit ID (proper UUID format)
        audit_id = str(uuid.uuid4())
        
        # Get user's selected website (same method as GSC metrics endpoint)
        website_url = db.get_user_website(current_user)
        if not website_url:
            raise HTTPException(
                status_code=400,
                detail="No website selected. Please select a website first."
            )
        
        # PERMANENT FIX: Clear all caches when audit is triggered
        # This ensures fresh Google API data for every audit
        print(f"[AUDIT CACHE CLEAR] 🧹 Clearing all caches for fresh data...")

        # 1. Clear GSC credentials cache to force fresh token validation
        try:
            google_oauth.clear_credentials_cache(current_user)
            print(f"[AUDIT CACHE CLEAR] ✅ Cleared GSC credentials cache for {current_user}")
        except Exception as cache_error:
            print(f"[AUDIT CACHE CLEAR] ⚠️ Warning: Could not clear credentials cache: {cache_error}")

        # 2. Clear GSC metrics cache to force fresh API calls
        try:
            # Clear cached GSC metrics for all date ranges for this user/website
            date_ranges_to_clear = [7, 14, 28, 30, 90]  # Common date ranges
            for days in date_ranges_to_clear:
                end_date_temp = datetime.now().date()
                start_date_temp = end_date_temp - timedelta(days=days)
                date_range_temp = {
                    'start_date': start_date_temp,
                    'end_date': end_date_temp,
                    'days': days
                }
                db.clear_gsc_metrics_cache(current_user, website_url, date_range_temp)
            print(f"[AUDIT CACHE CLEAR] ✅ Cleared GSC metrics cache for {website_url}")
        except Exception as metrics_cache_error:
            print(f"[AUDIT CACHE CLEAR] ⚠️ Warning: Could not clear metrics cache: {metrics_cache_error}")

        # 3. Clear dashboard cache to force fresh UI data
        try:
            db.clear_dashboard_cache(current_user, website_url)
            print(f"[AUDIT CACHE CLEAR] ✅ Cleared dashboard cache for {website_url}")
        except Exception as dashboard_cache_error:
            print(f"[AUDIT CACHE CLEAR] ⚠️ Warning: Could not clear dashboard cache: {dashboard_cache_error}")

        print(f"[AUDIT CACHE CLEAR] 🎯 All caches cleared - audit will use fresh Google API data")

        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=request.date_range_days)

        # ULTRATHINK AUTOMATIC RE-AUTHENTICATION: Ensure credentials are valid before fetching
        print(f"[AUDIT REFRESH] 🔍 Verifying GSC credentials before audit...")
        from app.auth.utils import verify_gsc_credentials

        has_valid_credentials = verify_gsc_credentials(current_user)
        if not has_valid_credentials:
            print(f"[AUDIT REFRESH] 🔄 GSC credentials invalid, attempting automatic refresh for audit...")

            # Try automatic refresh (verify_gsc_credentials contains the refresh logic)
            try:
                import time
                time.sleep(1)  # Brief pause

                refresh_success = verify_gsc_credentials(current_user)
                if refresh_success:
                    print(f"[AUDIT REFRESH] 🎉 ✅ Automatic token refresh SUCCESSFUL for audit!")
                else:
                    print(f"[AUDIT REFRESH] 💥 ❌ Automatic token refresh FAILED for audit")
                    raise HTTPException(
                        status_code=401,
                        detail="Google Search Console credentials expired and automatic refresh failed. Please re-authenticate with Google."
                    )
            except Exception as refresh_error:
                print(f"[AUDIT REFRESH] 💥 ❌ Exception during automatic refresh for audit: {refresh_error}")
                raise HTTPException(
                    status_code=401,
                    detail="Google Search Console credentials expired and automatic refresh failed. Please re-authenticate with Google."
                )

        # ULTRATHINK FIX: Use fetch_filtered_metrics() for consistency with dashboard
        # This ensures 1:1 metrics parity and uses unified SEO scoring
        print(f"[AUDIT DATA] 🚀 Fetching GSC metrics using filtered API for consistency...")

        from app.auth.models import GSCFilterRequest
        from app.core.seo_scoring import SEOScoringEngine

        # Create filter request matching date range
        filter_request = GSCFilterRequest(
            start_date=start_date,
            end_date=end_date,
            search_type='web',
            dimensions=[],  # Summary data only (no breakdowns)
            aggregation_type='auto'
        )

        try:
            # Fetch metrics using the same reliable method as dashboard
            raw_metrics = await gsc_fetcher.fetch_filtered_metrics(
                current_user,
                website_url,
                filter_request
            )

            print(f"[AUDIT DATA] 📊 Received filtered metrics:")
            print(f"[AUDIT DATA]    Clicks: {raw_metrics.get('total_clicks', 0)}")
            print(f"[AUDIT DATA]    Impressions: {raw_metrics.get('total_impressions', 0)}")
            print(f"[AUDIT DATA]    CTR: {raw_metrics.get('average_ctr', 0) * 100:.2f}%")
            print(f"[AUDIT DATA]    Position: {raw_metrics.get('average_position', 0):.1f}")

            # Calculate SEO score WITH component breakdown using unified scoring engine
            score_breakdown = SEOScoringEngine.calculate_score_with_breakdown(
                clicks=raw_metrics.get('total_clicks', 0),
                impressions=raw_metrics.get('total_impressions', 0),
                ctr=raw_metrics.get('average_ctr', 0),
                position=raw_metrics.get('average_position', 0)
            )

            seo_score = score_breakdown['seo_score']

            print(f"[AUDIT DATA] ✅ Calculated SEO Score: {seo_score}/100 (using unified engine)")
            print(f"[AUDIT DATA] 📊 Component Breakdown:")
            print(f"[AUDIT DATA]    Traffic: {score_breakdown['traffic_score']}/100 (30%)")
            print(f"[AUDIT DATA]    Position: {score_breakdown['position_score']}/100 (25%)")
            print(f"[AUDIT DATA]    CTR: {score_breakdown['ctr_score']}/100 (25%)")
            print(f"[AUDIT DATA]    Trends: {score_breakdown['trend_score']}/100 (20%)")

            # Transform to expected format for audit engine
            metrics = {
                'seo_score': seo_score,
                'organic_traffic': raw_metrics.get('total_clicks', 0),
                'impressions': raw_metrics.get('total_impressions', 0),
                'ctr': raw_metrics.get('average_ctr', 0) * 100,  # Convert to percentage
                'avg_position': raw_metrics.get('average_position', 0),
                'clicks_change': raw_metrics.get('clicks_change', 0),
                'impressions_change': raw_metrics.get('impressions_change', 0),
                'position_change': raw_metrics.get('position_change', 0),
                # Add component scores for PDF generation
                'scores': score_breakdown
            }

            print(f"[AUDIT DATA] 🎯 Using REAL GSC data for audit (not defaults)")

        except Exception as fetch_error:
            print(f"[AUDIT DATA] ❌ Error fetching filtered metrics: {fetch_error}")
            print(f"[AUDIT DATA] 🔄 Falling back to unified scoring with zero data...")

            # Fallback: Use unified scoring engine with zero data (returns 25.0 base score WITH breakdown)
            from app.core.seo_scoring import SEOScoringEngine
            score_breakdown = SEOScoringEngine.calculate_score_with_breakdown(
                clicks=0,
                impressions=0,
                ctr=0,
                position=0
            )

            base_score = score_breakdown['seo_score']

            metrics = {
                'seo_score': base_score,  # Unified base score (25.0) from scoring engine
                'organic_traffic': 0,
                'impressions': 0,
                'ctr': 0,
                'avg_position': 0,
                'clicks_change': 0,
                'impressions_change': 0,
                'position_change': 0,
                # Add component scores even for fallback
                'scores': score_breakdown
            }

            print(f"[AUDIT DATA] ⚠️ Using fallback base score: {base_score}/100")
        
        # Start progress tracking
        progress_tracker.start_audit(audit_id, current_user, website_url)
        
        # Stage 1: Initialize (0-10%)
        await progress_tracker.update_progress(
            audit_id,
            "initializing",
            10,
            f"Starting comprehensive SEO audit for {website_url}...",
            {"website": website_url, "date_range": request.date_range_days}
        )
        
        # Stage 2: Fetch enhanced GSC data (10-30%)
        await progress_tracker.update_progress(
            audit_id,
            "fetching_gsc_data", 
            20,
            "Connecting to Google Search Console..."
        )
        
        # Use existing GSC fetcher for now (to avoid import issues)
        # We'll prepare data in the format expected by enhanced RAG
        detailed_data = {
            'seo_score': metrics.get('seo_score', 25.0),
            'organic_traffic': metrics.get('organic_traffic', 0),
            'impressions': metrics.get('impressions', 0),
            'ctr': metrics.get('ctr', 0),
            'avg_position': metrics.get('avg_position', 0),
            'top_pages': [],  # Will be enhanced in future versions
            'top_queries': [],  # Will be enhanced in future versions
            'timeline_data': []  # Will be enhanced in future versions
        }
        
        await progress_tracker.update_progress(
            audit_id,
            "fetching_gsc_data",
            30, 
            f"Retrieved GSC metrics: {detailed_data['impressions']} impressions, {detailed_data['organic_traffic']} clicks"
        )
        
        # Stage 3: Enhanced analysis with RAG (30-60%)
        await progress_tracker.update_progress(
            audit_id,
            "analyzing_metrics",
            40,
            "Analyzing metrics with enhanced RAG intelligence..."
        )
        
        # Detect industry from website URL (simple heuristic)
        industry = detect_industry_from_url(website_url)
        
        # Run enhanced RAG analysis
        enhanced_issues = await enhanced_rag_analyzer.analyze_audit_data(
            detailed_data,
            website_url, 
            industry
        )
        
        await progress_tracker.update_progress(
            audit_id,
            "detecting_issues",
            60,
            f"Enhanced AI analysis complete. Found {len(enhanced_issues)} priority issues."
        )
        
        # Stage 4: Initialize and run audit engine (60-80%)  
        await progress_tracker.update_progress(
            audit_id,
            "generating_recommendations",
            70,
            "Running comprehensive audit engine..."
        )
        
        # Initialize audit engine
        audit_engine = AuditEngine(db)

        # ULTRATHINK FIX: Prepare pre-calculated metrics for AuditEngine
        # Pass the correctly calculated data from fetch_filtered_metrics() to avoid AuditEngine overwriting it
        precalculated_metrics = {
            'total_clicks': raw_metrics.get('total_clicks', 0) if 'raw_metrics' in locals() else 0,
            'total_impressions': raw_metrics.get('total_impressions', 0) if 'raw_metrics' in locals() else 0,
            'average_ctr': raw_metrics.get('average_ctr', 0) if 'raw_metrics' in locals() else 0,
            'average_position': raw_metrics.get('average_position', 0) if 'raw_metrics' in locals() else 0,
            'total_queries': 0,  # Will be filled by AuditEngine from detailed data
            'total_pages': 0     # Will be filled by AuditEngine from detailed data
        }

        # Use the seo_score we calculated earlier from unified scoring engine
        precalculated_seo_score = metrics.get('seo_score', 25.0)

        print(f"[AUDIT ROUTES] 🎯 Passing pre-calculated data to AuditEngine:")
        print(f"[AUDIT ROUTES]    SEO Score: {precalculated_seo_score}/100")
        print(f"[AUDIT ROUTES]    Clicks: {precalculated_metrics['total_clicks']}")
        print(f"[AUDIT ROUTES]    Impressions: {precalculated_metrics['total_impressions']}")

        # Run comprehensive audit WITH pre-calculated metrics and score
        audit_result = await audit_engine.run_audit(
            user_email=current_user,
            website_url=website_url,
            date_range_days=request.date_range_days,
            precalculated_metrics=precalculated_metrics,
            precalculated_seo_score=precalculated_seo_score
        )
        
        # Merge enhanced RAG insights with audit results
        audit_result = merge_rag_insights(audit_result, enhanced_issues)

        # ULTRATHINK FIX: Add component scores breakdown to audit result for PDF generation
        if 'scores' in metrics:
            audit_result['scores'] = metrics['scores']
            print(f"[AUDIT DATA] 📊 Added component scores to audit result for PDF:")
            print(f"[AUDIT DATA]    Traffic: {metrics['scores']['traffic_score']}")
            print(f"[AUDIT DATA]    Position: {metrics['scores']['position_score']}")
            print(f"[AUDIT DATA]    CTR: {metrics['scores']['ctr_score']}")
            print(f"[AUDIT DATA]    Trends: {metrics['scores']['trend_score']}")

        await progress_tracker.update_progress(
            audit_id,
            "generating_recommendations",
            80,
            "Merging AI insights with technical audit results..."
        )
        
        # Stage 5: Finalize report (80-95%)
        await progress_tracker.update_progress(
            audit_id,
            "creating_report",
            90,
            "Generating comprehensive audit report..."
        )
        
        # Final progress update
        await progress_tracker.update_progress(
            audit_id,
            "completed",
            100,
            f"✅ Audit complete! SEO Score: {audit_result.get('seo_score', 0)}/100"
        )
        
        # Extract top issues (top 3 for homepage display)
        top_issues = []
        if audit_result.get('issues'):
            # Sort by severity and impact
            sorted_issues = sorted(
                audit_result['issues'],
                key=lambda x: (
                    {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.get('severity', 'low'), 3),
                    -x.get('impact_score', 0)
                )
            )
            top_issues = sorted_issues[:3]
        
        # Store audit results in database
        audit_data = {
            'audit_id': audit_id,
            'user_email': current_user,
            'website_url': website_url,
            'seo_score': audit_result.get('seo_score', 0),
            'audit_data': json.dumps(audit_result),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': request.date_range_days
            },
            # Fix: Get issue counts from the nested audit data issues array
            'critical_issues': audit_result.get('summary', {}).get('critical_issues', 0),
            'high_issues': audit_result.get('summary', {}).get('high_issues', 0), 
            'medium_issues': audit_result.get('summary', {}).get('medium_issues', 0),
            'low_issues': audit_result.get('summary', {}).get('low_issues', 0),
            'total_issues': audit_result.get('summary', {}).get('total_issues', 0),
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }
        
        # Create a new db instance to ensure service role key is used
        db_with_role = SupabaseAuthDB()
        stored_id = db_with_role.store_audit_result(current_user, audit_data, website_url)
        if stored_id:
            print(f"[AUDIT SUCCESS] Stored audit {stored_id} to database")
        else:
            print(f"[AUDIT WARNING] Failed to store audit to database")
        
        # Update GSC cache with the new SEO score
        if stored_id:
            db_with_role.update_gsc_cache_with_audit_score(current_user, website_url, audit_data['seo_score'])
            print(f"[AUDIT SUCCESS] Updated GSC cache with new SEO score: {audit_data['seo_score']}")
        
        # Store chat message about audit completion  
        print(f"[AUDIT] Storing chat message for user: {current_user}")
        try:
            # Get correct counts from the summary
            critical_count = audit_result.get('summary', {}).get('critical_issues', 0)
            total_count = audit_result.get('summary', {}).get('total_issues', 0)
            
            db_with_role.store_chat_message(
                current_user,
                f"✅ Audit completed! SEO Score: {audit_data['seo_score']}/100. Found {critical_count} critical issues out of {total_count} total issues.",
                "ai",
                "Solvia"
            )
            print(f"[AUDIT] Chat message stored successfully")
        except Exception as e:
            print(f"[AUDIT] Failed to store chat message: {e}")
        
        # Generate PDF report in background if requested
        pdf_generated = False
        email_sent = False
        
        if request.report_format in ['pdf', 'both']:
            background_tasks.add_task(
                generate_pdf_report,
                audit_id,
                audit_result,
                current_user,
                website_url,
                request.delivery_method == 'email'
            )
            pdf_generated = True
            email_sent = request.delivery_method == 'email'
        
        return AuditReportResponse(
            audit_id=audit_id,
            status='completed',
            seo_score=audit_result.get('seo_score', 0),
            pdf_generated=pdf_generated,
            email_sent=email_sent,
            issues_count={
                'critical': audit_result.get('summary', {}).get('critical_issues', 0),
                'high': audit_result.get('summary', {}).get('high_issues', 0),
                'medium': audit_result.get('summary', {}).get('medium_issues', 0),
                'low': audit_result.get('summary', {}).get('low_issues', 0)
            },
            top_issues=top_issues,
            message=f"Audit completed successfully. SEO Score: {audit_result.get('seo_score', 0)}/100"
        )
        
    except Exception as e:
        print(f"[AGENT] Error triggering audit: {str(e)}")
        import traceback
        print(f"[AGENT] Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger audit: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    message: ChatMessage,
    current_user: str = Depends(get_current_user)
):
    """
    Chat with Solvia agent. The agent can:
    1. Answer questions about SEO performance
    2. Trigger audits when requested
    3. Provide insights from existing data
    """
    try:
        user_message = message.message.lower().strip()
        
        # Check if user wants to trigger an audit - be more specific to avoid false positives
        audit_keywords = ['run audit', 'run the audit', 'new audit', 'run a new audit', 'generate report', 'generate audit', 'analyze my site', 'run seo audit', 'start audit', 'perform audit', 'trigger audit', 'comprehensive audit']
        # Check for exact phrases or with common prefixes
        should_trigger_audit = any(
            keyword in user_message for keyword in audit_keywords
        ) or user_message in ['audit', 'run', 'analyze']
        
        audit_id = None
        audit_triggered = False
        
        if should_trigger_audit:
            # Trigger audit
            audit_request = AuditRequest()
            try:
                audit_response = await trigger_audit(
                    audit_request,
                    BackgroundTasks(),
                    current_user
                )
                audit_id = audit_response.audit_id
                audit_triggered = True
                
                response_message = f"""I've started a comprehensive SEO audit for your website! 🚀

Here's what I'm doing:
• Analyzing your last 30 days of search performance
• Identifying critical issues impacting your visibility
• Calculating your updated SEO score
• Generating a detailed PDF report

Your audit ID is: {audit_id}

The report will be emailed to you shortly. You can also view it in your audit history.

Your current SEO score is {audit_response.seo_score}/100."""
                
            except Exception as e:
                response_message = f"I encountered an issue while trying to run your audit: {str(e)}. Please make sure you have selected a website first."
        else:
            # Regular chat response using RAG system for intelligent context
            try:
                from app.agent.chat_integration_supabase import ChatIntegrationSupabase
                
                # Use RAG-powered chat integration
                chat_integration = ChatIntegrationSupabase()
                
                if chat_integration.rag_agent:
                    print(f"[CHAT-RAG] Using RAG agent: {type(chat_integration.rag_agent).__name__} in {chat_integration.rag_mode} mode")
                    
                    # Get user's website for context
                    user_data = await db.get_user_session(current_user)
                    website_url = user_data.get('selected_website') if user_data else None
                    
                    # Get chat history for conversation context
                    chat_history = db.get_chat_messages(current_user, limit=10)
                    
                    # Convert chat history to RAG format
                    conversation_history = []
                    if chat_history:
                        for msg in chat_history[-5:]:  # Last 5 messages for context
                            role = "user" if msg.get('message_type') == 'user' else "assistant"
                            conversation_history.append({
                                "role": role,
                                "content": msg.get('message_content', '')
                            })
                    
                    print(f"[CHAT-RAG] Query: '{user_message}', Website: {website_url}, History: {len(conversation_history)} messages")
                    
                    # Generate RAG response with full audit and GSC context
                    response_message = await chat_integration.rag_agent.generate_response(
                        user_email=current_user,
                        query=user_message,
                        conversation_history=conversation_history
                    )
                    
                    print(f"[CHAT-RAG] ✅ Generated response: {len(response_message)} chars")

                    # RAG system success - store messages and return
                    print(f"[CHAT-RAG] ✅ RAG response generated successfully")

                    # Store messages via RAG system and return immediately
                    # Always show suggestions for normal chat
                    return ChatResponse(
                        message=response_message,
                        audit_triggered=False,
                        audit_id=None,
                        action_buttons=[
                            "How was my SEO last week?",
                            "Run a new audit",
                            "What are my top issues?",
                            "Show me traffic trends"
                        ]
                    )
                    
                else:
                    print(f"[CHAT-RAG] ❌ No RAG agent available, falling back to basic OpenAI")
                    # Fallback to basic OpenAI if RAG not available
                    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                    completion = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": get_agent_instructions('solvia')},
                            {"role": "user", "content": user_message}
                        ],
                        max_tokens=800,
                        temperature=0.7
                    )
                    response_message = completion.choices[0].message.content
                    
            except Exception as e:
                print(f"[CHAT-RAG] ❌ Error using RAG system: {e}")
                # Fallback to basic OpenAI on error
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": get_agent_instructions('solvia')},
                        {"role": "user", "content": user_message}
                    ],
                    max_tokens=800,
                    temperature=0.7
                )
                response_message = completion.choices[0].message.content
        
        # Store chat messages (for non-RAG fallback cases only)
        if 'response_message' in locals():
            db.store_chat_message(
                current_user,
                message.message,
                'user',
                current_user.split('@')[0]
            )

            db.store_chat_message(
                current_user,
                response_message,
                'ai',
                'Solvia'
            )
        
        # Return with appropriate action buttons
        action_buttons = []
        if not audit_triggered:
            # Only show suggestions if not triggering audit
            action_buttons = [
                "How was my SEO last week?",
                "Run a new audit",
                "What are my top issues?",
                "Show me traffic trends"
            ]

        return ChatResponse(
            message=response_message,
            audit_triggered=audit_triggered,
            audit_id=audit_id,
            action_buttons=action_buttons
        )
        
    except Exception as e:
        print(f"[AGENT] Error in chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )

@router.get("/history", response_model=List[AuditHistoryItem])
async def get_audit_history(
    current_user: str = Depends(get_current_user),
    limit: int = Query(10, description="Number of audits to return"),
    offset: int = Query(0, description="Number of audits to skip")
):
    """Get user's audit history"""
    try:
        audits = db.get_audit_history(current_user, limit, offset)
        
        history_items = []
        for audit in audits:
            history_items.append(AuditHistoryItem(
                audit_id=audit['audit_id'],
                website_url=audit['website_url'],
                seo_score=audit['seo_score'],
                created_at=audit['created_at'],
                status=audit.get('status', 'completed'),
                critical_issues=audit.get('critical_issues', 0),
                high_issues=audit.get('high_issues', 0),
                medium_issues=audit.get('medium_issues', 0),
                total_issues=audit.get('total_issues', 0),
                pdf_url=f"/agent/report/{audit['audit_id']}/pdf" if audit.get('pdf_generated') else None,
                json_data=json.loads(audit['audit_data']) if (audit.get('audit_data') and isinstance(audit['audit_data'], str)) else audit.get('audit_data', None)
            ))
        
        return history_items
        
    except Exception as e:
        print(f"[AGENT] Error getting audit history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit history: {str(e)}"
        )

@router.get("/report/{audit_id}/pdf")
async def get_audit_pdf(
    audit_id: str,
    current_user: str = Depends(get_current_user)
):
    """Download PDF report for a specific audit"""
    try:
        # Verify user owns this audit
        audit = db.get_audit_by_id(audit_id, current_user)
        if not audit:
            raise HTTPException(
                status_code=404,
                detail="Audit not found or access denied"
            )
        
        # Check if PDF exists
        pdf_path = f"reports/{audit_id}.pdf"
        if not os.path.exists(pdf_path):
            # Generate PDF on demand if not exists
            audit_data = json.loads(audit['audit_data']) if isinstance(audit['audit_data'], str) else audit['audit_data']
            await generate_pdf_report(
                audit_id,
                audit_data,
                current_user,
                audit['website_url'],
                send_email=False
            )
        
        if os.path.exists(pdf_path):
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"seo_audit_{audit_id}.pdf"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="PDF report not found"
            )
            
    except Exception as e:
        print(f"[AGENT] Error getting PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get PDF report: {str(e)}"
        )

@router.get("/report/{audit_id}/json")
async def get_audit_json(
    audit_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get JSON data for a specific audit"""
    try:
        audit = db.get_audit_by_id(audit_id, current_user)
        if not audit:
            raise HTTPException(
                status_code=404,
                detail="Audit not found or access denied"
            )
        
        audit_data = json.loads(audit['audit_data']) if (audit.get('audit_data') and isinstance(audit['audit_data'], str)) else audit.get('audit_data', {})
        
        return JSONResponse(content=audit_data)
        
    except Exception as e:
        print(f"[AGENT] Error getting JSON: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get JSON report: {str(e)}"
        )

@router.get("/current-issues")
async def get_current_issues(
    current_user: str = Depends(get_current_user)
):
    """
    Get current top issues - FIXED VERSION.
    Prioritizes real Google data for consistency with dashboard metrics.
    Falls back to cached audit data only when Google data is unavailable.
    """
    try:
        # Get user's website
        website_url = db.get_user_website(current_user)
        print(f"[CURRENT-ISSUES] User: {current_user}, Website: {website_url}")

        # PRIORITY 0: Check for fresh audit data first (< 1 hour old) - prioritize recent audit results
        db_instance = SupabaseAuthDB()
        latest_audit = db_instance.get_latest_audit(current_user, website_url) if website_url else None

        if latest_audit and latest_audit.get('created_at'):
            from datetime import timezone
            created_at_str = latest_audit['created_at']
            if isinstance(created_at_str, str):
                if 'T' in created_at_str:
                    if '+' in created_at_str or 'Z' in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.fromisoformat(created_at_str).replace(tzinfo=timezone.utc)
                else:
                    created_at = datetime.fromisoformat(created_at_str).replace(tzinfo=timezone.utc)
            else:
                created_at = created_at_str

            now_utc = datetime.now(timezone.utc)
            audit_age_hours = (now_utc - created_at).total_seconds() / 3600

            # If audit is less than 1 hour old, prioritize it over real-time GSC data
            if audit_age_hours < 1 and latest_audit.get('audit_data'):
                print(f"[CURRENT-ISSUES] 🎯 PRIORITIZING fresh audit data ({audit_age_hours:.1f}h old) over GSC data")
                audit_data = latest_audit['audit_data']

                if 'audit_data' in audit_data and isinstance(audit_data['audit_data'], str):
                    try:
                        import json
                        nested_data = json.loads(audit_data['audit_data'])
                        issues = nested_data.get('issues', []) or nested_data.get('top_issues', [])
                    except:
                        issues = audit_data.get('issues', []) or audit_data.get('top_issues', [])
                else:
                    issues = audit_data.get('issues', []) or audit_data.get('top_issues', [])

                # Format issues for display
                formatted_issues = []
                for issue in issues[:5]:
                    formatted_issues.append({
                        'title': issue.get('title', 'SEO Issue'),
                        'description': issue.get('description', 'Issue detected in audit'),
                        'severity': issue.get('severity', 'medium'),
                        'impact': issue.get('impact', 'This may affect your SEO performance'),
                        'recommendation': issue.get('recommendation', 'Review and address this issue'),
                        'icon': _get_issue_icon(issue.get('category', 'general'))
                    })

                return {
                    "has_issues": len(formatted_issues) > 0,
                    "issues": formatted_issues,
                    "last_audit": created_at_str,
                    "seo_score": audit_data.get('seo_score', 0),
                    "source": "fresh-audit-data",
                    "cache_age_hours": audit_age_hours
                }

        # PRIORITY 1: Try to get real-time Google data for consistency with dashboard metrics
        if website_url:
            print(f"[CURRENT-ISSUES] Fetching real Google data for consistency...")
            try:
                from app.auth.google_oauth import GSCDataFetcher
                from app.agent.rag_analyzer import rag_analyzer

                # Check GSC credentials first
                from app.auth.utils import verify_gsc_credentials
                has_valid_gsc_credentials = verify_gsc_credentials(current_user)

                if has_valid_gsc_credentials:
                    gsc_fetcher = GSCDataFetcher(google_oauth, db)
                    metrics = await gsc_fetcher.fetch_metrics(current_user, website_url, days=30)

                    if metrics and metrics.get('summary'):
                        # Transform metrics for analysis - using REAL GOOGLE DATA
                        audit_data = {
                            'seo_score': google_oauth._calculate_seo_score(
                                metrics['summary'].get('total_clicks', 0),
                                metrics['summary'].get('total_impressions', 0),
                                metrics['summary'].get('avg_ctr', 0),
                                metrics['summary'].get('avg_position', 0)
                            ),
                            'organic_traffic': metrics['summary'].get('total_clicks', 0),
                            'impressions': metrics['summary'].get('total_impressions', 0),
                            'ctr': metrics['summary'].get('avg_ctr', 0) * 100,
                            'avg_position': metrics['summary'].get('avg_position', 0),
                            'clicks_change': metrics['summary'].get('clicks_change', 0),
                            'impressions_change': metrics['summary'].get('impressions_change', 0),
                            'position_change': metrics['summary'].get('position_change', 0)
                        }

                        print(f"[CURRENT-ISSUES] ✅ Using REAL Google data - SEO Score: {audit_data['seo_score']}")

                        # Analyze with RAG for real-time issues
                        rag_issues = await rag_analyzer.analyze_audit_data(audit_data, website_url)

                        # Format for display
                        issues = []
                        for issue in rag_issues[:5]:  # Top 5 issues
                            issues.append({
                                'title': issue.title,
                                'description': issue.description,
                                'severity': issue.severity,
                                'impact': issue.impact,
                                'recommendation': issue.recommendation,
                                'icon': _get_issue_icon(issue.category)
                            })

                        return {
                            "has_issues": len(issues) > 0,
                            "issues": issues,
                            "last_audit": datetime.now().isoformat(),
                            "seo_score": audit_data.get('seo_score', 0),
                            "source": "real-google-data",
                            "cache_age_hours": 0
                        }
                else:
                    print(f"[CURRENT-ISSUES] GSC credentials invalid, falling back to cached data")
            except Exception as e:
                print(f"[CURRENT-ISSUES] Real-time Google data failed: {e}, falling back to cached data")

        # PRIORITY 2: Fall back to older cached audit data if Google data unavailable
        # Reuse the latest_audit already fetched in PRIORITY 0 to avoid duplicate queries
        if latest_audit and latest_audit.get('created_at') and latest_audit.get('audit_data'):
            from datetime import timezone
            created_at_str = latest_audit['created_at']
            if isinstance(created_at_str, str):
                if 'T' in created_at_str:
                    if '+' in created_at_str or 'Z' in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.fromisoformat(created_at_str).replace(tzinfo=timezone.utc)
                else:
                    created_at = datetime.fromisoformat(created_at_str).replace(tzinfo=timezone.utc)
            else:
                created_at = created_at_str

            now_utc = datetime.now(timezone.utc)
            audit_age_hours = (now_utc - created_at).total_seconds() / 3600

            # Use stored audit if 1+ hours old but less than 24 hours old (not handled by PRIORITY 0)
            if 1 <= audit_age_hours < 24:
                print(f"[CURRENT-ISSUES] Using cached audit as fallback ({audit_age_hours:.1f} hours old)")

                # Use stored audit data (FALLBACK PATH)
                audit_data = latest_audit['audit_data']

                # Parse nested data if needed
                if 'audit_data' in audit_data and isinstance(audit_data['audit_data'], str):
                    try:
                        import json
                        nested_data = json.loads(audit_data['audit_data'])
                        issues = nested_data.get('issues', []) or nested_data.get('top_issues', [])
                    except:
                        issues = audit_data.get('issues', []) or audit_data.get('top_issues', [])
                else:
                    issues = audit_data.get('issues', []) or audit_data.get('top_issues', [])

                # Format issues for display
                formatted_issues = []
                for issue in issues[:5]:  # Top 5 issues
                    if isinstance(issue, dict):
                        formatted_issues.append({
                            'title': issue.get('title', 'Unknown Issue'),
                            'description': issue.get('description', ''),
                            'severity': issue.get('severity', 'medium'),
                            'impact': issue.get('impact', ''),
                            'recommendation': issue.get('recommendation', ''),
                            'icon': _get_issue_icon(issue.get('category', 'other'))
                        })

                return {
                    "has_issues": len(formatted_issues) > 0,
                    "issues": formatted_issues,
                    "last_audit": latest_audit.get('created_at', datetime.now().isoformat()),
                    "seo_score": audit_data.get('seo_score', 0),
                    "source": "stored-audit-fallback",
                    "cache_age_hours": audit_age_hours
                }

        # PRIORITY 3: Legacy fallback for older systems
        if website_url:
            print(f"[CURRENT-ISSUES] No recent audit found, fetching fresh data (slow)")
            try:
                from app.agent.rag_analyzer import rag_analyzer
                from app.auth.google_oauth import GSCDataFetcher
                
                gsc_fetcher = GSCDataFetcher(google_oauth, db)
                metrics = await gsc_fetcher.fetch_metrics(current_user, website_url, days=30)
                
                if metrics and metrics.get('summary'):
                    # Transform metrics for analysis
                    audit_data = {
                        'seo_score': google_oauth._calculate_seo_score(
                            metrics['summary'].get('total_clicks', 0),
                            metrics['summary'].get('total_impressions', 0),
                            metrics['summary'].get('avg_ctr', 0),
                            metrics['summary'].get('avg_position', 0)
                        ),
                        'organic_traffic': metrics['summary'].get('total_clicks', 0),
                        'impressions': metrics['summary'].get('total_impressions', 0),
                        'ctr': metrics['summary'].get('avg_ctr', 0) * 100,
                        'avg_position': metrics['summary'].get('avg_position', 0),
                        'clicks_change': metrics['summary'].get('clicks_change', 0),
                        'impressions_change': metrics['summary'].get('impressions_change', 0),
                        'position_change': metrics['summary'].get('position_change', 0)
                    }
                    
                    # Analyze with RAG
                    rag_issues = await rag_analyzer.analyze_audit_data(audit_data, website_url)
                    
                    # Format for display
                    issues = []
                    for issue in rag_issues:
                        issues.append({
                            'title': issue.title,
                            'description': issue.description,
                            'severity': issue.severity,
                            'impact': issue.impact,
                            'recommendation': issue.recommendation,
                            'icon': _get_issue_icon(issue.category)
                        })
                    
                    if issues:
                        return {
                            "has_issues": True,
                            "issues": issues,
                            "last_audit": datetime.now().isoformat(),
                            "seo_score": audit_data.get('seo_score', 0),
                            "source": "real-time-analysis"
                        }
            except Exception as e:
                print(f"[AGENT] Real-time analysis failed: {e}")
        
        # No audit data available
        return {
            "has_issues": False,
            "issues": [],
            "last_audit": None,
            "message": "No audit data available. Run your first audit to see SEO issues.",
            "source": "no-data"
        }
        
    except Exception as e:
        print(f"[AGENT] Error getting current issues: {str(e)}")
        return {
            "has_issues": False,
            "issues": [],
            "last_audit": None,
            "error": str(e)
        }

# Helper functions
async def generate_pdf_report(
    audit_id: str,
    audit_data: Dict[str, Any],
    user_email: str,
    website_url: str,
    send_email: bool = True
):
    """Generate PDF report from audit data"""
    try:
        from app.agent.pdf_generator import PDFReportGenerator
        
        # Create reports directory if not exists
        os.makedirs('reports', exist_ok=True)
        
        # Generate PDF
        generator = PDFReportGenerator()
        pdf_path = f"reports/{audit_id}.pdf"
        
        generator.generate_report(
            audit_data=audit_data,
            output_path=pdf_path,
            website_url=website_url,
            audit_id=audit_id
        )
        
        # Send email if requested
        if send_email:
            from app.agent.email_service import send_audit_report_email
            await send_audit_report_email(
                recipient_email=user_email,
                pdf_path=pdf_path,
                audit_id=audit_id,
                seo_score=audit_data.get('seo_score', 0),
                user_email=user_email  # Pass user for logging
            )
        
        # Update database to mark PDF as generated
        db.update_audit_status(audit_id, user_email, 'completed', pdf_path)
        
        return pdf_path
        
    except Exception as e:
        print(f"[AGENT] Error generating PDF: {str(e)}")
        raise

def _get_issue_icon(category: str) -> str:
    """Get icon emoji for issue category"""
    icons = {
        'content': '📝',
        'technical': '⚙️',
        'performance': '⚡',
        'visibility': '👁️',
        'engagement': '🎯',
        'images': '🖼️',
        'meta': '🏷️',
        'other': '⚠️'
    }
    return icons.get(category, '⚠️')