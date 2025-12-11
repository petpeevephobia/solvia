package service

import (
	"context"
	"net/http"
	"strings"
	"time"

	"github.com/rs/zerolog/log"

	chatDomain "github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/repository"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/scoring"
)

// UserTokenGetter interface to get user tokens
type UserTokenGetter interface {
	GetUserTokens(ctx context.Context, email string) (accessToken, refreshToken string, err error)
}

// CredentialDeleter interface to delete user credentials (1:1 with Python clear-credentials)
type CredentialDeleter interface {
	DeleteTokens(ctx context.Context, email string) error
}

// GSCService handles GSC business logic
type GSCService struct {
	repo              repository.GSCRepository
	gscClient         *google.SearchConsoleClient
	oauthClient       *google.OAuthClient
	tokenGetter       UserTokenGetter
	credentialDeleter CredentialDeleter // For clearing credentials (1:1 with Python)
}

// NewGSCService creates a new GSC service
func NewGSCService(
	repo repository.GSCRepository,
	gscClient *google.SearchConsoleClient,
	oauthClient *google.OAuthClient,
	tokenGetter UserTokenGetter,
	credentialDeleter CredentialDeleter,
) *GSCService {
	return &GSCService{
		repo:              repo,
		gscClient:         gscClient,
		oauthClient:       oauthClient,
		tokenGetter:       tokenGetter,
		credentialDeleter: credentialDeleter,
	}
}

// GetWebsites returns all connected websites for a user
func (s *GSCService) GetWebsites(ctx context.Context, userEmail string) ([]domain.Website, error) {
	// Get from database first
	websites, err := s.repo.GetWebsites(ctx, userEmail)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return websites, nil
}

// GetSelectedWebsite returns the user's selected website URL (1:1 parity with original Python)
func (s *GSCService) GetSelectedWebsite(ctx context.Context, userEmail string) (string, error) {
	websiteURL, err := s.repo.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return "", apperrors.DatabaseError(err)
	}

	return websiteURL, nil
}

// SetSelectedWebsite sets the user's selected website URL (1:1 parity with original Python)
func (s *GSCService) SetSelectedWebsite(ctx context.Context, userEmail, websiteURL string) error {
	if err := s.repo.SetSelectedWebsite(ctx, userEmail, websiteURL); err != nil {
		return apperrors.DatabaseError(err)
	}

	return nil
}

// SyncWebsites fetches websites from GSC and syncs to database
func (s *GSCService) SyncWebsites(ctx context.Context, userEmail string) ([]domain.Website, error) {
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	// Fetch from GSC API
	sites, err := s.gscClient.GetSites(ctx, client)
	if err != nil {
		return nil, apperrors.ExternalServiceError("Google Search Console", err)
	}

	// Save to database
	var websites []domain.Website
	for _, site := range sites {
		website := &domain.Website{
			UserEmail:       userEmail,
			SiteURL:         site.SiteURL,
			PermissionLevel: site.PermissionLevel,
			ConnectedAt:     time.Now(),
		}

		if err := s.repo.SaveWebsite(ctx, website); err != nil {
			return nil, apperrors.DatabaseError(err)
		}

		websites = append(websites, *website)
	}

	return websites, nil
}

// GetMetrics returns metrics for a website with comparison period (1:1 with Python)
// CRITICAL: Uses proper GSC calculation - CTR = sum(clicks)/sum(impressions), Position = weighted by impressions
// ULTRATHINK: Includes automatic 401 retry with token refresh (1:1 with Python)
func (s *GSCService) GetMetrics(ctx context.Context, userEmail, websiteURL string, filter domain.MetricsFilter) (*domain.Metrics, error) {
	// Check cache first
	cached, err := s.repo.GetCachedMetrics(ctx, userEmail, websiteURL, filter.StartDate, filter.EndDate)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if cached != nil {
		cached.Source = "cached"
		return cached, nil
	}

	// Fetch from GSC API with automatic 401 retry
	var aggregatedMetrics *google.AggregatedMetrics

	err = s.executeWithAutoRefresh(ctx, userEmail, func(client *http.Client) error {
		var fetchErr error
		// CRITICAL FIX: Use GetAggregatedMetrics for proper CTR and Position calculation (1:1 with Python)
		// CTR = total_clicks / total_impressions (NOT average of individual row CTRs)
		// Position = sum(position * impressions) / total_impressions (weighted average)
		aggregatedMetrics, fetchErr = s.gscClient.GetAggregatedMetrics(ctx, client, websiteURL, filter.StartDate, filter.EndDate, true)
		return fetchErr
	})
	if err != nil {
		return nil, apperrors.ExternalServiceError("Google Search Console", err)
	}

	// Calculate SEO score using the new scoring engine (1:1 with Python)
	scoringMetrics := &scoring.GSCMetrics{
		Impressions:       aggregatedMetrics.TotalImpressions,
		Clicks:            aggregatedMetrics.TotalClicks,
		CTR:               aggregatedMetrics.AverageCTR,     // Properly calculated: total_clicks / total_impressions
		Position:          aggregatedMetrics.AveragePosition, // Properly calculated: weighted by impressions
		ImpressionsChange: domain.CalculateChange(float64(aggregatedMetrics.TotalImpressions), float64(aggregatedMetrics.ComparisonImpressions)),
		ClicksChange:      domain.CalculateChange(float64(aggregatedMetrics.TotalClicks), float64(aggregatedMetrics.ComparisonClicks)),
		CTRChange:         domain.CalculateChange(aggregatedMetrics.AverageCTR, aggregatedMetrics.ComparisonCTR),
		PositionChange:    aggregatedMetrics.AveragePosition - aggregatedMetrics.ComparisonPosition, // Not percentage for position
	}

	// Use historical data for trend scoring
	historicalData := &scoring.HistoricalData{
		Clicks:   aggregatedMetrics.ComparisonClicks,
		Position: aggregatedMetrics.ComparisonPosition,
		CTR:      aggregatedMetrics.ComparisonCTR,
	}

	seoScoreResult := scoring.CalculateGSCScoreWithHistory(scoringMetrics, historicalData)

	// Calculate previous period SEO score for comparison
	prevScoringMetrics := &scoring.GSCMetrics{
		Impressions: aggregatedMetrics.ComparisonImpressions,
		Clicks:      aggregatedMetrics.ComparisonClicks,
		CTR:         aggregatedMetrics.ComparisonCTR,
		Position:    aggregatedMetrics.ComparisonPosition,
	}
	prevSeoScoreResult := scoring.CalculateGSCScore(prevScoringMetrics)

	metrics := &domain.Metrics{
		UserEmail:   userEmail,
		WebsiteURL:  websiteURL,
		StartDate:   filter.StartDate,
		EndDate:     filter.EndDate,
		SEOScore:    seoScoreResult.Total,
		Impressions: aggregatedMetrics.TotalImpressions,
		Clicks:      aggregatedMetrics.TotalClicks,
		CTR:         aggregatedMetrics.AverageCTR,     // Properly calculated
		Position:    aggregatedMetrics.AveragePosition, // Properly calculated
		CacheDate:   time.Now(),

		// Change indicators (1:1 with Python - raw int difference for clicks/impressions)
		SEOScoreChange:    seoScoreResult.Total - prevSeoScoreResult.Total,
		ImpressionsChange: float64(aggregatedMetrics.TotalImpressions - aggregatedMetrics.ComparisonImpressions), // Raw int difference (1:1 with Python)
		ClicksChange:      float64(aggregatedMetrics.TotalClicks - aggregatedMetrics.ComparisonClicks),           // Raw int difference (1:1 with Python)
		CTRChange:         domain.CalculateChange(aggregatedMetrics.AverageCTR, aggregatedMetrics.ComparisonCTR),
		PositionChange:    aggregatedMetrics.AveragePosition - aggregatedMetrics.ComparisonPosition,

		// Previous period values
		PrevImpressions: aggregatedMetrics.ComparisonImpressions,
		PrevClicks:      aggregatedMetrics.ComparisonClicks,
		PrevCTR:         aggregatedMetrics.ComparisonCTR,
		PrevPosition:    aggregatedMetrics.ComparisonPosition,

		// Score breakdown
		Grade:          seoScoreResult.Grade,
		ScoreBreakdown: seoScoreResult.Breakdown,

		Source: "live",
	}

	// Cache metrics
	if err := s.repo.SaveMetrics(ctx, metrics); err != nil {
		// Log but don't fail on cache error
	}

	// Update last sync
	_ = s.repo.UpdateLastSync(ctx, userEmail, websiteURL)

	return metrics, nil
}

// GetQueries returns top queries for a website
func (s *GSCService) GetQueries(ctx context.Context, userEmail, websiteURL string, filter domain.MetricsFilter) ([]domain.Query, error) {
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	rows, err := s.gscClient.GetQueries(ctx, client, websiteURL, filter.StartDate, filter.EndDate, filter.Limit)
	if err != nil {
		return nil, apperrors.ExternalServiceError("Google Search Console", err)
	}

	var queries []domain.Query
	for _, row := range rows {
		if len(row.Keys) > 0 {
			queries = append(queries, domain.Query{
				Query:       row.Keys[0],
				Clicks:      int(row.Clicks),
				Impressions: int(row.Impressions),
				CTR:         row.CTR,
				Position:    row.Position,
			})
		}
	}

	return queries, nil
}

// GetPages returns top pages for a website
func (s *GSCService) GetPages(ctx context.Context, userEmail, websiteURL string, filter domain.MetricsFilter) ([]domain.Page, error) {
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	rows, err := s.gscClient.GetPages(ctx, client, websiteURL, filter.StartDate, filter.EndDate, filter.Limit)
	if err != nil {
		return nil, apperrors.ExternalServiceError("Google Search Console", err)
	}

	var pages []domain.Page
	for _, row := range rows {
		if len(row.Keys) > 0 {
			pages = append(pages, domain.Page{
				Page:        row.Keys[0],
				Clicks:      int(row.Clicks),
				Impressions: int(row.Impressions),
				CTR:         row.CTR,
				Position:    row.Position,
			})
		}
	}

	return pages, nil
}

// GetDailyMetrics returns daily metrics for charts
func (s *GSCService) GetDailyMetrics(ctx context.Context, userEmail, websiteURL string, filter domain.MetricsFilter) ([]domain.DailyMetric, error) {
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	rows, err := s.gscClient.GetDailyMetrics(ctx, client, websiteURL, filter.StartDate, filter.EndDate)
	if err != nil {
		return nil, apperrors.ExternalServiceError("Google Search Console", err)
	}

	var metrics []domain.DailyMetric
	for _, row := range rows {
		if len(row.Keys) > 0 {
			date, _ := time.Parse("2006-01-02", row.Keys[0])
			metrics = append(metrics, domain.DailyMetric{
				Date:        date,
				Clicks:      int(row.Clicks),
				Impressions: int(row.Impressions),
				CTR:         row.CTR,
				Position:    row.Position,
			})
		}
	}

	return metrics, nil
}

// GetWebsiteContext returns website context for chat injection (internal use)
func (s *GSCService) GetWebsiteContext(ctx context.Context, userEmail, websiteURL string) (*WebsiteContext, error) {
	// Get current metrics
	filter := domain.DefaultFilter()
	metrics, err := s.GetMetrics(ctx, userEmail, websiteURL, filter)
	if err != nil {
		return nil, err
	}

	return &WebsiteContext{
		URL:               websiteURL,
		Impressions:       metrics.Impressions,
		Clicks:            metrics.Clicks,
		CTR:               metrics.CTR,
		Position:          metrics.Position,
		SEOScore:          metrics.SEOScore,
		ImpressionsChange: metrics.ImpressionsChange,
		ClicksChange:      metrics.ClicksChange,
		CTRChange:         metrics.CTRChange,
		PositionChange:    metrics.PositionChange,
	}, nil
}

// GetWebsiteMetricsForChat returns metrics in chat domain format (for adapter interface)
// Enhanced to include weekly and daily data for "last week" and "trends" queries
func (s *GSCService) GetWebsiteMetricsForChat(ctx context.Context, userEmail, websiteURL string) (*chatDomain.WebsiteContext, error) {
	log.Debug().
		Str("user", userEmail).
		Str("website", websiteURL).
		Msg("[GSC] GetWebsiteMetricsForChat called")

	wsCtx, err := s.GetWebsiteContext(ctx, userEmail, websiteURL)
	if err != nil {
		log.Error().Err(err).Msg("[GSC] GetWebsiteMetricsForChat failed to get website context")
		return nil, err
	}

	result := &chatDomain.WebsiteContext{
		URL:               wsCtx.URL,
		Impressions:       wsCtx.Impressions,
		Clicks:            wsCtx.Clicks,
		CTR:               wsCtx.CTR,
		Position:          wsCtx.Position,
		SEOScore:          wsCtx.SEOScore,
		ImpressionsChange: wsCtx.ImpressionsChange,
		ClicksChange:      wsCtx.ClicksChange,
		CTRChange:         wsCtx.CTRChange,
		PositionChange:    wsCtx.PositionChange,
	}

	// Fetch weekly data for "last week" queries (last 7 days vs previous 7 days)
	weeklyData, err := s.getWeeklyComparison(ctx, userEmail, websiteURL)
	if err == nil && weeklyData != nil {
		result.WeeklyMetrics = weeklyData
		log.Debug().
			Int("last_week_impressions", weeklyData.LastWeekImpressions).
			Msg("[GSC] GetWebsiteMetricsForChat added weekly data")
	} else if err != nil {
		log.Error().Err(err).Msg("[GSC] GetWebsiteMetricsForChat failed to get weekly data")
	}

	// Fetch daily trend data for "show trends" queries (last 7 days)
	dailyTrend, err := s.getDailyTrendData(ctx, userEmail, websiteURL)
	if err == nil && dailyTrend != nil {
		result.DailyTrend = dailyTrend
		log.Debug().
			Int("daily_trend_count", len(dailyTrend)).
			Msg("[GSC] GetWebsiteMetricsForChat added daily trend data")
	} else if err != nil {
		log.Error().Err(err).Msg("[GSC] GetWebsiteMetricsForChat failed to get daily trend data")
	}

	log.Debug().
		Bool("has_weekly", result.WeeklyMetrics != nil).
		Int("daily_count", len(result.DailyTrend)).
		Msg("[GSC] GetWebsiteMetricsForChat returning result")

	return result, nil
}

// getWeeklyComparison fetches last 7 days vs previous 7 days for "last week" queries
func (s *GSCService) getWeeklyComparison(ctx context.Context, userEmail, websiteURL string) (*chatDomain.WeeklyMetrics, error) {
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	// Calculate date ranges (accounting for 1-day GSC data delay)
	now := time.Now()
	endDate := now.AddDate(0, 0, -1)                          // Yesterday (GSC data delay)
	startDate := endDate.AddDate(0, 0, -6)                    // Last 7 days
	prevEndDate := startDate.AddDate(0, 0, -1)                // Day before last week
	prevStartDate := prevEndDate.AddDate(0, 0, -6)            // Previous 7 days

	// Fetch last week metrics
	lastWeekMetrics, err := s.gscClient.GetAggregatedMetrics(ctx, client, websiteURL, startDate, endDate, false)
	if err != nil {
		return nil, err
	}

	// Fetch previous week metrics
	prevWeekMetrics, err := s.gscClient.GetAggregatedMetrics(ctx, client, websiteURL, prevStartDate, prevEndDate, false)
	if err != nil {
		return nil, err
	}

	// Calculate week-over-week changes
	impressionsChange := domain.CalculateChange(float64(lastWeekMetrics.TotalImpressions), float64(prevWeekMetrics.TotalImpressions))
	clicksChange := domain.CalculateChange(float64(lastWeekMetrics.TotalClicks), float64(prevWeekMetrics.TotalClicks))
	ctrChange := domain.CalculateChange(lastWeekMetrics.AverageCTR, prevWeekMetrics.AverageCTR)
	positionChange := lastWeekMetrics.AveragePosition - prevWeekMetrics.AveragePosition

	return &chatDomain.WeeklyMetrics{
		LastWeekImpressions: lastWeekMetrics.TotalImpressions,
		LastWeekClicks:      lastWeekMetrics.TotalClicks,
		LastWeekCTR:         lastWeekMetrics.AverageCTR,
		LastWeekPosition:    lastWeekMetrics.AveragePosition,
		PrevWeekImpressions: prevWeekMetrics.TotalImpressions,
		PrevWeekClicks:      prevWeekMetrics.TotalClicks,
		PrevWeekCTR:         prevWeekMetrics.AverageCTR,
		PrevWeekPosition:    prevWeekMetrics.AveragePosition,
		ImpressionsChange:   impressionsChange,
		ClicksChange:        clicksChange,
		CTRChange:           ctrChange,
		PositionChange:      positionChange,
	}, nil
}

// getDailyTrendData fetches daily metrics for the last 7 days for trend visualization
func (s *GSCService) getDailyTrendData(ctx context.Context, userEmail, websiteURL string) ([]chatDomain.DailyPoint, error) {
	log.Debug().
		Str("user", userEmail).
		Str("website", websiteURL).
		Msg("[GSC] getDailyTrendData called")

	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		log.Error().Err(err).Msg("[GSC] getDailyTrendData failed to get HTTP client")
		return nil, err
	}

	// Calculate date range (last 7 days, accounting for 1-day GSC data delay)
	now := time.Now()
	endDate := now.AddDate(0, 0, -1)      // Yesterday
	startDate := endDate.AddDate(0, 0, -6) // 7 days ago

	log.Debug().
		Str("start_date", startDate.Format("2006-01-02")).
		Str("end_date", endDate.Format("2006-01-02")).
		Msg("[GSC] getDailyTrendData fetching metrics")

	// Fetch daily metrics
	rows, err := s.gscClient.GetDailyMetrics(ctx, client, websiteURL, startDate, endDate)
	if err != nil {
		log.Error().Err(err).Msg("[GSC] getDailyTrendData failed to fetch daily metrics")
		return nil, err
	}

	log.Debug().Int("rows_returned", len(rows)).Msg("[GSC] getDailyTrendData raw rows from GSC")

	var dailyPoints []chatDomain.DailyPoint
	for _, row := range rows {
		if len(row.Keys) > 0 {
			dailyPoints = append(dailyPoints, chatDomain.DailyPoint{
				Date:        row.Keys[0],
				Impressions: int(row.Impressions),
				Clicks:      int(row.Clicks),
				CTR:         row.CTR,
				Position:    row.Position,
			})
		}
	}

	log.Debug().Int("daily_points_count", len(dailyPoints)).Msg("[GSC] getDailyTrendData returning daily points")

	return dailyPoints, nil
}

// WebsiteContext provides SEO context for chat (internal)
type WebsiteContext struct {
	URL               string  `json:"url"`
	Impressions       int     `json:"impressions"`
	Clicks            int     `json:"clicks"`
	CTR               float64 `json:"ctr"`
	Position          float64 `json:"position"`
	SEOScore          float64 `json:"seo_score"`
	ImpressionsChange float64 `json:"impressions_change,omitempty"`
	ClicksChange      float64 `json:"clicks_change,omitempty"`
	CTRChange         float64 `json:"ctr_change,omitempty"`
	PositionChange    float64 `json:"position_change,omitempty"`
}

// TokenRefresher interface for refreshing and saving tokens
type TokenRefresher interface {
	RefreshAndSaveTokens(ctx context.Context, email, refreshToken string) (newAccessToken string, err error)
}

// tokenRefresherImpl implements token refresh (set via SetTokenRefresher)
var gscTokenRefresher TokenRefresher

// SetTokenRefresher sets the token refresher (called from main.go)
func SetTokenRefresher(refresher TokenRefresher) {
	gscTokenRefresher = refresher
}

// getHTTPClient gets an authenticated HTTP client for a user
func (s *GSCService) getHTTPClient(ctx context.Context, userEmail string) (*http.Client, error) {
	accessToken, refreshToken, err := s.tokenGetter.GetUserTokens(ctx, userEmail)
	if err != nil {
		return nil, apperrors.New(apperrors.CodeUnauthorized, "Failed to get user tokens", 401)
	}

	return s.oauthClient.GetHTTPClient(ctx, accessToken, refreshToken), nil
}

// getHTTPClientWithRetry gets an HTTP client, and if the operation fails with 401, refreshes token and retries
// This is 1:1 with Python's ULTRATHINK AUTOMATIC RETRY logic
func (s *GSCService) getHTTPClientWithRetry(ctx context.Context, userEmail string) (*http.Client, string, error) {
	accessToken, refreshToken, err := s.tokenGetter.GetUserTokens(ctx, userEmail)
	if err != nil {
		return nil, "", apperrors.New(apperrors.CodeUnauthorized, "Failed to get user tokens", 401)
	}

	return s.oauthClient.GetHTTPClient(ctx, accessToken, refreshToken), refreshToken, nil
}

// executeWithAutoRefresh executes a GSC operation with automatic 401 retry (1:1 with Python)
func (s *GSCService) executeWithAutoRefresh(ctx context.Context, userEmail string, operation func(*http.Client) error) error {
	client, refreshToken, err := s.getHTTPClientWithRetry(ctx, userEmail)
	if err != nil {
		log.Error().Err(err).Msg("[GSC] executeWithAutoRefresh failed to get HTTP client")
		return err
	}

	log.Debug().
		Str("user", userEmail).
		Bool("has_refresh_token", refreshToken != "").
		Msg("[GSC] executeWithAutoRefresh first attempt")

	// First attempt
	err = operation(client)
	if err == nil {
		return nil
	}

	// Check if it's an authentication error (401 or 403)
	errStr := err.Error()
	isAuth := isAuthError(errStr)
	log.Debug().
		Str("error", errStr).
		Bool("is_auth_error", isAuth).
		Msg("[GSC] executeWithAutoRefresh first attempt failed")

	if !isAuth {
		return err
	}

	// ULTRATHINK AUTOMATIC RETRY: Attempt token refresh and retry
	if gscTokenRefresher == nil {
		log.Warn().Msg("[GSC] executeWithAutoRefresh: gscTokenRefresher is nil, cannot refresh")
		return err
	}
	if refreshToken == "" {
		log.Warn().Msg("[GSC] executeWithAutoRefresh: refreshToken is empty, cannot refresh")
		return err
	}

	log.Info().Str("user", userEmail).Msg("[GSC] executeWithAutoRefresh: attempting token refresh")

	// Refresh token
	newAccessToken, refreshErr := gscTokenRefresher.RefreshAndSaveTokens(ctx, userEmail, refreshToken)
	if refreshErr != nil {
		log.Error().Err(refreshErr).Msg("[GSC] executeWithAutoRefresh: token refresh failed")
		return err // Return original error if refresh fails
	}

	log.Info().Msg("[GSC] executeWithAutoRefresh: token refreshed successfully, retrying operation")

	// Retry with new token
	newClient := s.oauthClient.GetHTTPClient(ctx, newAccessToken, refreshToken)
	return operation(newClient)
}

// isAuthError checks if an error is an authentication error (1:1 with Python)
// Updated to also handle 403 errors since Google sometimes returns 403 for token issues
func isAuthError(errStr string) bool {
	lowerErr := strings.ToLower(errStr)
	return strings.Contains(lowerErr, "401") ||
		strings.Contains(lowerErr, "403") || // Google sometimes returns 403 for expired tokens
		strings.Contains(lowerErr, "unauthorized") ||
		strings.Contains(lowerErr, "forbidden") ||
		strings.Contains(lowerErr, "invalid_grant") ||
		strings.Contains(lowerErr, "credentials")
}

// ============================================================================
// GSC FILTER SYSTEM (1:1 with Python implementation)
// ============================================================================

// ApplyFilter applies filters to GSC data and returns metrics (1:1 with Python)
// CRITICAL: Now properly sends dimensionFilterGroups to Google API
func (s *GSCService) ApplyFilter(ctx context.Context, userEmail string, filterReq *domain.GSCFilterRequest) (*domain.GSCFilterResponse, string, error) {
	// Get user's selected website
	websiteURL, err := s.repo.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return nil, "", apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return nil, "", apperrors.New(apperrors.CodeValidation, "No website selected. Please select a domain first.", 400)
	}

	// Get HTTP client
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, "", err
	}

	// Convert domain filter groups to infrastructure layer format (1:1 with Python)
	var gscFilterGroups []google.DimensionFilterGroup
	for _, fg := range filterReq.FilterGroups {
		gscFG := google.DimensionFilterGroup{
			GroupType: fg.GroupType,
			Filters:   make([]google.DimensionFilter, 0, len(fg.Filters)),
		}
		for _, f := range fg.Filters {
			gscFG.Filters = append(gscFG.Filters, google.DimensionFilter{
				Dimension:  f.Dimension,
				Operator:   f.Operator,
				Expression: f.Expression,
			})
		}
		gscFilterGroups = append(gscFilterGroups, gscFG)
	}

	// Build filter request for GSC client (1:1 with Python)
	gscFilterReq := &google.FilterRequest{
		StartDate:       filterReq.StartDate,
		EndDate:         filterReq.EndDate,
		Dimensions:      filterReq.Dimensions,
		SearchType:      filterReq.SearchType,
		FilterGroups:    gscFilterGroups,
		AggregationType: filterReq.AggregationType,
		DataState:       filterReq.DataState,
		RowLimit:        filterReq.RowLimit,
		StartRow:        filterReq.StartRow,
		WithComparison:  filterReq.ComparisonEnabled,
	}

	// Add comparison dates if provided
	if filterReq.ComparisonStartDate != nil {
		gscFilterReq.ComparisonStart = filterReq.ComparisonStartDate
	}
	if filterReq.ComparisonEndDate != nil {
		gscFilterReq.ComparisonEnd = filterReq.ComparisonEndDate
	}

	// CRITICAL: Use GetFilteredMetrics which actually sends dimensionFilterGroups to GSC API
	aggregatedMetrics, err := s.gscClient.GetFilteredMetrics(
		ctx,
		client,
		websiteURL,
		gscFilterReq,
	)
	if err != nil {
		return nil, "", apperrors.ExternalServiceError("Google Search Console", err)
	}

	// Calculate SEO score
	scoringMetrics := &scoring.GSCMetrics{
		Impressions: aggregatedMetrics.TotalImpressions,
		Clicks:      aggregatedMetrics.TotalClicks,
		CTR:         aggregatedMetrics.AverageCTR,
		Position:    aggregatedMetrics.AveragePosition,
	}
	seoScoreResult := scoring.CalculateGSCScore(scoringMetrics)

	// Build filters applied description
	var filtersApplied []string
	if filterReq.SearchType != "web" {
		filtersApplied = append(filtersApplied, "Search type: "+filterReq.SearchType)
	}
	for _, fg := range filterReq.FilterGroups {
		for _, f := range fg.Filters {
			filtersApplied = append(filtersApplied, f.Dimension+": "+f.Expression)
		}
	}

	// Format date range description
	dateRange := filterReq.StartDate.Format("Jan 02") + " - " + filterReq.EndDate.Format("Jan 02, 2006")

	response := &domain.GSCFilterResponse{
		TotalClicks:      aggregatedMetrics.TotalClicks,
		TotalImpressions: aggregatedMetrics.TotalImpressions,
		AverageCTR:       aggregatedMetrics.AverageCTR,
		AveragePosition:  aggregatedMetrics.AveragePosition,
		SEOScore:         seoScoreResult.Total,
		DateRange:        dateRange,
		SearchType:       filterReq.SearchType,
		FiltersApplied:   filtersApplied,
		RowCount:         aggregatedMetrics.RowCount,
	}

	// Add comparison data if enabled
	if filterReq.ComparisonEnabled {
		response.ComparisonClicks = &aggregatedMetrics.ComparisonClicks
		response.ComparisonImpressions = &aggregatedMetrics.ComparisonImpressions
		response.ComparisonCTR = &aggregatedMetrics.ComparisonCTR
		response.ComparisonPosition = &aggregatedMetrics.ComparisonPosition

		// 1:1 with Python: clicks_change and impressions_change are raw integer differences
		// Python: clicks_change = current_total_clicks - previous_total_clicks
		clicksChange := aggregatedMetrics.TotalClicks - aggregatedMetrics.ComparisonClicks
		impressionsChange := aggregatedMetrics.TotalImpressions - aggregatedMetrics.ComparisonImpressions
		ctrChange := domain.CalculateChange(aggregatedMetrics.AverageCTR, aggregatedMetrics.ComparisonCTR)
		positionChange := aggregatedMetrics.AveragePosition - aggregatedMetrics.ComparisonPosition

		response.ClicksChange = &clicksChange
		response.ImpressionsChange = &impressionsChange
		response.CTRChange = &ctrChange
		response.PositionChange = &positionChange
	}

	return response, websiteURL, nil
}

// GetDatePreset returns a date range preset configuration (1:1 with Python)
func (s *GSCService) GetDatePreset(presetName string) (*domain.DateRangePreset, error) {
	preset, err := domain.GetDatePreset(presetName)
	if err != nil {
		return nil, err
	}

	if preset == nil {
		availablePresets := domain.GetAvailablePresets()
		return nil, apperrors.New(
			apperrors.CodeValidation,
			"Invalid preset name. Available: "+joinStrings(availablePresets, ", "),
			400,
		)
	}

	return preset, nil
}

// joinStrings joins string slice with separator
func joinStrings(strs []string, sep string) string {
	result := ""
	for i, s := range strs {
		if i > 0 {
			result += sep
		}
		result += s
	}
	return result
}

// ============================================================================
// ADDITIONAL 1:1 PARITY METHODS
// ============================================================================

// GetKeywords returns keywords (queries) for the selected website (1:1 with Python /gsc/keywords)
func (s *GSCService) GetKeywords(ctx context.Context, userEmail string) ([]domain.Query, error) {
	// Get user's selected website
	websiteURL, err := s.repo.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return nil, apperrors.New(apperrors.CodeValidation, "No GSC property selected. Please select a property first.", 404)
	}

	// Use default filter
	filter := domain.DefaultFilter()
	filter.Limit = 1000 // 1:1 with Python google_oauth.py:911 - Get top 1000 keywords

	// Get keywords using existing GetQueries method
	return s.GetQueries(ctx, userEmail, websiteURL, filter)
}

// RefreshMetrics refreshes SEO metrics from GSC (1:1 with Python /gsc/refresh)
func (s *GSCService) RefreshMetrics(ctx context.Context, userEmail string) (*domain.Metrics, string, error) {
	// Get user's selected website
	websiteURL, err := s.repo.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return nil, "", apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return nil, "", apperrors.New(apperrors.CodeValidation, "No GSC property selected. Please select a property first.", 404)
	}

	// Invalidate cache first
	_ = s.repo.InvalidateMetricsCache(ctx, userEmail, websiteURL)

	// Fetch fresh metrics
	filter := domain.DefaultFilter()
	metrics, err := s.GetMetrics(ctx, userEmail, websiteURL, filter)
	if err != nil {
		return nil, "", err
	}

	return metrics, websiteURL, nil
}

// GetProperties returns GSC properties (alias for GetWebsites) (1:1 with Python /gsc/properties)
func (s *GSCService) GetProperties(ctx context.Context, userEmail string) ([]domain.Website, error) {
	// Get HTTP client
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	// Fetch from GSC API
	sites, err := s.gscClient.GetSites(ctx, client)
	if err != nil {
		return nil, apperrors.ExternalServiceError("Google Search Console", err)
	}

	// Convert to Website domain objects
	var websites []domain.Website
	for _, site := range sites {
		websites = append(websites, domain.Website{
			UserEmail:       userEmail,
			SiteURL:         site.SiteURL,
			PermissionLevel: site.PermissionLevel,
		})
	}

	return websites, nil
}

// ClearCredentials clears the user's GSC OAuth credentials (1:1 with Python /gsc/clear-credentials)
// This allows users to disconnect their GSC account and re-authenticate
func (s *GSCService) ClearCredentials(ctx context.Context, userEmail string) error {
	if s.credentialDeleter == nil {
		return apperrors.ExternalServiceError("credential service", nil)
	}

	// Delete tokens from database and clear cache
	if err := s.credentialDeleter.DeleteTokens(ctx, userEmail); err != nil {
		return apperrors.DatabaseError(err)
	}

	return nil
}
