"""
Core Audit Engine for SEO health assessment
Implements clean architecture with separation of concerns
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import numpy as np
from statistics import mean, stdev

from app.audit.models import (
    AuditResult, AuditIssue, SEOMetrics, MetricTrend,
    IssueSeverity, IssueCategory, IssueType
)
from app.audit.analyzers import (
    PerformanceAnalyzer,
    AnomalyDetector,
    TrendAnalyzer,
    OpportunityAnalyzer
)
from app.database.supabase_db import SupabaseAuthDB
from app.data_pipeline.detailed_fetcher import DetailedGSCDataFetcher
from app.core.seo_scoring import SEOScoringEngine


class AuditEngine:
    """
    Main orchestrator for SEO audits
    Coordinates analyzers and generates comprehensive audit results
    """
    
    def __init__(self, db: SupabaseAuthDB):
        """Initialize audit engine with dependencies"""
        self.db = db
        self.fetcher = DetailedGSCDataFetcher(db)
        
        # Initialize analyzers
        self.performance_analyzer = PerformanceAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.opportunity_analyzer = OpportunityAnalyzer()
        
        # Configuration
        self.default_days = 30
        self.score_weights = {
            'traffic': 0.30,
            'position': 0.25,
            'ctr': 0.25,
            'trends': 0.20
        }
    
    async def run_audit(
        self,
        user_email: str,
        website_url: str,
        date_range_days: int = 30,
        force_refresh: bool = False
    ) -> AuditResult:
        """
        Run complete SEO audit for a website
        
        Args:
            user_email: User's email for data access
            website_url: Website to audit
            date_range_days: Days of data to analyze
            force_refresh: Force fresh data fetch
            
        Returns:
            Complete audit result with issues and recommendations
        """
        start_time = time.time()
        
        # Initialize audit result
        audit_result = AuditResult(
            user_email=user_email,
            website_url=website_url,
            metrics=SEOMetrics()
        )
        
        try:
            # Step 1: Fetch current and historical data
            current_data, historical_data = await self._fetch_audit_data(
                user_email, website_url, date_range_days, force_refresh
            )
            
            # Step 2: Calculate current metrics
            audit_result.metrics = self._calculate_metrics(current_data)
            
            # Step 3: Calculate SEO score
            audit_result.seo_score = self._calculate_enhanced_seo_score(
                audit_result.metrics, historical_data
            )
            
            # Step 4: Get previous audit for comparison
            previous_audit = await self._get_previous_audit(user_email, website_url)
            if previous_audit:
                audit_result.previous_score = previous_audit.get('seo_score')
                audit_result.score_delta = audit_result.seo_score - audit_result.previous_score
            
            # Step 5: Run all analyzers in parallel
            issues = await self._run_analyzers(
                current_data, historical_data, audit_result.metrics
            )
            
            # Step 6: Prioritize and filter issues
            audit_result.issues = self._prioritize_issues(issues)
            audit_result.calculate_issue_counts()
            
            # Step 7: Calculate performance changes
            audit_result.traffic_change = self._calculate_change(
                audit_result.metrics.total_clicks,
                historical_data.get('previous_clicks', 0)
            )
            audit_result.position_change = self._calculate_change(
                audit_result.metrics.average_position,
                historical_data.get('previous_position', 0),
                inverse=True  # Lower position is better
            )
            audit_result.ctr_change = self._calculate_change(
                audit_result.metrics.average_ctr,
                historical_data.get('previous_ctr', 0)
            )
            
            # Step 8: Store audit results
            await self._store_audit_results(audit_result)
            
        except Exception as e:
            print(f"[AUDIT ERROR] Failed to complete audit: {e}")
            raise
        
        finally:
            # Calculate processing time
            audit_result.processing_time_ms = int((time.time() - start_time) * 1000)
        
        return audit_result
    
    async def _fetch_audit_data(
        self,
        user_email: str,
        website_url: str,
        date_range_days: int,
        force_refresh: bool
    ) -> Tuple[Dict, Dict]:
        """Fetch current and historical data for audit"""
        
        # Calculate date ranges
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=date_range_days)
        
        # Previous period for comparison
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=date_range_days)
        
        # Fetch current period data
        current_data = await self._fetch_period_data(
            user_email, website_url, start_date, end_date, force_refresh
        )
        
        # Fetch previous period data for comparison
        historical_data = await self._fetch_period_data(
            user_email, website_url, prev_start_date, prev_end_date, False
        )
        
        # Add baseline statistics for anomaly detection
        baseline_data = await self._fetch_baseline_statistics(
            user_email, website_url, date_range_days * 3  # Use 90 days for baseline
        )
        
        historical_data.update(baseline_data)
        
        return current_data, historical_data
    
    async def _fetch_period_data(
        self,
        user_email: str,
        website_url: str,
        start_date,
        end_date,
        force_refresh: bool
    ) -> Dict:
        """Fetch data for a specific period"""
        
        # Query from enhanced data pipeline tables
        query = """
            SELECT 
                COUNT(DISTINCT query_text) as total_queries,
                COUNT(DISTINCT page_url) as total_pages,
                SUM(clicks) as total_clicks,
                SUM(impressions) as total_impressions,
                AVG(ctr) as average_ctr,
                AVG(position) as average_position,
                ARRAY_AGG(DISTINCT query_text) as queries,
                ARRAY_AGG(DISTINCT page_url) as pages
            FROM (
                SELECT * FROM gsc_queries
                WHERE user_email = %s 
                AND website_url = %s
                AND date BETWEEN %s AND %s
                
                UNION ALL
                
                SELECT 
                    NULL as query_text,
                    page_url,
                    date,
                    clicks,
                    impressions,
                    ctr,
                    position,
                    user_email,
                    website_url
                FROM gsc_pages
                WHERE user_email = %s 
                AND website_url = %s
                AND date BETWEEN %s AND %s
            ) combined
        """
        
        # Use enhanced data pipeline for detailed metrics
        try:
            # Get query-level data
            query_data = self.db.supabase.table('gsc_queries').select('*').eq(
                'user_email', user_email
            ).eq(
                'website_url', website_url
            ).gte(
                'date', start_date.isoformat()
            ).lte(
                'date', end_date.isoformat()
            ).execute()
            
            # Get page-level data
            page_data = self.db.supabase.table('gsc_pages').select('*').eq(
                'user_email', user_email
            ).eq(
                'website_url', website_url
            ).gte(
                'date', start_date.isoformat()
            ).lte(
                'date', end_date.isoformat()
            ).execute()
            
            # Get daily summary for quick stats
            summary_data = self.db.supabase.table('gsc_daily_summary').select('*').eq(
                'user_email', user_email
            ).eq(
                'website_url', website_url
            ).gte(
                'date', start_date.isoformat()
            ).lte(
                'date', end_date.isoformat()
            ).execute()
            
            if summary_data.data:
                # Calculate aggregates from daily summaries
                total_clicks = sum(day['total_clicks'] for day in summary_data.data)
                total_impressions = sum(day['total_impressions'] for day in summary_data.data)
                avg_ctr = sum(day['average_ctr'] for day in summary_data.data) / len(summary_data.data) if summary_data.data else 0
                avg_position = sum(day['average_position'] for day in summary_data.data) / len(summary_data.data) if summary_data.data else 0
                
                return {
                    'total_clicks': total_clicks,
                    'total_impressions': total_impressions,
                    'average_ctr': avg_ctr,
                    'average_position': avg_position,
                    'total_queries': len(set(q['query'] for q in query_data.data)) if query_data.data else 0,
                    'total_pages': len(set(p['page_url'] for p in page_data.data)) if page_data.data else 0,
                    'queries': query_data.data[:100] if query_data.data else [],  # Top 100 queries
                    'pages': page_data.data[:50] if page_data.data else []  # Top 50 pages
                }
        except Exception as e:
            print(f"[AUDIT] Error fetching enhanced data: {e}")
            # Fallback to cached metrics if enhanced tables don't exist yet
            cached_metrics = await self.db.get_gsc_metrics_cache(
                user_email, 
                website_url,
                {'start_date': start_date, 'end_date': end_date}
            )
            
            if cached_metrics:
                return {
                    'total_clicks': cached_metrics.get('clicks', 0),
                    'total_impressions': cached_metrics.get('impressions', 0),
                    'average_ctr': cached_metrics.get('ctr', 0),
                    'average_position': cached_metrics.get('avg_position', 0),
                    'total_queries': cached_metrics.get('keywords', 0),
                    'total_pages': 0,
                    'queries': [],
                    'pages': []
                }
        
        # Default empty data
        return {
            'total_clicks': 0,
            'total_impressions': 0,
            'average_ctr': 0,
            'average_position': 0,
            'total_queries': 0,
            'total_pages': 0,
            'queries': [],
            'pages': []
        }
    
    async def _fetch_baseline_statistics(
        self,
        user_email: str,
        website_url: str,
        days: int
    ) -> Dict:
        """Fetch statistical baselines for anomaly detection"""
        
        # This would query the audit_baselines table
        # For now, calculate from historical data
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get daily metrics for statistical analysis
        daily_metrics = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            metrics = await self.db.get_gsc_metrics_cache(
                user_email,
                website_url,
                {'start_date': date, 'end_date': date}
            )
            if metrics:
                daily_metrics.append(metrics)
        
        if not daily_metrics:
            return {}
        
        # Calculate statistical measures
        clicks_values = [m.get('clicks', 0) for m in daily_metrics]
        impressions_values = [m.get('impressions', 0) for m in daily_metrics]
        ctr_values = [m.get('ctr', 0) for m in daily_metrics]
        position_values = [m.get('avg_position', 0) for m in daily_metrics if m.get('avg_position', 0) > 0]
        
        baseline = {}
        
        if clicks_values:
            baseline['clicks_mean'] = mean(clicks_values)
            baseline['clicks_stdev'] = stdev(clicks_values) if len(clicks_values) > 1 else 0
            baseline['clicks_min'] = min(clicks_values)
            baseline['clicks_max'] = max(clicks_values)
        
        if impressions_values:
            baseline['impressions_mean'] = mean(impressions_values)
            baseline['impressions_stdev'] = stdev(impressions_values) if len(impressions_values) > 1 else 0
        
        if ctr_values:
            baseline['ctr_mean'] = mean(ctr_values)
            baseline['ctr_stdev'] = stdev(ctr_values) if len(ctr_values) > 1 else 0
        
        if position_values:
            baseline['position_mean'] = mean(position_values)
            baseline['position_stdev'] = stdev(position_values) if len(position_values) > 1 else 0
        
        return baseline
    
    def _calculate_metrics(self, data: Dict) -> SEOMetrics:
        """Calculate current SEO metrics from data"""
        
        metrics = SEOMetrics(
            total_clicks=data.get('total_clicks', 0),
            total_impressions=data.get('total_impressions', 0),
            average_ctr=data.get('average_ctr', 0),
            average_position=data.get('average_position', 0),
            total_queries=data.get('total_queries', 0),
            total_pages=data.get('total_pages', 0)
        )
        
        return metrics
    
    def _calculate_enhanced_seo_score(
        self,
        metrics: SEOMetrics,
        historical_data: Dict
    ) -> float:
        """
        Calculate SEO score using unified scoring engine.
        Ensures consistency across the entire application.
        """
        
        # Prepare historical data in expected format
        historical = None
        if historical_data:
            historical = {
                'clicks': historical_data.get('previous_clicks', 0),
                'impressions': historical_data.get('previous_impressions', 0),
                'ctr': historical_data.get('previous_ctr', 0),
                'position': historical_data.get('previous_position', 0)
            }
        
        # Use unified scoring engine
        score = SEOScoringEngine.calculate_score(
            clicks=metrics.total_clicks,
            impressions=metrics.total_impressions,
            ctr=metrics.average_ctr,
            position=metrics.average_position,
            historical_data=historical
        )
        
        return score
    
    def _get_expected_ctr(self, position: float, benchmarks: Dict) -> float:
        """Get expected CTR based on position using industry benchmarks"""
        
        if position <= 0:
            return 0
        
        # Find closest benchmark
        positions = sorted(benchmarks.keys())
        
        if position <= positions[0]:
            return benchmarks[positions[0]]
        
        if position >= positions[-1]:
            # Extrapolate for positions beyond 10
            return benchmarks[positions[-1]] * (10 / position)
        
        # Interpolate between benchmarks
        for i in range(len(positions) - 1):
            if positions[i] <= position <= positions[i + 1]:
                # Linear interpolation
                x1, y1 = positions[i], benchmarks[positions[i]]
                x2, y2 = positions[i + 1], benchmarks[positions[i + 1]]
                
                expected_ctr = y1 + (y2 - y1) * (position - x1) / (x2 - x1)
                return expected_ctr
        
        return 0.02  # Default 2% for unknown positions
    
    async def _run_analyzers(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """Run all analyzers in parallel and collect issues"""
        
        # Run analyzers concurrently
        tasks = [
            self.performance_analyzer.analyze(current_data, historical_data, metrics),
            self.anomaly_detector.detect_anomalies(current_data, historical_data, metrics),
            self.trend_analyzer.analyze_trends(current_data, historical_data, metrics),
            self.opportunity_analyzer.find_opportunities(current_data, historical_data, metrics)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all issues
        all_issues = []
        for result in results:
            if isinstance(result, Exception):
                print(f"[ANALYZER ERROR] {result}")
                continue
            if result:
                all_issues.extend(result)
        
        return all_issues
    
    def _prioritize_issues(self, issues: List[AuditIssue]) -> List[AuditIssue]:
        """Prioritize issues by severity and business impact"""
        
        # Define severity weights
        severity_weights = {
            IssueSeverity.CRITICAL: 1000,
            IssueSeverity.HIGH: 100,
            IssueSeverity.MEDIUM: 10,
            IssueSeverity.LOW: 1
        }
        
        # Sort issues by severity and traffic impact
        prioritized = sorted(
            issues,
            key=lambda x: (
                -severity_weights[x.severity],
                -abs(x.traffic_impact),
                x.detected_date
            )
        )
        
        # Limit to top 20 issues to avoid overwhelming users
        return prioritized[:20]
    
    def _calculate_change(
        self,
        current: float,
        previous: float,
        inverse: bool = False
    ) -> float:
        """Calculate percentage change between two values"""
        
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        
        change = ((current - previous) / abs(previous)) * 100
        
        if inverse:  # For metrics where lower is better (e.g., position)
            change = -change
        
        return round(change, 2)
    
    async def _get_previous_audit(
        self,
        user_email: str,
        website_url: str
    ) -> Optional[Dict]:
        """Get the most recent previous audit for comparison"""
        
        # Query the audit_results table for the latest audit
        # For now, return None as tables aren't created yet
        return None
    
    async def _store_audit_results(self, audit_result: AuditResult) -> bool:
        """Store audit results in database"""
        
        try:
            # Store main audit result
            audit_data = audit_result.to_dict()
            
            # In production, this would insert into audit_results table
            # For now, we'll store in a generic way
            print(f"[AUDIT] Storing audit {audit_result.audit_id} for {audit_result.website_url}")
            
            # Store individual issues
            for issue in audit_result.issues:
                issue_data = issue.to_dict()
                issue_data['audit_id'] = audit_result.audit_id
                issue_data['user_email'] = audit_result.user_email
                issue_data['website_url'] = audit_result.website_url
                
                # In production, insert into audit_issues table
                print(f"[AUDIT] Storing issue: {issue.title} ({issue.severity.value})")
            
            return True
            
        except Exception as e:
            print(f"[AUDIT ERROR] Failed to store results: {e}")
            return False