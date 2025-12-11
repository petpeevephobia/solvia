// Package core provides centralized SEO scoring for Solvia
// 1:1 parity with Python app/core/seo_scoring.py (388 lines)
package core

import (
	"math"
)

// SEOScoringEngine provides centralized SEO scoring ensuring consistency across the application.
//
// The scoring algorithm uses a weighted multi-factor approach:
// - Traffic Impact: 30% (business value)
// - Position Performance: 25% (visibility potential)
// - CTR Effectiveness: 25% (content relevance)
// - Growth Trends: 20% (momentum indicator)
//
// Score Range: 0-100
// Base Score: 25 (when no data available)
type SEOScoringEngine struct{}

// Industry standard CTR benchmarks by position (1:1 with Python)
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

// Component weights (must sum to 1.0) - 1:1 with Python
var Weights = map[string]float64{
	"traffic":  0.30,
	"position": 0.25,
	"ctr":      0.25,
	"trends":   0.20,
}

// HistoricalData represents previous period data for trend analysis
type HistoricalData struct {
	Clicks   int
	Position float64
	CTR      float64
}

// ScoreBreakdown contains detailed score components
type ScoreBreakdown struct {
	SEOScore      float64 `json:"seo_score"`
	TrafficScore  float64 `json:"traffic_score"`
	PositionScore float64 `json:"position_score"`
	CTRScore      float64 `json:"ctr_score"`
	TrendScore    float64 `json:"trend_score"`
}

// ScoreInterpretation provides human-readable interpretation of SEO score
type ScoreInterpretation struct {
	Rating         string `json:"rating"`
	Description    string `json:"description"`
	Recommendation string `json:"recommendation"`
}

// NewSEOScoringEngine creates a new scoring engine instance
func NewSEOScoringEngine() *SEOScoringEngine {
	return &SEOScoringEngine{}
}

// CalculateScore calculates SEO score using unified algorithm (1:1 with Python)
func (e *SEOScoringEngine) CalculateScore(clicks, impressions int, ctr, position float64, historical *HistoricalData) float64 {
	// Handle completely empty data case
	if impressions == 0 && clicks == 0 && position == 0 {
		return 25.0 // Base score for no data
	}

	// Calculate component scores
	trafficScore := e.calculateTrafficScore(clicks)
	positionScore := e.calculatePositionScore(position)
	ctrScore := e.calculateCTRScore(ctr, position)
	trendScore := e.calculateTrendScore(clicks, position, ctr, historical)

	// Calculate weighted final score
	finalScore := trafficScore*Weights["traffic"] +
		positionScore*Weights["position"] +
		ctrScore*Weights["ctr"] +
		trendScore*Weights["trends"]

	// Apply penalties for critical issues
	finalScore = e.applyPenalties(finalScore, clicks, impressions, ctr)

	// Ensure score is within valid range
	return math.Round(math.Max(0, math.Min(100, finalScore))*100) / 100
}

// CalculateScoreWithBreakdown calculates SEO score with component breakdown for detailed reporting (1:1 with Python)
func (e *SEOScoringEngine) CalculateScoreWithBreakdown(clicks, impressions int, ctr, position float64, historical *HistoricalData) ScoreBreakdown {
	// Handle completely empty data case
	if impressions == 0 && clicks == 0 && position == 0 {
		return ScoreBreakdown{
			SEOScore:      25.0,
			TrafficScore:  0.0,
			PositionScore: 0.0,
			CTRScore:      0.0,
			TrendScore:    0.0,
		}
	}

	// Calculate component scores
	trafficScore := e.calculateTrafficScore(clicks)
	positionScore := e.calculatePositionScore(position)
	ctrScore := e.calculateCTRScore(ctr, position)
	trendScore := e.calculateTrendScore(clicks, position, ctr, historical)

	// Calculate weighted final score
	finalScore := trafficScore*Weights["traffic"] +
		positionScore*Weights["position"] +
		ctrScore*Weights["ctr"] +
		trendScore*Weights["trends"]

	// Apply penalties for critical issues
	finalScore = e.applyPenalties(finalScore, clicks, impressions, ctr)

	// Ensure score is within valid range
	finalScore = math.Round(math.Max(0, math.Min(100, finalScore))*100) / 100

	return ScoreBreakdown{
		SEOScore:      finalScore,
		TrafficScore:  math.Round(trafficScore*10) / 10,
		PositionScore: math.Round(positionScore*10) / 10,
		CTRScore:      math.Round(ctrScore*10) / 10,
		TrendScore:    math.Round(trendScore*10) / 10,
	}
}

// calculateTrafficScore calculates traffic component score (0-100) - 1:1 with Python
func (e *SEOScoringEngine) calculateTrafficScore(clicks int) float64 {
	if clicks <= 0 {
		return 0
	}

	// Logarithmic scale to handle wide range of traffic volumes
	// 10 clicks = 20, 100 clicks = 40, 1000 clicks = 60, 10000 clicks = 80
	score := math.Log10(float64(clicks)+1) * 20
	return math.Min(100, score)
}

// calculatePositionScore calculates position component score (0-100) - 1:1 with Python
func (e *SEOScoringEngine) calculatePositionScore(position float64) float64 {
	if position <= 0 {
		return 0
	}

	// Position 1 = 100, Position 10 = 10, Position 20+ = 0
	if position <= 1 {
		return 100
	} else if position <= 10 {
		return math.Max(0, 110-(position*10))
	} else if position <= 20 {
		return math.Max(0, 20-position)
	}
	return 0
}

// calculateCTRScore calculates CTR component score relative to benchmarks (0-100) - 1:1 with Python
func (e *SEOScoringEngine) calculateCTRScore(ctr, position float64) float64 {
	if ctr <= 0 {
		return 0
	}

	// Get expected CTR for position
	expectedCTR := e.getExpectedCTR(position)

	if expectedCTR > 0 {
		// Score based on performance vs benchmark
		// 100% of benchmark = 50 score, 200% = 100 score
		relativePerformance := ctr / expectedCTR
		return math.Min(100, relativePerformance*50)
	}

	// No benchmark available, use absolute CTR
	// 5% CTR = 50 score, 10% CTR = 100 score
	return math.Min(100, ctr*1000)
}

// getExpectedCTR gets expected CTR for a given position - 1:1 with Python
func (e *SEOScoringEngine) getExpectedCTR(position float64) float64 {
	if position <= 0 {
		return 0
	}

	// Exact match - 1:1 with Python seo_scoring.py:230 and shared/scoring/seo_score.go:212
	// Must verify position is an exact integer before returning benchmark
	posInt := int(position)
	if val, exists := CTRBenchmarks[posInt]; exists && position == float64(posInt) {
		return val
	}

	// Interpolate between known values
	if position < 1 {
		return CTRBenchmarks[1]
	} else if position > 10 {
		// Exponential decay after position 10
		return CTRBenchmarks[10] * math.Pow(0.9, position-10)
	}

	// Linear interpolation between known points
	lower := int(position)
	upper := lower + 1

	lowerVal, lowerExists := CTRBenchmarks[lower]
	upperVal, upperExists := CTRBenchmarks[upper]

	if lowerExists && upperExists {
		weight := position - float64(lower)
		return lowerVal*(1-weight) + upperVal*weight
	} else if lowerExists {
		return lowerVal
	}

	// Estimate based on position 10
	return CTRBenchmarks[10]
}

// calculateTrendScore calculates trend component score (0-100) - 1:1 with Python
func (e *SEOScoringEngine) calculateTrendScore(clicks int, position, ctr float64, historical *HistoricalData) float64 {
	// Start with neutral score
	score := 50.0

	if historical == nil {
		return score
	}

	// Traffic trend (±25 points)
	if historical.Clicks > 0 {
		changePct := (float64(clicks-historical.Clicks) / float64(historical.Clicks)) * 100
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

	// Position trend (±25 points, inverse - lower is better)
	if historical.Position > 0 && position > 0 {
		positionChange := historical.Position - position // Positive = improvement
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

	return math.Max(0, math.Min(100, score))
}

// applyPenalties applies penalties for critical SEO issues - 1:1 with Python
func (e *SEOScoringEngine) applyPenalties(baseScore float64, clicks, impressions int, ctr float64) float64 {
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

// GetScoreInterpretation gets human-readable interpretation of SEO score - 1:1 with Python
func (e *SEOScoringEngine) GetScoreInterpretation(score float64) ScoreInterpretation {
	if score >= 80 {
		return ScoreInterpretation{
			Rating:         "Excellent",
			Description:    "Your SEO performance is outstanding",
			Recommendation: "Maintain current strategy and explore new opportunities",
		}
	} else if score >= 60 {
		return ScoreInterpretation{
			Rating:         "Good",
			Description:    "Your SEO is performing well with room for improvement",
			Recommendation: "Focus on optimizing underperforming pages",
		}
	} else if score >= 40 {
		return ScoreInterpretation{
			Rating:         "Fair",
			Description:    "Your SEO needs attention in several areas",
			Recommendation: "Review and fix critical issues first",
		}
	} else if score >= 20 {
		return ScoreInterpretation{
			Rating:         "Poor",
			Description:    "Your SEO has significant problems",
			Recommendation: "Urgent action needed on visibility and content",
		}
	}

	return ScoreInterpretation{
		Rating:         "Critical",
		Description:    "Your site has minimal or no search visibility",
		Recommendation: "Check indexing, robots.txt, and submit sitemap",
	}
}

// CalculateSEOScore is a convenience function for backward compatibility - 1:1 with Python
func CalculateSEOScore(clicks, impressions int, ctr, position float64, historical *HistoricalData) float64 {
	engine := NewSEOScoringEngine()
	return engine.CalculateScore(clicks, impressions, ctr, position, historical)
}
