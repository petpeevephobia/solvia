package domain

// BenchmarkInsights represents AI-generated benchmark analysis (1:1 with Python)
type BenchmarkInsights struct {
	VisibilityPerformance *VisibilityPerformance `json:"visibility_performance"`
	Analysis              *Analysis              `json:"analysis"`
	GeneratedAt           string                 `json:"generated_at,omitempty"`
}

// VisibilityPerformance represents visibility assessment
type VisibilityPerformance struct {
	OverallAssessment string                 `json:"overall_assessment"`
	Metrics           map[string]interface{} `json:"metrics"`
	Score             float64                `json:"score,omitempty"`
	Trend             string                 `json:"trend,omitempty"` // improving, declining, stable
}

// Analysis represents overall SEO analysis
type Analysis struct {
	Summary         string   `json:"summary"`
	Strengths       []string `json:"strengths,omitempty"`
	Improvements    []string `json:"improvements,omitempty"`
	Recommendations []string `json:"recommendations,omitempty"`
}

// DashboardMetrics represents metrics used for benchmark analysis
type DashboardMetrics struct {
	Summary    *MetricsSummary    `json:"summary"`
	TimeSeries *MetricsTimeSeries `json:"time_series,omitempty"`
}

// MetricsSummary contains aggregated metrics
type MetricsSummary struct {
	TotalImpressions int     `json:"total_impressions"`
	TotalClicks      int     `json:"total_clicks"`
	AverageCTR       float64 `json:"average_ctr"`
	AveragePosition  float64 `json:"average_position"`
	SEOScore         float64 `json:"seo_score,omitempty"`
	SEOStage         string  `json:"seo_stage,omitempty"`
}

// MetricsTimeSeries contains daily metrics data
type MetricsTimeSeries struct {
	Days []DailyMetricPoint `json:"days"`
}

// DailyMetricPoint represents a single day's metrics
type DailyMetricPoint struct {
	Date        string  `json:"date"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}
