package domain

import (
	"time"
)

// Website represents a connected GSC website
type Website struct {
	ID              int64     `json:"id"`
	UserEmail       string    `json:"user_email"`
	SiteURL         string    `json:"site_url"`
	PermissionLevel string    `json:"permission_level"`
	IsVerified      bool      `json:"is_verified"` // 1:1 with Python - indicates site ownership verification
	ConnectedAt     time.Time `json:"connected_at"`
	LastSyncAt      time.Time `json:"last_sync_at,omitempty"`
}

// Metrics represents aggregated GSC metrics with change indicators (1:1 with Python)
type Metrics struct {
	UserEmail   string    `json:"user_email"`
	WebsiteURL  string    `json:"website_url"`
	StartDate   time.Time `json:"start_date"`
	EndDate     time.Time `json:"end_date"`
	SEOScore    float64   `json:"seo_score"`
	Impressions int       `json:"impressions"`
	Clicks      int       `json:"clicks"`
	CTR         float64   `json:"ctr"`
	Position    float64   `json:"position"`
	CacheDate   time.Time `json:"cache_date"`

	// Change indicators (comparison with previous period)
	SEOScoreChange    float64 `json:"seo_score_change,omitempty"`
	ImpressionsChange float64 `json:"impressions_change,omitempty"`
	ClicksChange      float64 `json:"clicks_change,omitempty"`
	CTRChange         float64 `json:"ctr_change,omitempty"`
	PositionChange    float64 `json:"position_change,omitempty"`

	// Previous period values (for detailed comparison)
	PrevImpressions int     `json:"prev_impressions,omitempty"`
	PrevClicks      int     `json:"prev_clicks,omitempty"`
	PrevCTR         float64 `json:"prev_ctr,omitempty"`
	PrevPosition    float64 `json:"prev_position,omitempty"`

	// Score breakdown
	Grade         string             `json:"grade,omitempty"`
	ScoreBreakdown map[string]float64 `json:"score_breakdown,omitempty"`

	// Data source
	Source string `json:"source,omitempty"` // "live" or "cached"
}

// Query represents a search query with metrics
type Query struct {
	Query       string  `json:"query"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// Page represents a page with metrics
type Page struct {
	Page        string  `json:"page"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// DailyMetric represents metrics for a single day
type DailyMetric struct {
	Date        time.Time `json:"date"`
	Clicks      int       `json:"clicks"`
	Impressions int       `json:"impressions"`
	CTR         float64   `json:"ctr"`
	Position    float64   `json:"position"`
}

// MetricsFilter for querying GSC data
type MetricsFilter struct {
	StartDate time.Time
	EndDate   time.Time
	Limit     int
}

// DefaultFilter returns a default 30-day filter (1:1 with Python)
// Python: current_end_date = today - timedelta(days=1)
// Python: current_start_date = current_end_date - timedelta(days=29) = 30 days total
func DefaultFilter() MetricsFilter {
	now := time.Now()
	endDate := now.AddDate(0, 0, -1) // Yesterday (GSC data is delayed by 1 day)
	return MetricsFilter{
		StartDate: endDate.AddDate(0, 0, -29), // 30 days total (1:1 with Python)
		EndDate:   endDate,
		Limit:     1000, // 1:1 with Python google_oauth.py:911 - default 1000 rows
	}
}

// CalculateChange calculates percentage change between current and previous values
func CalculateChange(current, previous float64) float64 {
	if previous == 0 {
		if current > 0 {
			return 100.0
		}
		return 0.0
	}
	return ((current - previous) / previous) * 100
}

// ============================================================================
// GSC FILTER SYSTEM (1:1 with Python implementation)
// ============================================================================

// DimensionFilter represents a single filter on a dimension (e.g., device=MOBILE)
type DimensionFilter struct {
	Dimension  string `json:"dimension"`  // device, country, page, query, searchAppearance
	Operator   string `json:"operator"`   // equals, contains, notContains, notEquals, includingRegex, excludingRegex
	Expression string `json:"expression"` // filter value
}

// FilterGroup represents a group of filters with AND/OR logic
type FilterGroup struct {
	GroupType string            `json:"group_type"` // "and" or "or"
	Filters   []DimensionFilter `json:"filters"`
}

// GSCFilterRequest represents the complete filter request from frontend (1:1 with Python)
type GSCFilterRequest struct {
	// Date range (required)
	StartDate time.Time `json:"start_date" binding:"required"`
	EndDate   time.Time `json:"end_date" binding:"required"`

	// Search type (optional, defaults to web)
	SearchType string `json:"search_type"` // web, image, video, discover, news, googleNews

	// Dimensions to group by (optional)
	Dimensions []string `json:"dimensions"` // date, query, page, country, device, searchAppearance

	// Filters (optional)
	FilterGroups []FilterGroup `json:"filter_groups,omitempty"`

	// Aggregation (optional)
	AggregationType string `json:"aggregation_type"` // auto, byPage, byProperty, byNewsShowcasePanel

	// Pagination (optional)
	RowLimit int `json:"row_limit"`
	StartRow int `json:"start_row"`

	// Data state (optional)
	DataState string `json:"data_state"` // final, all

	// Comparison mode (optional)
	ComparisonEnabled   bool       `json:"comparison_enabled"`
	ComparisonStartDate *time.Time `json:"comparison_start_date,omitempty"`
	ComparisonEndDate   *time.Time `json:"comparison_end_date,omitempty"`
}

// DefaultGSCFilterRequest returns default filter request values (1:1 with Python - 30 days)
func DefaultGSCFilterRequest() *GSCFilterRequest {
	now := time.Now()
	endDate := now.AddDate(0, 0, -1)   // GSC data available until yesterday
	startDate := now.AddDate(0, 0, -30) // Default 30 days (1:1 with Python)

	return &GSCFilterRequest{
		StartDate:       startDate,
		EndDate:         endDate,
		SearchType:      "web",
		Dimensions:      []string{"date"},
		AggregationType: "auto",
		RowLimit:        1000,
		StartRow:        0,
		DataState:       "final",
	}
}

// GSCFilterResponse represents the filtered metrics response (1:1 with Python)
type GSCFilterResponse struct {
	// Current period metrics
	TotalClicks      int     `json:"total_clicks"`
	TotalImpressions int     `json:"total_impressions"`
	AverageCTR       float64 `json:"average_ctr"`      // As decimal (0.20 for 20%)
	AveragePosition  float64 `json:"average_position"`
	SEOScore         float64 `json:"seo_score"`

	// Comparison metrics (if comparison enabled)
	ComparisonClicks      *int     `json:"comparison_clicks,omitempty"`
	ComparisonImpressions *int     `json:"comparison_impressions,omitempty"`
	ComparisonCTR         *float64 `json:"comparison_ctr,omitempty"`
	ComparisonPosition    *float64 `json:"comparison_position,omitempty"`

	// Change indicators (if comparison enabled)
	// 1:1 with Python: clicks_change and impressions_change are raw integer differences
	ClicksChange      *int     `json:"clicks_change,omitempty"`
	ImpressionsChange *int     `json:"impressions_change,omitempty"`
	CTRChange         *float64 `json:"ctr_change,omitempty"`
	PositionChange    *float64 `json:"position_change,omitempty"`

	// Metadata
	DateRange      string   `json:"date_range"`
	SearchType     string   `json:"search_type"`
	FiltersApplied []string `json:"filters_applied"`
	RowCount       int      `json:"row_count"` // Number of data rows returned
}

// DateRangePreset represents a predefined date range (24h, 7d, 28d, 3mo)
type DateRangePreset struct {
	StartDate string `json:"start_date"` // ISO format
	EndDate   string `json:"end_date"`   // ISO format
	Days      int    `json:"days"`
	Name      string `json:"name"`
}

// GetDatePreset returns a preset configuration by name
func GetDatePreset(presetName string) (*DateRangePreset, error) {
	now := time.Now()
	endDate := now.AddDate(0, 0, -1) // GSC data available until yesterday

	presets := map[string]*DateRangePreset{
		"24h": {
			StartDate: endDate.Format("2006-01-02"),
			EndDate:   endDate.Format("2006-01-02"),
			Days:      1,
			Name:      "Last 24 hours",
		},
		"7d": {
			StartDate: endDate.AddDate(0, 0, -6).Format("2006-01-02"),
			EndDate:   endDate.Format("2006-01-02"),
			Days:      7,
			Name:      "Last 7 days",
		},
		"28d": {
			StartDate: endDate.AddDate(0, 0, -27).Format("2006-01-02"),
			EndDate:   endDate.Format("2006-01-02"),
			Days:      28,
			Name:      "Last 28 days",
		},
		"3mo": {
			StartDate: endDate.AddDate(0, 0, -89).Format("2006-01-02"),
			EndDate:   endDate.Format("2006-01-02"),
			Days:      90,
			Name:      "Last 3 months",
		},
	}

	if preset, ok := presets[presetName]; ok {
		return preset, nil
	}

	return nil, nil // Will be handled as error in handler
}

// GetAvailablePresets returns all available preset names
func GetAvailablePresets() []string {
	return []string{"24h", "7d", "28d", "3mo"}
}
