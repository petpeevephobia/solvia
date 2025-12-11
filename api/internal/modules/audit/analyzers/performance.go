// Package analyzers provides SEO analysis tools (1:1 parity with Python audit_engine.py)
package analyzers

import (
	"fmt"
	"math"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
)

// CTR benchmarks by position (1:1 with Python seo_scoring.py and audit/analyzers/performance.py)
var CTRBenchmarks = map[int]float64{
	1:  0.285, // Position 1: 28.5% CTR
	2:  0.157, // Position 2: 15.7% CTR
	3:  0.094, // Position 3: 9.4% CTR
	4:  0.062, // Position 4: 6.2% CTR
	5:  0.050, // Position 5: 5.0% CTR
	6:  0.038, // Position 6: 3.8% CTR
	7:  0.030, // Position 7: 3.0% CTR
	8:  0.024, // Position 8: 2.4% CTR
	9:  0.020, // Position 9: 2.0% CTR
	10: 0.025, // Position 10: 2.5% CTR
}

// PerformanceAnalyzer analyzes CTR, position, and visibility performance
// Implements performance analysis logic from Python audit_engine.py
type PerformanceAnalyzer struct {
	// CTR thresholds (as decimal values, not percentages)
	lowCTRThreshold      float64
	veryLowCTRThreshold  float64

	// Position thresholds
	poorPositionThreshold float64
	goodPositionThreshold float64

	// Visibility thresholds
	veryLowImpressions int
	lowImpressions     int
	emergingThreshold  int
}

// NewPerformanceAnalyzer creates a new performance analyzer with default thresholds
func NewPerformanceAnalyzer() *PerformanceAnalyzer {
	return &PerformanceAnalyzer{
		// CTR thresholds (0.03 = 3%, 0.01 = 1%)
		lowCTRThreshold:      0.03,
		veryLowCTRThreshold:  0.01,

		// Position thresholds
		poorPositionThreshold: 50.0,
		goodPositionThreshold: 10.0,

		// Visibility thresholds (matches Python SEO stages)
		veryLowImpressions: 100,
		lowImpressions:     500,
		emergingThreshold:  50,
	}
}

// AnalyzeResult contains results from performance analysis
type AnalyzeResult struct {
	Issues []domain.AuditIssue
}

// Analyze performs comprehensive performance analysis (1:1 with Python audit_engine.py)
func (a *PerformanceAnalyzer) Analyze(metrics *domain.AuditMetrics, auditID int64) *AnalyzeResult {
	result := &AnalyzeResult{
		Issues: []domain.AuditIssue{},
	}

	// Analyze CTR performance
	ctrIssues := a.analyzeCTR(metrics, auditID)
	result.Issues = append(result.Issues, ctrIssues...)

	// Analyze position performance
	positionIssues := a.analyzePosition(metrics, auditID)
	result.Issues = append(result.Issues, positionIssues...)

	// Analyze visibility (impressions)
	visibilityIssues := a.analyzeVisibility(metrics, auditID)
	result.Issues = append(result.Issues, visibilityIssues...)

	// Analyze CTR vs position benchmark
	benchmarkIssues := a.analyzeCTRBenchmark(metrics, auditID)
	result.Issues = append(result.Issues, benchmarkIssues...)

	// Analyze zero clicks issue (1:1 with Python - CRITICAL severity)
	zeroClicksIssues := a.analyzeZeroClicks(metrics, auditID)
	result.Issues = append(result.Issues, zeroClicksIssues...)

	return result
}

// analyzeCTR checks CTR performance against thresholds
func (a *PerformanceAnalyzer) analyzeCTR(metrics *domain.AuditMetrics, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// Skip if no meaningful impressions
	if metrics.Impressions < a.veryLowImpressions {
		return issues
	}

	// Very low CTR (< 1%)
	if metrics.CTR < a.veryLowCTRThreshold {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "ctr",
			Title:       "Very Low Click-Through Rate",
			Description: fmt.Sprintf("CTR is only %.2f%%, well below the industry average of 2-5%%.", metrics.CTR*100),
			Impact:      "People see your site in search results but don't click - you're wasting visibility. Every impression without a click is a missed opportunity.",
			Recommendation:  "Improve meta titles and descriptions to be more compelling. Use action words, include numbers, and address user intent directly.",
		})
	} else if metrics.CTR < a.lowCTRThreshold {
		// Below average CTR (1-3%)
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "ctr",
			Title:       "Below Average Click-Through Rate",
			Description: fmt.Sprintf("CTR is %.2f%%, below the typical 2-5%% range for most industries.", metrics.CTR*100),
			Impact:      "You're not maximizing the traffic potential from your current search visibility.",
			Recommendation:  "Test different meta descriptions and add structured data (schema markup) to enhance your search snippets.",
		})
	}

	return issues
}

// analyzePosition checks position performance
func (a *PerformanceAnalyzer) analyzePosition(metrics *domain.AuditMetrics, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// Skip if no data
	if metrics.Position == 0 {
		return issues
	}

	// Very poor position (50+)
	if metrics.Position > a.poorPositionThreshold {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "position",
			Title:       "Poor Search Rankings",
			Description: fmt.Sprintf("Average position is %.1f, which means your pages typically appear on page 5+ of search results.", metrics.Position),
			Impact:      "Users rarely scroll past page 1-2 of search results. Position 50+ means virtually no organic clicks.",
			Recommendation:  "Focus on improving content quality, building authoritative backlinks, and better matching user search intent.",
		})
	} else if metrics.Position > 20 {
		// Moderate position (20-50)
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "position",
			Title:       "Average Rankings Need Improvement",
			Description: fmt.Sprintf("Average position is %.1f, mostly appearing on page 2-5 of search results.", metrics.Position),
			Impact:      "Page 2+ gets significantly less clicks than page 1. Only 0.78%% of searchers click on page 2 results.",
			Recommendation:  "Identify your best-performing queries (positions 11-20) and focus on moving them to page 1.",
		})
	} else if metrics.Position > a.goodPositionThreshold {
		// Good but not great (10-20)
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "low",
			Category:    "position",
			Title:       "Rankings Close to Page 1",
			Description: fmt.Sprintf("Average position is %.1f - you're on the edge of page 1.", metrics.Position),
			Impact:      "Small improvements could push you to page 1 where 91%% of clicks happen.",
			Recommendation:  "Focus on 'low-hanging fruit' - queries where you rank 11-15 that could easily move to page 1.",
		})
	}

	return issues
}

// analyzeVisibility checks impressions/visibility
func (a *PerformanceAnalyzer) analyzeVisibility(metrics *domain.AuditMetrics, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// Very low visibility (< 100 impressions)
	if metrics.Impressions < a.veryLowImpressions {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "visibility",
			Title:       "Very Low Search Visibility",
			Description: fmt.Sprintf("Your website had only %d impressions in the last 28 days.", metrics.Impressions),
			Impact:      "Low visibility means potential customers cannot find your website through search. You're missing out on organic discovery.",
			Recommendation:  "Focus on creating quality content targeting relevant keywords your audience searches for. Consider long-tail keywords with less competition.",
		})
	} else if metrics.Impressions < a.lowImpressions {
		// Low visibility (100-500 impressions)
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "visibility",
			Title:       "Limited Search Visibility",
			Description: fmt.Sprintf("Your website had %d impressions in the last 28 days - still in the 'emerging' stage.", metrics.Impressions),
			Impact:      "You're starting to appear in search results but haven't reached critical mass for consistent organic traffic.",
			Recommendation:  "Expand your content strategy to target more keywords. Consider creating cornerstone content and topic clusters.",
		})
	}

	return issues
}

// analyzeCTRBenchmark compares actual CTR to expected CTR for current position
func (a *PerformanceAnalyzer) analyzeCTRBenchmark(metrics *domain.AuditMetrics, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// Need meaningful data to compare
	if metrics.Position == 0 || metrics.Impressions < a.veryLowImpressions {
		return issues
	}

	// Get expected CTR for current position
	positionInt := int(metrics.Position)
	if positionInt > 10 {
		positionInt = 10 // Cap at position 10 for benchmarks
	}
	if positionInt < 1 {
		positionInt = 1
	}

	expectedCTR, exists := CTRBenchmarks[positionInt]
	if !exists {
		return issues
	}

	// Calculate CTR gap (actual vs expected)
	ctrGap := expectedCTR - metrics.CTR
	ctrGapPercent := (ctrGap / expectedCTR) * 100

	// Significant underperformance (>50% below benchmark)
	if ctrGapPercent > 50 && metrics.CTR < expectedCTR {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "medium",
			Category:    "ctr",
			Title:       "CTR Below Position Benchmark",
			Description: fmt.Sprintf("At position %.1f, expected CTR is ~%.1f%%, but actual CTR is %.2f%%. You're underperforming by %.0f%%.",
				metrics.Position, expectedCTR*100, metrics.CTR*100, ctrGapPercent),
			Impact:      "Your search snippets are not compelling enough compared to competitors at similar positions.",
			Recommendation:  "Review your meta titles and descriptions. Test different formats, add unique value propositions, and include calls-to-action.",
		})
	}

	return issues
}

// GetExpectedCTR returns the expected CTR for a given position (1:1 with Python)
// Uses exponential decay for positions > 10 instead of hardcoded value
func GetExpectedCTR(position float64) float64 {
	positionInt := int(position)
	if positionInt < 1 {
		positionInt = 1
	}

	// For positions 1-10, use benchmark values
	if ctr, exists := CTRBenchmarks[positionInt]; exists {
		return ctr
	}

	// For positions > 10, use exponential decay (1:1 with Python)
	// Formula: CTR_10 * 0.9^(position - 10)
	if position > 10 {
		return CTRBenchmarks[10] * math.Pow(0.9, position-10)
	}

	return 0.02 // Default 2% CTR
}

// analyzeZeroClicks detects zero clicks with significant impressions (1:1 with Python)
// This is a CRITICAL issue indicating severe CTR or intent mismatch problem
func (a *PerformanceAnalyzer) analyzeZeroClicks(metrics *domain.AuditMetrics, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// 1:1 with Python: >= 1000 impressions but 0 clicks = CRITICAL
	if metrics.Impressions >= 1000 && metrics.Clicks == 0 {
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "critical", // 1:1 with Python - CRITICAL severity
			Category:    "ctr",
			Title:       "Zero Clicks Despite High Visibility",
			Description: fmt.Sprintf("Your site had %d impressions but received 0 clicks - a 0%% CTR.", metrics.Impressions),
			Impact:      "Users are seeing your site in search results but never clicking. This indicates a severe disconnect between your content and user expectations, or extremely poor meta descriptions/titles.",
			Recommendation:  "Urgently review and rewrite your page titles and meta descriptions. Ensure they accurately describe your content and include compelling calls-to-action. Consider if your pages are targeting the wrong search intent.",
		})
	} else if metrics.Impressions >= 500 && metrics.Clicks == 0 {
		// Medium impressions with zero clicks - still critical but slightly less severe
		issues = append(issues, domain.AuditIssue{
			AuditID:     auditID,
			Severity:    "high",
			Category:    "ctr",
			Title:       "No Clicks From Search Results",
			Description: fmt.Sprintf("Your site had %d impressions but received 0 clicks.", metrics.Impressions),
			Impact:      "You're appearing in search results but failing to attract any clicks. This is wasting your search visibility.",
			Recommendation:  "Review your meta titles and descriptions. Make sure they're compelling and accurately represent your content. Check if you're ranking for irrelevant queries.",
		})
	}

	return issues
}
