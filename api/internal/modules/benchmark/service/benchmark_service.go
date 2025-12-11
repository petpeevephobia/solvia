package service

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/gemini"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/benchmark/domain"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"github.com/petpeevephobia/solvia-v2/api/internal/shared/scoring"
	"github.com/rs/zerolog/log"
)

// UserTokenGetter interface to get user tokens
type UserTokenGetter interface {
	GetUserTokens(ctx context.Context, email string) (accessToken, refreshToken string, err error)
}

// WebsiteGetter interface to get selected website
type WebsiteGetter interface {
	GetSelectedWebsite(ctx context.Context, userEmail string) (string, error)
}

// DashboardCacheGetter interface to get dashboard cache (for ai_insights) - 1:1 with Python
type DashboardCacheGetter interface {
	GetCache(ctx context.Context, userEmail, websiteURL string) (map[string]interface{}, error)
	SaveCache(ctx context.Context, userEmail, websiteURL string, data map[string]interface{}) error
}

// BenchmarkAIClient interface for AI insights generation (1:1 with Python)
type BenchmarkAIClient interface {
	ChatWithBenchmark(ctx context.Context, messages []gemini.Message) (*gemini.ChatResponse, error)
}

// BenchmarkService handles benchmark analysis business logic
type BenchmarkService struct {
	gscClient      *google.SearchConsoleClient
	oauthClient    *google.OAuthClient
	tokenGetter    UserTokenGetter
	websiteGetter  WebsiteGetter
	dashboardCache DashboardCacheGetter // For storing/retrieving ai_insights (1:1 with Python)
	aiClient       BenchmarkAIClient    // For AI-powered insights (1:1 with Python)
}

// NewBenchmarkService creates a new benchmark service
func NewBenchmarkService(
	gscClient *google.SearchConsoleClient,
	oauthClient *google.OAuthClient,
	tokenGetter UserTokenGetter,
	websiteGetter WebsiteGetter,
) *BenchmarkService {
	return &BenchmarkService{
		gscClient:     gscClient,
		oauthClient:   oauthClient,
		tokenGetter:   tokenGetter,
		websiteGetter: websiteGetter,
	}
}

// SetDashboardCache sets the dashboard cache getter (optional, for ai_insights caching)
func (s *BenchmarkService) SetDashboardCache(cache DashboardCacheGetter) {
	s.dashboardCache = cache
}

// SetAIClient sets the AI client for AI-powered insights (1:1 with Python)
func (s *BenchmarkService) SetAIClient(client BenchmarkAIClient) {
	s.aiClient = client
}

// GetBenchmarkInsights generates AI-powered benchmark insights (1:1 with Python)
func (s *BenchmarkService) GetBenchmarkInsights(ctx context.Context, userEmail string, explicit bool) (*domain.BenchmarkInsights, error) {
	// Get user's selected website
	websiteURL, err := s.websiteGetter.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return nil, apperrors.New(apperrors.CodeNotFound, "No GSC property selected. Please select a property first.", 404)
	}

	// Check cache if not explicit request (1:1 with Python)
	if s.dashboardCache != nil {
		cachedData, err := s.dashboardCache.GetCache(ctx, userEmail, websiteURL)
		if err == nil && cachedData != nil {
			// Check if ai_insights exists in cache (1:1 with Python)
			if aiInsights, ok := cachedData["ai_insights"]; ok && aiInsights != nil {
				if insightsMap, ok := aiInsights.(map[string]interface{}); ok {
					// Return cached insights if not explicit request
					if !explicit {
						return s.convertCachedInsights(insightsMap), nil
					}
				}
			}
		}
	}

	// If not explicit and no cache, return 404 (1:1 with Python)
	if !explicit {
		return nil, apperrors.New(apperrors.CodeNotFound, "No cached AI analysis available. Please generate AI analysis explicitly.", 404)
	}

	// Fetch GSC metrics
	client, err := s.getHTTPClient(ctx, userEmail)
	if err != nil {
		return nil, err
	}

	now := time.Now()
	endDate := now.AddDate(0, 0, -1)
	startDate := endDate.AddDate(0, 0, -29) // 30 days total (1:1 with Python)

	metrics, err := s.gscClient.GetAggregatedMetrics(ctx, client, websiteURL, startDate, endDate, true)
	if err != nil {
		return nil, apperrors.ExternalServiceError("Google Search Console", err)
	}

	// Generate insights based on metrics (uses AI when available, 1:1 with Python)
	insights := s.generateInsights(ctx, websiteURL, metrics)

	// Save to cache (1:1 with Python)
	if s.dashboardCache != nil {
		cachedData, _ := s.dashboardCache.GetCache(ctx, userEmail, websiteURL)
		if cachedData == nil {
			cachedData = make(map[string]interface{})
		}
		cachedData["ai_insights"] = s.insightsToMap(insights)
		_ = s.dashboardCache.SaveCache(ctx, userEmail, websiteURL, cachedData)
	}

	return insights, nil
}

// generateInsights creates benchmark insights from GSC metrics
// Uses AI for generation when available, falls back to template (1:1 with Python)
func (s *BenchmarkService) generateInsights(ctx context.Context, websiteURL string, metrics *google.AggregatedMetrics) *domain.BenchmarkInsights {
	// Calculate SEO score
	scoringMetrics := &scoring.GSCMetrics{
		Impressions: metrics.TotalImpressions,
		Clicks:      metrics.TotalClicks,
		CTR:         metrics.AverageCTR,
		Position:    metrics.AveragePosition,
	}
	seoResult := scoring.CalculateGSCScore(scoringMetrics)
	seoStage := string(scoring.GetSEOStage(metrics.TotalImpressions))

	// Try AI-powered generation first (1:1 with Python)
	if s.aiClient != nil {
		aiInsights, err := s.generateAIInsights(ctx, websiteURL, metrics, seoResult.Total, seoStage)
		if err == nil && aiInsights != nil {
			log.Info().Msg("Generated AI-powered benchmark insights")
			return aiInsights
		}
		log.Warn().Err(err).Msg("AI insights generation failed, falling back to template")
	}

	// Fallback to template-based generation
	return s.generateTemplateInsights(metrics, seoResult.Total, seoStage)
}

// generateAIInsights uses Gemini AI to generate insights (1:1 with Python)
func (s *BenchmarkService) generateAIInsights(ctx context.Context, websiteURL string, metrics *google.AggregatedMetrics, seoScore float64, seoStage string) (*domain.BenchmarkInsights, error) {
	// Build metrics for prompt
	promptMetrics := &gemini.WebsiteMetrics{
		Impressions:       metrics.TotalImpressions,
		Clicks:            metrics.TotalClicks,
		CTR:               metrics.AverageCTR,
		Position:          metrics.AveragePosition,
		SEOScore:          seoScore,
		ImpressionsChange: float64(metrics.ImpressionsChange),
		ClicksChange:      float64(metrics.ClicksChange),
		CTRChange:         metrics.CTRChange,
		PositionChange:    metrics.PositionChange,
	}

	// Build the benchmark prompt
	benchmarkPrompt := gemini.BuildBenchmarkPrompt(websiteURL, promptMetrics, seoStage)

	// Create messages for AI
	messages := []gemini.Message{
		{Role: "system", Content: benchmarkPrompt},
		{Role: "user", Content: "Analyze these SEO metrics and provide comprehensive insights in JSON format."},
	}

	// Call AI
	response, err := s.aiClient.ChatWithBenchmark(ctx, messages)
	if err != nil {
		return nil, fmt.Errorf("AI API error: %w", err)
	}

	// Parse AI response
	return s.parseAIResponse(response.Content, metrics, seoScore, seoStage)
}

// parseAIResponse parses the AI JSON response into BenchmarkInsights (1:1 with Python)
func (s *BenchmarkService) parseAIResponse(content string, metrics *google.AggregatedMetrics, seoScore float64, seoStage string) (*domain.BenchmarkInsights, error) {
	// Clean the response (remove markdown code blocks if present)
	content = strings.TrimSpace(content)
	content = strings.TrimPrefix(content, "```json")
	content = strings.TrimPrefix(content, "```")
	content = strings.TrimSuffix(content, "```")
	content = strings.TrimSpace(content)

	// Parse JSON response
	var aiResponse struct {
		VisibilityPerformance struct {
			OverallAssessment string  `json:"overall_assessment"`
			Score             float64 `json:"score"`
			Trend             string  `json:"trend"`
		} `json:"visibility_performance"`
		Analysis struct {
			Summary         string   `json:"summary"`
			Strengths       []string `json:"strengths"`
			Improvements    []string `json:"improvements"`
			Recommendations []string `json:"recommendations"`
		} `json:"analysis"`
	}

	if err := json.Unmarshal([]byte(content), &aiResponse); err != nil {
		return nil, fmt.Errorf("failed to parse AI response: %w", err)
	}

	// Use AI score if valid, otherwise use calculated
	score := aiResponse.VisibilityPerformance.Score
	if score <= 0 || score > 100 {
		score = seoScore
	}

	// Validate trend
	trend := aiResponse.VisibilityPerformance.Trend
	if trend != "improving" && trend != "stable" && trend != "declining" {
		if metrics.ImpressionsChange > 10 {
			trend = "improving"
		} else if metrics.ImpressionsChange < -10 {
			trend = "declining"
		} else {
			trend = "stable"
		}
	}

	return &domain.BenchmarkInsights{
		VisibilityPerformance: &domain.VisibilityPerformance{
			OverallAssessment: aiResponse.VisibilityPerformance.OverallAssessment,
			Metrics: map[string]interface{}{
				"impressions":        metrics.TotalImpressions,
				"clicks":             metrics.TotalClicks,
				"ctr":                metrics.AverageCTR * 100,
				"position":           metrics.AveragePosition,
				"impressions_change": metrics.ImpressionsChange,
				"clicks_change":      metrics.ClicksChange,
			},
			Score: score,
			Trend: trend,
		},
		Analysis: &domain.Analysis{
			Summary:         aiResponse.Analysis.Summary,
			Strengths:       aiResponse.Analysis.Strengths,
			Improvements:    aiResponse.Analysis.Improvements,
			Recommendations: aiResponse.Analysis.Recommendations,
		},
		GeneratedAt: time.Now().Format(time.RFC3339),
	}, nil
}

// generateTemplateInsights creates template-based insights (fallback)
func (s *BenchmarkService) generateTemplateInsights(metrics *google.AggregatedMetrics, seoScore float64, seoStage string) *domain.BenchmarkInsights {
	// Determine trend based on comparison data
	trend := "stable"
	if metrics.ImpressionsChange > 10 {
		trend = "improving"
	} else if metrics.ImpressionsChange < -10 {
		trend = "declining"
	}

	// Generate overall assessment
	assessment := s.generateAssessment(metrics, seoScore, seoStage)

	// Generate strengths and improvements
	strengths, improvements := s.analyzeStrengthsAndImprovements(metrics)

	// Generate recommendations
	recommendations := s.generateRecommendations(metrics, seoStage)

	return &domain.BenchmarkInsights{
		VisibilityPerformance: &domain.VisibilityPerformance{
			OverallAssessment: assessment,
			Metrics: map[string]interface{}{
				"impressions":        metrics.TotalImpressions,
				"clicks":             metrics.TotalClicks,
				"ctr":                metrics.AverageCTR * 100, // Convert to percentage
				"position":           metrics.AveragePosition,
				"impressions_change": metrics.ImpressionsChange,
				"clicks_change":      metrics.ClicksChange,
			},
			Score: seoScore,
			Trend: trend,
		},
		Analysis: &domain.Analysis{
			Summary:         s.generateSummary(metrics, seoStage),
			Strengths:       strengths,
			Improvements:    improvements,
			Recommendations: recommendations,
		},
		GeneratedAt: time.Now().Format(time.RFC3339),
	}
}

// generateAssessment creates an overall assessment string
func (s *BenchmarkService) generateAssessment(metrics *google.AggregatedMetrics, score float64, stage string) string {
	switch stage {
	case "hidden":
		return fmt.Sprintf("Your website is currently in the Hidden stage with %d impressions. "+
			"Your SEO score is %.0f/100. Focus on creating quality content and improving indexing to increase visibility.",
			metrics.TotalImpressions, score)
	case "emerging":
		return fmt.Sprintf("Your website is in the Emerging stage with %d impressions. "+
			"Your SEO score is %.0f/100. You're building visibility - keep creating content and optimizing for targeted keywords.",
			metrics.TotalImpressions, score)
	case "discoverable":
		return fmt.Sprintf("Your website is Discoverable with %d impressions. "+
			"Your SEO score is %.0f/100. You're gaining visibility! Focus on improving CTR and moving up in rankings.",
			metrics.TotalImpressions, score)
	case "trusted":
		return fmt.Sprintf("Excellent! Your website is in the Trusted stage with %d impressions. "+
			"Your SEO score is %.0f/100. Maintain quality and explore new growth opportunities.",
			metrics.TotalImpressions, score)
	default:
		return fmt.Sprintf("Your website has %d impressions with an SEO score of %.0f/100.",
			metrics.TotalImpressions, score)
	}
}

// generateSummary creates a summary of the SEO performance
func (s *BenchmarkService) generateSummary(metrics *google.AggregatedMetrics, stage string) string {
	ctrPercentage := metrics.AverageCTR * 100

	summary := fmt.Sprintf("Over the last 30 days, your website received %d impressions and %d clicks, "+
		"with an average CTR of %.2f%% and average position of %.1f. ",
		metrics.TotalImpressions, metrics.TotalClicks, ctrPercentage, metrics.AveragePosition)

	// Add trend information
	if metrics.ImpressionsChange > 0 {
		summary += fmt.Sprintf("Impressions increased by %d compared to the previous period. ", metrics.ImpressionsChange)
	} else if metrics.ImpressionsChange < 0 {
		summary += fmt.Sprintf("Impressions decreased by %d compared to the previous period. ", -metrics.ImpressionsChange)
	}

	// Add stage-specific advice
	switch stage {
	case "hidden":
		summary += "Your primary focus should be on increasing visibility through content creation and technical SEO improvements."
	case "emerging":
		summary += "Continue building content and focus on keyword optimization to accelerate growth."
	case "discoverable":
		summary += "Optimize your top-performing pages and work on improving click-through rates."
	case "trusted":
		summary += "Maintain your strong position and explore new keyword opportunities."
	}

	return summary
}

// analyzeStrengthsAndImprovements identifies strengths and areas for improvement
func (s *BenchmarkService) analyzeStrengthsAndImprovements(metrics *google.AggregatedMetrics) ([]string, []string) {
	var strengths, improvements []string
	ctrPercentage := metrics.AverageCTR * 100

	// Analyze CTR
	if ctrPercentage >= 5 {
		strengths = append(strengths, "Strong click-through rate indicates compelling titles and descriptions")
	} else if ctrPercentage < 2 {
		improvements = append(improvements, "Low CTR - consider improving meta titles and descriptions")
	}

	// Analyze position
	if metrics.AveragePosition <= 10 {
		strengths = append(strengths, "Good average position on page 1 of search results")
	} else if metrics.AveragePosition > 20 {
		improvements = append(improvements, "Average position is beyond page 2 - focus on content quality and backlinks")
	}

	// Analyze trends
	if metrics.ImpressionsChange > 20 {
		strengths = append(strengths, "Strong upward trend in impressions")
	} else if metrics.ImpressionsChange < -20 {
		improvements = append(improvements, "Declining impressions - investigate potential issues")
	}

	if metrics.ClicksChange > 0 {
		strengths = append(strengths, "Growing organic traffic")
	} else if metrics.ClicksChange < -10 {
		improvements = append(improvements, "Traffic decline detected - review recent changes")
	}

	// Add defaults if empty
	if len(strengths) == 0 {
		strengths = append(strengths, "Consistent search presence")
	}
	if len(improvements) == 0 {
		improvements = append(improvements, "Continue monitoring and optimizing content")
	}

	return strengths, improvements
}

// generateRecommendations creates actionable recommendations
func (s *BenchmarkService) generateRecommendations(metrics *google.AggregatedMetrics, stage string) []string {
	var recommendations []string
	ctrPercentage := metrics.AverageCTR * 100

	// Stage-specific recommendations
	switch stage {
	case "hidden":
		recommendations = append(recommendations,
			"Submit your sitemap to Google Search Console",
			"Create high-quality content targeting relevant keywords",
			"Ensure your website is properly indexed",
		)
	case "emerging":
		recommendations = append(recommendations,
			"Expand your content with targeted blog posts",
			"Build internal links between related pages",
		)
	case "discoverable":
		recommendations = append(recommendations,
			"Optimize your top-performing pages for better rankings",
			"Consider building quality backlinks",
		)
	case "trusted":
		recommendations = append(recommendations,
			"Maintain content freshness with regular updates",
			"Explore new keyword opportunities in your niche",
		)
	}

	// CTR-based recommendations
	if ctrPercentage < 2 {
		recommendations = append(recommendations, "Improve meta titles with compelling, action-oriented language")
	}

	// Position-based recommendations
	if metrics.AveragePosition > 10 {
		recommendations = append(recommendations, "Focus on improving page load speed and user experience")
	}

	// Limit to 5 recommendations
	if len(recommendations) > 5 {
		recommendations = recommendations[:5]
	}

	return recommendations
}

// getHTTPClient gets an authenticated HTTP client
func (s *BenchmarkService) getHTTPClient(ctx context.Context, userEmail string) (*http.Client, error) {
	accessToken, refreshToken, err := s.tokenGetter.GetUserTokens(ctx, userEmail)
	if err != nil {
		return nil, apperrors.New(apperrors.CodeUnauthorized, "Failed to get user tokens", 401)
	}

	return s.oauthClient.GetHTTPClient(ctx, accessToken, refreshToken), nil
}

// convertCachedInsights converts cached map to BenchmarkInsights (1:1 with Python)
func (s *BenchmarkService) convertCachedInsights(data map[string]interface{}) *domain.BenchmarkInsights {
	insights := &domain.BenchmarkInsights{}

	// Convert visibility_performance
	if vp, ok := data["visibility_performance"].(map[string]interface{}); ok {
		insights.VisibilityPerformance = &domain.VisibilityPerformance{
			OverallAssessment: getStringValue(vp, "overall_assessment"),
			Metrics:           getMapValue(vp, "metrics"),
			Score:             getFloatValue(vp, "score"),
			Trend:             getStringValue(vp, "trend"),
		}
	}

	// Convert analysis
	if analysis, ok := data["analysis"].(map[string]interface{}); ok {
		insights.Analysis = &domain.Analysis{
			Summary:         getStringValue(analysis, "summary"),
			Strengths:       getStringSlice(analysis, "strengths"),
			Improvements:    getStringSlice(analysis, "improvements"),
			Recommendations: getStringSlice(analysis, "recommendations"),
		}
	}

	// Convert generated_at
	if generatedAt, ok := data["generated_at"].(string); ok {
		insights.GeneratedAt = generatedAt
	}

	return insights
}

// insightsToMap converts BenchmarkInsights to map for caching (1:1 with Python)
func (s *BenchmarkService) insightsToMap(insights *domain.BenchmarkInsights) map[string]interface{} {
	result := make(map[string]interface{})

	if insights.VisibilityPerformance != nil {
		result["visibility_performance"] = map[string]interface{}{
			"overall_assessment": insights.VisibilityPerformance.OverallAssessment,
			"metrics":            insights.VisibilityPerformance.Metrics,
			"score":              insights.VisibilityPerformance.Score,
			"trend":              insights.VisibilityPerformance.Trend,
		}
	}

	if insights.Analysis != nil {
		result["analysis"] = map[string]interface{}{
			"summary":         insights.Analysis.Summary,
			"strengths":       insights.Analysis.Strengths,
			"improvements":    insights.Analysis.Improvements,
			"recommendations": insights.Analysis.Recommendations,
		}
	}

	result["generated_at"] = insights.GeneratedAt

	return result
}

// Helper functions for type conversion
func getStringValue(m map[string]interface{}, key string) string {
	if v, ok := m[key].(string); ok {
		return v
	}
	return ""
}

func getFloatValue(m map[string]interface{}, key string) float64 {
	switch v := m[key].(type) {
	case float64:
		return v
	case int:
		return float64(v)
	case int64:
		return float64(v)
	}
	return 0
}

func getMapValue(m map[string]interface{}, key string) map[string]interface{} {
	if v, ok := m[key].(map[string]interface{}); ok {
		return v
	}
	return nil
}

func getStringSlice(m map[string]interface{}, key string) []string {
	if v, ok := m[key].([]interface{}); ok {
		result := make([]string, 0, len(v))
		for _, item := range v {
			if str, ok := item.(string); ok {
				result = append(result, str)
			}
		}
		return result
	}
	if v, ok := m[key].([]string); ok {
		return v
	}
	return nil
}
