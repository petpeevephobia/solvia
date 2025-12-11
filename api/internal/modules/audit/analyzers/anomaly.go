package analyzers

import (
	"fmt"
	"math"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/google"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
)

// ChangeThreshold defines percentage thresholds for different severity levels (1:1 with Python)
type ChangeThreshold struct {
	Critical float64
	High     float64
	Medium   float64
}

// AnomalyDetector detects statistical anomalies in GSC data
// Implements Z-score based anomaly detection (1:1 with Python audit_engine.py)
type AnomalyDetector struct {
	// Z-score thresholds for anomaly detection
	zScoreThresholdHigh   float64 // Above this = severe anomaly (3.0 = 99.7% confidence)
	zScoreThresholdMedium float64 // Above this = moderate anomaly (2.0 = 95% confidence)

	// Percentage change thresholds (1:1 with Python change_thresholds)
	trafficThresholds    ChangeThreshold
	positionThresholds   ChangeThreshold
	ctrThresholds        ChangeThreshold
	impressionThresholds ChangeThreshold

	// Minimum data points required for reliable statistics
	minDataPoints int

	// Minimum impressions to consider meaningful
	minImpressions int
}

// NewAnomalyDetector creates a new anomaly detector with default thresholds (1:1 with Python)
func NewAnomalyDetector() *AnomalyDetector {
	return &AnomalyDetector{
		// Z-score thresholds (1:1 with Python z_score_thresholds)
		zScoreThresholdHigh:   3.0, // 3.0 standard deviations = critical (99.7% confidence)
		zScoreThresholdMedium: 2.0, // 2.0 standard deviations = warning (95% confidence)

		// Percentage change thresholds (1:1 with Python change_thresholds)
		trafficThresholds: ChangeThreshold{
			Critical: -50, // >50% traffic loss
			High:     -20, // 20-50% traffic loss
			Medium:   -10, // 10-20% traffic loss
		},
		positionThresholds: ChangeThreshold{
			Critical: 5, // Dropped 5+ positions
			High:     3, // Dropped 3-5 positions
			Medium:   2, // Dropped 2-3 positions
		},
		ctrThresholds: ChangeThreshold{
			Critical: -50, // >50% CTR drop
			High:     -30, // 30-50% CTR drop
			Medium:   -15, // 15-30% CTR drop
		},
		impressionThresholds: ChangeThreshold{
			Critical: -60, // >60% impression loss
			High:     -30, // 30-60% impression loss
			Medium:   -15, // 15-30% impression loss
		},

		minDataPoints:  7,  // Need at least a week of data
		minImpressions: 50, // Minimum impressions to analyze
	}
}

// AnomalyResult contains detected anomalies
type AnomalyResult struct {
	Issues        []domain.AuditIssue
	Anomalies     []Anomaly
	HasAnomalies  bool
}

// Anomaly represents a detected statistical anomaly
type Anomaly struct {
	Type        string  `json:"type"`        // "drop", "spike", "volatility"
	Metric      string  `json:"metric"`      // "impressions", "clicks", "ctr", "position"
	Date        string  `json:"date"`
	Value       float64 `json:"value"`
	ExpectedMin float64 `json:"expected_min"`
	ExpectedMax float64 `json:"expected_max"`
	ZScore      float64 `json:"z_score"`
	Severity    string  `json:"severity"`    // "high", "medium", "low"
}

// Analyze performs anomaly detection on time series data
func (d *AnomalyDetector) Analyze(dailyMetrics []google.DailyMetric, auditID int64) *AnomalyResult {
	result := &AnomalyResult{
		Issues:       []domain.AuditIssue{},
		Anomalies:    []Anomaly{},
		HasAnomalies: false,
	}

	// Need sufficient data for statistical analysis
	if len(dailyMetrics) < d.minDataPoints {
		return result
	}

	// Detect anomalies in each metric using Z-score (statistical method)
	impressionAnomalies := d.detectAnomaliesInSeries(extractImpressions(dailyMetrics), dailyMetrics, "impressions")
	clickAnomalies := d.detectAnomaliesInSeries(extractClicks(dailyMetrics), dailyMetrics, "clicks")
	ctrAnomalies := d.detectAnomaliesInSeries(extractCTR(dailyMetrics), dailyMetrics, "ctr")
	positionAnomalies := d.detectAnomaliesInSeries(extractPosition(dailyMetrics), dailyMetrics, "position")

	// Combine all anomalies
	result.Anomalies = append(result.Anomalies, impressionAnomalies...)
	result.Anomalies = append(result.Anomalies, clickAnomalies...)
	result.Anomalies = append(result.Anomalies, ctrAnomalies...)
	result.Anomalies = append(result.Anomalies, positionAnomalies...)

	result.HasAnomalies = len(result.Anomalies) > 0

	// Convert significant anomalies to issues
	result.Issues = d.convertAnomaliestoIssues(result.Anomalies, auditID)

	return result
}

// AnalyzeWithComparison performs percentage-based anomaly detection comparing current vs previous period
// This is 1:1 with Python's detect_anomalies() method
func (d *AnomalyDetector) AnalyzeWithComparison(
	currentClicks, previousClicks int,
	currentImpressions, previousImpressions int,
	currentCTR, previousCTR float64,
	currentPosition, previousPosition float64,
	auditID int64,
) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// 1. Traffic Drop Detection (1:1 with Python _detect_traffic_anomaly)
	if issue := d.detectTrafficPercentageAnomaly(currentClicks, previousClicks, auditID); issue != nil {
		issues = append(issues, *issue)
	}

	// 2. Position Loss Detection (1:1 with Python _detect_position_anomaly)
	if issue := d.detectPositionPercentageAnomaly(currentPosition, previousPosition, auditID); issue != nil {
		issues = append(issues, *issue)
	}

	// 3. CTR Decline Detection (1:1 with Python _detect_ctr_anomaly)
	if issue := d.detectCTRPercentageAnomaly(currentCTR, previousCTR, currentImpressions, previousImpressions, auditID); issue != nil {
		issues = append(issues, *issue)
	}

	// 4. Impression Drop Detection (1:1 with Python _detect_impression_anomaly)
	if issue := d.detectImpressionPercentageAnomaly(currentImpressions, previousImpressions, auditID); issue != nil {
		issues = append(issues, *issue)
	}

	return issues
}

// detectTrafficPercentageAnomaly detects significant traffic drops (1:1 with Python _detect_traffic_anomaly)
func (d *AnomalyDetector) detectTrafficPercentageAnomaly(currentClicks, previousClicks int, auditID int64) *domain.AuditIssue {
	if previousClicks == 0 {
		return nil
	}

	changePct := float64(currentClicks-previousClicks) / float64(previousClicks) * 100

	var severity string
	if changePct <= d.trafficThresholds.Critical {
		severity = "critical"
	} else if changePct <= d.trafficThresholds.High {
		severity = "high"
	} else if changePct <= d.trafficThresholds.Medium {
		severity = "medium"
	} else {
		return nil
	}

	return &domain.AuditIssue{
		AuditID:  auditID,
		Severity: severity,
		Category: "anomaly",
		Title:    "Significant Traffic Drop Detected",
		Description: fmt.Sprintf(
			"Organic traffic has dropped by %.1f%% compared to the previous period. Current: %d clicks, Previous: %d clicks.",
			math.Abs(changePct), currentClicks, previousClicks,
		),
		Impact:         "Fewer clicks means less organic traffic to your website, potentially impacting leads and conversions.",
		Recommendation: "Investigate recent changes to your site, check for algorithm updates, and review your top-performing pages for issues.",
	}
}

// detectPositionPercentageAnomaly detects significant position losses (1:1 with Python _detect_position_anomaly)
func (d *AnomalyDetector) detectPositionPercentageAnomaly(currentPosition, previousPosition float64, auditID int64) *domain.AuditIssue {
	if previousPosition == 0 || currentPosition == 0 {
		return nil
	}

	// Position change (positive means dropped in rankings - higher position number is worse)
	positionChange := currentPosition - previousPosition

	var severity string
	if positionChange >= d.positionThresholds.Critical {
		severity = "critical"
	} else if positionChange >= d.positionThresholds.High {
		severity = "high"
	} else if positionChange >= d.positionThresholds.Medium {
		severity = "medium"
	} else {
		return nil
	}

	return &domain.AuditIssue{
		AuditID:  auditID,
		Severity: severity,
		Category: "anomaly",
		Title:    "Average Position Declined",
		Description: fmt.Sprintf(
			"Your average search position has dropped from %.1f to %.1f (declined by %.1f positions).",
			previousPosition, currentPosition, positionChange,
		),
		Impact:         "Worse rankings mean your pages appear lower in search results, reducing visibility and clicks.",
		Recommendation: "Review your content quality, check for new competitors, and ensure your pages are optimized for target keywords.",
	}
}

// detectCTRPercentageAnomaly detects CTR problems (1:1 with Python _detect_ctr_anomaly)
func (d *AnomalyDetector) detectCTRPercentageAnomaly(currentCTR, previousCTR float64, currentImpressions, previousImpressions int, auditID int64) *domain.AuditIssue {
	if previousCTR == 0 {
		return nil
	}

	ctrChangePct := (currentCTR - previousCTR) / previousCTR * 100

	// Special case: CTR declined but impressions are stable/growing
	impressionsStable := float64(currentImpressions) >= float64(previousImpressions)*0.9

	var severity string
	if ctrChangePct <= d.ctrThresholds.Critical {
		if impressionsStable {
			severity = "critical"
		} else {
			severity = "high"
		}
	} else if ctrChangePct <= d.ctrThresholds.High {
		if impressionsStable {
			severity = "high"
		} else {
			severity = "medium"
		}
	} else if ctrChangePct <= d.ctrThresholds.Medium && impressionsStable {
		severity = "medium"
	} else {
		return nil
	}

	title := "Click-Through Rate Declined"
	description := fmt.Sprintf(
		"CTR has dropped from %.2f%% to %.2f%% (%.1f%% decline).",
		previousCTR*100, currentCTR*100, math.Abs(ctrChangePct),
	)
	if impressionsStable {
		title = "Click-Through Rate Declined Despite Stable Impressions"
		description += " Your pages are showing in search but not attracting clicks."
	}

	return &domain.AuditIssue{
		AuditID:        auditID,
		Severity:       severity,
		Category:       "anomaly",
		Title:          title,
		Description:    description,
		Impact:         "Lower CTR means fewer visitors despite search visibility.",
		Recommendation: "Review and improve your title tags and meta descriptions. Ensure they are compelling and match search intent.",
	}
}

// detectImpressionPercentageAnomaly detects significant impression drops (1:1 with Python _detect_impression_anomaly)
func (d *AnomalyDetector) detectImpressionPercentageAnomaly(currentImpressions, previousImpressions int, auditID int64) *domain.AuditIssue {
	if previousImpressions == 0 {
		return nil
	}

	changePct := float64(currentImpressions-previousImpressions) / float64(previousImpressions) * 100

	var severity string
	if changePct <= d.impressionThresholds.Critical {
		severity = "critical"
	} else if changePct <= d.impressionThresholds.High {
		severity = "high"
	} else if changePct <= d.impressionThresholds.Medium {
		severity = "medium"
	} else {
		return nil
	}

	return &domain.AuditIssue{
		AuditID:  auditID,
		Severity: severity,
		Category: "anomaly",
		Title:    "Search Visibility Declined",
		Description: fmt.Sprintf(
			"Search impressions have dropped by %.1f%%. Current: %d impressions, Previous: %d impressions.",
			math.Abs(changePct), currentImpressions, previousImpressions,
		),
		Impact:         "Declining impressions indicate your site is being shown less in search results.",
		Recommendation: "Check for indexing issues, review your sitemap, and ensure important pages are not blocked by robots.txt.",
	}
}

// detectAnomaliesInSeries detects anomalies in a single metric series
func (d *AnomalyDetector) detectAnomaliesInSeries(values []float64, dailyMetrics []google.DailyMetric, metricName string) []Anomaly {
	var anomalies []Anomaly

	if len(values) < d.minDataPoints {
		return anomalies
	}

	// Calculate mean and standard deviation
	mean := calculateMean(values)
	stdDev := calculateStdDev(values, mean)

	// Skip if no variation (all same values)
	if stdDev == 0 {
		return anomalies
	}

	// Check each value for anomalies
	for i, value := range values {
		zScore := (value - mean) / stdDev

		// Detect drops (significant negative z-score)
		if zScore < -d.zScoreThresholdHigh {
			anomalies = append(anomalies, Anomaly{
				Type:        "drop",
				Metric:      metricName,
				Date:        dailyMetrics[i].Date,
				Value:       value,
				ExpectedMin: mean - (2 * stdDev),
				ExpectedMax: mean + (2 * stdDev),
				ZScore:      zScore,
				Severity:    "high",
			})
		} else if zScore < -d.zScoreThresholdMedium {
			anomalies = append(anomalies, Anomaly{
				Type:        "drop",
				Metric:      metricName,
				Date:        dailyMetrics[i].Date,
				Value:       value,
				ExpectedMin: mean - (2 * stdDev),
				ExpectedMax: mean + (2 * stdDev),
				ZScore:      zScore,
				Severity:    "medium",
			})
		}

		// Detect spikes (significant positive z-score)
		// Note: For position, a spike (higher value) is actually bad
		if zScore > d.zScoreThresholdHigh {
			anomalyType := "spike"
			severity := "medium" // Spikes are often less critical than drops

			// For position, a spike means worse rankings - this is bad
			if metricName == "position" {
				severity = "high"
			}

			anomalies = append(anomalies, Anomaly{
				Type:        anomalyType,
				Metric:      metricName,
				Date:        dailyMetrics[i].Date,
				Value:       value,
				ExpectedMin: mean - (2 * stdDev),
				ExpectedMax: mean + (2 * stdDev),
				ZScore:      zScore,
				Severity:    severity,
			})
		}
	}

	// Detect volatility (high coefficient of variation)
	cv := (stdDev / mean) * 100
	if cv > 50 && metricName == "impressions" {
		// High volatility in impressions might indicate ranking instability
		anomalies = append(anomalies, Anomaly{
			Type:        "volatility",
			Metric:      metricName,
			Date:        "",
			Value:       cv,
			ExpectedMin: 0,
			ExpectedMax: 30, // CV above 30% is high
			ZScore:      0,
			Severity:    "medium",
		})
	}

	return anomalies
}

// convertAnomaliestoIssues converts detected anomalies to audit issues
func (d *AnomalyDetector) convertAnomaliestoIssues(anomalies []Anomaly, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// Group anomalies by type to avoid duplicate issues
	hasTrafficDrop := false
	hasRankingSpike := false
	hasVolatility := false

	for _, anomaly := range anomalies {
		switch {
		case anomaly.Type == "drop" && anomaly.Metric == "impressions" && !hasTrafficDrop && anomaly.Severity == "high":
			hasTrafficDrop = true
			issues = append(issues, domain.AuditIssue{
				AuditID:     auditID,
				Severity:    "high",
				Category:    "anomaly",
				Title:       "Unusual Traffic Drop Detected",
				Description: fmt.Sprintf("On %s, impressions dropped to %.0f, which is %.1f standard deviations below your average.",
					anomaly.Date, anomaly.Value, math.Abs(anomaly.ZScore)),
				Impact:      "Sudden traffic drops may indicate algorithm updates, technical issues, or manual actions.",
				Recommendation:  "Check Google Search Console for manual actions, review recent site changes, and monitor competitor activity.",
			})

		case anomaly.Type == "spike" && anomaly.Metric == "position" && !hasRankingSpike && anomaly.Severity == "high":
			hasRankingSpike = true
			issues = append(issues, domain.AuditIssue{
				AuditID:     auditID,
				Severity:    "high",
				Category:    "anomaly",
				Title:       "Sudden Ranking Drop Detected",
				Description: fmt.Sprintf("On %s, average position worsened to %.1f, significantly below your normal range.",
					anomaly.Date, anomaly.Value),
				Impact:      "Sudden ranking drops can dramatically reduce organic traffic and clicks.",
				Recommendation:  "Review recent content changes, check for technical SEO issues, and analyze competitor activity.",
			})

		case anomaly.Type == "volatility" && !hasVolatility:
			hasVolatility = true
			issues = append(issues, domain.AuditIssue{
				AuditID:     auditID,
				Severity:    "medium",
				Category:    "anomaly",
				Title:       "High Traffic Volatility",
				Description: fmt.Sprintf("Your %s show high variability (CV: %.1f%%), indicating unstable search performance.",
					anomaly.Metric, anomaly.Value),
				Impact:      "Volatile traffic makes it difficult to predict and plan for organic growth.",
				Recommendation:  "Focus on building a diverse keyword portfolio and consistent content publishing schedule.",
			})
		}
	}

	return issues
}

// Helper functions for extracting metric values from daily data

func extractImpressions(dailyMetrics []google.DailyMetric) []float64 {
	values := make([]float64, len(dailyMetrics))
	for i, m := range dailyMetrics {
		values[i] = float64(m.Impressions)
	}
	return values
}

func extractClicks(dailyMetrics []google.DailyMetric) []float64 {
	values := make([]float64, len(dailyMetrics))
	for i, m := range dailyMetrics {
		values[i] = float64(m.Clicks)
	}
	return values
}

func extractCTR(dailyMetrics []google.DailyMetric) []float64 {
	values := make([]float64, len(dailyMetrics))
	for i, m := range dailyMetrics {
		values[i] = m.CTR
	}
	return values
}

func extractPosition(dailyMetrics []google.DailyMetric) []float64 {
	values := make([]float64, len(dailyMetrics))
	for i, m := range dailyMetrics {
		values[i] = m.Position
	}
	return values
}

// Statistical helper functions

func calculateMean(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

func calculateStdDev(values []float64, mean float64) float64 {
	if len(values) < 2 {
		return 0
	}
	sumSquares := 0.0
	for _, v := range values {
		diff := v - mean
		sumSquares += diff * diff
	}
	variance := sumSquares / float64(len(values)-1)
	return math.Sqrt(variance)
}
