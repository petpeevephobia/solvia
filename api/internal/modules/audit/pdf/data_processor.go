package pdf

import (
	"fmt"
	"math"
	"sort"
	"time"
)

// ============================================================================
// SEO STAGE DEFINITIONS (1:1 with Python)
// ============================================================================

// SEOStage represents an SEO visibility stage
type SEOStage struct {
	Name             string  `json:"name"`
	ThresholdMin     int     `json:"threshold_min"`
	ThresholdMax     float64 `json:"threshold_max"`
	ThresholdDisplay string  `json:"threshold_display"`
	Description      string  `json:"description"`
	NextStage        string  `json:"next_stage,omitempty"`
}

var SEOStages = map[string]*SEOStage{
	"hidden": {
		Name:             "Hidden",
		ThresholdMin:     0,
		ThresholdMax:     49,
		ThresholdDisplay: "1 impression",
		Description:      "Your site is still hidden from most search results. Let's work on visibility by improving content and indexing.",
		NextStage:        "emerging",
	},
	"emerging": {
		Name:             "Emerging",
		ThresholdMin:     50,
		ThresholdMax:     299,
		ThresholdDisplay: "50 impressions",
		Description:      "Your site is starting to gain visibility. Continue building quality content and improving technical SEO.",
		NextStage:        "discoverable",
	},
	"discoverable": {
		Name:             "Discoverable",
		ThresholdMin:     300,
		ThresholdMax:     1999,
		ThresholdDisplay: "300 impressions",
		Description:      "Your site is becoming more discoverable. Focus on optimizing top-performing pages and expanding keyword coverage.",
		NextStage:        "trusted",
	},
	"trusted": {
		Name:             "Trusted",
		ThresholdMin:     2000,
		ThresholdMax:     math.Inf(1),
		ThresholdDisplay: "2000+ impressions",
		Description:      "Your site has strong search visibility. Maintain quality and explore new growth opportunities.",
		NextStage:        "",
	},
}

// ============================================================================
// 28-DAY CHANGE CALCULATION (V1 vs V2 METHOD)
// ============================================================================

// DailyMetric represents metrics for a single day
type DailyMetric struct {
	Date        string  `json:"date"`
	Clicks      int     `json:"clicks"`
	Impressions int     `json:"impressions"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// Changes28Day represents V1 (first day) vs V2 (last day) changes
type Changes28Day struct {
	ImpressionsChange  interface{} `json:"impressions_change"`  // float64 or "N/A"
	ClicksChange       interface{} `json:"clicks_change"`       // float64 or "N/A"
	CTRChange          interface{} `json:"ctr_change"`          // float64 or "N/A"
	PositionChange     interface{} `json:"position_change"`     // float64 or "N/A"
	IndexedPagesChange interface{} `json:"indexed_pages_change"` // int or "N/A"
	HasSufficientData  bool        `json:"has_sufficient_data"`
	V1Date             string      `json:"v1_date,omitempty"`
	V2Date             string      `json:"v2_date,omitempty"`
}

// Calculate28DayChanges calculates changes using V1 (first day) vs V2 (last day) method
func Calculate28DayChanges(timeSeriesData []DailyMetric) *Changes28Day {
	// Validate input
	if len(timeSeriesData) == 0 {
		return &Changes28Day{
			ImpressionsChange:  "N/A",
			ClicksChange:       "N/A",
			CTRChange:          "N/A",
			PositionChange:     "N/A",
			IndexedPagesChange: "N/A",
			HasSufficientData:  false,
		}
	}

	// Sort by date to ensure correct V1/V2 order
	sortedData := make([]DailyMetric, len(timeSeriesData))
	copy(sortedData, timeSeriesData)
	sort.Slice(sortedData, func(i, j int) bool {
		return sortedData[i].Date < sortedData[j].Date
	})

	// Check if we have at least 2 data points
	if len(sortedData) < 2 {
		return &Changes28Day{
			ImpressionsChange:  "N/A",
			ClicksChange:       "N/A",
			CTRChange:          "N/A",
			PositionChange:     "N/A",
			IndexedPagesChange: "N/A",
			HasSufficientData:  false,
			V1Date:             sortedData[0].Date,
			V2Date:             sortedData[0].Date,
		}
	}

	// Get V1 (first day) and V2 (last day)
	v1 := sortedData[0]
	v2 := sortedData[len(sortedData)-1]

	changes := &Changes28Day{
		HasSufficientData: true,
		V1Date:            v1.Date,
		V2Date:            v2.Date,
	}

	// Calculate Impressions Change (percentage)
	if v1.Impressions > 0 {
		changes.ImpressionsChange = roundFloat((float64(v2.Impressions-v1.Impressions) / float64(v1.Impressions)) * 100)
	} else if v2.Impressions > 0 {
		changes.ImpressionsChange = 100.0 // Special case: went from 0 to positive
	} else {
		changes.ImpressionsChange = 0.0 // Both are 0
	}

	// Calculate Clicks Change (percentage)
	if v1.Clicks > 0 {
		changes.ClicksChange = roundFloat((float64(v2.Clicks-v1.Clicks) / float64(v1.Clicks)) * 100)
	} else if v2.Clicks > 0 {
		changes.ClicksChange = 100.0
	} else {
		changes.ClicksChange = 0.0
	}

	// Calculate CTR Change (absolute difference in percentage points)
	var v1CTR, v2CTR float64
	if v1.Impressions > 0 {
		v1CTR = (float64(v1.Clicks) / float64(v1.Impressions)) * 100
	}
	if v2.Impressions > 0 {
		v2CTR = (float64(v2.Clicks) / float64(v2.Impressions)) * 100
	}
	changes.CTRChange = roundFloat2(v2CTR - v1CTR)

	// Calculate Position Change (absolute difference, negative = improved)
	if v1.Position > 0 && v2.Position > 0 {
		changes.PositionChange = roundFloat(v2.Position - v1.Position)
	} else {
		changes.PositionChange = "N/A"
	}

	// Indexed pages change (placeholder)
	changes.IndexedPagesChange = "N/A"

	return changes
}

// ============================================================================
// SEO STAGE DETERMINATION (1:1 with Python)
// ============================================================================

// DetermineSEOStage determines SEO stage based on impression count
func DetermineSEOStage(impressions int) string {
	if impressions < 50 {
		return "hidden"
	} else if impressions < 300 {
		return "emerging"
	} else if impressions < 2000 {
		return "discoverable"
	}
	return "trusted"
}

// GetSEOStageInfo returns complete information about an SEO stage
func GetSEOStageInfo(stageKey string) *SEOStage {
	if stage, ok := SEOStages[stageKey]; ok {
		return stage
	}
	return SEOStages["hidden"]
}

// ============================================================================
// PDF DATA STRUCTURES
// ============================================================================

// PDFMetrics contains all metrics for PDF generation
type PDFMetrics struct {
	TotalImpressions  int     `json:"total_impressions"`
	TotalClicks       int     `json:"total_clicks"`
	AverageCTR        float64 `json:"average_ctr"`        // As decimal (0.0909)
	AveragePosition   float64 `json:"average_position"`
	IndexedPages      int     `json:"indexed_pages"`
}

// SummaryParagraphs contains the 3 summary paragraphs for Page 1
type SummaryParagraphs struct {
	ImpressionsPara string `json:"impressions_para"`
	ClicksCTRPara   string `json:"clicks_ctr_para"`
	PositionPara    string `json:"position_para"`
}

// MetricNotes contains notes for each metric
type MetricNotes struct {
	ImpressionsNote   string `json:"impressions_note"`
	ClicksNote        string `json:"clicks_note"`
	CTRNote           string `json:"ctr_note"`
	PositionNote      string `json:"position_note"`
	IndexedPagesNote  string `json:"indexed_pages_note"`
}

// PDFData contains all processed data for PDF generation
type PDFData struct {
	// Website info
	WebsiteURL   string    `json:"website_url"`
	ReportDate   time.Time `json:"report_date"`
	DateRange    string    `json:"date_range"`

	// SEO Stage
	SEOStage     string    `json:"seo_stage"`
	SEOStageInfo *SEOStage `json:"seo_stage_info"`

	// Metrics
	Metrics      *PDFMetrics     `json:"metrics"`
	Changes      *Changes28Day   `json:"changes"`

	// Generated content
	Summary      *SummaryParagraphs `json:"summary"`
	Notes        *MetricNotes       `json:"notes"`
	NextSteps    []string           `json:"next_steps"`

	// Motivational quotes
	QuotePage1   string `json:"quote_page1"`
	QuotePage2   string `json:"quote_page2"`
}

// ============================================================================
// DATA PROCESSING FUNCTIONS
// ============================================================================

// GenerateSummaryParagraphs generates the 3 summary paragraphs using rule-based text
func GenerateSummaryParagraphs(metrics *PDFMetrics) *SummaryParagraphs {
	// Convert CTR to percentage
	ctrPercentage := metrics.AverageCTR * 100

	return &SummaryParagraphs{
		ImpressionsPara: GetImpressionsStatement(metrics.TotalImpressions),
		ClicksCTRPara:   GetClicksCTRStatement(metrics.TotalClicks, ctrPercentage),
		PositionPara:    GetPositionStatement(metrics.AveragePosition),
	}
}

// GenerateMetricNotes generates notes for each metric using rule-based text
func GenerateMetricNotes(metrics *PDFMetrics, changes *Changes28Day, seoStage string) *MetricNotes {
	// Convert CTR to percentage
	ctrPercentage := metrics.AverageCTR * 100

	// Extract change values (handle "N/A")
	impressionsChange := getFloatFromInterface(changes.ImpressionsChange)
	clicksChange := getFloatFromInterface(changes.ClicksChange)
	ctrChange := getFloatFromInterface(changes.CTRChange)
	positionChange := getFloatFromInterface(changes.PositionChange)
	indexedPagesChange := getIntFromInterface(changes.IndexedPagesChange)

	// Calculate unindexed pages
	unindexedCount := 0
	if metrics.IndexedPages < 10 {
		unindexedCount = 1
	}

	return &MetricNotes{
		ImpressionsNote:  GetImpressionsNote(impressionsChange),
		ClicksNote:       GetClicksNote(metrics.TotalClicks, clicksChange),
		CTRNote:          GetCTRNote(ctrPercentage, ctrChange),
		PositionNote:     GetPositionNote(metrics.AveragePosition, positionChange),
		IndexedPagesNote: GetIndexedPagesNote(unindexedCount, indexedPagesChange),
	}
}

// GenerateNextSteps generates the next steps list using rule-based logic
func GenerateNextSteps(metrics *PDFMetrics, changes *Changes28Day, seoStage string) []string {
	// Convert CTR to percentage
	ctrPercentage := metrics.AverageCTR * 100

	// Calculate unindexed pages
	unindexedCount := 0
	if metrics.IndexedPages < 10 {
		unindexedCount = 1
	}

	// Assume sitemap not submitted to trigger that recommendation
	sitemapSubmitted := false

	return GetAllNextSteps(
		sitemapSubmitted,
		ctrPercentage,
		metrics.AveragePosition,
		metrics.TotalImpressions,
		unindexedCount,
		metrics.TotalClicks,
	)
}

// ProcessPDFData processes all data needed for PDF generation (1:1 with Python)
func ProcessPDFData(websiteURL string, metrics *PDFMetrics, timeSeriesData []DailyMetric) *PDFData {
	// Determine SEO stage
	seoStage := DetermineSEOStage(metrics.TotalImpressions)
	stageInfo := GetSEOStageInfo(seoStage)

	// Calculate 28-day changes
	changes := Calculate28DayChanges(timeSeriesData)

	// Generate content
	summary := GenerateSummaryParagraphs(metrics)
	notes := GenerateMetricNotes(metrics, changes, seoStage)
	nextSteps := GenerateNextSteps(metrics, changes, seoStage)

	// Get motivational quotes
	quotePage1 := GetMotivationalQuotePage1(seoStage)
	quotePage2 := GetMotivationalQuotePage2(seoStage)

	// Calculate date range
	dateRange := "Last 28 days"
	if len(timeSeriesData) > 0 {
		sortedData := make([]DailyMetric, len(timeSeriesData))
		copy(sortedData, timeSeriesData)
		sort.Slice(sortedData, func(i, j int) bool {
			return sortedData[i].Date < sortedData[j].Date
		})
		dateRange = fmt.Sprintf("%s to %s", sortedData[0].Date, sortedData[len(sortedData)-1].Date)
	}

	return &PDFData{
		WebsiteURL:   websiteURL,
		ReportDate:   time.Now(),
		DateRange:    dateRange,
		SEOStage:     seoStage,
		SEOStageInfo: stageInfo,
		Metrics:      metrics,
		Changes:      changes,
		Summary:      summary,
		Notes:        notes,
		NextSteps:    nextSteps,
		QuotePage1:   quotePage1,
		QuotePage2:   quotePage2,
	}
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// FormatChangeDisplay formats change value for display in PDF (1:1 with Python)
func FormatChangeDisplay(change interface{}, metricType string) string {
	if change == nil || change == "N/A" {
		return "N/A"
	}

	changeNumeric, ok := change.(float64)
	if !ok {
		return "N/A"
	}

	sign := ""
	if changeNumeric > 0 {
		sign = "+"
	}

	switch metricType {
	case "percentage":
		return fmt.Sprintf("%s%.1f%%", sign, changeNumeric)
	case "ctr":
		// CTR uses percentage points (pp), not percent (1:1 with Python)
		// Add asterisk to reference footnote
		return fmt.Sprintf("%s%.2fpp*", sign, changeNumeric)
	case "absolute":
		return fmt.Sprintf("%s%.2f", sign, changeNumeric)
	case "position":
		return fmt.Sprintf("%s%.1f", sign, changeNumeric)
	default:
		return fmt.Sprintf("%s%.1f", sign, changeNumeric)
	}
}

// FormatCTRDisplay formats CTR for display (always multiply by 100)
func FormatCTRDisplay(ctrDecimal float64) string {
	if ctrDecimal == 0 {
		return "0.00%"
	}
	ctrPercentage := ctrDecimal * 100
	return fmt.Sprintf("%.2f%%", ctrPercentage)
}

// roundFloat rounds to 1 decimal place
func roundFloat(val float64) float64 {
	return math.Round(val*10) / 10
}

// roundFloat2 rounds to 2 decimal places
func roundFloat2(val float64) float64 {
	return math.Round(val*100) / 100
}

// getFloatFromInterface extracts float64 from interface{}, returns 0 if "N/A"
func getFloatFromInterface(v interface{}) float64 {
	if v == nil || v == "N/A" {
		return 0
	}
	if f, ok := v.(float64); ok {
		return f
	}
	return 0
}

// getIntFromInterface extracts int from interface{}, returns 0 if "N/A"
func getIntFromInterface(v interface{}) int {
	if v == nil || v == "N/A" {
		return 0
	}
	if i, ok := v.(int); ok {
		return i
	}
	if f, ok := v.(float64); ok {
		return int(f)
	}
	return 0
}
