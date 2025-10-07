"""
User models and schemas for Solvia authentication system.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr


class UserCreate(UserBase):
    """Model for user registration."""
    password: str


class UserLogin(BaseModel):
    """Model for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Model for user response (without sensitive data)."""
    id: str
    message: Optional[str] = None
    is_verified: Optional[bool] = False
    created_at: Optional[str] = None


class UserInDB(UserResponse):
    """Model for user in database (includes hashed password)."""
    password_hash: str
    verification_token: Optional[str] = None
    reset_token: Optional[str] = None


class TokenResponse(BaseModel):
    """Model for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: float


class TokenData(BaseModel):
    """Model for token payload data."""
    email: Optional[str] = None


class PasswordReset(BaseModel):
    """Model for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Model for password reset confirmation."""
    token: str
    new_password: str


class EmailVerification(BaseModel):
    """Model for email verification."""
    token: str


# Google Search Console Filter Models

class DimensionFilter(BaseModel):
    """Single dimension filter for GSC data (e.g., device=MOBILE)."""
    dimension: str  # device, country, page, query, searchAppearance
    operator: str = "equals"  # equals, contains, notContains, notEquals, includingRegex, excludingRegex
    expression: str


class FilterGroup(BaseModel):
    """Group of filters with AND/OR logic."""
    group_type: str = "and"  # and, or
    filters: List[DimensionFilter]


class GSCFilterRequest(BaseModel):
    """Complete filter request from frontend - matches GSC API format exactly."""

    # Date range (required)
    start_date: date
    end_date: date

    # Search type (optional, defaults to web)
    search_type: str = "web"  # web, image, video, discover, news, googleNews

    # Dimensions to group by (optional)
    dimensions: List[str] = ["date"]  # date, query, page, country, device, searchAppearance

    # Filters (optional)
    filter_groups: Optional[List[FilterGroup]] = None

    # Aggregation (optional)
    aggregation_type: str = "auto"  # auto, byPage, byProperty, byNewsShowcasePanel

    # Pagination (optional)
    row_limit: int = 1000
    start_row: int = 0

    # Data state (optional)
    data_state: str = "final"  # final, all

    # Comparison mode (optional)
    comparison_enabled: bool = False
    comparison_start_date: Optional[date] = None
    comparison_end_date: Optional[date] = None


class GSCMetricsResponse(BaseModel):
    """GSC metrics response - 1:1 with Google Search Console."""

    # Current period metrics
    total_clicks: int
    total_impressions: int
    average_ctr: float  # As decimal (0.20 for 20%)
    average_position: float

    # Comparison metrics (if comparison enabled)
    comparison_clicks: Optional[int] = None
    comparison_impressions: Optional[int] = None
    comparison_ctr: Optional[float] = None
    comparison_position: Optional[float] = None

    # Change indicators (if comparison enabled)
    clicks_change: Optional[int] = None
    impressions_change: Optional[int] = None
    ctr_change: Optional[float] = None
    position_change: Optional[float] = None

    # Metadata
    date_range: str
    search_type: str
    filters_applied: List[str]
    row_count: int  # Number of data rows returned


class DateRangePreset(BaseModel):
    """Predefined date range preset (7d, 28d, etc)."""
    start_date: date
    end_date: date
    days: int
    name: str 