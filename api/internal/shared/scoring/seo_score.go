package scoring

import (
	"math"
)

// SEOScore represents the overall SEO score breakdown
type SEOScore struct {
	Total     float64            `json:"total"`
	Grade     string             `json:"grade"`
	Breakdown map[string]float64 `json:"breakdown"`
}

// GSCMetrics represents Google Search Console metrics for scoring
type GSCMetrics struct {
	Impressions       int     `json:"impressions"`
	Clicks            int     `json:"clicks"`
	CTR               float64 `json:"ctr"`
	Position          float64 `json:"position"`
	ImpressionsChange float64 `json:"impressions_change,omitempty"`
	ClicksChange      float64 `json:"clicks_change,omitempty"`
	CTRChange         float64 `json:"ctr_change,omitempty"`
	PositionChange    float64 `json:"position_change,omitempty"`
}

// HistoricalData represents previous period data for trend analysis
type HistoricalData struct {
	Clicks   int     `json:"clicks"`
	Position float64 `json:"position"`
	CTR      float64 `json:"ctr"`
}

// Score weights for SEO calculation (matching Python exactly)
// Formula: Traffic(30%) + Position(25%) + CTR(25%) + Trends(20%)
const (
	WeightTraffic  = 0.30
	WeightPosition = 0.25
	WeightCTR      = 0.25
	WeightTrends   = 0.20
	BaseScore      = 25.0 // Minimum score when no data
)

// Industry standard CTR benchmarks by position (matching Python exactly)
var ctrBenchmarks = map[int]float64{
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

// CalculateGSCScore calculates SEO score from GSC metrics
// This is the canonical scoring algorithm matching Python exactly
func CalculateGSCScore(metrics *GSCMetrics) *SEOScore {
	if metrics == nil {
		return &SEOScore{
			Total: BaseScore,
			Grade: GetGrade(BaseScore),
			Breakdown: map[string]float64{
				"traffic":  0,
				"position": 0,
				"ctr":      0,
				"trends":   0,
				"base":     BaseScore,
			},
		}
	}

	return CalculateGSCScoreWithHistory(metrics, nil)
}

// CalculateGSCScoreWithHistory calculates SEO score with historical data for trends
func CalculateGSCScoreWithHistory(metrics *GSCMetrics, historical *HistoricalData) *SEOScore {
	if metrics == nil {
		return &SEOScore{
			Total: BaseScore,
			Grade: GetGrade(BaseScore),
			Breakdown: map[string]float64{
				"traffic":  0,
				"position": 0,
				"ctr":      0,
				"trends":   0,
				"base":     BaseScore,
			},
		}
	}

	// Handle completely empty data case
	if metrics.Impressions == 0 && metrics.Clicks == 0 && metrics.Position == 0 {
		return &SEOScore{
			Total: BaseScore,
			Grade: GetGrade(BaseScore),
			Breakdown: map[string]float64{
				"traffic":  0,
				"position": 0,
				"ctr":      0,
				"trends":   0,
				"base":     BaseScore,
			},
		}
	}

	// Calculate component scores (0-100 each)
	trafficScore := calculateTrafficScore(metrics.Clicks)
	positionScore := calculatePositionScore(metrics.Position)
	ctrScore := calculateCTRScore(metrics.CTR, metrics.Position)
	trendsScore := calculateTrendsScore(metrics, historical)

	// Calculate weighted final score
	finalScore := trafficScore*WeightTraffic +
		positionScore*WeightPosition +
		ctrScore*WeightCTR +
		trendsScore*WeightTrends

	// Apply penalties for critical issues
	finalScore = applyPenalties(finalScore, metrics.Clicks, metrics.Impressions, metrics.CTR)

	// Ensure score is within valid range
	if finalScore < 0 {
		finalScore = 0
	}
	if finalScore > 100 {
		finalScore = 100
	}

	// Round to 2 decimal places
	finalScore = math.Round(finalScore*100) / 100

	return &SEOScore{
		Total: finalScore,
		Grade: GetGrade(finalScore),
		Breakdown: map[string]float64{
			"traffic":  math.Round(trafficScore*10) / 10,
			"position": math.Round(positionScore*10) / 10,
			"ctr":      math.Round(ctrScore*10) / 10,
			"trends":   math.Round(trendsScore*10) / 10,
		},
	}
}

// calculateTrafficScore calculates traffic component score (0-100)
// Uses logarithmic scale matching Python: log10(clicks + 1) * 20
func calculateTrafficScore(clicks int) float64 {
	if clicks <= 0 {
		return 0
	}

	// Logarithmic scale to handle wide range of traffic volumes
	// 10 clicks = 20, 100 clicks = 40, 1000 clicks = 60, 10000 clicks = 80
	score := math.Log10(float64(clicks)+1) * 20
	if score > 100 {
		score = 100
	}
	return score
}

// calculatePositionScore calculates position component score (0-100)
// Matching Python exactly: Position 1 = 100, Position 10 = 10, Position 20+ = 0
func calculatePositionScore(position float64) float64 {
	if position <= 0 {
		return 0
	}

	if position <= 1 {
		return 100
	} else if position <= 10 {
		// Position 1 = 100, Position 10 = 10
		return math.Max(0, 110-(position*10))
	} else if position <= 20 {
		// Position 11-20: gradual decrease
		return math.Max(0, 20-position)
	}
	return 0
}

// calculateCTRScore calculates CTR component score relative to benchmarks (0-100)
// Matching Python exactly: compares actual CTR to expected CTR for position
func calculateCTRScore(ctr float64, position float64) float64 {
	if ctr <= 0 {
		return 0
	}

	// Get expected CTR for position
	expectedCTR := getExpectedCTR(position)

	if expectedCTR > 0 {
		// Score based on performance vs benchmark
		// 100% of benchmark = 50 score, 200% = 100 score
		relativePerformance := ctr / expectedCTR
		score := math.Min(100, relativePerformance*50)
		return score
	}

	// No benchmark available, use absolute CTR
	// 5% CTR = 50 score, 10% CTR = 100 score
	return math.Min(100, ctr*1000)
}

// getExpectedCTR returns expected CTR for a given position (matching Python)
func getExpectedCTR(position float64) float64 {
	if position <= 0 {
		return 0
	}

	// Exact match
	posInt := int(position)
	if benchmark, ok := ctrBenchmarks[posInt]; ok && position == float64(posInt) {
		return benchmark
	}

	if position < 1 {
		return ctrBenchmarks[1]
	} else if position > 10 {
		// Exponential decay after position 10
		return ctrBenchmarks[10] * math.Pow(0.9, position-10)
	}

	// Linear interpolation between known points
	lower := int(position)
	upper := lower + 1

	lowerBench, lowerOk := ctrBenchmarks[lower]
	upperBench, upperOk := ctrBenchmarks[upper]

	if lowerOk && upperOk {
		weight := position - float64(lower)
		return lowerBench*(1-weight) + upperBench*weight
	} else if lowerOk {
		return lowerBench
	}

	// Fallback to position 10 benchmark
	return ctrBenchmarks[10]
}

// calculateTrendsScore calculates trend component score (0-100)
// Matching Python: starts at 50 (neutral), adds/subtracts based on trends
func calculateTrendsScore(metrics *GSCMetrics, historical *HistoricalData) float64 {
	// Start with neutral score
	score := 50.0

	// If we have change data from metrics directly
	if metrics.ClicksChange != 0 || metrics.PositionChange != 0 {
		// Traffic trend (±25 points)
		if metrics.ClicksChange > 20 {
			score += 25
		} else if metrics.ClicksChange > 0 {
			score += 12
		} else if metrics.ClicksChange < -20 {
			score -= 25
		} else if metrics.ClicksChange < 0 {
			score -= 12
		}

		// Position trend (±25 points, inverse - lower is better)
		// PositionChange < 0 means position improved (went from 20 to 15)
		if metrics.PositionChange < -2 {
			score += 25
		} else if metrics.PositionChange < 0 {
			score += 12
		} else if metrics.PositionChange > 2 {
			score -= 25
		} else if metrics.PositionChange > 0 {
			score -= 12
		}
	} else if historical != nil {
		// Use historical data if provided
		// Traffic trend
		if historical.Clicks > 0 {
			changePct := (float64(metrics.Clicks-historical.Clicks) / float64(historical.Clicks)) * 100
			if changePct > 20 {
				score += 25
			} else if changePct > 0 {
				score += 12
			} else if changePct < -20 {
				score -= 25
			} else if changePct < 0 {
				score -= 12
			}
		}

		// Position trend (inverse - lower is better)
		if historical.Position > 0 && metrics.Position > 0 {
			positionChange := historical.Position - metrics.Position // Positive = improvement
			if positionChange > 2 {
				score += 25
			} else if positionChange > 0 {
				score += 12
			} else if positionChange < -2 {
				score -= 25
			} else if positionChange < 0 {
				score -= 12
			}
		}
	}

	// Clamp to 0-100
	if score < 0 {
		score = 0
	}
	if score > 100 {
		score = 100
	}

	return score
}

// applyPenalties applies penalties for critical SEO issues (matching Python)
func applyPenalties(baseScore float64, clicks int, impressions int, ctr float64) float64 {
	score := baseScore

	// No visibility penalty
	if impressions == 0 {
		score *= 0.3 // 70% penalty
	} else if clicks == 0 && impressions > 100 {
		// Zero CTR with impressions penalty
		score *= 0.5 // 50% penalty
	} else if impressions > 1000 && ctr < 0.001 {
		// Very low CTR penalty
		score *= 0.7 // 30% penalty
	}

	return score
}

// GetGrade returns a grade based on score (1:1 with Python)
// Python thresholds: Excellent >= 80, Good >= 60, Fair >= 40, Poor >= 20, Critical < 20
func GetGrade(score float64) string {
	switch {
	case score >= 80:
		return "Excellent"
	case score >= 60:
		return "Good"
	case score >= 40:
		return "Fair"
	case score >= 20:
		return "Poor"
	default:
		return "Critical"
	}
}

// SEOStage represents visibility stages based on impressions
type SEOStage string

const (
	StageHidden       SEOStage = "hidden"       // < 50 impressions
	StageEmerging     SEOStage = "emerging"     // 50-299 impressions
	StageDiscoverable SEOStage = "discoverable" // 300-1999 impressions
	StageTrusted      SEOStage = "trusted"      // 2000+ impressions
)

// GetSEOStage determines visibility stage based on impressions
func GetSEOStage(impressions int) SEOStage {
	switch {
	case impressions >= 2000:
		return StageTrusted
	case impressions >= 300:
		return StageDiscoverable
	case impressions >= 50:
		return StageEmerging
	default:
		return StageHidden
	}
}

// GetStageDescription returns a description for the SEO stage
func GetStageDescription(stage SEOStage) string {
	switch stage {
	case StageTrusted:
		return "Your website has established trust with search engines and receives significant organic traffic."
	case StageDiscoverable:
		return "Your website is being discovered by search engines and gaining visibility."
	case StageEmerging:
		return "Your website is starting to appear in search results. Focus on content quality."
	default:
		return "Your website has limited visibility. Priority: improve content and technical SEO."
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

// OnPageScore represents on-page SEO score
type OnPageScore struct {
	Total      float64                  `json:"total"`
	Grade      string                   `json:"grade"`
	Categories map[string]CategoryScore `json:"categories"`
}

// CategoryScore represents score for a specific category
type CategoryScore struct {
	Score    float64 `json:"score"`
	MaxScore float64 `json:"max_score"`
	Issues   int     `json:"issues"`
}

// CalculateOnPageScore calculates on-page SEO score
func CalculateOnPageScore(issues map[string][]string) *OnPageScore {
	categories := map[string]CategoryScore{
		"title":     {MaxScore: 20},
		"meta":      {MaxScore: 15},
		"content":   {MaxScore: 25},
		"images":    {MaxScore: 15},
		"links":     {MaxScore: 10},
		"technical": {MaxScore: 15},
	}

	// Start with full scores and deduct for issues
	for cat := range categories {
		categories[cat] = CategoryScore{
			Score:    categories[cat].MaxScore,
			MaxScore: categories[cat].MaxScore,
			Issues:   0,
		}
	}

	// Deduct for issues
	for cat, issueList := range issues {
		if _, exists := categories[cat]; exists {
			deduction := float64(len(issueList)) * 5 // 5 points per issue
			newScore := categories[cat].Score - deduction
			if newScore < 0 {
				newScore = 0
			}
			categories[cat] = CategoryScore{
				Score:    newScore,
				MaxScore: categories[cat].MaxScore,
				Issues:   len(issueList),
			}
		}
	}

	// Calculate total
	var total float64
	for _, cs := range categories {
		total += cs.Score
	}

	return &OnPageScore{
		Total:      total,
		Grade:      GetGrade(total),
		Categories: categories,
	}
}

// GetScoreInterpretation returns human-readable interpretation of SEO score
func GetScoreInterpretation(score float64) map[string]string {
	if score >= 80 {
		return map[string]string{
			"rating":         "Excellent",
			"description":    "Your SEO performance is outstanding",
			"recommendation": "Maintain current strategy and explore new opportunities",
		}
	} else if score >= 60 {
		return map[string]string{
			"rating":         "Good",
			"description":    "Your SEO is performing well with room for improvement",
			"recommendation": "Focus on optimizing underperforming pages",
		}
	} else if score >= 40 {
		return map[string]string{
			"rating":         "Fair",
			"description":    "Your SEO needs attention in several areas",
			"recommendation": "Review and fix critical issues first",
		}
	} else if score >= 20 {
		return map[string]string{
			"rating":         "Poor",
			"description":    "Your SEO has significant problems",
			"recommendation": "Urgent action needed on visibility and content",
		}
	}
	return map[string]string{
		"rating":         "Critical",
		"description":    "Your site has minimal or no search visibility",
		"recommendation": "Check indexing, robots.txt, and submit sitemap",
	}
}
