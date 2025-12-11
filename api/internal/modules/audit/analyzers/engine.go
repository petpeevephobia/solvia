package analyzers

import (
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
)

// AuditEngine orchestrates all analyzers (1:1 with Python audit_engine.py)
// Combines Performance, Anomaly, Trend, and Opportunity analyzers
type AuditEngine struct {
	performanceAnalyzer *PerformanceAnalyzer
	anomalyDetector     *AnomalyDetector
	trendAnalyzer       *TrendAnalyzer
	opportunityAnalyzer *OpportunityAnalyzer
}

// NewAuditEngine creates a new audit engine with all analyzers
func NewAuditEngine() *AuditEngine {
	return &AuditEngine{
		performanceAnalyzer: NewPerformanceAnalyzer(),
		anomalyDetector:     NewAnomalyDetector(),
		trendAnalyzer:       NewTrendAnalyzer(),
		opportunityAnalyzer: NewOpportunityAnalyzer(),
	}
}

// AuditEngineResult contains combined results from all analyzers
type AuditEngineResult struct {
	// All detected issues sorted by severity
	Issues []domain.AuditIssue `json:"issues"`

	// Analysis results from each analyzer
	PerformanceResult  *AnalyzeResult     `json:"performance,omitempty"`
	AnomalyResult      *AnomalyResult     `json:"anomaly,omitempty"`
	TrendResult        *TrendResult       `json:"trend,omitempty"`
	OpportunityResult  *OpportunityResult `json:"opportunity,omitempty"`

	// Summary statistics (1:1 with Python - includes critical)
	TotalIssues            int     `json:"total_issues"`
	CriticalSeverityCount  int     `json:"critical_severity_count"` // 1:1 with Python
	HighSeverityCount      int     `json:"high_severity_count"`
	MediumSeverityCount    int     `json:"medium_severity_count"`
	LowSeverityCount       int     `json:"low_severity_count"`
	MomentumScore          float64 `json:"momentum_score"`
	PotentialClicks        int     `json:"potential_clicks"`
}

// RunFullAnalysis executes all analyzers and combines results
func (e *AuditEngine) RunFullAnalysis(
	metrics *domain.AuditMetrics,
	dailyMetrics []google.DailyMetric,
	topQueries []domain.TopQuery,
	topPages []domain.TopPage,
	auditID int64,
) *AuditEngineResult {
	result := &AuditEngineResult{
		Issues: []domain.AuditIssue{},
	}

	// Run Performance Analyzer
	result.PerformanceResult = e.performanceAnalyzer.Analyze(metrics, auditID)
	result.Issues = append(result.Issues, result.PerformanceResult.Issues...)

	// Run Anomaly Detector (requires daily metrics)
	if len(dailyMetrics) >= 7 {
		result.AnomalyResult = e.anomalyDetector.Analyze(dailyMetrics, auditID)
		result.Issues = append(result.Issues, result.AnomalyResult.Issues...)
	}

	// Run Trend Analyzer (requires daily metrics)
	if len(dailyMetrics) >= 14 {
		result.TrendResult = e.trendAnalyzer.Analyze(dailyMetrics, auditID)
		result.Issues = append(result.Issues, result.TrendResult.Issues...)
		result.MomentumScore = result.TrendResult.MomentumScore
	}

	// Run Opportunity Analyzer
	result.OpportunityResult = e.opportunityAnalyzer.Analyze(metrics, topQueries, topPages, auditID)
	result.Issues = append(result.Issues, result.OpportunityResult.Issues...)
	result.PotentialClicks = result.OpportunityResult.TotalPotential

	// Deduplicate and sort issues
	result.Issues = e.deduplicateIssues(result.Issues)
	result.Issues = e.sortIssuesBySeverity(result.Issues)

	// Calculate summary statistics (1:1 with Python - includes critical)
	result.TotalIssues = len(result.Issues)
	for _, issue := range result.Issues {
		switch issue.Severity {
		case "critical":
			result.CriticalSeverityCount++
		case "high":
			result.HighSeverityCount++
		case "medium":
			result.MediumSeverityCount++
		case "low":
			result.LowSeverityCount++
		}
	}

	return result
}

// RunQuickAnalysis runs only performance analysis (for real-time endpoints)
func (e *AuditEngine) RunQuickAnalysis(metrics *domain.AuditMetrics, auditID int64) []domain.AuditIssue {
	result := e.performanceAnalyzer.Analyze(metrics, auditID)
	return e.sortIssuesBySeverity(result.Issues)
}

// deduplicateIssues removes duplicate issues based on title
func (e *AuditEngine) deduplicateIssues(issues []domain.AuditIssue) []domain.AuditIssue {
	seen := make(map[string]bool)
	var deduplicated []domain.AuditIssue

	for _, issue := range issues {
		key := issue.Category + ":" + issue.Title
		if !seen[key] {
			seen[key] = true
			deduplicated = append(deduplicated, issue)
		}
	}

	return deduplicated
}

// sortIssuesBySeverity sorts issues by severity (critical > high > medium > low) - 1:1 with Python
func (e *AuditEngine) sortIssuesBySeverity(issues []domain.AuditIssue) []domain.AuditIssue {
	severityOrder := map[string]int{
		"critical": 0, // 1:1 with Python - weight 1000
		"high":     1, // 1:1 with Python - weight 100
		"medium":   2, // 1:1 with Python - weight 10
		"low":      3, // 1:1 with Python - weight 1
	}

	// Bubble sort by severity
	for i := 0; i < len(issues)-1; i++ {
		for j := i + 1; j < len(issues); j++ {
			iOrder := severityOrder[issues[i].Severity]
			jOrder := severityOrder[issues[j].Severity]
			if iOrder > jOrder {
				issues[i], issues[j] = issues[j], issues[i]
			}
		}
	}

	return issues
}

// GetTopIssues returns the top N issues sorted by severity
func (e *AuditEngine) GetTopIssues(issues []domain.AuditIssue, limit int) []domain.AuditIssue {
	sorted := e.sortIssuesBySeverity(issues)
	if len(sorted) <= limit {
		return sorted
	}
	return sorted[:limit]
}

// AnalyzeMetricsOnly runs analysis using only aggregate metrics (no time series)
func (e *AuditEngine) AnalyzeMetricsOnly(metrics *domain.AuditMetrics, auditID int64) *AuditEngineResult {
	result := &AuditEngineResult{
		Issues: []domain.AuditIssue{},
	}

	// Run Performance Analyzer
	result.PerformanceResult = e.performanceAnalyzer.Analyze(metrics, auditID)
	result.Issues = append(result.Issues, result.PerformanceResult.Issues...)

	// Sort and calculate statistics (1:1 with Python)
	result.Issues = e.sortIssuesBySeverity(result.Issues)
	result.TotalIssues = len(result.Issues)

	for _, issue := range result.Issues {
		switch issue.Severity {
		case "critical":
			result.CriticalSeverityCount++
		case "high":
			result.HighSeverityCount++
		case "medium":
			result.MediumSeverityCount++
		case "low":
			result.LowSeverityCount++
		}
	}

	return result
}

// AnalyzeWithQueries runs analysis using metrics and query data
func (e *AuditEngine) AnalyzeWithQueries(
	metrics *domain.AuditMetrics,
	topQueries []domain.TopQuery,
	topPages []domain.TopPage,
	auditID int64,
) *AuditEngineResult {
	result := &AuditEngineResult{
		Issues: []domain.AuditIssue{},
	}

	// Run Performance Analyzer
	result.PerformanceResult = e.performanceAnalyzer.Analyze(metrics, auditID)
	result.Issues = append(result.Issues, result.PerformanceResult.Issues...)

	// Run Opportunity Analyzer
	result.OpportunityResult = e.opportunityAnalyzer.Analyze(metrics, topQueries, topPages, auditID)
	result.Issues = append(result.Issues, result.OpportunityResult.Issues...)
	result.PotentialClicks = result.OpportunityResult.TotalPotential

	// Deduplicate and sort
	result.Issues = e.deduplicateIssues(result.Issues)
	result.Issues = e.sortIssuesBySeverity(result.Issues)

	// Calculate statistics (1:1 with Python)
	result.TotalIssues = len(result.Issues)
	for _, issue := range result.Issues {
		switch issue.Severity {
		case "critical":
			result.CriticalSeverityCount++
		case "high":
			result.HighSeverityCount++
		case "medium":
			result.MediumSeverityCount++
		case "low":
			result.LowSeverityCount++
		}
	}

	return result
}
