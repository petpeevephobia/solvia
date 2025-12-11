package domain

import "time"

// DashboardCache represents cached dashboard data (1:1 with Python)
type DashboardCache struct {
	ID          int64                  `json:"id,omitempty"`
	UserEmail   string                 `json:"user_email"`
	WebsiteURL  string                 `json:"website_url"`
	Data        map[string]interface{} `json:"data"`
	AIInsights  interface{}            `json:"ai_insights,omitempty"`
	Keywords    interface{}            `json:"keywords,omitempty"`
	CachedAt    time.Time              `json:"cached_at"`
	LastUpdated time.Time              `json:"last_updated"`
}

// CacheDashboardRequest represents the request to cache dashboard data
type CacheDashboardRequest struct {
	DashboardData map[string]interface{} `json:"dashboard_data"`
	AIInsights    interface{}            `json:"ai_insights,omitempty"`
	Keywords      interface{}            `json:"keywords,omitempty"`
}
