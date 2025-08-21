"""
Anomaly Detection Analyzer
Implements statistical methods to detect unusual patterns in SEO metrics
"""

from typing import Dict, List, Optional
import numpy as np
from statistics import mean, stdev

from app.audit.models import (
    AuditIssue, SEOMetrics,
    IssueSeverity, IssueCategory, IssueType
)


class AnomalyDetector:
    """
    Detects anomalies in SEO metrics using statistical methods
    Based on research: Z-score, IQR, and threshold-based detection
    """
    
    def __init__(self):
        """Initialize anomaly detector with thresholds"""
        
        # Z-score thresholds for anomaly detection
        self.z_score_thresholds = {
            'warning': 2.0,    # 2 standard deviations (95% confidence)
            'critical': 3.0    # 3 standard deviations (99.7% confidence)
        }
        
        # Percentage change thresholds
        self.change_thresholds = {
            'traffic': {
                'critical': -50,  # >50% traffic loss
                'high': -20,      # 20-50% traffic loss
                'medium': -10     # 10-20% traffic loss
            },
            'position': {
                'critical': 5,    # Dropped 5+ positions
                'high': 3,        # Dropped 3-5 positions
                'medium': 2       # Dropped 2-3 positions
            },
            'ctr': {
                'critical': -50,  # >50% CTR drop
                'high': -30,      # 30-50% CTR drop
                'medium': -15     # 15-30% CTR drop
            },
            'impressions': {
                'critical': -60,  # >60% impression loss
                'high': -30,      # 30-60% impression loss
                'medium': -15     # 15-30% impression loss
            }
        }
    
    async def detect_anomalies(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """
        Detect anomalies in SEO metrics
        
        Args:
            current_data: Current period metrics
            historical_data: Historical data with baselines
            metrics: Current SEO metrics
            
        Returns:
            List of detected anomaly issues
        """
        
        issues = []
        
        # 1. Traffic Drop Detection
        traffic_issue = self._detect_traffic_anomaly(
            current_data, historical_data, metrics
        )
        if traffic_issue:
            issues.append(traffic_issue)
        
        # 2. Position Loss Detection
        position_issue = self._detect_position_anomaly(
            current_data, historical_data, metrics
        )
        if position_issue:
            issues.append(position_issue)
        
        # 3. CTR Decline Detection
        ctr_issue = self._detect_ctr_anomaly(
            current_data, historical_data, metrics
        )
        if ctr_issue:
            issues.append(ctr_issue)
        
        # 4. Impression Drop Detection
        impression_issue = self._detect_impression_anomaly(
            current_data, historical_data, metrics
        )
        if impression_issue:
            issues.append(impression_issue)
        
        # 5. Statistical Anomaly Detection using Z-score
        statistical_issues = self._detect_statistical_anomalies(
            current_data, historical_data, metrics
        )
        issues.extend(statistical_issues)
        
        return issues
    
    def _detect_traffic_anomaly(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Detect significant traffic drops"""
        
        current_clicks = metrics.total_clicks
        previous_clicks = historical_data.get('previous_clicks', 0)
        
        if previous_clicks == 0:
            return None
        
        # Calculate percentage change
        change_pct = ((current_clicks - previous_clicks) / previous_clicks) * 100
        
        # Determine severity based on thresholds
        severity = None
        thresholds = self.change_thresholds['traffic']
        
        if change_pct <= thresholds['critical']:
            severity = IssueSeverity.CRITICAL
        elif change_pct <= thresholds['high']:
            severity = IssueSeverity.HIGH
        elif change_pct <= thresholds['medium']:
            severity = IssueSeverity.MEDIUM
        
        if severity:
            # Calculate z-score if baseline data available
            z_score = None
            if 'clicks_mean' in historical_data and 'clicks_stdev' in historical_data:
                if historical_data['clicks_stdev'] > 0:
                    z_score = (current_clicks - historical_data['clicks_mean']) / historical_data['clicks_stdev']
            
            issue = AuditIssue(
                issue_type=IssueType.TRAFFIC_DROP,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title=f"Significant Traffic Drop Detected",
                description=f"Organic traffic has dropped by {abs(change_pct):.1f}% compared to the previous period. "
                           f"Current: {current_clicks} clicks, Previous: {previous_clicks} clicks.",
                recommendation="Investigate recent changes to your site, check for algorithm updates, "
                              "and review your top-performing pages for issues.",
                traffic_impact=abs(change_pct),
                business_impact="high" if severity == IssueSeverity.CRITICAL else "medium",
                evidence={
                    'current_clicks': current_clicks,
                    'previous_clicks': previous_clicks,
                    'change_percentage': change_pct,
                    'z_score': z_score
                }
            )
            
            return issue
        
        return None
    
    def _detect_position_anomaly(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Detect significant position losses"""
        
        current_position = metrics.average_position
        previous_position = historical_data.get('previous_position', 0)
        
        if previous_position == 0 or current_position == 0:
            return None
        
        # Position change (positive means dropped in rankings)
        position_change = current_position - previous_position
        
        # Determine severity based on thresholds
        severity = None
        thresholds = self.change_thresholds['position']
        
        if position_change >= thresholds['critical']:
            severity = IssueSeverity.CRITICAL
        elif position_change >= thresholds['high']:
            severity = IssueSeverity.HIGH
        elif position_change >= thresholds['medium']:
            severity = IssueSeverity.MEDIUM
        
        if severity:
            # Calculate statistical significance
            z_score = None
            if 'position_mean' in historical_data and 'position_stdev' in historical_data:
                if historical_data['position_stdev'] > 0:
                    z_score = (current_position - historical_data['position_mean']) / historical_data['position_stdev']
            
            issue = AuditIssue(
                issue_type=IssueType.POSITION_LOSS,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title=f"Average Position Declined",
                description=f"Your average search position has dropped from {previous_position:.1f} to {current_position:.1f} "
                           f"(declined by {position_change:.1f} positions).",
                recommendation="Review your content quality, check for new competitors, "
                              "and ensure your pages are optimized for target keywords.",
                traffic_impact=position_change * 10,  # Estimate impact
                business_impact="high" if severity == IssueSeverity.CRITICAL else "medium",
                evidence={
                    'current_position': current_position,
                    'previous_position': previous_position,
                    'position_change': position_change,
                    'z_score': z_score
                }
            )
            
            return issue
        
        return None
    
    def _detect_ctr_anomaly(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Detect CTR problems despite impressions"""
        
        current_ctr = metrics.average_ctr
        previous_ctr = historical_data.get('previous_ctr', 0)
        current_impressions = metrics.total_impressions
        
        # Check for CTR decline with maintained/increased impressions
        if previous_ctr == 0:
            return None
        
        # Calculate CTR change
        ctr_change_pct = ((current_ctr - previous_ctr) / previous_ctr) * 100
        
        # Special case: CTR declined but impressions are stable/growing
        impressions_stable = current_impressions >= historical_data.get('previous_impressions', 0) * 0.9
        
        # Determine severity
        severity = None
        thresholds = self.change_thresholds['ctr']
        
        if ctr_change_pct <= thresholds['critical']:
            severity = IssueSeverity.CRITICAL if impressions_stable else IssueSeverity.HIGH
        elif ctr_change_pct <= thresholds['high']:
            severity = IssueSeverity.HIGH if impressions_stable else IssueSeverity.MEDIUM
        elif ctr_change_pct <= thresholds['medium'] and impressions_stable:
            severity = IssueSeverity.MEDIUM
        
        if severity:
            issue = AuditIssue(
                issue_type=IssueType.CTR_DECLINE,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Click-Through Rate Declined" + (" Despite Stable Impressions" if impressions_stable else ""),
                description=f"CTR has dropped from {previous_ctr:.2f}% to {current_ctr:.2f}% "
                           f"({abs(ctr_change_pct):.1f}% decline)." +
                           (" Your pages are showing in search but not attracting clicks." if impressions_stable else ""),
                recommendation="Review and improve your title tags and meta descriptions. "
                              "Ensure they are compelling and match search intent.",
                traffic_impact=abs(ctr_change_pct),
                business_impact="high" if impressions_stable else "medium",
                evidence={
                    'current_ctr': current_ctr,
                    'previous_ctr': previous_ctr,
                    'ctr_change': ctr_change_pct,
                    'impressions_stable': impressions_stable,
                    'current_impressions': current_impressions
                }
            )
            
            return issue
        
        return None
    
    def _detect_impression_anomaly(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> Optional[AuditIssue]:
        """Detect significant impression drops"""
        
        current_impressions = metrics.total_impressions
        previous_impressions = historical_data.get('previous_impressions', 0)
        
        if previous_impressions == 0:
            return None
        
        # Calculate percentage change
        change_pct = ((current_impressions - previous_impressions) / previous_impressions) * 100
        
        # Determine severity
        severity = None
        thresholds = self.change_thresholds['impressions']
        
        if change_pct <= thresholds['critical']:
            severity = IssueSeverity.CRITICAL
        elif change_pct <= thresholds['high']:
            severity = IssueSeverity.HIGH
        elif change_pct <= thresholds['medium']:
            severity = IssueSeverity.MEDIUM
        
        if severity:
            issue = AuditIssue(
                issue_type=IssueType.IMPRESSION_DROP,
                severity=severity,
                category=IssueCategory.PERFORMANCE,
                title="Search Visibility Declined",
                description=f"Search impressions have dropped by {abs(change_pct):.1f}%. "
                           f"Current: {current_impressions:,} impressions, Previous: {previous_impressions:,} impressions.",
                recommendation="Check for indexing issues, review your sitemap, "
                              "and ensure important pages are not blocked by robots.txt.",
                traffic_impact=abs(change_pct),
                business_impact="high",
                evidence={
                    'current_impressions': current_impressions,
                    'previous_impressions': previous_impressions,
                    'change_percentage': change_pct
                }
            )
            
            return issue
        
        return None
    
    def _detect_statistical_anomalies(
        self,
        current_data: Dict,
        historical_data: Dict,
        metrics: SEOMetrics
    ) -> List[AuditIssue]:
        """Detect anomalies using statistical methods (Z-score)"""
        
        issues = []
        
        # Check clicks anomaly
        if 'clicks_mean' in historical_data and 'clicks_stdev' in historical_data:
            if historical_data['clicks_stdev'] > 0:
                z_score = abs((metrics.total_clicks - historical_data['clicks_mean']) / historical_data['clicks_stdev'])
                
                if z_score >= self.z_score_thresholds['critical']:
                    issues.append(self._create_statistical_anomaly_issue(
                        'clicks', metrics.total_clicks, historical_data['clicks_mean'],
                        z_score, IssueSeverity.HIGH
                    ))
                elif z_score >= self.z_score_thresholds['warning']:
                    issues.append(self._create_statistical_anomaly_issue(
                        'clicks', metrics.total_clicks, historical_data['clicks_mean'],
                        z_score, IssueSeverity.MEDIUM
                    ))
        
        # Check impressions anomaly
        if 'impressions_mean' in historical_data and 'impressions_stdev' in historical_data:
            if historical_data['impressions_stdev'] > 0:
                z_score = abs((metrics.total_impressions - historical_data['impressions_mean']) / 
                             historical_data['impressions_stdev'])
                
                if z_score >= self.z_score_thresholds['critical']:
                    issues.append(self._create_statistical_anomaly_issue(
                        'impressions', metrics.total_impressions, historical_data['impressions_mean'],
                        z_score, IssueSeverity.HIGH
                    ))
        
        return issues
    
    def _create_statistical_anomaly_issue(
        self,
        metric_name: str,
        current_value: float,
        expected_value: float,
        z_score: float,
        severity: IssueSeverity
    ) -> AuditIssue:
        """Create an issue for statistical anomaly"""
        
        deviation_pct = abs((current_value - expected_value) / expected_value * 100) if expected_value != 0 else 0
        
        return AuditIssue(
            issue_type=IssueType.TRAFFIC_DROP if metric_name == 'clicks' else IssueType.IMPRESSION_DROP,
            severity=severity,
            category=IssueCategory.PERFORMANCE,
            title=f"Statistical Anomaly in {metric_name.capitalize()}",
            description=f"The {metric_name} metric shows a significant statistical deviation. "
                       f"Current: {current_value:.0f}, Expected: {expected_value:.0f} "
                       f"(Z-score: {z_score:.2f}, {deviation_pct:.1f}% deviation).",
            recommendation=f"This unusual pattern may indicate a technical issue or external factor. "
                          f"Review recent changes and check for any errors or penalties.",
            traffic_impact=deviation_pct,
            business_impact="medium",
            evidence={
                'metric': metric_name,
                'current_value': current_value,
                'expected_value': expected_value,
                'z_score': z_score,
                'deviation_percentage': deviation_pct,
                'confidence_level': '99.7%' if z_score >= 3 else '95%'
            }
        )