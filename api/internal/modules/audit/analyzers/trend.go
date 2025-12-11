package analyzers

import (
	"fmt"
	"math"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
)

// TrendAnalyzer analyzes trend momentum and direction
// Implements trend detection logic (1:1 with Python audit_engine.py)
type TrendAnalyzer struct {
	// Threshold for significant trend (percentage change)
	significantTrendThreshold float64

	// Threshold for critical trend (percentage change)
	criticalTrendThreshold float64

	// Threshold for trend reversal (1:1 with Python)
	trendReversalThreshold float64

	// Number of consecutive days to confirm trend
	trendConfirmationDays int

	// Minimum data points required
	minDataPoints int
}

// NewTrendAnalyzer creates a new trend analyzer with default thresholds (1:1 with Python)
func NewTrendAnalyzer() *TrendAnalyzer {
	return &TrendAnalyzer{
		significantTrendThreshold: 15.0, // 15% change is significant (1:1 with Python trend_thresholds['significant_change'])
		criticalTrendThreshold:    30.0, // 30% change is critical (1:1 with Python trend_thresholds['critical_change'])
		trendReversalThreshold:    20.0, // 20% opposite direction is reversal (1:1 with Python trend_thresholds['trend_reversal'])
		trendConfirmationDays:     5,    // 5 days of consistent direction
		minDataPoints:             7,    // Need at least 1 week of data (1:1 with Python min_data_points)
	}
}

// TrendResult contains trend analysis results
type TrendResult struct {
	Issues            []domain.AuditIssue
	Trends            []Trend
	OverallMomentum   string  // "positive", "negative", "neutral"
	MomentumScore     float64 // -100 to +100
	HasSignificantTrend bool
}

// Trend represents a detected trend in data (1:1 with Python MetricTrend)
type Trend struct {
	Metric          string  `json:"metric"`           // "impressions", "clicks", "ctr", "position"
	Direction       string  `json:"direction"`        // "up", "down", "stable"
	Strength        string  `json:"strength"`         // "strong", "moderate", "weak"
	PercentChange   float64 `json:"percent_change"`   // Total change from start to end
	WeekOverWeek    float64 `json:"week_over_week"`   // Recent week vs previous week
	ConsistencyDays int     `json:"consistency_days"` // How many days trend has held
	IsAnomaly       bool    `json:"is_anomaly"`       // Whether this is an anomalous trend (1:1 with Python)
	ZScore          float64 `json:"z_score"`          // Z-score if calculated (1:1 with Python)
}

// Analyze performs comprehensive trend analysis
func (a *TrendAnalyzer) Analyze(dailyMetrics []google.DailyMetric, auditID int64) *TrendResult {
	result := &TrendResult{
		Issues:            []domain.AuditIssue{},
		Trends:            []Trend{},
		OverallMomentum:   "neutral",
		MomentumScore:     0,
		HasSignificantTrend: false,
	}

	// Need sufficient data for trend analysis
	if len(dailyMetrics) < a.minDataPoints {
		return result
	}

	// Analyze trends for each metric
	impressionsTrend := a.analyzeSingleTrend(extractImpressions(dailyMetrics), dailyMetrics, "impressions")
	clicksTrend := a.analyzeSingleTrend(extractClicks(dailyMetrics), dailyMetrics, "clicks")
	ctrTrend := a.analyzeSingleTrend(extractCTR(dailyMetrics), dailyMetrics, "ctr")
	positionTrend := a.analyzeSingleTrend(extractPosition(dailyMetrics), dailyMetrics, "position")

	result.Trends = []Trend{impressionsTrend, clicksTrend, ctrTrend, positionTrend}

	// Calculate overall momentum score
	result.MomentumScore = a.calculateMomentumScore(result.Trends)
	result.OverallMomentum = a.getMomentumLabel(result.MomentumScore)

	// Check for significant trends
	for _, trend := range result.Trends {
		if trend.Strength == "strong" || math.Abs(trend.PercentChange) > a.significantTrendThreshold {
			result.HasSignificantTrend = true
			break
		}
	}

	// Convert significant trends to issues
	result.Issues = a.convertTrendsToIssues(result.Trends, auditID)

	return result
}

// analyzeSingleTrend analyzes trend for a single metric
func (a *TrendAnalyzer) analyzeSingleTrend(values []float64, dailyMetrics []google.DailyMetric, metricName string) Trend {
	trend := Trend{
		Metric:    metricName,
		Direction: "stable",
		Strength:  "weak",
	}

	if len(values) < a.minDataPoints {
		return trend
	}

	// Calculate overall percent change (first day vs last day)
	firstValue := values[0]
	lastValue := values[len(values)-1]

	if firstValue > 0 {
		trend.PercentChange = ((lastValue - firstValue) / firstValue) * 100
	} else if lastValue > 0 {
		trend.PercentChange = 100.0
	}

	// Calculate week-over-week change
	if len(values) >= 14 {
		lastWeekSum := sum(values[len(values)-7:])
		prevWeekSum := sum(values[len(values)-14 : len(values)-7])

		if prevWeekSum > 0 {
			trend.WeekOverWeek = ((lastWeekSum - prevWeekSum) / prevWeekSum) * 100
		}
	}

	// Determine direction
	if trend.PercentChange > 5 {
		trend.Direction = "up"
	} else if trend.PercentChange < -5 {
		trend.Direction = "down"
	}

	// For position, lower is better - so reverse direction interpretation
	if metricName == "position" {
		if trend.PercentChange > 5 {
			trend.Direction = "down" // Position increased = rankings got worse
		} else if trend.PercentChange < -5 {
			trend.Direction = "up" // Position decreased = rankings improved
		}
	}

	// Calculate trend strength based on consistency
	trend.ConsistencyDays = a.calculateConsistency(values, trend.Direction)

	absChange := math.Abs(trend.PercentChange)
	if absChange > 50 || trend.ConsistencyDays >= 20 {
		trend.Strength = "strong"
	} else if absChange > a.significantTrendThreshold || trend.ConsistencyDays >= 10 {
		trend.Strength = "moderate"
	}

	return trend
}

// calculateConsistency counts consecutive days trending in the same direction
func (a *TrendAnalyzer) calculateConsistency(values []float64, direction string) int {
	if len(values) < 2 {
		return 0
	}

	consecutiveDays := 0
	for i := len(values) - 1; i > 0; i-- {
		diff := values[i] - values[i-1]

		if direction == "up" && diff > 0 {
			consecutiveDays++
		} else if direction == "down" && diff < 0 {
			consecutiveDays++
		} else {
			break
		}
	}

	return consecutiveDays
}

// calculateMomentumScore calculates overall momentum (-100 to +100)
func (a *TrendAnalyzer) calculateMomentumScore(trends []Trend) float64 {
	if len(trends) == 0 {
		return 0
	}

	// Weights for each metric (impressions and clicks most important)
	weights := map[string]float64{
		"impressions": 0.30,
		"clicks":      0.35,
		"ctr":         0.20,
		"position":    0.15,
	}

	score := 0.0
	for _, trend := range trends {
		weight := weights[trend.Metric]
		if weight == 0 {
			weight = 0.25
		}

		// For position, reverse the sign (negative change = improvement)
		change := trend.PercentChange
		if trend.Metric == "position" {
			change = -change
		}

		// Cap the impact at +/- 100%
		if change > 100 {
			change = 100
		} else if change < -100 {
			change = -100
		}

		score += change * weight
	}

	// Normalize to -100 to +100 range
	if score > 100 {
		score = 100
	} else if score < -100 {
		score = -100
	}

	return score
}

// getMomentumLabel returns human-readable momentum label
func (a *TrendAnalyzer) getMomentumLabel(score float64) string {
	switch {
	case score > 30:
		return "strong_positive"
	case score > 10:
		return "positive"
	case score < -30:
		return "strong_negative"
	case score < -10:
		return "negative"
	default:
		return "neutral"
	}
}

// convertTrendsToIssues converts significant trends to audit issues
func (a *TrendAnalyzer) convertTrendsToIssues(trends []Trend, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	for _, trend := range trends {
		// Only create issues for significant trends
		if trend.Strength == "weak" && math.Abs(trend.PercentChange) < a.significantTrendThreshold {
			continue
		}

		switch trend.Metric {
		case "impressions":
			if trend.Direction == "down" && trend.PercentChange < -20 {
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    getSeverity(trend.PercentChange, -50, -30),
					Category:    "trend",
					Title:       "Declining Search Visibility",
					Description: fmt.Sprintf("Impressions have declined %.1f%% over the period, with a week-over-week change of %.1f%%.", trend.PercentChange, trend.WeekOverWeek),
					Impact:      "Declining impressions indicate your site is being shown less in search results, reducing organic discovery opportunities.",
					Recommendation:  "Review recent content changes, check for algorithm updates, and analyze competitor activity. Consider refreshing top-performing content.",
				})
			} else if trend.Direction == "up" && trend.PercentChange > 30 {
				// Positive trend - still noteworthy but lower priority
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    "low",
					Category:    "trend",
					Title:       "Growing Search Visibility",
					Description: fmt.Sprintf("Impressions have grown %.1f%% over the period. Great momentum!", trend.PercentChange),
					Impact:      "Your content is reaching more potential visitors through organic search.",
					Recommendation:  "Identify which content is driving this growth and create more similar content. Consider optimizing CTR to convert more impressions to clicks.",
				})
			}

		case "clicks":
			if trend.Direction == "down" && trend.PercentChange < -20 {
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    getSeverity(trend.PercentChange, -50, -30),
					Category:    "trend",
					Title:       "Declining Organic Clicks",
					Description: fmt.Sprintf("Organic clicks have declined %.1f%% over the period.", trend.PercentChange),
					Impact:      "Fewer clicks means less organic traffic to your website, potentially impacting leads and conversions.",
					Recommendation:  "Check if the decline is due to ranking drops, CTR issues, or seasonal factors. Review top queries for changes.",
				})
			}

		case "position":
			if trend.Direction == "down" && trend.PercentChange > 20 {
				// Position increased = rankings got worse
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    getSeverity(trend.PercentChange, 50, 30),
					Category:    "trend",
					Title:       "Declining Search Rankings",
					Description: fmt.Sprintf("Average position has worsened by %.1f%% over the period.", trend.PercentChange),
					Impact:      "Worse rankings mean your pages appear lower in search results, reducing visibility and clicks.",
					Recommendation:  "Analyze which queries have dropped, review content quality, and check for new competitors entering your space.",
				})
			} else if trend.Direction == "up" && trend.PercentChange < -15 {
				// Position decreased = rankings improved
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    "low",
					Category:    "trend",
					Title:       "Improving Search Rankings",
					Description: fmt.Sprintf("Average position has improved by %.1f%% over the period. Nice progress!", math.Abs(trend.PercentChange)),
					Impact:      "Better rankings increase visibility and organic traffic potential.",
					Recommendation:  "Identify which pages improved and understand what's working. Apply similar strategies to other content.",
				})
			}
		}
	}

	return issues
}

// Helper functions

func sum(values []float64) float64 {
	total := 0.0
	for _, v := range values {
		total += v
	}
	return total
}

func getSeverity(value, highThreshold, medThreshold float64) string {
	absValue := math.Abs(value)
	if absValue >= math.Abs(highThreshold) {
		return "high"
	} else if absValue >= math.Abs(medThreshold) {
		return "medium"
	}
	return "low"
}

// detectTrendReversals detects sudden trend reversals (1:1 with Python _detect_trend_reversals)
// A trend reversal is when a metric that was trending in one direction suddenly reverses
func (a *TrendAnalyzer) detectTrendReversals(trends []Trend, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// This would detect sudden changes in trend direction
	// For example, traffic that was growing suddenly declining
	// Currently a stub like Python - returns empty as it requires more historical data

	for _, trend := range trends {
		// Check if the week-over-week change reversed direction significantly
		if trend.PercentChange != 0 && trend.WeekOverWeek != 0 {
			// If overall trend is positive but recent week is negative (or vice versa)
			if (trend.PercentChange > 0 && trend.WeekOverWeek < -a.trendReversalThreshold) ||
				(trend.PercentChange < 0 && trend.WeekOverWeek > a.trendReversalThreshold) {

				severity := "medium"
				if math.Abs(trend.WeekOverWeek) >= a.criticalTrendThreshold {
					severity = "high"
				}

				issues = append(issues, domain.AuditIssue{
					AuditID:  auditID,
					Severity: severity,
					Category: "trend",
					Title:    fmt.Sprintf("Trend Reversal Detected in %s", trend.Metric),
					Description: fmt.Sprintf(
						"The %s metric shows a trend reversal. Overall trend: %.1f%%, but recent week: %.1f%%.",
						trend.Metric, trend.PercentChange, trend.WeekOverWeek,
					),
					Impact:         "Trend reversals may indicate significant changes in search behavior or algorithm updates.",
					Recommendation: "Investigate recent changes and monitor closely over the next few days.",
				})
			}
		}
	}

	return issues
}

// detectSeasonalPatterns detects seasonal patterns and anomalies (1:1 with Python _detect_seasonal_patterns)
// This is a stub like Python - returns empty as it requires more historical data
func (a *TrendAnalyzer) detectSeasonalPatterns(dailyMetrics []google.DailyMetric, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// This would detect seasonal patterns
	// For now, return empty as it requires more historical data
	// TODO: Implement when year-over-year data is available

	return issues
}
