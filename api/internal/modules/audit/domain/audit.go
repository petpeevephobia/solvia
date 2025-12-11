package domain

import (
	"strings"
	"time"
)

// AuditStatus represents the status of an audit
type AuditStatus string

const (
	AuditStatusPending    AuditStatus = "pending"
	AuditStatusProcessing AuditStatus = "processing"
	AuditStatusCompleted  AuditStatus = "completed"
	AuditStatusFailed     AuditStatus = "failed"
)

// SEOStage represents the SEO visibility stage
type SEOStage string

const (
	SEOStageHidden       SEOStage = "hidden"       // < 50 impressions
	SEOStageEmerging     SEOStage = "emerging"     // 50-299 impressions
	SEOStageDiscoverable SEOStage = "discoverable" // 300-1999 impressions
	SEOStageTrusted      SEOStage = "trusted"      // 2000+ impressions
)

// Audit represents an SEO audit record
type Audit struct {
	ID          int64       `json:"id"`
	UserEmail   string      `json:"user_email"`
	WebsiteURL  string      `json:"website_url"`
	Status      AuditStatus `json:"status"`
	SEOScore    float64     `json:"seo_score"`
	SEOStage    SEOStage    `json:"seo_stage"`
	PDFPath     string      `json:"pdf_path,omitempty"`
	PDFGenerated bool       `json:"pdf_generated"`          // 1:1 with Python
	EmailSent    bool       `json:"email_sent"`             // 1:1 with Python
	CreatedAt   time.Time   `json:"created_at"`
	CompletedAt *time.Time  `json:"completed_at,omitempty"`
	Error       string      `json:"error,omitempty"`
}

// IssuesCount represents issue counts by severity (1:1 with Python issues_count dict)
type IssuesCount struct {
	Critical int `json:"critical"`
	High     int `json:"high"`
	Medium   int `json:"medium"`
	Low      int `json:"low"`
}

// AuditReportResponse matches Python AuditReportResponse exactly
type AuditReportResponse struct {
	AuditID      string                   `json:"audit_id"`      // String UUID for 1:1 with Python
	Status       string                   `json:"status"`
	SEOScore     float64                  `json:"seo_score"`
	PDFGenerated bool                     `json:"pdf_generated"`
	EmailSent    bool                     `json:"email_sent"`
	IssuesCount  IssuesCount              `json:"issues_count"`
	TopIssues    []map[string]interface{} `json:"top_issues"`
	Message      string                   `json:"message"`
}

// AuditMetrics contains all metrics for an audit
type AuditMetrics struct {
	// Current period (last 28 days)
	Impressions int     `json:"impressions"`
	Clicks      int     `json:"clicks"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`

	// Previous period (28 days before current)
	PrevImpressions int     `json:"prev_impressions"`
	PrevClicks      int     `json:"prev_clicks"`
	PrevCTR         float64 `json:"prev_ctr"`
	PrevPosition    float64 `json:"prev_position"`

	// Changes (percentage)
	ImpressionsChange float64 `json:"impressions_change"`
	ClicksChange      float64 `json:"clicks_change"`
	CTRChange         float64 `json:"ctr_change"`
	PositionChange    float64 `json:"position_change"`
}

// AuditIssue represents a critical SEO issue (1:1 with Python AuditIssue)
type AuditIssue struct {
	ID             int64     `json:"id"`
	AuditID        int64     `json:"audit_id"`
	Severity       string    `json:"severity"` // critical, high, medium, low (1:1 with Python)
	Category       string    `json:"category"` // traffic, position, ctr, technical
	Title          string    `json:"title"`
	Description    string    `json:"description"`
	Impact         string    `json:"impact"`
	Recommendation string    `json:"recommendation"` // 1:1 with Python (was "suggestion")
	CreatedAt      time.Time `json:"created_at"`
}

// TopQuery represents a top-performing query
type TopQuery struct {
	Query       string  `json:"query"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// TopPage represents a top-performing page
type TopPage struct {
	Page        string  `json:"page"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// AuditData contains all data needed for PDF generation
type AuditData struct {
	Audit        *Audit          `json:"audit"`
	Metrics      *AuditMetrics   `json:"metrics"`
	Issues       []AuditIssue    `json:"issues"`
	TopQueries   []TopQuery      `json:"top_queries"`
	TopPages     []TopPage       `json:"top_pages"`
	Changes28Day *Changes28Day   `json:"changes_28day,omitempty"` // V1 vs V2 changes for gamified PDF
	TimeSeriesData []DailyMetric `json:"time_series_data,omitempty"` // Daily metrics for charts
}

// DailyMetric represents metrics for a single day (for V1 vs V2 calculation)
type DailyMetric struct {
	Date        string  `json:"date"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// Changes28Day represents V1 (first day) vs V2 (last day) changes (1:1 with Python)
type Changes28Day struct {
	ImpressionsChange string `json:"impressions_change"` // "+X" or "-X" or "N/A"
	ClicksChange      string `json:"clicks_change"`
	CTRChange         string `json:"ctr_change"`
	PositionChange    string `json:"position_change"`
	V1Date            string `json:"v1_date,omitempty"`
	V2Date            string `json:"v2_date,omitempty"`
	HasSufficientData bool   `json:"has_sufficient_data"`
}

// GetSEOStage determines the SEO stage based on impressions
func GetSEOStage(impressions int) SEOStage {
	switch {
	case impressions >= 2000:
		return SEOStageTrusted
	case impressions >= 300:
		return SEOStageDiscoverable
	case impressions >= 50:
		return SEOStageEmerging
	default:
		return SEOStageHidden
	}
}

// CalculateChange calculates percentage change between two values
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
// INDUSTRY DETECTION (1:1 with Python detect_industry_from_url)
// ============================================================================

// IndustryType represents detected industry type
type IndustryType string

const (
	IndustryECommerce     IndustryType = "e-commerce"
	IndustrySaaS          IndustryType = "saas"
	IndustryBlog          IndustryType = "blog"
	IndustryLocalBusiness IndustryType = "local_business"
	IndustryDefault       IndustryType = "default"
)

// DetectIndustryFromURL detects industry from website URL (1:1 with Python)
func DetectIndustryFromURL(websiteURL string) IndustryType {
	urlLower := strings.ToLower(websiteURL)

	// E-commerce indicators
	eCommerceKeywords := []string{"shop", "store", "buy", "cart", "product"}
	for _, word := range eCommerceKeywords {
		if strings.Contains(urlLower, word) {
			return IndustryECommerce
		}
	}

	// SaaS indicators
	saasKeywords := []string{"saas", "software", "app", "platform", "tool"}
	for _, word := range saasKeywords {
		if strings.Contains(urlLower, word) {
			return IndustrySaaS
		}
	}

	// Blog/content indicators
	blogKeywords := []string{"blog", "news", "article", "content", "media"}
	for _, word := range blogKeywords {
		if strings.Contains(urlLower, word) {
			return IndustryBlog
		}
	}

	// Local business indicators
	localKeywords := []string{"local", "restaurant", "service", "clinic", "lawyer"}
	for _, word := range localKeywords {
		if strings.Contains(urlLower, word) {
			return IndustryLocalBusiness
		}
	}

	// Default
	return IndustryDefault
}

// ============================================================================
// MERGE RAG INSIGHTS (1:1 with Python merge_rag_insights)
// ============================================================================

// EnhancedIssue represents a RAG-enhanced issue with additional metadata
type EnhancedIssue struct {
	AuditIssue
	ConfidenceScore  float64                `json:"confidence_score"`
	EvidenceCount    int                    `json:"evidence_count"`
	PatternsDetected int                    `json:"patterns_detected"`
	DataPoints       map[string]interface{} `json:"data_points,omitempty"`
	Source           string                 `json:"source"` // "audit_engine" or "enhanced_rag"
	PriorityScore    float64                `json:"priority_score"`
}

// EnhancedInsights contains summary of RAG-enhanced analysis
type EnhancedInsights struct {
	TotalRAGIssues        int  `json:"total_rag_issues"`
	EvidenceBackedIssues  int  `json:"evidence_backed_issues"`
	PatternDetectedIssues int  `json:"pattern_detected_issues"`
	HighConfidenceIssues  int  `json:"high_confidence_issues"`
	RAGEnhanced           bool `json:"rag_enhanced"`
}

// MergedAuditResult contains merged audit results with RAG insights
type MergedAuditResult struct {
	Issues           []EnhancedIssue  `json:"issues"`
	EnhancedInsights EnhancedInsights `json:"enhanced_insights"`
	CriticalCount    int              `json:"critical_count"`
	HighCount        int              `json:"high_count"`
	MediumCount      int              `json:"medium_count"`
	LowCount         int              `json:"low_count"`
}

// MergeRAGInsights merges enhanced RAG insights with traditional audit results (1:1 with Python)
func MergeRAGInsights(existingIssues []AuditIssue, ragIssues []EnhancedIssue) *MergedAuditResult {
	result := &MergedAuditResult{
		Issues: make([]EnhancedIssue, 0),
	}

	// Convert existing issues to enhanced format with audit_engine source
	for _, issue := range existingIssues {
		enhanced := EnhancedIssue{
			AuditIssue:       issue,
			ConfidenceScore:  0.7, // Default confidence for audit engine issues
			EvidenceCount:    0,
			PatternsDetected: 0,
			Source:           "audit_engine",
			PriorityScore:    calculateIssuePriority(issue.Severity, 0.7),
		}
		result.Issues = append(result.Issues, enhanced)
	}

	// Add RAG issues with enhanced_rag source
	for _, issue := range ragIssues {
		issue.Source = "enhanced_rag"
		result.Issues = append(result.Issues, issue)
	}

	// Sort by severity and confidence (1:1 with Python)
	sortEnhancedIssues(result.Issues)

	// Limit to top 10 issues
	if len(result.Issues) > 10 {
		result.Issues = result.Issues[:10]
	}

	// Calculate counts
	for _, issue := range result.Issues {
		switch issue.Severity {
		case "critical":
			result.CriticalCount++
		case "high":
			result.HighCount++
		case "medium":
			result.MediumCount++
		case "low":
			result.LowCount++
		}
	}

	// Calculate enhanced insights
	result.EnhancedInsights = EnhancedInsights{
		TotalRAGIssues:        len(ragIssues),
		RAGEnhanced:           len(ragIssues) > 0,
	}
	for _, issue := range ragIssues {
		if issue.EvidenceCount > 0 {
			result.EnhancedInsights.EvidenceBackedIssues++
		}
		if issue.PatternsDetected > 0 {
			result.EnhancedInsights.PatternDetectedIssues++
		}
		if issue.ConfidenceScore > 0.8 {
			result.EnhancedInsights.HighConfidenceIssues++
		}
	}

	return result
}

// calculateIssuePriority calculates priority score (1:1 with Python)
func calculateIssuePriority(severity string, confidence float64) float64 {
	severityWeights := map[string]float64{
		"critical": 100,
		"high":     75,
		"medium":   50,
		"low":      25,
	}

	weight, ok := severityWeights[severity]
	if !ok {
		weight = 25
	}

	return weight * confidence
}

// sortEnhancedIssues sorts issues by severity and confidence (1:1 with Python)
func sortEnhancedIssues(issues []EnhancedIssue) {
	severityOrder := map[string]int{
		"critical": 0,
		"high":     1,
		"medium":   2,
		"low":      3,
	}

	// Simple bubble sort for small list
	for i := 0; i < len(issues)-1; i++ {
		for j := i + 1; j < len(issues); j++ {
			iSeverity := severityOrder[issues[i].Severity]
			jSeverity := severityOrder[issues[j].Severity]

			// Sort by severity first, then by confidence, then by priority
			if iSeverity > jSeverity ||
				(iSeverity == jSeverity && issues[i].ConfidenceScore < issues[j].ConfidenceScore) ||
				(iSeverity == jSeverity && issues[i].ConfidenceScore == issues[j].ConfidenceScore && issues[i].PriorityScore < issues[j].PriorityScore) {
				issues[i], issues[j] = issues[j], issues[i]
			}
		}
	}
}
