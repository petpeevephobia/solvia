"""
Data models for the Audit Engine
Following clean architecture principles with domain models
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import uuid


class IssueSeverity(str, Enum):
    """Issue severity levels based on business impact"""
    CRITICAL = "critical"  # >50% traffic/revenue impact
    HIGH = "high"          # 20-50% impact
    MEDIUM = "medium"      # 10-20% impact
    LOW = "low"            # <10% impact


class IssueCategory(str, Enum):
    """Categories for organizing issues"""
    TECHNICAL = "technical"      # Technical SEO issues
    CONTENT = "content"          # Content quality/gaps
    PERFORMANCE = "performance"  # Rankings, CTR, traffic
    OPPORTUNITY = "opportunity"  # Growth opportunities


class IssueType(str, Enum):
    """Specific issue types for detection"""
    TRAFFIC_DROP = "traffic_drop"
    POSITION_LOSS = "position_loss"
    CTR_DECLINE = "ctr_decline"
    KEYWORD_BLEEDING = "keyword_bleeding"
    IMPRESSION_DROP = "impression_drop"
    CANNIBALIZATION = "cannibalization"
    TECHNICAL_ERROR = "technical_error"
    CONTENT_GAP = "content_gap"
    OPPORTUNITY_MISSED = "opportunity_missed"


class MetricTrend(BaseModel):
    """Represents a metric's trend over time"""
    current_value: float
    previous_value: float
    change_value: float
    change_percentage: float
    trend_direction: str  # up, down, stable
    is_anomaly: bool = False
    z_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "current_value": self.current_value,
            "previous_value": self.previous_value,
            "change_value": self.change_value,
            "change_percentage": self.change_percentage,
            "trend_direction": self.trend_direction,
            "is_anomaly": self.is_anomaly,
            "z_score": self.z_score
        }


class AuditIssue(BaseModel):
    """Represents a single issue detected during audit"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Identification
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    issue_type: IssueType
    severity: IssueSeverity
    category: IssueCategory
    
    # Description
    title: str
    description: str
    recommendation: Optional[str] = None
    
    # Impact Analysis
    affected_pages: int = 0
    affected_queries: int = 0
    traffic_impact: float = 0.0  # Estimated traffic loss/gain
    business_impact: str = "low"  # high, medium, low
    
    # Supporting Evidence
    evidence: Dict[str, Any] = Field(default_factory=dict)
    affected_urls: List[str] = Field(default_factory=list)
    affected_keywords: List[str] = Field(default_factory=list)
    
    # Dates
    detected_date: datetime = Field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "issue_id": self.issue_id,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "affected_pages": self.affected_pages,
            "affected_queries": self.affected_queries,
            "traffic_impact": self.traffic_impact,
            "business_impact": self.business_impact,
            "evidence": self.evidence,
            "affected_urls": self.affected_urls,
            "affected_keywords": self.affected_keywords,
            "detected_date": self.detected_date.isoformat()
        }


class SEOMetrics(BaseModel):
    """Current SEO metrics snapshot"""
    total_clicks: int = 0
    total_impressions: int = 0
    average_ctr: float = 0.0
    average_position: float = 0.0
    total_queries: int = 0
    total_pages: int = 0
    
    # Trends (30-day comparison)
    clicks_trend: Optional[MetricTrend] = None
    impressions_trend: Optional[MetricTrend] = None
    ctr_trend: Optional[MetricTrend] = None
    position_trend: Optional[MetricTrend] = None


class AuditResult(BaseModel):
    """Complete audit result with all findings"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Identification
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_email: str
    website_url: str
    
    # Scoring
    seo_score: float = 0.0  # 0-100
    previous_score: Optional[float] = None
    score_delta: Optional[float] = None
    
    # Metrics
    metrics: SEOMetrics
    
    # Issues
    issues: List[AuditIssue] = Field(default_factory=list)
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    total_issues: int = 0
    
    # Performance Changes (30-day)
    traffic_change: Optional[float] = None
    position_change: Optional[float] = None
    ctr_change: Optional[float] = None
    
    # Metadata
    audit_date: datetime = Field(default_factory=datetime.now)
    processing_time_ms: int = 0
    data_freshness: str = "real-time"  # real-time, cached, stale
    
    def calculate_issue_counts(self):
        """Calculate issue counts by severity"""
        self.critical_issues = len([i for i in self.issues if i.severity == IssueSeverity.CRITICAL])
        self.high_issues = len([i for i in self.issues if i.severity == IssueSeverity.HIGH])
        self.medium_issues = len([i for i in self.issues if i.severity == IssueSeverity.MEDIUM])
        self.low_issues = len([i for i in self.issues if i.severity == IssueSeverity.LOW])
        self.total_issues = len(self.issues)
    
    def get_top_issues(self, limit: int = 3) -> List[AuditIssue]:
        """Get top issues by severity and impact"""
        # Sort by severity (critical first) then by traffic impact
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3
        }
        
        sorted_issues = sorted(
            self.issues,
            key=lambda x: (severity_order[x.severity], -x.traffic_impact)
        )
        
        return sorted_issues[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "audit_id": self.audit_id,
            "user_email": self.user_email,
            "website_url": self.website_url,
            "seo_score": self.seo_score,
            "previous_score": self.previous_score,
            "score_delta": self.score_delta,
            "metrics": {
                "total_clicks": self.metrics.total_clicks,
                "total_impressions": self.metrics.total_impressions,
                "average_ctr": self.metrics.average_ctr,
                "average_position": self.metrics.average_position,
                "total_queries": self.metrics.total_queries,
                "total_pages": self.metrics.total_pages
            },
            "issues": [issue.to_dict() for issue in self.issues],
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "low_issues": self.low_issues,
            "total_issues": self.total_issues,
            "traffic_change": self.traffic_change,
            "position_change": self.position_change,
            "ctr_change": self.ctr_change,
            "audit_date": self.audit_date.isoformat(),
            "processing_time_ms": self.processing_time_ms,
            "data_freshness": self.data_freshness
        }


class AuditRequest(BaseModel):
    """Request model for triggering an audit"""
    force_refresh: bool = False  # Force fresh data fetch
    include_recommendations: bool = True
    date_range_days: int = 30  # Days to analyze


class AuditStatus(BaseModel):
    """Status of an ongoing audit"""
    audit_id: str
    status: str  # pending, processing, completed, failed
    progress: int = 0  # 0-100
    message: str = ""
    estimated_completion: Optional[datetime] = None


class AuditHistoryItem(BaseModel):
    """Simplified audit item for history view"""
    audit_id: str
    audit_date: datetime
    seo_score: float
    score_delta: Optional[float]
    total_issues: int
    critical_issues: int
    trend: str  # improved, declined, stable