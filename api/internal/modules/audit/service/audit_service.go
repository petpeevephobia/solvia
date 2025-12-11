package service

import (
	"context"
	"fmt"
	"net/http"
	"time"

	chatDomain "github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/email"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/pdf"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/analyzers" // Enhanced analyzers (1:1 with Python)
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/repository"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/scoring"
)

// UserTokenGetter interface to get user tokens
type UserTokenGetter interface {
	GetUserTokens(ctx context.Context, email string) (accessToken, refreshToken string, err error)
}

// CacheClearer interface for clearing caches before audit (1:1 with Python)
type CacheClearer interface {
	ClearAllCaches(ctx context.Context, userEmail, websiteURL string) error
}

// AuditOptions represents options for audit creation (1:1 with Python AuditRequest)
type AuditOptions struct {
	DateRangeDays          int    `json:"date_range_days"`          // Days to analyze (default: 30)
	ReportFormat           string `json:"report_format"`            // pdf, json, or both (default: both)
	DeliveryMethod         string `json:"delivery_method"`          // email or download (default: email)
	ForceRefresh           bool   `json:"force_refresh"`            // Force fresh data fetch (default: false)
	IncludeRecommendations bool   `json:"include_recommendations"`  // Include AI recommendations (default: true)
}

// DefaultAuditOptions returns default audit options (1:1 with Python)
func DefaultAuditOptions() *AuditOptions {
	return &AuditOptions{
		DateRangeDays:          30,
		ReportFormat:           "both",
		DeliveryMethod:         "email",
		ForceRefresh:           false,
		IncludeRecommendations: true,
	}
}

// AuditService handles audit business logic
type AuditService struct {
	repo            repository.AuditRepository
	gscClient       *google.SearchConsoleClient
	oauthClient     *google.OAuthClient
	pdfGenerator    *pdf.Generator
	tokenGetter     UserTokenGetter
	emailService    *email.Service                 // Email service for sending reports (1:1 with Python)
	detailedFetcher *google.DetailedGSCDataFetcher // Detailed GSC data fetcher (1:1 with Python)
	cacheClearer    CacheClearer                   // Cache clearer for fresh data (1:1 with Python ULTRATHINK)
	auditEngine     *analyzers.AuditEngine         // Enhanced analyzers engine (1:1 with Python)
}

// NewAuditService creates a new audit service
func NewAuditService(
	repo repository.AuditRepository,
	gscClient *google.SearchConsoleClient,
	oauthClient *google.OAuthClient,
	pdfGenerator *pdf.Generator,
	tokenGetter UserTokenGetter,
	emailService *email.Service,
) *AuditService {
	return &AuditService{
		repo:            repo,
		gscClient:       gscClient,
		oauthClient:     oauthClient,
		pdfGenerator:    pdfGenerator,
		tokenGetter:     tokenGetter,
		emailService:    emailService,
		detailedFetcher: google.NewDetailedGSCDataFetcher(gscClient), // Initialize detailed fetcher
		auditEngine:     analyzers.NewAuditEngine(),                   // Initialize enhanced analyzers (1:1 with Python)
	}
}

// SetCacheClearer sets the cache clearer (1:1 with Python ULTRATHINK)
func (s *AuditService) SetCacheClearer(clearer CacheClearer) {
	s.cacheClearer = clearer
}

// CreateAudit starts a new audit for a website (backward compatible)
func (s *AuditService) CreateAudit(ctx context.Context, userEmail, websiteURL string) (*domain.Audit, error) {
	return s.CreateAuditWithOptions(ctx, userEmail, websiteURL, DefaultAuditOptions())
}

// CreateAuditWithOptions starts a new audit with custom options (1:1 with Python)
func (s *AuditService) CreateAuditWithOptions(ctx context.Context, userEmail, websiteURL string, options *AuditOptions) (*domain.Audit, error) {
	// Use defaults if options is nil
	if options == nil {
		options = DefaultAuditOptions()
	}

	// Create initial audit record
	audit := &domain.Audit{
		UserEmail:  userEmail,
		WebsiteURL: websiteURL,
		Status:     domain.AuditStatusPending,
		SEOScore:   25, // Base score
		SEOStage:   domain.SEOStageHidden,
		CreatedAt:  time.Now(),
	}

	if err := s.repo.CreateAudit(ctx, audit); err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	// Process audit asynchronously with options
	go s.processAuditWithOptions(context.Background(), audit.ID, userEmail, websiteURL, options)

	return audit, nil
}

// processAudit performs the actual audit processing (backward compatible)
func (s *AuditService) processAudit(ctx context.Context, auditID int64, userEmail, websiteURL string) {
	s.processAuditWithOptions(ctx, auditID, userEmail, websiteURL, DefaultAuditOptions())
}

// processAuditWithOptions performs the actual audit processing with options (1:1 with Python)
func (s *AuditService) processAuditWithOptions(ctx context.Context, auditID int64, userEmail, websiteURL string, options *AuditOptions) {
	// Panic recovery to prevent silent goroutine failures
	defer func() {
		if r := recover(); r != nil {
			fmt.Printf("[AUDIT PANIC] Goroutine panicked for audit %d: %v\n", auditID, r)
			_ = s.repo.UpdateAuditError(ctx, auditID, fmt.Sprintf("Audit processing panicked: %v", r))
		}
	}()

	// Start tracking progress
	domain.GlobalProgressTracker.StartTracking(auditID)
	defer domain.GlobalProgressTracker.CleanupAudit(auditID)

	// Stage 1: Initializing
	domain.GlobalProgressTracker.SetStage(auditID, domain.StageInitializing, "Initializing audit environment...")

	// Update status to processing
	_ = s.repo.UpdateAuditStatus(ctx, auditID, domain.AuditStatusProcessing, "")

	// Clear caches if force_refresh is true OR always clear (1:1 with Python ULTRATHINK)
	// Python clears cache on every audit to ensure fresh data
	if s.cacheClearer != nil {
		domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageInitializing, 2, "Clearing caches for fresh data...")
		_ = s.cacheClearer.ClearAllCaches(ctx, userEmail, websiteURL)
	}

	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageInitializing, 5, "Authenticating with Google...")

	// Get HTTP client
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		domain.GlobalProgressTracker.SetError(auditID, "Failed to authenticate: "+err.Error())
		_ = s.repo.UpdateAuditError(ctx, auditID, "Failed to authenticate: "+err.Error())
		return
	}

	// Stage 2: Fetching GSC Data
	domain.GlobalProgressTracker.SetStage(auditID, domain.StageFetchingGSCData, "Fetching data from Google Search Console...")

	// Fetch metrics for current period using options.DateRangeDays (1:1 with Python)
	now := time.Now()
	endDate := now.AddDate(0, 0, -1) // GSC data delayed by 1 day
	startDate := endDate.AddDate(0, 0, -(options.DateRangeDays - 1)) // Use custom date range

	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageFetchingGSCData, 15, "Fetching current period metrics...")

	currentMetrics, err := s.gscClient.GetMetrics(ctx, client, websiteURL, startDate, endDate)
	if err != nil {
		domain.GlobalProgressTracker.SetError(auditID, "Failed to fetch metrics: "+err.Error())
		_ = s.repo.UpdateAuditError(ctx, auditID, "Failed to fetch metrics: "+err.Error())
		return
	}

	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageFetchingGSCData, 25, "Fetching comparison period metrics...")

	// Fetch metrics for previous period (same duration before current, 1:1 with Python)
	prevEndDate := startDate.AddDate(0, 0, -1)
	prevStartDate := prevEndDate.AddDate(0, 0, -(options.DateRangeDays - 1)) // Same duration as current

	prevMetrics, err := s.gscClient.GetMetrics(ctx, client, websiteURL, prevStartDate, prevEndDate)
	if err != nil {
		// Non-fatal - continue with zeros for previous period
		prevMetrics = &google.GSCMetrics{}
	}

	// Calculate changes
	auditMetrics := &domain.AuditMetrics{
		Impressions:       currentMetrics.Impressions,
		Clicks:            currentMetrics.Clicks,
		CTR:               currentMetrics.CTR,
		Position:          currentMetrics.Position,
		PrevImpressions:   prevMetrics.Impressions,
		PrevClicks:        prevMetrics.Clicks,
		PrevCTR:           prevMetrics.CTR,
		PrevPosition:      prevMetrics.Position,
		ImpressionsChange: domain.CalculateChange(float64(currentMetrics.Impressions), float64(prevMetrics.Impressions)),
		ClicksChange:      domain.CalculateChange(float64(currentMetrics.Clicks), float64(prevMetrics.Clicks)),
		CTRChange:         domain.CalculateChange(currentMetrics.CTR, prevMetrics.CTR),
		PositionChange:    domain.CalculateChange(currentMetrics.Position, prevMetrics.Position),
	}

	// Stage 3: Analyzing Metrics
	domain.GlobalProgressTracker.SetStage(auditID, domain.StageAnalyzingMetrics, "Analyzing SEO metrics...")

	// Fetch top queries
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageAnalyzingMetrics, 35, "Fetching top queries...")
	queries, _ := s.gscClient.GetQueries(ctx, client, websiteURL, startDate, endDate, 10)
	var topQueries []domain.TopQuery
	for _, q := range queries {
		if len(q.Keys) > 0 {
			topQueries = append(topQueries, domain.TopQuery{
				Query:       q.Keys[0],
				Clicks:      int(q.Clicks),
				Impressions: int(q.Impressions),
				CTR:         q.CTR,
				Position:    q.Position,
			})
		}
	}

	// Fetch top pages
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageAnalyzingMetrics, 40, "Fetching top pages...")
	pages, _ := s.gscClient.GetPages(ctx, client, websiteURL, startDate, endDate, 10)
	var topPages []domain.TopPage
	for _, p := range pages {
		if len(p.Keys) > 0 {
			topPages = append(topPages, domain.TopPage{
				Page:        p.Keys[0],
				Clicks:      int(p.Clicks),
				Impressions: int(p.Impressions),
				CTR:         p.CTR,
				Position:    p.Position,
			})
		}
	}

	// Fetch time series data for V1/V2 28-day changes (1:1 with Python gamified PDF)
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageAnalyzingMetrics, 42, "Fetching time series data...")
	timeSeriesData, _ := s.gscClient.GetTimeSeriesMetrics(ctx, client, websiteURL, startDate, endDate)

	// Calculate 28-day changes using V1 (first day) vs V2 (last day) method
	changes28Day := google.Calculate28DayChanges(timeSeriesData)

	// Calculate SEO score and stage using shared scoring engine (1:1 with Python)
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageAnalyzingMetrics, 45, "Calculating SEO score...")
	seoScore := s.calculateSEOScore(auditMetrics)
	seoStage := domain.SEOStage(scoring.GetSEOStage(currentMetrics.Impressions))

	// Stage 4: Detecting Issues with Enhanced Analyzers (1:1 with Python)
	domain.GlobalProgressTracker.SetStage(auditID, domain.StageDetectingIssues, "Detecting SEO issues and anomalies...")
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageDetectingIssues, 55, "Running enhanced analyzers...")

	// Convert time series for analyzers
	var googleDailyMetrics []google.DailyMetric
	for _, ts := range timeSeriesData {
		googleDailyMetrics = append(googleDailyMetrics, google.DailyMetric{
			Date:        ts.Date,
			Clicks:      ts.Clicks,
			Impressions: ts.Impressions,
			CTR:         ts.CTR,
			Position:    ts.Position,
		})
	}

	// Run full analysis with enhanced analyzers (1:1 with Python rag_analyzer_enhanced.py)
	analysisResult := s.auditEngine.RunFullAnalysis(auditMetrics, googleDailyMetrics, topQueries, topPages, auditID)
	issues := analysisResult.Issues

	// If no issues from enhanced analyzers, fallback to basic detection
	if len(issues) == 0 {
		issues = s.detectIssues(auditID, auditMetrics)
	}

	// Stage 5: Generating Recommendations
	domain.GlobalProgressTracker.SetStage(auditID, domain.StageGeneratingRecommendations, "Generating recommendations...")
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageGeneratingRecommendations, 75, "Saving detected issues...")

	// Save issues
	if len(issues) > 0 {
		_ = s.repo.SaveIssues(ctx, issues)
	}

	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageGeneratingRecommendations, 80, "Updating audit score...")

	// Update audit with score
	_ = s.repo.UpdateAuditScore(ctx, auditID, seoScore, seoStage)

	// Get audit for PDF generation
	audit, err := s.repo.GetAudit(ctx, auditID)
	if err != nil || audit == nil {
		domain.GlobalProgressTracker.SetError(auditID, "Failed to retrieve audit")
		_ = s.repo.UpdateAuditError(ctx, auditID, "Failed to retrieve audit")
		return
	}
	audit.SEOScore = seoScore
	audit.SEOStage = seoStage

	// Stage 6: Creating Report
	domain.GlobalProgressTracker.SetStage(auditID, domain.StageCreatingReport, "Creating PDF report...")
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageCreatingReport, 88, "Generating gamified PDF report...")

	// Convert time series data for domain
	var domainTimeSeries []domain.DailyMetric
	for _, ts := range timeSeriesData {
		domainTimeSeries = append(domainTimeSeries, domain.DailyMetric{
			Date:        ts.Date,
			Clicks:      ts.Clicks,
			Impressions: ts.Impressions,
			CTR:         ts.CTR,
			Position:    ts.Position,
		})
	}

	// Convert 28-day changes for domain
	domainChanges := &domain.Changes28Day{
		ImpressionsChange: changes28Day.ImpressionsChange,
		ClicksChange:      changes28Day.ClicksChange,
		CTRChange:         changes28Day.CTRChange,
		PositionChange:    changes28Day.PositionChange,
		V1Date:            changes28Day.V1Date,
		V2Date:            changes28Day.V2Date,
		HasSufficientData: changes28Day.HasSufficientData,
	}

	// Prepare audit data for PDF/JSON generation
	auditData := &domain.AuditData{
		Audit:          audit,
		Metrics:        auditMetrics,
		Issues:         issues,
		TopQueries:     topQueries,
		TopPages:       topPages,
		Changes28Day:   domainChanges,
		TimeSeriesData: domainTimeSeries,
	}

	var pdfPath string

	// Generate PDF based on report_format option (1:1 with Python)
	// options.ReportFormat: "pdf", "json", or "both"
	if options.ReportFormat == "pdf" || options.ReportFormat == "both" {
		var err error
		pdfPath, err = s.pdfGenerator.GenerateAuditReport(auditData)
		if err != nil {
			domain.GlobalProgressTracker.SetError(auditID, "Failed to generate PDF: "+err.Error())
			_ = s.repo.UpdateAuditError(ctx, auditID, "Failed to generate PDF: "+err.Error())
			return
		}
	}

	// Send email with PDF report based on delivery_method option (1:1 with Python)
	// options.DeliveryMethod: "email" or "download"
	if options.DeliveryMethod == "email" && pdfPath != "" {
		domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageCreatingReport, 92, "Sending report via email...")
		if s.emailService != nil {
			auditIDStr := fmt.Sprintf("%d", auditID)
			if err := s.emailService.SendAuditReportEmail(ctx, userEmail, pdfPath, auditIDStr, seoScore, userEmail); err != nil {
				// Non-fatal error - log but don't fail the audit
				fmt.Printf("[AUDIT] Warning: Failed to send email: %v\n", err)
			}
		}
	} else if options.DeliveryMethod == "download" {
		domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageCreatingReport, 92, "Report ready for download...")
	}

	// Stage 7: Finalizing
	domain.GlobalProgressTracker.SetStage(auditID, domain.StageFinalizing, "Finalizing audit...")
	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageFinalizing, 96, "Saving results...")

	// Update status to completed with proper error logging
	fmt.Printf("[AUDIT] Updating status to completed for audit %d, pdfPath: %s\n", auditID, pdfPath)
	if err := s.repo.UpdateAuditStatus(ctx, auditID, domain.AuditStatusCompleted, pdfPath); err != nil {
		fmt.Printf("[AUDIT ERROR] Failed to update status to completed: %v\n", err)
	} else {
		fmt.Printf("[AUDIT] ✅ Status updated to completed for audit %d\n", auditID)
	}

	domain.GlobalProgressTracker.UpdateProgress(auditID, domain.StageFinalizing, 98, "Cleaning up old audits...")

	// Cleanup old audits (keep last 10)
	if err := s.repo.DeleteOldAudits(ctx, userEmail, 10); err != nil {
		fmt.Printf("[AUDIT WARNING] Failed to cleanup old audits: %v\n", err)
	}

	// Stage 8: Completed
	fmt.Printf("[AUDIT] ✅ Audit %d completed successfully\n", auditID)
	domain.GlobalProgressTracker.Complete(auditID)
}

// GetAudit retrieves an audit by ID
func (s *AuditService) GetAudit(ctx context.Context, id int64, userEmail string) (*domain.Audit, error) {
	audit, err := s.repo.GetAudit(ctx, id)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if audit == nil {
		return nil, apperrors.NotFoundError("Audit", fmt.Sprintf("%d", id))
	}

	// Verify ownership
	if audit.UserEmail != userEmail {
		return nil, apperrors.ForbiddenError("Access denied")
	}

	return audit, nil
}

// GetAuditHistory retrieves audit history for a user
func (s *AuditService) GetAuditHistory(ctx context.Context, userEmail string, limit int) ([]domain.Audit, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}

	audits, err := s.repo.GetAuditsByUser(ctx, userEmail, limit)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return audits, nil
}

// GetAuditWithIssues retrieves audit with its issues
func (s *AuditService) GetAuditWithIssues(ctx context.Context, id int64, userEmail string) (*domain.AuditData, error) {
	audit, err := s.GetAudit(ctx, id, userEmail)
	if err != nil {
		return nil, err
	}

	issues, err := s.repo.GetIssuesByAudit(ctx, id)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return &domain.AuditData{
		Audit:  audit,
		Issues: issues,
	}, nil
}

// GetLatestAudit retrieves the most recent audit for a website
func (s *AuditService) GetLatestAudit(ctx context.Context, userEmail, websiteURL string) (*domain.Audit, error) {
	audit, err := s.repo.GetLatestAudit(ctx, userEmail, websiteURL)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return audit, nil
}

// GetLatestAuditContext returns audit context for chat injection (1:1 with Python)
func (s *AuditService) GetLatestAuditContext(ctx context.Context, userEmail, websiteURL string) (*chatDomain.AuditContext, error) {
	// Get the latest completed audit
	audit, err := s.repo.GetLatestAudit(ctx, userEmail, websiteURL)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	// No audit found - return nil (not an error)
	if audit == nil || audit.Status != domain.AuditStatusCompleted {
		return nil, nil
	}

	// Get issues for context
	issues, err := s.repo.GetIssuesByAudit(ctx, audit.ID)
	if err != nil {
		// Non-fatal, continue without issues
		issues = []domain.AuditIssue{}
	}

	// Build audit context for chat
	auditCtx := &chatDomain.AuditContext{
		AuditDate: audit.CreatedAt.Format("2006-01-02"),
		SEOScore:  audit.SEOScore,
		SEOStage:  string(audit.SEOStage),
	}

	// Convert issues to chat domain format
	for _, issue := range issues {
		auditCtx.Issues = append(auditCtx.Issues, chatDomain.AuditIssue{
			Severity:    issue.Severity,
			Title:       issue.Title,
			Description: issue.Description,
		})
	}

	return auditCtx, nil
}

// CurrentIssuesResponse is the response for current issues endpoint (1:1 with Python)
type CurrentIssuesResponse struct {
	HasIssues     bool                `json:"has_issues"`
	Issues        []domain.AuditIssue `json:"issues"`
	SEOScore      float64             `json:"seo_score"`
	Source        string              `json:"source"`        // "fresh-audit-data", "real-google-data", "stored-audit-fallback", "no-data"
	LastAudit     *string             `json:"last_audit"`    // ISO timestamp or nil
	CacheAgeHours float64             `json:"cache_age_hours,omitempty"`
}

// GetCurrentIssues retrieves issues using 4-level priority (1:1 with Python)
// PRIORITY 0: Fresh audit data (<1 hour old) - prioritize recent audit results
// PRIORITY 1: Real-time Google data - fetch live GSC metrics
// PRIORITY 2: Cached audit data (1-24 hours old) - fallback to stored audit
// PRIORITY 3: Fallback analysis - no data available
func (s *AuditService) GetCurrentIssues(ctx context.Context, userEmail, websiteURL string) (*CurrentIssuesResponse, error) {
	// PRIORITY 0: Check for fresh audit data first (<1 hour old)
	audit, err := s.repo.GetLatestAudit(ctx, userEmail, websiteURL)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if audit != nil && audit.Status == domain.AuditStatusCompleted {
		// Calculate audit age in hours
		auditAgeHours := time.Since(audit.CreatedAt).Hours()

		// PRIORITY 0: If audit is less than 1 hour old, prioritize it
		if auditAgeHours < 1 {
			issues, _ := s.repo.GetIssuesByAudit(ctx, audit.ID)
			if issues == nil {
				issues = []domain.AuditIssue{}
			}

			lastAudit := audit.CreatedAt.Format(time.RFC3339)
			return &CurrentIssuesResponse{
				HasIssues:     len(issues) > 0,
				Issues:        s.limitIssues(issues, 5),
				SEOScore:      audit.SEOScore,
				Source:        "fresh-audit-data",
				LastAudit:     &lastAudit,
				CacheAgeHours: auditAgeHours,
			}, nil
		}

		// PRIORITY 2: If audit is 1-24 hours old, use as fallback
		if auditAgeHours < 24 {
			// First try to get real-time Google data (PRIORITY 1)
			liveResponse, err := s.tryRealTimeGoogleData(ctx, userEmail, websiteURL)
			if err == nil && liveResponse != nil {
				return liveResponse, nil
			}

			// Fallback to stored audit
			issues, _ := s.repo.GetIssuesByAudit(ctx, audit.ID)
			if issues == nil {
				issues = []domain.AuditIssue{}
			}

			lastAudit := audit.CreatedAt.Format(time.RFC3339)
			return &CurrentIssuesResponse{
				HasIssues:     len(issues) > 0,
				Issues:        s.limitIssues(issues, 5),
				SEOScore:      audit.SEOScore,
				Source:        "stored-audit-fallback",
				LastAudit:     &lastAudit,
				CacheAgeHours: auditAgeHours,
			}, nil
		}
	}

	// PRIORITY 1: Try real-time Google data
	liveResponse, err := s.tryRealTimeGoogleData(ctx, userEmail, websiteURL)
	if err == nil && liveResponse != nil {
		return liveResponse, nil
	}

	// PRIORITY 3: No data available
	return &CurrentIssuesResponse{
		HasIssues: false,
		Issues:    []domain.AuditIssue{},
		SEOScore:  25, // Base score
		Source:    "no-data",
		LastAudit: nil,
	}, nil
}

// tryRealTimeGoogleData attempts to fetch real-time GSC data and analyze it
func (s *AuditService) tryRealTimeGoogleData(ctx context.Context, userEmail, websiteURL string) (*CurrentIssuesResponse, error) {
	if websiteURL == "" {
		return nil, fmt.Errorf("no website URL")
	}

	// Get HTTP client for GSC API
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	// Fetch current metrics (30 days, 1:1 with Python)
	now := time.Now()
	endDate := now.AddDate(0, 0, -1)
	startDate := endDate.AddDate(0, 0, -29) // 30 days total

	// Use aggregated metrics for proper calculation
	metrics, err := s.gscClient.GetAggregatedMetrics(ctx, client, websiteURL, startDate, endDate, true)
	if err != nil {
		return nil, err
	}

	// Convert to audit metrics for analysis
	auditMetrics := &domain.AuditMetrics{
		Impressions:       metrics.TotalImpressions,
		Clicks:            metrics.TotalClicks,
		CTR:               metrics.AverageCTR,
		Position:          metrics.AveragePosition,
		ImpressionsChange: float64(metrics.ImpressionsChange),
		ClicksChange:      float64(metrics.ClicksChange),
		CTRChange:         metrics.CTRChange,
		PositionChange:    metrics.PositionChange,
	}

	// Calculate SEO score
	seoScore := s.calculateSEOScore(auditMetrics)

	// Detect issues using enhanced analyzers (1:1 with Python)
	analysisResult := s.auditEngine.AnalyzeMetricsOnly(auditMetrics, 0) // 0 for real-time (no audit ID)
	issues := analysisResult.Issues

	// Fallback to basic detection if no issues found
	if len(issues) == 0 {
		issues = s.detectIssues(0, auditMetrics)
	}

	lastAudit := time.Now().Format(time.RFC3339)
	return &CurrentIssuesResponse{
		HasIssues:     len(issues) > 0,
		Issues:        s.limitIssues(issues, 5),
		SEOScore:      seoScore,
		Source:        "real-google-data",
		LastAudit:     &lastAudit,
		CacheAgeHours: 0,
	}, nil
}

// limitIssues limits issues to top N sorted by severity (1:1 with Python - includes critical)
func (s *AuditService) limitIssues(issues []domain.AuditIssue, limit int) []domain.AuditIssue {
	if len(issues) <= limit {
		return issues
	}

	// Sort by severity (critical > high > medium > low) - 1:1 with Python
	severityOrder := map[string]int{"critical": 0, "high": 1, "medium": 2, "low": 3}
	for i := 0; i < len(issues)-1; i++ {
		for j := i + 1; j < len(issues); j++ {
			iOrder := severityOrder[issues[i].Severity]
			jOrder := severityOrder[issues[j].Severity]
			if iOrder > jOrder {
				issues[i], issues[j] = issues[j], issues[i]
			}
		}
	}

	return issues[:limit]
}

// getHTTPClient gets an authenticated HTTP client
func (s *AuditService) getHTTPClient(ctx context.Context, userEmail string) (*http.Client, error) {
	accessToken, refreshToken, err := s.tokenGetter.GetUserTokens(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	return s.oauthClient.GetHTTPClient(ctx, accessToken, refreshToken), nil
}

// calculateSEOScore calculates SEO score using shared scoring engine (1:1 with Python)
func (s *AuditService) calculateSEOScore(metrics *domain.AuditMetrics) float64 {
	// Convert audit metrics to scoring metrics
	scoringMetrics := &scoring.GSCMetrics{
		Impressions:       metrics.Impressions,
		Clicks:            metrics.Clicks,
		CTR:               metrics.CTR,
		Position:          metrics.Position,
		ImpressionsChange: metrics.ImpressionsChange,
		ClicksChange:      metrics.ClicksChange,
		CTRChange:         metrics.CTRChange,
		PositionChange:    metrics.PositionChange,
	}

	// Use historical data for trend scoring
	historicalData := &scoring.HistoricalData{
		Clicks:   metrics.PrevClicks,
		Position: metrics.PrevPosition,
		CTR:      metrics.PrevCTR,
	}

	// Calculate score using shared engine
	result := scoring.CalculateGSCScoreWithHistory(scoringMetrics, historicalData)
	return result.Total
}

// detectIssues detects SEO issues based on metrics
func (s *AuditService) detectIssues(auditID int64, metrics *domain.AuditMetrics) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// Low impressions
	if metrics.Impressions < 100 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "traffic",
			Title:       "Very Low Visibility",
			Description: "Your website has very few impressions in search results.",
			Impact:      "Low visibility means potential customers cannot find your website.",
			Recommendation:  "Focus on creating quality content targeting relevant keywords.",
		})
	} else if metrics.Impressions < 500 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "traffic",
			Title:       "Low Search Visibility",
			Description: "Your website has limited impressions in search results.",
			Impact:      "You're missing out on potential organic traffic.",
			Recommendation:  "Expand your content strategy and target more keywords.",
		})
	}

	// Poor average position
	if metrics.Position > 50 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "position",
			Title:       "Poor Search Rankings",
			Description: fmt.Sprintf("Average position is %.1f, which is very low in search results.", metrics.Position),
			Impact:      "Users rarely scroll past page 1-2 of search results.",
			Recommendation:  "Improve content quality, build backlinks, and optimize for user intent.",
		})
	} else if metrics.Position > 20 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "position",
			Title:       "Average Rankings Need Improvement",
			Description: fmt.Sprintf("Average position is %.1f, mostly on page 2-3.", metrics.Position),
			Impact:      "Page 2+ gets significantly less clicks than page 1.",
			Recommendation:  "Focus on moving your best-performing queries to page 1.",
		})
	}

	// Low CTR
	if metrics.CTR < 0.01 && metrics.Impressions > 100 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "ctr",
			Title:       "Very Low Click-Through Rate",
			Description: fmt.Sprintf("CTR is only %.2f%%, well below average.", metrics.CTR*100),
			Impact:      "People see your site but don't click - wasted visibility.",
			Recommendation:  "Improve meta titles and descriptions to be more compelling.",
		})
	} else if metrics.CTR < 0.03 && metrics.Impressions > 100 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "ctr",
			Title:       "Below Average Click-Through Rate",
			Description: fmt.Sprintf("CTR is %.2f%%, below the typical 2-5%% range.", metrics.CTR*100),
			Impact:      "You're not maximizing the traffic from your visibility.",
			Recommendation:  "Test different meta descriptions and add structured data.",
		})
	}

	// Declining trends
	if metrics.ImpressionsChange < -20 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "traffic",
			Title:       "Significant Traffic Decline",
			Description: fmt.Sprintf("Impressions dropped %.1f%% compared to previous period.", metrics.ImpressionsChange),
			Impact:      "Your organic visibility is declining rapidly.",
			Recommendation:  "Check for Google algorithm updates, technical issues, or content decay.",
		})
	}

	if metrics.PositionChange > 10 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "position",
			Title:       "Rankings Dropping",
			Description: fmt.Sprintf("Average position worsened by %.1f positions.", metrics.PositionChange),
			Impact:      "Lower rankings lead to less visibility and traffic.",
			Recommendation:  "Review recently changed pages and monitor competitor activity.",
		})
	}

	return issues
}
