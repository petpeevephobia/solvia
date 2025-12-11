package rag

import (
	"fmt"
	"math"
	"time"
)

// ============================================================================
// ENHANCED SEO ISSUE ANALYZERS (1:1 with Python rag_analyzer_enhanced.py)
// ============================================================================

// IssueSeverity represents severity levels (1:1 with Python)
type IssueSeverity string

const (
	SeverityCritical IssueSeverity = "critical" // >50% traffic loss
	SeverityHigh     IssueSeverity = "high"     // 20-50% impact
	SeverityMedium   IssueSeverity = "medium"   // 10-20% impact
	SeverityLow      IssueSeverity = "low"      // <10% impact
)

// EnhancedIssue represents an SEO issue with evidence and confidence (1:1 with Python)
type EnhancedIssue struct {
	Title           string                 `json:"title"`
	Description     string                 `json:"description"`
	Severity        IssueSeverity          `json:"severity"`
	Impact          string                 `json:"impact"`
	Recommendation  string                 `json:"recommendation"`
	Category        string                 `json:"category"`
	DataPoints      map[string]interface{} `json:"data_points"`
	ConfidenceScore float64                `json:"confidence_score"`
	EvidenceCount   int                    `json:"evidence_count"`
	PatternsCount   int                    `json:"patterns_count"`
	Source          string                 `json:"source"`
	PriorityScore   float64                `json:"priority_score"`
}

// GSCMetricsData represents GSC metrics for analysis
type GSCMetricsData struct {
	TotalImpressions int
	TotalClicks      int
	AverageCTR       float64
	AveragePosition  float64
	PrevImpressions  int
	PrevClicks       int
	PrevCTR          float64
	PrevPosition     float64
	TimeSeriesData   []DailyMetric
}

// DailyMetric represents a single day's metrics
type DailyMetric struct {
	Date        time.Time
	Impressions int
	Clicks      int
	CTR         float64
	Position    float64
}

// PerformanceAnalyzer analyzes performance issues (1:1 with Python)
type PerformanceAnalyzer struct{}

// Analyze checks for performance-related SEO issues
func (a *PerformanceAnalyzer) Analyze(data *GSCMetricsData) []EnhancedIssue {
	var issues []EnhancedIssue

	// CTR below benchmark (position-based)
	expectedCTR := getExpectedCTR(data.AveragePosition)
	if data.AverageCTR < expectedCTR*0.7 { // 30% below expected
		severity := SeverityMedium
		if data.AverageCTR < expectedCTR*0.5 {
			severity = SeverityHigh
		}

		issues = append(issues, EnhancedIssue{
			Title:       "CTR Below Benchmark",
			Description: fmt.Sprintf("Your CTR of %.2f%% is below the expected %.2f%% for position %.1f", data.AverageCTR*100, expectedCTR*100, data.AveragePosition),
			Severity:    severity,
			Impact:      "Fewer clicks despite good impressions - potential for 20-40% more traffic",
			Recommendation: "Improve meta titles and descriptions to be more compelling. Add numbers, power words, and clear value propositions.",
			Category:       "performance",
			DataPoints: map[string]interface{}{
				"current_ctr":  data.AverageCTR,
				"expected_ctr": expectedCTR,
				"position":     data.AveragePosition,
			},
			ConfidenceScore: 0.85,
			Source:          "performance_analyzer",
		})
	}

	// Position declining
	if data.PrevPosition > 0 && data.AveragePosition-data.PrevPosition > 2 {
		severity := SeverityMedium
		if data.AveragePosition-data.PrevPosition > 5 {
			severity = SeverityHigh
		}

		issues = append(issues, EnhancedIssue{
			Title:       "Position Decline Detected",
			Description: fmt.Sprintf("Average position dropped from %.1f to %.1f (%.1f positions)", data.PrevPosition, data.AveragePosition, data.AveragePosition-data.PrevPosition),
			Severity:    severity,
			Impact:      "Lower positions mean fewer impressions and clicks",
			Recommendation: "Review recent content changes, check for new competitors, and update content freshness.",
			Category:       "performance",
			DataPoints: map[string]interface{}{
				"current_position":  data.AveragePosition,
				"previous_position": data.PrevPosition,
				"change":           data.AveragePosition - data.PrevPosition,
			},
			ConfidenceScore: 0.9,
			Source:          "performance_analyzer",
		})
	}

	return issues
}

// AnomalyAnalyzer detects anomalies in metrics (1:1 with Python)
type AnomalyAnalyzer struct{}

// Analyze checks for metric anomalies
func (a *AnomalyAnalyzer) Analyze(data *GSCMetricsData) []EnhancedIssue {
	var issues []EnhancedIssue

	// Check for sudden traffic drops
	if data.PrevImpressions > 0 {
		impressionChange := float64(data.TotalImpressions-data.PrevImpressions) / float64(data.PrevImpressions) * 100

		if impressionChange < -50 {
			issues = append(issues, EnhancedIssue{
				Title:       "Critical Traffic Drop",
				Description: fmt.Sprintf("Impressions dropped by %.1f%% from previous period", -impressionChange),
				Severity:    SeverityCritical,
				Impact:      "Major visibility loss - potential indexing or penalty issue",
				Recommendation: "Check Google Search Console for manual actions, verify robots.txt, and review recent site changes.",
				Category:       "anomaly",
				DataPoints: map[string]interface{}{
					"current_impressions":  data.TotalImpressions,
					"previous_impressions": data.PrevImpressions,
					"change_percent":       impressionChange,
				},
				ConfidenceScore: 0.95,
				Source:          "anomaly_analyzer",
			})
		} else if impressionChange < -30 {
			issues = append(issues, EnhancedIssue{
				Title:       "Significant Traffic Decline",
				Description: fmt.Sprintf("Impressions dropped by %.1f%% from previous period", -impressionChange),
				Severity:    SeverityHigh,
				Impact:      "Noticeable visibility loss - may indicate algorithm update or content decay",
				Recommendation: "Analyze which queries/pages lost impressions and update content accordingly.",
				Category:       "anomaly",
				DataPoints: map[string]interface{}{
					"current_impressions":  data.TotalImpressions,
					"previous_impressions": data.PrevImpressions,
					"change_percent":       impressionChange,
				},
				ConfidenceScore: 0.85,
				Source:          "anomaly_analyzer",
			})
		}
	}

	// Check for click anomalies
	if data.PrevClicks > 0 {
		clickChange := float64(data.TotalClicks-data.PrevClicks) / float64(data.PrevClicks) * 100

		if clickChange < -40 && data.TotalImpressions >= data.PrevImpressions {
			issues = append(issues, EnhancedIssue{
				Title:       "Click-Through Collapse",
				Description: fmt.Sprintf("Clicks dropped %.1f%% while impressions remained stable", -clickChange),
				Severity:    SeverityHigh,
				Impact:      "Users seeing your site but not clicking - meta tag or SERP feature issue",
				Recommendation: "Review meta descriptions for all major pages, check for SERP feature changes.",
				Category:       "anomaly",
				DataPoints: map[string]interface{}{
					"current_clicks":   data.TotalClicks,
					"previous_clicks":  data.PrevClicks,
					"change_percent":   clickChange,
					"impressions_stable": true,
				},
				ConfidenceScore: 0.88,
				Source:          "anomaly_analyzer",
			})
		}
	}

	return issues
}

// TrendAnalyzer analyzes trends in time series data (1:1 with Python)
type TrendAnalyzer struct{}

// Analyze checks for concerning trends
func (a *TrendAnalyzer) Analyze(data *GSCMetricsData) []EnhancedIssue {
	var issues []EnhancedIssue

	if len(data.TimeSeriesData) < 7 {
		return issues // Not enough data
	}

	// Calculate trend direction
	firstHalf := data.TimeSeriesData[:len(data.TimeSeriesData)/2]
	secondHalf := data.TimeSeriesData[len(data.TimeSeriesData)/2:]

	firstHalfAvg := averageImpressions(firstHalf)
	secondHalfAvg := averageImpressions(secondHalf)

	if firstHalfAvg > 0 {
		trendChange := (secondHalfAvg - firstHalfAvg) / firstHalfAvg * 100

		if trendChange < -20 {
			issues = append(issues, EnhancedIssue{
				Title:       "Declining Trend Detected",
				Description: fmt.Sprintf("Impressions trending down %.1f%% over the period", -trendChange),
				Severity:    SeverityMedium,
				Impact:      "Gradual visibility loss - may indicate content decay or competitive pressure",
				Recommendation: "Refresh content on top-performing pages, add new relevant content, build quality backlinks.",
				Category:       "trend",
				DataPoints: map[string]interface{}{
					"first_half_avg":  firstHalfAvg,
					"second_half_avg": secondHalfAvg,
					"trend_change":    trendChange,
				},
				ConfidenceScore: 0.75,
				Source:          "trend_analyzer",
			})
		}
	}

	// Check for volatility
	volatility := calculateVolatility(data.TimeSeriesData)
	if volatility > 0.5 {
		issues = append(issues, EnhancedIssue{
			Title:       "High Traffic Volatility",
			Description: fmt.Sprintf("Daily traffic varies significantly (volatility: %.2f)", volatility),
			Severity:    SeverityLow,
			Impact:      "Inconsistent visibility - may indicate ranking fluctuations",
			Recommendation: "Focus on stabilizing top keywords, diversify traffic sources.",
			Category:       "trend",
			DataPoints: map[string]interface{}{
				"volatility_score": volatility,
			},
			ConfidenceScore: 0.7,
			Source:          "trend_analyzer",
		})
	}

	return issues
}

// OpportunityAnalyzer identifies growth opportunities (1:1 with Python)
type OpportunityAnalyzer struct{}

// Analyze identifies opportunities for improvement
func (a *OpportunityAnalyzer) Analyze(data *GSCMetricsData) []EnhancedIssue {
	var issues []EnhancedIssue

	// Low impressions opportunity
	if data.TotalImpressions < 300 {
		issues = append(issues, EnhancedIssue{
			Title:       "Visibility Growth Opportunity",
			Description: fmt.Sprintf("With only %d impressions, there's significant room for growth", data.TotalImpressions),
			Severity:    SeverityMedium,
			Impact:      "Potential to 10x visibility with proper optimization",
			Recommendation: "Focus on keyword research, create more content, and build topical authority.",
			Category:       "opportunity",
			DataPoints: map[string]interface{}{
				"current_impressions": data.TotalImpressions,
				"potential_growth":    "10x",
			},
			ConfidenceScore: 0.8,
			Source:          "opportunity_analyzer",
		})
	}

	// Striking distance keywords (positions 4-10)
	if data.AveragePosition >= 4 && data.AveragePosition <= 10 {
		issues = append(issues, EnhancedIssue{
			Title:       "Striking Distance Keywords",
			Description: fmt.Sprintf("Average position of %.1f is in striking distance of top 3", data.AveragePosition),
			Severity:    SeverityLow,
			Impact:      "Moving to top 3 could increase CTR by 2-3x",
			Recommendation: "Focus on content depth, add supporting content, improve internal linking.",
			Category:       "opportunity",
			DataPoints: map[string]interface{}{
				"current_position":   data.AveragePosition,
				"target_position":    3,
				"potential_ctr_gain": "2-3x",
			},
			ConfidenceScore: 0.85,
			Source:          "opportunity_analyzer",
		})
	}

	// CTR improvement opportunity
	if data.AverageCTR < 0.02 && data.AveragePosition < 5 {
		issues = append(issues, EnhancedIssue{
			Title:       "CTR Improvement Opportunity",
			Description: "Good positions but CTR below 2% - meta optimization opportunity",
			Severity:    SeverityMedium,
			Impact:      "Optimized meta tags could double your clicks",
			Recommendation: "A/B test meta titles, add numbers and power words, use emotional triggers.",
			Category:       "opportunity",
			DataPoints: map[string]interface{}{
				"current_ctr":      data.AverageCTR,
				"position":         data.AveragePosition,
				"potential_clicks": data.TotalClicks * 2,
			},
			ConfidenceScore: 0.82,
			Source:          "opportunity_analyzer",
		})
	}

	return issues
}

// getExpectedCTR returns expected CTR for a given position (1:1 with Python)
func getExpectedCTR(position float64) float64 {
	ctrBenchmarks := map[int]float64{
		1:  0.285,
		2:  0.157,
		3:  0.094,
		4:  0.062,
		5:  0.050,
		6:  0.038,
		7:  0.030,
		8:  0.024,
		9:  0.020,
		10: 0.025,
	}

	pos := int(math.Round(position))
	if pos < 1 {
		pos = 1
	}
	if pos > 10 {
		return 0.015 // Below position 10
	}

	if ctr, ok := ctrBenchmarks[pos]; ok {
		return ctr
	}
	return 0.025
}

// averageImpressions calculates average impressions from daily metrics
func averageImpressions(data []DailyMetric) float64 {
	if len(data) == 0 {
		return 0
	}
	var sum int
	for _, d := range data {
		sum += d.Impressions
	}
	return float64(sum) / float64(len(data))
}

// calculateVolatility calculates coefficient of variation for impressions
func calculateVolatility(data []DailyMetric) float64 {
	if len(data) < 2 {
		return 0
	}

	mean := averageImpressions(data)
	if mean == 0 {
		return 0
	}

	var sumSquares float64
	for _, d := range data {
		diff := float64(d.Impressions) - mean
		sumSquares += diff * diff
	}

	stdDev := math.Sqrt(sumSquares / float64(len(data)))
	return stdDev / mean // Coefficient of variation
}

// RunAllAnalyzers runs all analyzers and returns combined issues (1:1 with Python)
func RunAllAnalyzers(data *GSCMetricsData) []EnhancedIssue {
	var allIssues []EnhancedIssue

	performanceAnalyzer := &PerformanceAnalyzer{}
	allIssues = append(allIssues, performanceAnalyzer.Analyze(data)...)

	anomalyAnalyzer := &AnomalyAnalyzer{}
	allIssues = append(allIssues, anomalyAnalyzer.Analyze(data)...)

	trendAnalyzer := &TrendAnalyzer{}
	allIssues = append(allIssues, trendAnalyzer.Analyze(data)...)

	opportunityAnalyzer := &OpportunityAnalyzer{}
	allIssues = append(allIssues, opportunityAnalyzer.Analyze(data)...)

	// Calculate priority scores
	for i := range allIssues {
		allIssues[i].PriorityScore = calculatePriorityScore(allIssues[i])
	}

	return allIssues
}

// calculatePriorityScore calculates issue priority (1:1 with Python)
func calculatePriorityScore(issue EnhancedIssue) float64 {
	severityWeights := map[IssueSeverity]float64{
		SeverityCritical: 4.0,
		SeverityHigh:     3.0,
		SeverityMedium:   2.0,
		SeverityLow:      1.0,
	}

	weight := severityWeights[issue.Severity]
	if weight == 0 {
		weight = 1.0
	}

	return weight * issue.ConfidenceScore * 25 // Scale to 0-100
}
