package core

import (
	"math"
	"testing"
)

// TestBaseScoreForNoData verifies base score of 25 when no data available
func TestBaseScoreForNoData(t *testing.T) {
	engine := NewSEOScoringEngine()
	score := engine.CalculateScore(0, 0, 0, 0, nil)

	if score != 25.0 {
		t.Errorf("Expected base score 25.0, got %v", score)
	}
}

// TestCalculateTrafficScore verifies traffic score calculation (1:1 with Python)
func TestCalculateTrafficScore(t *testing.T) {
	engine := NewSEOScoringEngine()

	tests := []struct {
		clicks   int
		expected float64
	}{
		{0, 0},
		{10, 20.82},  // log10(11) * 20 ≈ 20.82
		{100, 40.04}, // log10(101) * 20 ≈ 40.04
		{1000, 60.03}, // log10(1001) * 20 ≈ 60.03
	}

	for _, tt := range tests {
		result := engine.calculateTrafficScore(tt.clicks)
		// Allow small floating point tolerance
		if math.Abs(result-tt.expected) > 0.1 {
			t.Errorf("Traffic score for %d clicks: expected ~%v, got %v", tt.clicks, tt.expected, result)
		}
	}
}

// TestCalculatePositionScore verifies position score calculation (1:1 with Python)
func TestCalculatePositionScore(t *testing.T) {
	engine := NewSEOScoringEngine()

	tests := []struct {
		position float64
		expected float64
	}{
		{0, 0},
		{1, 100},
		{5, 60},
		{10, 10},
		{15, 5},
		{20, 0},
		{25, 0},
	}

	for _, tt := range tests {
		result := engine.calculatePositionScore(tt.position)
		if result != tt.expected {
			t.Errorf("Position score for position %v: expected %v, got %v", tt.position, tt.expected, result)
		}
	}
}

// TestCTRBenchmarks verifies CTR benchmarks match Python values
func TestCTRBenchmarks(t *testing.T) {
	expected := map[int]float64{
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

	for pos, expectedCTR := range expected {
		if CTRBenchmarks[pos] != expectedCTR {
			t.Errorf("CTR benchmark for position %d: expected %v, got %v", pos, expectedCTR, CTRBenchmarks[pos])
		}
	}
}

// TestWeights verifies weights match Python values
func TestWeights(t *testing.T) {
	expected := map[string]float64{
		"traffic":  0.30,
		"position": 0.25,
		"ctr":      0.25,
		"trends":   0.20,
	}

	for key, expectedWeight := range expected {
		if Weights[key] != expectedWeight {
			t.Errorf("Weight for %s: expected %v, got %v", key, expectedWeight, Weights[key])
		}
	}

	// Verify weights sum to 1.0
	sum := 0.0
	for _, w := range Weights {
		sum += w
	}
	if sum != 1.0 {
		t.Errorf("Weights should sum to 1.0, got %v", sum)
	}
}

// TestScoreInterpretation verifies score interpretation thresholds (1:1 with Python)
func TestScoreInterpretation(t *testing.T) {
	engine := NewSEOScoringEngine()

	tests := []struct {
		score          float64
		expectedRating string
	}{
		{85, "Excellent"},
		{65, "Good"},
		{45, "Fair"},
		{25, "Poor"},
		{10, "Critical"},
	}

	for _, tt := range tests {
		result := engine.GetScoreInterpretation(tt.score)
		if result.Rating != tt.expectedRating {
			t.Errorf("Interpretation for score %v: expected %s, got %s", tt.score, tt.expectedRating, result.Rating)
		}
	}
}

// TestPenalties verifies penalty application (1:1 with Python)
func TestPenalties(t *testing.T) {
	engine := NewSEOScoringEngine()

	// No visibility penalty (70% penalty)
	result := engine.applyPenalties(100, 0, 0, 0)
	if result != 30 {
		t.Errorf("No visibility penalty: expected 30, got %v", result)
	}

	// Zero CTR with impressions penalty (50% penalty)
	result = engine.applyPenalties(100, 0, 200, 0)
	if result != 50 {
		t.Errorf("Zero CTR penalty: expected 50, got %v", result)
	}

	// Very low CTR penalty (30% penalty)
	result = engine.applyPenalties(100, 1, 2000, 0.0005)
	if result != 70 {
		t.Errorf("Very low CTR penalty: expected 70, got %v", result)
	}
}

// TestTrendScoring verifies trend calculation (1:1 with Python)
func TestTrendScoring(t *testing.T) {
	engine := NewSEOScoringEngine()

	// No historical data = neutral 50
	result := engine.calculateTrendScore(100, 5, 0.03, nil)
	if result != 50 {
		t.Errorf("Neutral trend: expected 50, got %v", result)
	}

	// Traffic increase > 20% = +25
	historical := &HistoricalData{Clicks: 80}
	result = engine.calculateTrendScore(100, 5, 0.03, historical)
	if result != 75 {
		t.Errorf("Traffic increase trend: expected 75, got %v", result)
	}

	// Traffic decrease > 20% = -25
	historical = &HistoricalData{Clicks: 150}
	result = engine.calculateTrendScore(100, 5, 0.03, historical)
	if result != 25 {
		t.Errorf("Traffic decrease trend: expected 25, got %v", result)
	}
}

// TestCalculateScoreWithBreakdown verifies breakdown structure
func TestCalculateScoreWithBreakdown(t *testing.T) {
	engine := NewSEOScoringEngine()

	breakdown := engine.CalculateScoreWithBreakdown(100, 1000, 0.1, 5, nil)

	if breakdown.SEOScore <= 0 || breakdown.SEOScore > 100 {
		t.Errorf("SEO score out of range: %v", breakdown.SEOScore)
	}

	// Verify all components are present
	if breakdown.TrafficScore == 0 && breakdown.PositionScore == 0 && breakdown.CTRScore == 0 {
		t.Error("All component scores are zero, expected some values")
	}
}

// TestConvenienceFunction verifies backward compatibility function
func TestConvenienceFunction(t *testing.T) {
	score := CalculateSEOScore(100, 1000, 0.1, 5, nil)

	if score <= 0 || score > 100 {
		t.Errorf("Convenience function score out of range: %v", score)
	}
}
