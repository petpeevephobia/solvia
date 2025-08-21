"""
Performance Analyzer
Analyzes SEO performance metrics and identifies issues
"""

from typing import Dict, List, Optional

from app.audit.models import (
    AuditIssue, SEOMetrics,
    IssueSeverity, IssueCategory, IssueType
)


class PerformanceAnalyzer:
    """
    Analyzes overall SEO performance and identifies performance-related issues
    """
    
    def __init__(self):
        """Initialize performance analyzer with benchmarks"""
        
        # Industry CTR benchmarks by position
        self.ctr_benchmarks = {
            1: 0.285,   # 28.5% CTR for position 1
            2: 0.157,   # 15.7% CTR for position 2
            3: 0.094,   # 9.4% CTR for position 3
            4: 0.062,   # 6.2% CTR for position 4
            5: 0.050,   # 5.0% CTR for position 5
            6: 0.038,   # 3.8% CTR for position 6
            7: 0.030,   # 3.0% CTR for position 7
            8: 0.024,   # 2.4% CTR for position 8
            9: 0.020,   # 2.0% CTR for position 9
            10: 0.025   # 2.5% CTR for position 10
        }
        
        # Performance thresholds
        self.performance_thresholds = {
            'low_ctr': 0.01,          # 1% CTR is concerning
            'poor_position': 20,       # Position 20+ is poor visibility
            'low_impressions': 100,    # Less than 100 impressions/month
            'zero_clicks_threshold': 1000  # Concerning if 1000+ impressions but 0 clicks
        }
    
    async def analyze(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """
        Analyze performance metrics and identify issues
        
        Args:
            current_data: Current period metrics
            historical_data: Historical comparison data
            metrics: Current SEO metrics
            
        Returns:
            List of performance-related issues
        """
        
        issues = []
        
        # 1. Check for poor CTR performance
        ctr_issue = self._analyze_ctr_performance(metrics)
        if ctr_issue:
            issues.append(ctr_issue)
        
        # 2. Check for poor average position
        position_issue = self._analyze_position_performance(metrics)
        if position_issue:
            issues.append(position_issue)
        
        # 3. Check for low visibility
        visibility_issue = self._analyze_visibility(metrics)
        if visibility_issue:
            issues.append(visibility_issue)
        
        # 4. Check for zero clicks problem
        zero_clicks_issue = self._analyze_zero_clicks(metrics)
        if zero_clicks_issue:
            issues.append(zero_clicks_issue)
        
        # 5. Check for keyword bleeding
        keyword_issue = self._analyze_keyword_performance(current_data, historical_data)
        if keyword_issue:
            issues.append(keyword_issue)
        
        # 6. Check for page performance issues
        page_issues = self._analyze_page_performance(current_data, historical_data)
        issues.extend(page_issues)
        
        return issues
    
    def _analyze_ctr_performance(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Analyze CTR performance against benchmarks"""
        
        if metrics.average_position == 0 or metrics.average_ctr == 0:
            return None
        
        # Get expected CTR for current position
        expected_ctr = self._get_expected_ctr(metrics.average_position)
        
        # Calculate performance ratio
        ctr_ratio = metrics.average_ctr / expected_ctr if expected_ctr > 0 else 0
        
        # Determine if CTR is underperforming
        if ctr_ratio < 0.5:  # Less than 50% of expected CTR
            severity = IssueSeverity.HIGH if ctr_ratio < 0.3 else IssueSeverity.MEDIUM
            
            issue = AuditIssue(
                issue_type=IssueType.CTR_DECLINE,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="CTR Below Industry Benchmark",
                description=f"Your average CTR ({metrics.average_ctr:.2f}%) is significantly below "
                           f"the industry benchmark ({expected_ctr:.2f}%) for position {metrics.average_position:.1f}. "
                           f"You're achieving only {ctr_ratio*100:.0f}% of expected performance.",
                recommendation="Improve your title tags and meta descriptions to be more compelling. "
                              "Ensure they match search intent and include your target keywords.",
                traffic_impact=(1 - ctr_ratio) * 100,
                business_impact="high",
                evidence={
                    'current_ctr': metrics.average_ctr,
                    'expected_ctr': expected_ctr,
                    'ctr_ratio': ctr_ratio,
                    'average_position': metrics.average_position
                }
            )
            
            return issue
        
        return None
    
    def _analyze_position_performance(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Analyze average position performance"""
        
        if metrics.average_position == 0:
            return None
        
        # Check for poor visibility
        if metrics.average_position >= self.performance_thresholds['poor_position']:
            severity = IssueSeverity.HIGH if metrics.average_position >= 30 else IssueSeverity.MEDIUM
            
            issue = AuditIssue(
                issue_type=IssueType.POSITION_LOSS,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Poor Search Visibility",
                description=f"Your average search position is {metrics.average_position:.1f}, "
                           f"which means most users won't see your content. "
                           f"90% of clicks go to the first page (positions 1-10).",
                recommendation="Focus on improving content quality, building relevant backlinks, "
                              "and optimizing for your target keywords to improve rankings.",
                traffic_impact=80,  # Estimate 80% traffic loss from poor position
                business_impact="high",
                evidence={
                    'average_position': metrics.average_position,
                    'visibility_score': max(0, 100 - metrics.average_position * 3)
                }
            )
            
            return issue
        
        return None
    
    def _analyze_visibility(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Analyze overall search visibility"""
        
        # Check for very low impressions
        if metrics.total_impressions < self.performance_thresholds['low_impressions']:
            severity = IssueSeverity.CRITICAL if metrics.total_impressions == 0 else IssueSeverity.HIGH
            
            issue = AuditIssue(
                issue_type=IssueType.IMPRESSION_DROP,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Extremely Low Search Visibility",
                description=f"Your site has only {metrics.total_impressions} search impressions. "
                           f"This indicates serious visibility issues that need immediate attention.",
                recommendation="Check if your site is indexed properly, review robots.txt, "
                              "ensure your sitemap is submitted, and check for manual penalties in GSC.",
                traffic_impact=95,  # Near total traffic loss
                business_impact="critical",
                evidence={
                    'total_impressions': metrics.total_impressions,
                    'total_queries': metrics.total_queries,
                    'indexed_pages': metrics.total_pages
                }
            )
            
            return issue
        
        return None
    
    def _analyze_zero_clicks(self, metrics: SEOMetrics) -> Optional[AuditIssue]:
        """Analyze zero clicks despite impressions"""
        
        # Check for zero clicks with significant impressions
        if (metrics.total_clicks == 0 and 
            metrics.total_impressions >= self.performance_thresholds['zero_clicks_threshold']):
            
            issue = AuditIssue(
                issue_type=IssueType.CTR_DECLINE,
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.PERFORMANCE,
                title="Zero Clicks Despite Search Visibility",
                description=f"Your site received {metrics.total_impressions:,} impressions but ZERO clicks. "
                           f"This is a critical issue indicating your search listings are not compelling.",
                recommendation="Urgently review and rewrite all title tags and meta descriptions. "
                              "Ensure they are relevant, compelling, and match user search intent. "
                              "Consider A/B testing different variations.",
                traffic_impact=100,  # Complete traffic loss
                business_impact="critical",
                evidence={
                    'total_impressions': metrics.total_impressions,
                    'total_clicks': 0,
                    'ctr': 0,
                    'average_position': metrics.average_position
                }
            )
            
            return issue
        
        return None
    
    def _analyze_keyword_performance(
        self,
        current_data: Dict,
        historical_data: Dict
    ) -> Optional[AuditIssue]:
        """Analyze keyword bleeding and losses"""
        
        current_queries = set(current_data.get('queries', []))
        historical_queries = set(historical_data.get('queries', []))
        
        if not historical_queries:
            return None
        
        # Calculate keyword losses
        lost_keywords = historical_queries - current_queries
        new_keywords = current_queries - historical_queries
        
        # Calculate bleeding rate
        if len(historical_queries) > 0:
            bleeding_rate = len(lost_keywords) / len(historical_queries) * 100
        else:
            bleeding_rate = 0
        
        # Check for significant keyword bleeding
        if bleeding_rate > 30:  # Lost more than 30% of keywords
            severity = IssueSeverity.HIGH if bleeding_rate > 50 else IssueSeverity.MEDIUM
            
            issue = AuditIssue(
                issue_type=IssueType.KEYWORD_BLEEDING,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Significant Keyword Bleeding Detected",
                description=f"You've lost {len(lost_keywords)} keywords ({bleeding_rate:.0f}% bleeding rate). "
                           f"Previously ranking for {len(historical_queries)} keywords, now only {len(current_queries)}.",
                recommendation="Review the lost keywords and identify patterns. Check if content was removed, "
                              "competitors improved, or if there were algorithm changes affecting your rankings.",
                traffic_impact=bleeding_rate,
                business_impact="high",
                evidence={
                    'lost_keywords_count': len(lost_keywords),
                    'lost_keywords_sample': list(lost_keywords)[:10],  # Sample of lost keywords
                    'new_keywords_count': len(new_keywords),
                    'bleeding_rate': bleeding_rate,
                    'total_keywords_before': len(historical_queries),
                    'total_keywords_after': len(current_queries)
                },
                affected_keywords=list(lost_keywords)[:50]  # Store up to 50 lost keywords
            )
            
            return issue
        
        return None
    
    def _analyze_page_performance(
        self,
        current_data: Dict,
        historical_data: Dict
    ) -> List[AuditIssue]:
        """Analyze individual page performance issues"""
        
        issues = []
        
        # This would analyze individual page performance
        # For now, return empty as we need page-level data
        
        return issues
    
    def _get_expected_ctr(self, position: float) -> float:
        """Get expected CTR based on position"""
        
        if position <= 0:
            return 0
        
        # Find closest benchmark
        if position <= 1:
            return self.ctr_benchmarks[1]
        elif position >= 10:
            # Extrapolate for positions beyond 10
            return self.ctr_benchmarks[10] * (10 / position)
        else:
            # Interpolate between benchmarks
            lower = int(position)
            upper = lower + 1
            
            if lower in self.ctr_benchmarks and upper in self.ctr_benchmarks:
                # Linear interpolation
                weight = position - lower
                expected = (self.ctr_benchmarks[lower] * (1 - weight) + 
                           self.ctr_benchmarks[upper] * weight)
                return expected
            
        return 0.02  # Default 2% for unknown positions