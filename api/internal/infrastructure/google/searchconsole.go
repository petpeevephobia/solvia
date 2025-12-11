package google

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/rs/zerolog/log"
)

// GSC retry configuration (1:1 with Python detailed_fetcher.py)
const (
	maxRetries        = 3           // max_retries = 3 in Python
	baseRetryDelay    = 2 * time.Second // retry_delay = 2 in Python
	rateLimitDelay    = 60 * time.Second // Wait time for 429 rate limit
	rowLimit          = 25000       // row_limit = 25000 in Python
)

// SearchConsoleClient handles Google Search Console API operations
type SearchConsoleClient struct {
	baseURL string
}

// NewSearchConsoleClient creates a new GSC client
func NewSearchConsoleClient() *SearchConsoleClient {
	return &SearchConsoleClient{
		baseURL: "https://www.googleapis.com/webmasters/v3",
	}
}

// Site represents a GSC site
type Site struct {
	SiteURL         string `json:"siteUrl"`
	PermissionLevel string `json:"permissionLevel"`
}

// SitesResponse from GSC API
type SitesResponse struct {
	SiteEntry []Site `json:"siteEntry"`
}

// SearchAnalyticsRequest for querying GSC data (1:1 with Python implementation)
type SearchAnalyticsRequest struct {
	StartDate             string                  `json:"startDate"`
	EndDate               string                  `json:"endDate"`
	Dimensions            []string                `json:"dimensions,omitempty"`
	RowLimit              int                     `json:"rowLimit,omitempty"`
	StartRow              int                     `json:"startRow,omitempty"`
	Type                  string                  `json:"type,omitempty"`                  // web, image, video, discover, news, googleNews
	DimensionFilterGroups []DimensionFilterGroup  `json:"dimensionFilterGroups,omitempty"` // CRITICAL: Filter groups
	AggregationType       string                  `json:"aggregationType,omitempty"`       // auto, byPage, byProperty, byNewsShowcasePanel
	DataState             string                  `json:"dataState,omitempty"`             // final, all
}

// DimensionFilterGroup represents a group of dimension filters (1:1 with Python)
type DimensionFilterGroup struct {
	GroupType string            `json:"groupType"` // "and" or "or"
	Filters   []DimensionFilter `json:"filters"`
}

// DimensionFilter represents a single dimension filter (1:1 with Python)
type DimensionFilter struct {
	Dimension  string `json:"dimension"`  // device, country, page, query, searchAppearance
	Operator   string `json:"operator"`   // equals, contains, notContains, notEquals, includingRegex, excludingRegex
	Expression string `json:"expression"` // filter value
}

// SearchAnalyticsRow represents a single row of GSC data
type SearchAnalyticsRow struct {
	Keys        []string `json:"keys"`
	Clicks      float64  `json:"clicks"`
	Impressions float64  `json:"impressions"`
	CTR         float64  `json:"ctr"`
	Position    float64  `json:"position"`
}

// SearchAnalyticsResponse from GSC API
type SearchAnalyticsResponse struct {
	Rows                  []SearchAnalyticsRow `json:"rows"`
	ResponseAggregationType string             `json:"responseAggregationType"`
}

// Metrics represents aggregated GSC metrics
type Metrics struct {
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// GSCMetrics is an alias for Metrics (for backwards compatibility)
type GSCMetrics = Metrics

// AggregatedMetrics represents properly calculated GSC metrics (1:1 with Python)
// CTR = total_clicks / total_impressions (NOT average of individual CTRs)
// Position = sum(position * impressions) / total_impressions (weighted by impressions)
type AggregatedMetrics struct {
	TotalClicks       int     `json:"total_clicks"`
	TotalImpressions  int     `json:"total_impressions"`
	AverageCTR        float64 `json:"average_ctr"`        // Calculated: total_clicks / total_impressions
	AveragePosition   float64 `json:"average_position"`   // Weighted by impressions
	RowCount          int     `json:"row_count"`
	ComparisonClicks      int     `json:"comparison_clicks,omitempty"`
	ComparisonImpressions int     `json:"comparison_impressions,omitempty"`
	ComparisonCTR         float64 `json:"comparison_ctr,omitempty"`
	ComparisonPosition    float64 `json:"comparison_position,omitempty"`
	ClicksChange          int     `json:"clicks_change,omitempty"`
	ImpressionsChange     int     `json:"impressions_change,omitempty"`
	CTRChange             float64 `json:"ctr_change,omitempty"`
	PositionChange        float64 `json:"position_change,omitempty"`
}

// DailyMetric represents metrics for a single day (for V1 vs V2 calculation)
type DailyMetric struct {
	Date        string  `json:"date"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// Changes28Day represents V1 (first day) vs V2 (last day) changes
type Changes28Day struct {
	ImpressionsChange string  `json:"impressions_change"` // "+X" or "-X" or "N/A"
	ClicksChange      string  `json:"clicks_change"`
	CTRChange         string  `json:"ctr_change"`
	PositionChange    string  `json:"position_change"`
	V1Date            string  `json:"v1_date,omitempty"`
	V2Date            string  `json:"v2_date,omitempty"`
	HasSufficientData bool    `json:"has_sufficient_data"`
}

// GetSites returns all sites the user has access to
func (c *SearchConsoleClient) GetSites(ctx context.Context, client *http.Client) ([]Site, error) {
	url := fmt.Sprintf("%s/sites", c.baseURL)

	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to get sites: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("sites request failed with status: %d", resp.StatusCode)
	}

	var sitesResp SitesResponse
	if err := json.NewDecoder(resp.Body).Decode(&sitesResp); err != nil {
		return nil, fmt.Errorf("failed to decode sites: %w", err)
	}

	return sitesResp.SiteEntry, nil
}

// GetMetrics fetches aggregated metrics for a site
func (c *SearchConsoleClient) GetMetrics(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time) (*Metrics, error) {
	rows, err := c.querySearchAnalytics(ctx, client, siteURL, startDate, endDate, nil, 1)
	if err != nil {
		return nil, err
	}

	if len(rows) == 0 {
		return &Metrics{}, nil
	}

	row := rows[0]
	return &Metrics{
		Clicks:      int(row.Clicks),
		Impressions: int(row.Impressions),
		CTR:         row.CTR,
		Position:    row.Position,
	}, nil
}

// GetQueries fetches top queries for a site
func (c *SearchConsoleClient) GetQueries(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time, limit int) ([]SearchAnalyticsRow, error) {
	return c.querySearchAnalytics(ctx, client, siteURL, startDate, endDate, []string{"query"}, limit)
}

// GetPages fetches top pages for a site
func (c *SearchConsoleClient) GetPages(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time, limit int) ([]SearchAnalyticsRow, error) {
	return c.querySearchAnalytics(ctx, client, siteURL, startDate, endDate, []string{"page"}, limit)
}

// GetDailyMetrics fetches daily metrics for a site
func (c *SearchConsoleClient) GetDailyMetrics(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time) ([]SearchAnalyticsRow, error) {
	return c.querySearchAnalytics(ctx, client, siteURL, startDate, endDate, []string{"date"}, 0)
}

// querySearchAnalytics performs a search analytics query
func (c *SearchConsoleClient) querySearchAnalytics(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time, dimensions []string, limit int) ([]SearchAnalyticsRow, error) {
	return c.querySearchAnalyticsWithPagination(ctx, client, siteURL, startDate, endDate, dimensions, limit, 0)
}

// querySearchAnalyticsWithPagination performs a search analytics query with pagination (1:1 with Python)
func (c *SearchConsoleClient) querySearchAnalyticsWithPagination(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time, dimensions []string, limit int, startRow int) ([]SearchAnalyticsRow, error) {
	// URL-encode the site URL for the path (GSC API requirement)
	encodedSiteURL := url.PathEscape(siteURL)
	apiURL := fmt.Sprintf("%s/sites/%s/searchAnalytics/query", c.baseURL, encodedSiteURL)

	reqBody := SearchAnalyticsRequest{
		StartDate:  startDate.Format("2006-01-02"),
		EndDate:    endDate.Format("2006-01-02"),
		Dimensions: dimensions,
	}

	if limit > 0 {
		reqBody.RowLimit = limit
	}

	if startRow > 0 {
		reqBody.StartRow = startRow
	}

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", apiURL, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("search analytics request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		// Read the error response body for debugging
		bodyBytes, _ := io.ReadAll(resp.Body)
		log.Debug().
			Str("api_url", apiURL).
			Int("status", resp.StatusCode).
			Str("response_body", string(bodyBytes)).
			Msg("[GSC] Search Analytics API error")
		return nil, fmt.Errorf("search analytics failed with status: %d", resp.StatusCode)
	}

	var analyticsResp SearchAnalyticsResponse
	if err := json.NewDecoder(resp.Body).Decode(&analyticsResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return analyticsResp.Rows, nil
}

// GetAggregatedMetrics fetches and properly calculates GSC metrics (1:1 with Python)
// This method implements the CRITICAL calculation logic:
// CTR = total_clicks / total_impressions (NOT average of individual row CTRs)
// Position = sum(position * impressions) / total_impressions (weighted average)
func (c *SearchConsoleClient) GetAggregatedMetrics(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time, withComparison bool) (*AggregatedMetrics, error) {
	// Fetch current period data with dimensions to get individual rows
	rows, err := c.querySearchAnalytics(ctx, client, siteURL, startDate, endDate, []string{"query"}, 25000)
	if err != nil {
		return nil, err
	}

	// Calculate current period metrics using GSC-exact method
	current := c.calculateAggregatedFromRows(rows)

	// If comparison requested, fetch previous period
	if withComparison {
		// Calculate comparison period (same length, immediately before)
		periodDuration := endDate.Sub(startDate)
		prevEndDate := startDate.AddDate(0, 0, -1)
		prevStartDate := prevEndDate.Add(-periodDuration)

		prevRows, err := c.querySearchAnalytics(ctx, client, siteURL, prevStartDate, prevEndDate, []string{"query"}, 25000)
		if err == nil && len(prevRows) > 0 {
			prev := c.calculateAggregatedFromRows(prevRows)

			current.ComparisonClicks = prev.TotalClicks
			current.ComparisonImpressions = prev.TotalImpressions
			current.ComparisonCTR = prev.AverageCTR
			current.ComparisonPosition = prev.AveragePosition

			// Calculate changes EXACTLY like Python
			current.ClicksChange = current.TotalClicks - prev.TotalClicks
			current.ImpressionsChange = current.TotalImpressions - prev.TotalImpressions
			current.CTRChange = current.AverageCTR - prev.AverageCTR
			current.PositionChange = current.AveragePosition - prev.AveragePosition
		}
	}

	return current, nil
}

// calculateAggregatedFromRows calculates metrics from rows using GSC-exact method
func (c *SearchConsoleClient) calculateAggregatedFromRows(rows []SearchAnalyticsRow) *AggregatedMetrics {
	if len(rows) == 0 {
		return &AggregatedMetrics{}
	}

	var totalClicks, totalImpressions int
	var totalPositionSum float64 // For weighted position: sum(position * impressions)

	for _, row := range rows {
		totalClicks += int(row.Clicks)
		totalImpressions += int(row.Impressions)
		// CRITICAL: Weight position by impressions (like GSC does)
		totalPositionSum += row.Position * row.Impressions
	}

	// CRITICAL: Calculate CTR as total clicks / total impressions (NOT average of CTRs)
	var averageCTR float64
	if totalImpressions > 0 {
		averageCTR = float64(totalClicks) / float64(totalImpressions)
	}

	// CRITICAL: Position = weighted average by impressions
	var averagePosition float64
	if totalImpressions > 0 {
		averagePosition = totalPositionSum / float64(totalImpressions)
	}

	return &AggregatedMetrics{
		TotalClicks:      totalClicks,
		TotalImpressions: totalImpressions,
		AverageCTR:       averageCTR,
		AveragePosition:  averagePosition,
		RowCount:         len(rows),
	}
}

// GetTimeSeriesMetrics fetches daily time-series data for V1 vs V2 calculations
// This matches Python's fetch_time_series_metrics with dimensions=['date']
func (c *SearchConsoleClient) GetTimeSeriesMetrics(ctx context.Context, client *http.Client, siteURL string, startDate, endDate time.Time) ([]DailyMetric, error) {
	rows, err := c.querySearchAnalytics(ctx, client, siteURL, startDate, endDate, []string{"date"}, 1000)
	if err != nil {
		return nil, err
	}

	var metrics []DailyMetric
	for _, row := range rows {
		if len(row.Keys) > 0 {
			metrics = append(metrics, DailyMetric{
				Date:        row.Keys[0],
				Clicks:      int(row.Clicks),
				Impressions: int(row.Impressions),
				CTR:         row.CTR,
				Position:    row.Position,
			})
		}
	}

	// Sort by date to ensure V1 (first) and V2 (last) are correct
	sortDailyMetrics(metrics)

	return metrics, nil
}

// sortDailyMetrics sorts daily metrics by date ascending
func sortDailyMetrics(metrics []DailyMetric) {
	for i := 0; i < len(metrics)-1; i++ {
		for j := i + 1; j < len(metrics); j++ {
			if metrics[i].Date > metrics[j].Date {
				metrics[i], metrics[j] = metrics[j], metrics[i]
			}
		}
	}
}

// Calculate28DayChanges calculates V1 (first day) vs V2 (last day) changes
// This matches Python's calculate_28day_changes exactly
func Calculate28DayChanges(dailyMetrics []DailyMetric) *Changes28Day {
	changes := &Changes28Day{
		ImpressionsChange: "N/A",
		ClicksChange:      "N/A",
		CTRChange:         "N/A",
		PositionChange:    "N/A",
		HasSufficientData: false,
	}

	if len(dailyMetrics) < 2 {
		return changes
	}

	// V1 = first day, V2 = last day
	v1 := dailyMetrics[0]
	v2 := dailyMetrics[len(dailyMetrics)-1]

	changes.V1Date = v1.Date
	changes.V2Date = v2.Date
	changes.HasSufficientData = true

	// Calculate impressions change
	impDiff := v2.Impressions - v1.Impressions
	if impDiff > 0 {
		changes.ImpressionsChange = fmt.Sprintf("+%d", impDiff)
	} else {
		changes.ImpressionsChange = fmt.Sprintf("%d", impDiff)
	}

	// Calculate clicks change
	clickDiff := v2.Clicks - v1.Clicks
	if clickDiff > 0 {
		changes.ClicksChange = fmt.Sprintf("+%d", clickDiff)
	} else {
		changes.ClicksChange = fmt.Sprintf("%d", clickDiff)
	}

	// Calculate CTR change (as percentage points)
	ctrDiff := (v2.CTR - v1.CTR) * 100 // Convert to percentage points
	if ctrDiff > 0 {
		changes.CTRChange = fmt.Sprintf("+%.2f%%", ctrDiff)
	} else {
		changes.CTRChange = fmt.Sprintf("%.2f%%", ctrDiff)
	}

	// Calculate position change (lower is better, so show improvement as negative)
	posDiff := v2.Position - v1.Position
	if posDiff > 0 {
		changes.PositionChange = fmt.Sprintf("+%.1f", posDiff)
	} else if posDiff < 0 {
		changes.PositionChange = fmt.Sprintf("%.1f", posDiff) // Will show negative
	} else {
		changes.PositionChange = "0.0"
	}

	return changes
}

// ============================================================================
// FILTERED METRICS (1:1 with Python filter system)
// ============================================================================

// FilterRequest represents a full GSC filter request (1:1 with Python)
type FilterRequest struct {
	StartDate         time.Time
	EndDate           time.Time
	Dimensions        []string
	SearchType        string // web, image, video, discover, news, googleNews
	FilterGroups      []DimensionFilterGroup
	AggregationType   string // auto, byPage, byProperty, byNewsShowcasePanel
	DataState         string // final, all
	RowLimit          int
	StartRow          int
	WithComparison    bool
	ComparisonStart   *time.Time
	ComparisonEnd     *time.Time
}

// GetFilteredMetrics fetches GSC metrics with full filter support (1:1 with Python)
// CRITICAL: This method actually sends dimensionFilterGroups to the GSC API
func (c *SearchConsoleClient) GetFilteredMetrics(ctx context.Context, client *http.Client, siteURL string, filterReq *FilterRequest) (*AggregatedMetrics, error) {
	// Build request body exactly like Python
	reqBody := SearchAnalyticsRequest{
		StartDate:  filterReq.StartDate.Format("2006-01-02"),
		EndDate:    filterReq.EndDate.Format("2006-01-02"),
		RowLimit:   filterReq.RowLimit,
		StartRow:   filterReq.StartRow,
	}

	// Add dimensions
	if len(filterReq.Dimensions) > 0 {
		reqBody.Dimensions = filterReq.Dimensions
	} else {
		reqBody.Dimensions = []string{"query"} // Default for aggregation
	}

	// Add row limit if not set
	if reqBody.RowLimit == 0 {
		reqBody.RowLimit = 25000
	}

	// Add search type if not default 'web'
	if filterReq.SearchType != "" && filterReq.SearchType != "web" {
		reqBody.Type = filterReq.SearchType
	}

	// CRITICAL: Add filter groups if provided (this was missing!)
	if len(filterReq.FilterGroups) > 0 {
		reqBody.DimensionFilterGroups = filterReq.FilterGroups
	}

	// Add aggregation type if not 'auto'
	if filterReq.AggregationType != "" && filterReq.AggregationType != "auto" {
		reqBody.AggregationType = filterReq.AggregationType
	}

	// Add data state if not 'final'
	if filterReq.DataState != "" && filterReq.DataState != "final" {
		reqBody.DataState = filterReq.DataState
	}

	// Execute query
	rows, err := c.querySearchAnalyticsWithFilters(ctx, client, siteURL, reqBody)
	if err != nil {
		return nil, err
	}

	// Calculate current period metrics using GSC-exact method
	current := c.calculateAggregatedFromRows(rows)

	// If comparison requested, fetch comparison period with same filters
	if filterReq.WithComparison {
		var compStartDate, compEndDate time.Time

		if filterReq.ComparisonStart != nil && filterReq.ComparisonEnd != nil {
			compStartDate = *filterReq.ComparisonStart
			compEndDate = *filterReq.ComparisonEnd
		} else {
			// Calculate default comparison period (same length, immediately before)
			periodDuration := filterReq.EndDate.Sub(filterReq.StartDate)
			compEndDate = filterReq.StartDate.AddDate(0, 0, -1)
			compStartDate = compEndDate.Add(-periodDuration)
		}

		compReqBody := reqBody
		compReqBody.StartDate = compStartDate.Format("2006-01-02")
		compReqBody.EndDate = compEndDate.Format("2006-01-02")

		compRows, err := c.querySearchAnalyticsWithFilters(ctx, client, siteURL, compReqBody)
		if err == nil && len(compRows) > 0 {
			comp := c.calculateAggregatedFromRows(compRows)

			current.ComparisonClicks = comp.TotalClicks
			current.ComparisonImpressions = comp.TotalImpressions
			current.ComparisonCTR = comp.AverageCTR
			current.ComparisonPosition = comp.AveragePosition

			// Calculate changes EXACTLY like Python
			current.ClicksChange = current.TotalClicks - comp.TotalClicks
			current.ImpressionsChange = current.TotalImpressions - comp.TotalImpressions
			current.CTRChange = current.AverageCTR - comp.AverageCTR
			current.PositionChange = current.AveragePosition - comp.AveragePosition
		}
	}

	return current, nil
}

// querySearchAnalyticsWithFilters executes a search analytics query with full filter support
// Includes retry logic with exponential backoff (1:1 with Python _make_gsc_request)
func (c *SearchConsoleClient) querySearchAnalyticsWithFilters(ctx context.Context, client *http.Client, siteURL string, reqBody SearchAnalyticsRequest) ([]SearchAnalyticsRow, error) {
	// URL-encode the site URL for the path (GSC API requirement)
	encodedSiteURL := url.PathEscape(siteURL)
	apiURL := fmt.Sprintf("%s/sites/%s/searchAnalytics/query", c.baseURL, encodedSiteURL)

	bodyBytes, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	var lastErr error

	// Retry loop with exponential backoff (1:1 with Python)
	for attempt := 0; attempt < maxRetries; attempt++ {
		// Create new request for each attempt
		req, err := http.NewRequestWithContext(ctx, "POST", apiURL, bytes.NewReader(bodyBytes))
		if err != nil {
			return nil, fmt.Errorf("failed to create request: %w", err)
		}
		req.Header.Set("Content-Type", "application/json")

		resp, err := client.Do(req)
		if err != nil {
			lastErr = fmt.Errorf("search analytics request failed (attempt %d/%d): %w", attempt+1, maxRetries, err)
			// Wait before retry with exponential backoff
			if attempt < maxRetries-1 {
				delay := baseRetryDelay * time.Duration(1<<attempt) // 2s, 4s, 8s...
				select {
				case <-ctx.Done():
					return nil, ctx.Err()
				case <-time.After(delay):
				}
			}
			continue
		}

		// Handle rate limiting (429 status) - 1:1 with Python
		if resp.StatusCode == http.StatusTooManyRequests {
			resp.Body.Close()
			lastErr = fmt.Errorf("rate limit exceeded (429) on attempt %d/%d", attempt+1, maxRetries)
			if attempt < maxRetries-1 {
				select {
				case <-ctx.Done():
					return nil, ctx.Err()
				case <-time.After(rateLimitDelay):
				}
			}
			continue
		}

		// Handle server errors (5xx) - retry
		if resp.StatusCode >= 500 {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			lastErr = fmt.Errorf("server error (status %d) on attempt %d/%d: %s", resp.StatusCode, attempt+1, maxRetries, string(body))
			if attempt < maxRetries-1 {
				delay := baseRetryDelay * time.Duration(1<<attempt)
				select {
				case <-ctx.Done():
					return nil, ctx.Err()
				case <-time.After(delay):
				}
			}
			continue
		}

		// Handle client errors (4xx except 429) - don't retry
		if resp.StatusCode >= 400 && resp.StatusCode != http.StatusTooManyRequests {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			return nil, fmt.Errorf("client error (status %d): %s", resp.StatusCode, string(body))
		}

		// Success - parse response
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			return nil, fmt.Errorf("search analytics failed with status: %d, body: %s", resp.StatusCode, string(body))
		}

		var analyticsResp SearchAnalyticsResponse
		if err := json.NewDecoder(resp.Body).Decode(&analyticsResp); err != nil {
			return nil, fmt.Errorf("failed to decode response: %w", err)
		}

		return analyticsResp.Rows, nil
	}

	// All retries exhausted
	return nil, fmt.Errorf("all %d retries exhausted: %w", maxRetries, lastErr)
}
