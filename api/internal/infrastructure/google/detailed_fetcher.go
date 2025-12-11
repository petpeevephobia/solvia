package google

import (
	"context"
	"fmt"
	"net/http"
	"time"
)

// DetailedGSCDataFetcher handles detailed GSC data fetching (1:1 with Python)
// Implements pagination, weekly chunks, and batch processing
type DetailedGSCDataFetcher struct {
	client     *SearchConsoleClient
	maxRetries int
	retryDelay time.Duration
	batchSize  int
	rowLimit   int // Max GSC allows: 25000
}

// NewDetailedGSCDataFetcher creates a new detailed data fetcher
func NewDetailedGSCDataFetcher(client *SearchConsoleClient) *DetailedGSCDataFetcher {
	return &DetailedGSCDataFetcher{
		client:     client,
		maxRetries: 3,
		retryDelay: 2 * time.Second,
		batchSize:  1000,
		rowLimit:   25000,
	}
}

// PipelineResult represents the result of a data pipeline run
type PipelineResult struct {
	Status           string    `json:"status"`
	DateRange        string    `json:"date_range"`
	QueriesProcessed int       `json:"queries_processed"`
	PagesProcessed   int       `json:"pages_processed"`
	ProcessingTime   float64   `json:"processing_time_ms"`
	StartDate        time.Time `json:"start_date"`
	EndDate          time.Time `json:"end_date"`
	Error            string    `json:"error,omitempty"`
}

// QueryData represents normalized query-level GSC data
type QueryData struct {
	UserEmail   string    `json:"user_email"`
	WebsiteURL  string    `json:"website_url"`
	QueryText   string    `json:"query_text"`
	Date        time.Time `json:"date"`
	Clicks      int       `json:"clicks"`
	Impressions int       `json:"impressions"`
	CTR         float64   `json:"ctr"`
	Position    float64   `json:"position"`
}

// PageData represents normalized page-level GSC data
type PageData struct {
	UserEmail   string    `json:"user_email"`
	WebsiteURL  string    `json:"website_url"`
	PageURL     string    `json:"page_url"`
	Date        time.Time `json:"date"`
	Clicks      int       `json:"clicks"`
	Impressions int       `json:"impressions"`
	CTR         float64   `json:"ctr"`
	Position    float64   `json:"position"`
}

// DetailedFetchConfig configures the data fetch operation
type DetailedFetchConfig struct {
	UserEmail        string
	WebsiteURL       string
	StartDate        time.Time
	EndDate          time.Time
	ForceFullRefresh bool
	FetchQueries     bool
	FetchPages       bool
}

// DetailedFetchResult contains the fetched detailed data
type DetailedFetchResult struct {
	Queries          []QueryData  `json:"queries"`
	Pages            []PageData   `json:"pages"`
	DailyMetrics     []DailyMetric `json:"daily_metrics"`
	TotalQueries     int          `json:"total_queries"`
	TotalPages       int          `json:"total_pages"`
	ProcessedChunks  int          `json:"processed_chunks"`
}

// FetchDetailedData fetches detailed GSC data with pagination and weekly chunks (1:1 with Python)
func (f *DetailedGSCDataFetcher) FetchDetailedData(ctx context.Context, httpClient *http.Client, config *DetailedFetchConfig) (*DetailedFetchResult, error) {
	result := &DetailedFetchResult{
		Queries:      []QueryData{},
		Pages:        []PageData{},
		DailyMetrics: []DailyMetric{},
	}

	// Process data in weekly chunks to manage API quotas and memory
	currentDate := config.StartDate
	chunkCount := 0

	for currentDate.Before(config.EndDate) || currentDate.Equal(config.EndDate) {
		// Calculate chunk end (7 days from current or end date, whichever is first)
		chunkEnd := currentDate.AddDate(0, 0, 6)
		if chunkEnd.After(config.EndDate) {
			chunkEnd = config.EndDate
		}

		// Fetch queries for this chunk
		if config.FetchQueries {
			chunkQueries, err := f.fetchQueriesWithPagination(ctx, httpClient, config.WebsiteURL, currentDate, chunkEnd)
			if err != nil {
				// Log error but continue processing
				fmt.Printf("[GSC] Warning: Query fetch failed for chunk %s to %s: %v\n",
					currentDate.Format("2006-01-02"), chunkEnd.Format("2006-01-02"), err)
			} else {
				// Normalize and add to result
				for _, q := range chunkQueries {
					result.Queries = append(result.Queries, f.normalizeQueryData(config.UserEmail, config.WebsiteURL, q))
				}
			}
		}

		// Fetch pages for this chunk
		if config.FetchPages {
			chunkPages, err := f.fetchPagesWithPagination(ctx, httpClient, config.WebsiteURL, currentDate, chunkEnd)
			if err != nil {
				fmt.Printf("[GSC] Warning: Page fetch failed for chunk %s to %s: %v\n",
					currentDate.Format("2006-01-02"), chunkEnd.Format("2006-01-02"), err)
			} else {
				for _, p := range chunkPages {
					result.Pages = append(result.Pages, f.normalizePageData(config.UserEmail, config.WebsiteURL, p))
				}
			}
		}

		chunkCount++
		// Move to next chunk
		currentDate = chunkEnd.AddDate(0, 0, 1)

		// Small delay between chunks to respect API limits
		select {
		case <-ctx.Done():
			return result, ctx.Err()
		case <-time.After(200 * time.Millisecond):
		}
	}

	// Fetch daily metrics for the entire period (needed for V1/V2 calculations)
	dailyMetrics, err := f.client.GetTimeSeriesMetrics(ctx, httpClient, config.WebsiteURL, config.StartDate, config.EndDate)
	if err == nil {
		result.DailyMetrics = dailyMetrics
	}

	result.TotalQueries = len(result.Queries)
	result.TotalPages = len(result.Pages)
	result.ProcessedChunks = chunkCount

	return result, nil
}

// fetchQueriesWithPagination fetches all queries with GSC pagination (25000 row limit)
func (f *DetailedGSCDataFetcher) fetchQueriesWithPagination(ctx context.Context, httpClient *http.Client, websiteURL string, startDate, endDate time.Time) ([]rawQueryRow, error) {
	var allQueries []rawQueryRow
	startRow := 0

	for {
		// Build request with pagination
		rows, err := f.client.querySearchAnalyticsWithPagination(ctx, httpClient, websiteURL, startDate, endDate,
			[]string{"query", "date"}, f.rowLimit, startRow)
		if err != nil {
			return allQueries, err
		}

		if len(rows) == 0 {
			break
		}

		// Convert to rawQueryRow
		for _, row := range rows {
			if len(row.Keys) >= 2 {
				allQueries = append(allQueries, rawQueryRow{
					Query:       row.Keys[0],
					Date:        row.Keys[1],
					Clicks:      int(row.Clicks),
					Impressions: int(row.Impressions),
					CTR:         row.CTR,
					Position:    row.Position,
				})
			}
		}

		// If we got less than row limit, we're done
		if len(rows) < f.rowLimit {
			break
		}

		startRow += f.rowLimit
	}

	return allQueries, nil
}

// fetchPagesWithPagination fetches all pages with GSC pagination
func (f *DetailedGSCDataFetcher) fetchPagesWithPagination(ctx context.Context, httpClient *http.Client, websiteURL string, startDate, endDate time.Time) ([]rawPageRow, error) {
	var allPages []rawPageRow
	startRow := 0

	for {
		rows, err := f.client.querySearchAnalyticsWithPagination(ctx, httpClient, websiteURL, startDate, endDate,
			[]string{"page", "date"}, f.rowLimit, startRow)
		if err != nil {
			return allPages, err
		}

		if len(rows) == 0 {
			break
		}

		for _, row := range rows {
			if len(row.Keys) >= 2 {
				allPages = append(allPages, rawPageRow{
					PageURL:     row.Keys[0],
					Date:        row.Keys[1],
					Clicks:      int(row.Clicks),
					Impressions: int(row.Impressions),
					CTR:         row.CTR,
					Position:    row.Position,
				})
			}
		}

		if len(rows) < f.rowLimit {
			break
		}

		startRow += f.rowLimit
	}

	return allPages, nil
}

// rawQueryRow represents raw query data from GSC
type rawQueryRow struct {
	Query       string
	Date        string
	Clicks      int
	Impressions int
	CTR         float64
	Position    float64
}

// rawPageRow represents raw page data from GSC
type rawPageRow struct {
	PageURL     string
	Date        string
	Clicks      int
	Impressions int
	CTR         float64
	Position    float64
}

// normalizeQueryData normalizes raw query data into database format (1:1 with Python)
func (f *DetailedGSCDataFetcher) normalizeQueryData(userEmail, websiteURL string, raw rawQueryRow) QueryData {
	date, _ := time.Parse("2006-01-02", raw.Date)

	// Limit query text length
	queryText := raw.Query
	if len(queryText) > 500 {
		queryText = queryText[:500]
	}

	// Normalize values
	clicks := raw.Clicks
	if clicks < 0 {
		clicks = 0
	}

	impressions := raw.Impressions
	if impressions < 0 {
		impressions = 0
	}

	ctr := raw.CTR
	if ctr < 0 {
		ctr = 0
	}
	if ctr > 1 {
		ctr = 1
	}

	position := raw.Position
	if position < 0.1 {
		position = 0.1
	}

	return QueryData{
		UserEmail:   userEmail,
		WebsiteURL:  websiteURL,
		QueryText:   queryText,
		Date:        date,
		Clicks:      clicks,
		Impressions: impressions,
		CTR:         ctr,
		Position:    position,
	}
}

// normalizePageData normalizes raw page data into database format (1:1 with Python)
func (f *DetailedGSCDataFetcher) normalizePageData(userEmail, websiteURL string, raw rawPageRow) PageData {
	date, _ := time.Parse("2006-01-02", raw.Date)

	// Limit URL length
	pageURL := raw.PageURL
	if len(pageURL) > 2000 {
		pageURL = pageURL[:2000]
	}

	clicks := raw.Clicks
	if clicks < 0 {
		clicks = 0
	}

	impressions := raw.Impressions
	if impressions < 0 {
		impressions = 0
	}

	ctr := raw.CTR
	if ctr < 0 {
		ctr = 0
	}
	if ctr > 1 {
		ctr = 1
	}

	position := raw.Position
	if position < 0.1 {
		position = 0.1
	}

	return PageData{
		UserEmail:   userEmail,
		WebsiteURL:  websiteURL,
		PageURL:     pageURL,
		Date:        date,
		Clicks:      clicks,
		Impressions: impressions,
		CTR:         ctr,
		Position:    position,
	}
}

// GetFetchDateRange determines optimal date range for fetching (1:1 with Python)
func (f *DetailedGSCDataFetcher) GetFetchDateRange(lastFetchDate *time.Time, forceFullRefresh bool) (startDate, endDate time.Time) {
	// GSC data is typically available with 1-2 day delay
	endDate = time.Now().AddDate(0, 0, -1)

	if forceFullRefresh {
		// Full refresh: get last 16 months (GSC limit is ~480 days)
		startDate = endDate.AddDate(0, 0, -480)
		return startDate, endDate
	}

	if lastFetchDate != nil && !lastFetchDate.IsZero() {
		// Incremental: start from day after last fetch
		startDate = lastFetchDate.AddDate(0, 0, 1)

		// Don't fetch if already up to date
		if startDate.After(endDate) {
			startDate = endDate
		}
		return startDate, endDate
	}

	// Default: last 90 days for new users
	startDate = endDate.AddDate(0, 0, -90)
	return startDate, endDate
}

// ValidateQueryData validates normalized query data
func ValidateQueryData(data *QueryData) bool {
	return data.QueryText != "" &&
		len(data.QueryText) > 0 &&
		!data.Date.IsZero() &&
		data.Clicks >= 0 &&
		data.Impressions >= 0 &&
		data.CTR >= 0 && data.CTR <= 1 &&
		data.Position > 0
}

// ValidatePageData validates normalized page data
func ValidatePageData(data *PageData) bool {
	return data.PageURL != "" &&
		len(data.PageURL) > 0 &&
		!data.Date.IsZero() &&
		data.Clicks >= 0 &&
		data.Impressions >= 0 &&
		data.CTR >= 0 && data.CTR <= 1 &&
		data.Position > 0
}

// CalculateDailyAggregates calculates aggregated metrics for a specific date
type DailyAggregate struct {
	UserEmail        string    `json:"user_email"`
	WebsiteURL       string    `json:"website_url"`
	Date             time.Time `json:"date"`
	TotalClicks      int       `json:"total_clicks"`
	TotalImpressions int       `json:"total_impressions"`
	AvgCTR           float64   `json:"avg_ctr"`
	AvgPosition      float64   `json:"avg_position"`
	UniqueQueries    int       `json:"unique_queries"`
	UniquePages      int       `json:"unique_pages"`
}

// CalculateDailyAggregatesFromData calculates daily aggregates from query/page data
func CalculateDailyAggregatesFromData(queries []QueryData, pages []PageData, userEmail, websiteURL string) map[string]*DailyAggregate {
	aggregates := make(map[string]*DailyAggregate)

	// Process queries
	for _, q := range queries {
		dateKey := q.Date.Format("2006-01-02")
		if _, exists := aggregates[dateKey]; !exists {
			aggregates[dateKey] = &DailyAggregate{
				UserEmail:  userEmail,
				WebsiteURL: websiteURL,
				Date:       q.Date,
			}
		}
		agg := aggregates[dateKey]
		agg.TotalClicks += q.Clicks
		agg.TotalImpressions += q.Impressions
		agg.UniqueQueries++
	}

	// Process pages for unique page count
	pageCounts := make(map[string]map[string]bool) // date -> page -> exists
	for _, p := range pages {
		dateKey := p.Date.Format("2006-01-02")
		if _, exists := pageCounts[dateKey]; !exists {
			pageCounts[dateKey] = make(map[string]bool)
		}
		pageCounts[dateKey][p.PageURL] = true
	}

	// Update unique page counts
	for dateKey, pages := range pageCounts {
		if agg, exists := aggregates[dateKey]; exists {
			agg.UniquePages = len(pages)
		}
	}

	// Calculate CTR and position averages
	for _, agg := range aggregates {
		if agg.TotalImpressions > 0 {
			agg.AvgCTR = float64(agg.TotalClicks) / float64(agg.TotalImpressions)
		}
	}

	return aggregates
}

// GetTopQueriesFromData returns top N queries by clicks from fetched data
func GetTopQueriesFromData(queries []QueryData, limit int) []QueryData {
	if len(queries) <= limit {
		return queries
	}

	// Aggregate queries by text (sum metrics across dates)
	queryMap := make(map[string]*QueryData)
	for _, q := range queries {
		if existing, exists := queryMap[q.QueryText]; exists {
			existing.Clicks += q.Clicks
			existing.Impressions += q.Impressions
		} else {
			copy := q
			queryMap[q.QueryText] = &copy
		}
	}

	// Convert to slice
	var aggregated []QueryData
	for _, q := range queryMap {
		// Recalculate CTR after aggregation
		if q.Impressions > 0 {
			q.CTR = float64(q.Clicks) / float64(q.Impressions)
		}
		aggregated = append(aggregated, *q)
	}

	// Sort by clicks (descending)
	for i := 0; i < len(aggregated)-1; i++ {
		for j := i + 1; j < len(aggregated); j++ {
			if aggregated[j].Clicks > aggregated[i].Clicks {
				aggregated[i], aggregated[j] = aggregated[j], aggregated[i]
			}
		}
	}

	if len(aggregated) > limit {
		return aggregated[:limit]
	}
	return aggregated
}

// GetTopPagesFromData returns top N pages by clicks from fetched data
func GetTopPagesFromData(pages []PageData, limit int) []PageData {
	if len(pages) <= limit {
		return pages
	}

	// Aggregate pages by URL
	pageMap := make(map[string]*PageData)
	for _, p := range pages {
		if existing, exists := pageMap[p.PageURL]; exists {
			existing.Clicks += p.Clicks
			existing.Impressions += p.Impressions
		} else {
			copy := p
			pageMap[p.PageURL] = &copy
		}
	}

	// Convert to slice
	var aggregated []PageData
	for _, p := range pageMap {
		if p.Impressions > 0 {
			p.CTR = float64(p.Clicks) / float64(p.Impressions)
		}
		aggregated = append(aggregated, *p)
	}

	// Sort by clicks (descending)
	for i := 0; i < len(aggregated)-1; i++ {
		for j := i + 1; j < len(aggregated); j++ {
			if aggregated[j].Clicks > aggregated[i].Clicks {
				aggregated[i], aggregated[j] = aggregated[j], aggregated[i]
			}
		}
	}

	if len(aggregated) > limit {
		return aggregated[:limit]
	}
	return aggregated
}
