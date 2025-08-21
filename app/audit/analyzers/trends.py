"""
Trend Analyzer
Analyzes trends in SEO metrics over time
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta

from app.audit.models import (
    AuditIssue, SEOMetrics, MetricTrend,
    IssueSeverity, IssueCategory, IssueType
)


class TrendAnalyzer:
    """
    Analyzes trends in SEO metrics to identify patterns and issues
    """
    
    def __init__(self):
        """Initialize trend analyzer with configuration"""
        
        # Trend detection thresholds
        self.trend_thresholds = {
            'significant_change': 15,  # 15% change is significant
            'critical_change': 30,      # 30% change is critical
            'trend_reversal': 20,       # 20% opposite direction is reversal
        }
        
        # Minimum data points for trend analysis
        self.min_data_points = 7
    
    async def analyze_trends(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """
        Analyze trends and identify trend-related issues
        
        Args:
            current_data: Current period metrics
            historical_data: Historical comparison data
            metrics: Current SEO metrics
            
        Returns:
            List of trend-related issues
        """
        
        issues = []
        
        # 1. Analyze traffic trends
        traffic_trend = self._calculate_trend(
            metrics.total_clicks,
            historical_data.get('previous_clicks', 0),
            historical_data.get('clicks_mean', 0)
        )
        
        if traffic_trend:
            metrics.clicks_trend = traffic_trend
            traffic_issue = self._analyze_traffic_trend(traffic_trend, metrics)
            if traffic_issue:
                issues.append(traffic_issue)
        
        # 2. Analyze impression trends
        impression_trend = self._calculate_trend(
            metrics.total_impressions,
            historical_data.get('previous_impressions', 0),
            historical_data.get('impressions_mean', 0)
        )
        
        if impression_trend:
            metrics.impressions_trend = impression_trend
            impression_issue = self._analyze_impression_trend(impression_trend, metrics)
            if impression_issue:
                issues.append(impression_issue)
        
        # 3. Analyze CTR trends
        ctr_trend = self._calculate_trend(
            metrics.average_ctr,
            historical_data.get('previous_ctr', 0),
            historical_data.get('ctr_mean', 0)
        )
        
        if ctr_trend:
            metrics.ctr_trend = ctr_trend
            ctr_issue = self._analyze_ctr_trend(ctr_trend, metrics)
            if ctr_issue:
                issues.append(ctr_issue)
        
        # 4. Analyze position trends
        position_trend = self._calculate_trend(
            metrics.average_position,
            historical_data.get('previous_position', 0),
            historical_data.get('position_mean', 0),
            inverse=True  # Lower position is better
        )
        
        if position_trend:
            metrics.position_trend = position_trend
            position_issue = self._analyze_position_trend(position_trend, metrics)
            if position_issue:
                issues.append(position_issue)
        
        # 5. Detect trend reversals
        reversal_issues = self._detect_trend_reversals(
            current_data, historical_data, metrics
        )
        issues.extend(reversal_issues)
        
        # 6. Detect seasonal patterns
        seasonal_issues = self._detect_seasonal_patterns(
            current_data, historical_data, metrics
        )
        issues.extend(seasonal_issues)
        
        return issues
    
    def _calculate_trend(
        self,
        current_value: float,
        previous_value: float,
        mean_value: float,
        inverse: bool = False
    ) -> Optional[MetricTrend]:
        """Calculate trend for a metric"""
        
        if previous_value == 0 and current_value == 0:
            return None
        
        # Calculate changes
        if previous_value != 0:
            change_value = current_value - previous_value
            change_percentage = (change_value / abs(previous_value)) * 100
        else:
            change_value = current_value
            change_percentage = 100 if current_value > 0 else 0
        
        # Adjust for inverse metrics (where lower is better)
        if inverse:
            change_percentage = -change_percentage
            change_value = -change_value
        
        # Determine trend direction
        if abs(change_percentage) < 5:
            trend_direction = "stable"
        elif change_percentage > 0:
            trend_direction = "up"
        else:
            trend_direction = "down"
        
        # Check if it's an anomaly based on mean
        is_anomaly = False
        z_score = None
        if mean_value != 0:
            deviation = abs(current_value - mean_value) / mean_value * 100
            is_anomaly = deviation > 30  # More than 30% from mean
        
        return MetricTrend(
            current_value=current_value,
            previous_value=previous_value,
            change_value=change_value,
            change_percentage=change_percentage,
            trend_direction=trend_direction,
            is_anomaly=is_anomaly,
            z_score=z_score
        )
    
    def _analyze_traffic_trend(
        self,
        trend: MetricTrend,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Analyze traffic trend for issues"""
        
        # Check for significant negative trend
        if trend.trend_direction == "down" and abs(trend.change_percentage) >= self.trend_thresholds['significant_change']:
            severity = IssueSeverity.HIGH if abs(trend.change_percentage) >= self.trend_thresholds['critical_change'] else IssueSeverity.MEDIUM
            
            issue = AuditIssue(
                issue_type=IssueType.TRAFFIC_DROP,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Declining Traffic Trend",
                description=f"Traffic shows a consistent declining trend with {abs(trend.change_percentage):.1f}% decrease. "
                           f"Current: {trend.current_value:.0f} clicks, Previous: {trend.previous_value:.0f} clicks.",
                recommendation="Investigate the cause of the traffic decline. Check for algorithm updates, "
                              "technical issues, or increased competition. Review your content strategy.",
                traffic_impact=abs(trend.change_percentage),
                business_impact="high",
                evidence={
                    'trend_direction': trend.trend_direction,
                    'change_percentage': trend.change_percentage,
                    'current_clicks': trend.current_value,
                    'previous_clicks': trend.previous_value
                }
            )
            
            return issue
        
        return None
    
    def _analyze_impression_trend(
        self,
        trend: MetricTrend,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Analyze impression trend for issues"""
        
        # Check for declining visibility
        if trend.trend_direction == "down" and abs(trend.change_percentage) >= self.trend_thresholds['significant_change']:
            severity = IssueSeverity.HIGH if abs(trend.change_percentage) >= self.trend_thresholds['critical_change'] else IssueSeverity.MEDIUM
            
            # Special case: Impressions down but CTR up might indicate ranking for wrong keywords
            ctr_improving = metrics.ctr_trend and metrics.ctr_trend.trend_direction == "up"
            
            issue = AuditIssue(
                issue_type=IssueType.IMPRESSION_DROP,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Declining Search Visibility" + (" Despite Better CTR" if ctr_improving else ""),
                description=f"Search impressions show a declining trend with {abs(trend.change_percentage):.1f}% decrease. "
                           f"You're appearing less frequently in search results." +
                           (" However, CTR is improving, suggesting better keyword targeting." if ctr_improving else ""),
                recommendation="Review your keyword targeting and content coverage. "
                              "Ensure you're targeting the right keywords with sufficient search volume." +
                              (" Focus on expanding content for high-value keywords." if ctr_improving else ""),
                traffic_impact=abs(trend.change_percentage) * 0.8,  # Impressions affect traffic indirectly
                business_impact="medium",
                evidence={
                    'trend_direction': trend.trend_direction,
                    'change_percentage': trend.change_percentage,
                    'current_impressions': trend.current_value,
                    'previous_impressions': trend.previous_value,
                    'ctr_improving': ctr_improving
                }
            )
            
            return issue
        
        return None
    
    def _analyze_ctr_trend(
        self,
        trend: MetricTrend,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Analyze CTR trend for issues"""
        
        # Check for declining CTR
        if trend.trend_direction == "down" and abs(trend.change_percentage) >= self.trend_thresholds['significant_change']:
            
            # Check if position is stable or improving
            position_stable = (metrics.position_trend and 
                              metrics.position_trend.trend_direction in ["stable", "up"])
            
            if position_stable:
                # CTR declining despite stable/better position is more serious
                severity = IssueSeverity.HIGH
                title = "CTR Declining Despite Stable Rankings"
                impact = "high"
            else:
                severity = IssueSeverity.MEDIUM
                title = "Click-Through Rate Declining"
                impact = "medium"
            
            issue = AuditIssue(
                issue_type=IssueType.CTR_DECLINE,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title=title,
                description=f"CTR shows a declining trend with {abs(trend.change_percentage):.1f}% decrease. "
                           f"Current: {trend.current_value:.2f}%, Previous: {trend.previous_value:.2f}%." +
                           (" Your rankings are stable, so the issue is with click appeal." if position_stable else ""),
                recommendation="Update title tags and meta descriptions to be more compelling. "
                              "Test different variations and ensure they match search intent.",
                traffic_impact=abs(trend.change_percentage),
                business_impact=impact,
                evidence={
                    'trend_direction': trend.trend_direction,
                    'change_percentage': trend.change_percentage,
                    'current_ctr': trend.current_value,
                    'previous_ctr': trend.previous_value,
                    'position_stable': position_stable
                }
            )
            
            return issue
        
        return None
    
    def _analyze_position_trend(
        self,
        trend: MetricTrend,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Analyze position trend for issues"""
        
        # For positions, "down" trend means rankings are getting worse (higher numbers)
        if trend.trend_direction == "down" and abs(trend.change_percentage) >= self.trend_thresholds['significant_change']:
            
            # Calculate actual position change
            position_change = trend.current_value - trend.previous_value
            
            severity = IssueSeverity.HIGH if position_change >= 3 else IssueSeverity.MEDIUM
            
            issue = AuditIssue(
                issue_type=IssueType.POSITION_LOSS,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Rankings Declining Over Time",
                description=f"Average search position is getting worse, declining by {position_change:.1f} positions. "
                           f"Current: {trend.current_value:.1f}, Previous: {trend.previous_value:.1f}.",
                recommendation="Review your content quality and freshness. Check for new competitors "
                              "and ensure your content provides better value than competing pages.",
                traffic_impact=position_change * 10,  # Estimate impact
                business_impact="high",
                evidence={
                    'trend_direction': trend.trend_direction,
                    'position_change': position_change,
                    'current_position': trend.current_value,
                    'previous_position': trend.previous_value
                }
            )
            
            return issue
        
        return None
    
    def _detect_trend_reversals(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """Detect sudden trend reversals"""
        
        issues = []
        
        # This would detect sudden changes in trend direction
        # For example, traffic that was growing suddenly declining
        
        return issues
    
    def _detect_seasonal_patterns(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """Detect seasonal patterns and anomalies"""
        
        issues = []
        
        # This would detect seasonal patterns
        # For now, return empty as it requires more historical data
        
        return issues