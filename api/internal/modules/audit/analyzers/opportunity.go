package analyzers

import (
	"fmt"
	"math"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
)

// OpportunityAnalyzer identifies growth opportunities in SEO data
// Implements opportunity detection logic (1:1 with Python audit_engine.py)
type OpportunityAnalyzer struct {
	// Position thresholds for opportunity detection
	strikingDistanceMin float64 // Position 11-20: "striking distance" to page 1
	strikingDistanceMax float64

	// Impression thresholds
	highImpressionThreshold int // High impressions = good visibility
	lowClicksThreshold      int // But low clicks = missed opportunity

	// CTR gap threshold
	ctrGapThreshold float64 // How much below benchmark is significant
}

// NewOpportunityAnalyzer creates a new opportunity analyzer with default thresholds
// Thresholds are 1:1 with Python audit_engine.py
func NewOpportunityAnalyzer() *OpportunityAnalyzer {
	return &OpportunityAnalyzer{
		strikingDistanceMin:     11.0,
		strikingDistanceMax:     20.0,
		highImpressionThreshold: 500, // 1:1 with Python opportunities.py:306 - 500 impressions for quick wins
		lowClicksThreshold:      10,
		ctrGapThreshold:         0.50, // 50% below benchmark
	}
}

// OpportunityResult contains identified opportunities
type OpportunityResult struct {
	Issues        []domain.AuditIssue
	Opportunities []Opportunity
	TotalPotential int // Estimated additional clicks possible
}

// Opportunity represents a growth opportunity
type Opportunity struct {
	Type            string  `json:"type"`             // "striking_distance", "ctr_improvement", "quick_win", "content_gap"
	Description     string  `json:"description"`
	Query           string  `json:"query,omitempty"`
	Page            string  `json:"page,omitempty"`
	CurrentPosition float64 `json:"current_position,omitempty"`
	CurrentCTR      float64 `json:"current_ctr,omitempty"`
	CurrentClicks   int     `json:"current_clicks,omitempty"`
	Impressions     int     `json:"impressions,omitempty"`
	PotentialClicks int     `json:"potential_clicks"` // Estimated additional clicks if optimized
	Priority        string  `json:"priority"`         // "high", "medium", "low"
	Action          string  `json:"action"`           // Recommended action
}

// Analyze identifies growth opportunities from query and page data
func (a *OpportunityAnalyzer) Analyze(
	metrics *domain.AuditMetrics,
	topQueries []domain.TopQuery,
	topPages []domain.TopPage,
	auditID int64,
) *OpportunityResult {
	result := &OpportunityResult{
		Issues:        []domain.AuditIssue{},
		Opportunities: []Opportunity{},
		TotalPotential: 0,
	}

	// Analyze striking distance queries (position 11-20)
	strikingOpps := a.findStrikingDistanceQueries(topQueries)
	result.Opportunities = append(result.Opportunities, strikingOpps...)

	// Analyze CTR improvement opportunities
	ctrOpps := a.findCTRImprovementOpportunities(topQueries)
	result.Opportunities = append(result.Opportunities, ctrOpps...)

	// Analyze quick wins (high impressions, decent position, low clicks)
	quickWins := a.findQuickWins(topQueries)
	result.Opportunities = append(result.Opportunities, quickWins...)

	// Analyze page-level opportunities
	pageOpps := a.findPageOpportunities(topPages)
	result.Opportunities = append(result.Opportunities, pageOpps...)

	// Overall metrics-based opportunities
	overallOpps := a.findOverallOpportunities(metrics)
	result.Opportunities = append(result.Opportunities, overallOpps...)

	// Calculate total potential
	for _, opp := range result.Opportunities {
		result.TotalPotential += opp.PotentialClicks
	}

	// Convert top opportunities to audit issues
	result.Issues = a.convertOpportunitiesToIssues(result.Opportunities, auditID)

	return result
}

// AnalyzeWithHistory identifies opportunities including keyword bleeding (1:1 with Python)
func (a *OpportunityAnalyzer) AnalyzeWithHistory(
	metrics *domain.AuditMetrics,
	currentQueries []domain.TopQuery,
	historicalQueries []domain.TopQuery,
	topPages []domain.TopPage,
	auditID int64,
) *OpportunityResult {
	// Run standard analysis
	result := a.Analyze(metrics, currentQueries, topPages, auditID)

	// Add keyword bleeding detection (1:1 with Python performance.py)
	bleedingIssue := a.analyzeKeywordBleeding(currentQueries, historicalQueries, auditID)
	if bleedingIssue != nil {
		result.Issues = append(result.Issues, *bleedingIssue)
	}

	return result
}

// analyzeKeywordBleeding detects keyword losses between periods (1:1 with Python performance.py)
func (a *OpportunityAnalyzer) analyzeKeywordBleeding(
	currentQueries []domain.TopQuery,
	historicalQueries []domain.TopQuery,
	auditID int64,
) *domain.AuditIssue {
	if len(historicalQueries) == 0 {
		return nil
	}

	// Build sets of current and historical queries
	currentSet := make(map[string]bool)
	for _, q := range currentQueries {
		currentSet[q.Query] = true
	}

	historicalSet := make(map[string]bool)
	for _, q := range historicalQueries {
		historicalSet[q.Query] = true
	}

	// Calculate lost keywords
	var lostKeywords []string
	for query := range historicalSet {
		if !currentSet[query] {
			lostKeywords = append(lostKeywords, query)
		}
	}

	// Calculate bleeding rate (1:1 with Python)
	bleedingRate := 0.0
	if len(historicalSet) > 0 {
		bleedingRate = float64(len(lostKeywords)) / float64(len(historicalSet)) * 100
	}

	// Only flag if significant keyword bleeding (>30%) - 1:1 with Python
	if bleedingRate > 30 {
		severity := "medium"
		if bleedingRate > 50 {
			severity = "high"
		}

		// Sample of lost keywords (max 10)
		sampleKeywords := lostKeywords
		if len(sampleKeywords) > 10 {
			sampleKeywords = sampleKeywords[:10]
		}

		return &domain.AuditIssue{
			AuditID:  auditID,
			Severity: severity,
			Category: "performance",
			Title:    "Significant Keyword Bleeding Detected",
			Description: fmt.Sprintf("You've lost %d keywords (%.0f%% bleeding rate). "+
				"Previously ranking for %d keywords, now only %d. "+
				"Lost keywords include: %v",
				len(lostKeywords), bleedingRate, len(historicalSet), len(currentSet), sampleKeywords),
			Impact: "Keyword losses indicate potential ranking drops or content issues that are reducing your organic search visibility.",
			Recommendation: "Review the lost keywords and identify patterns. Check if content was removed, " +
				"competitors improved, or if there were algorithm changes affecting your rankings.",
		}
	}

	return nil
}

// findStrikingDistanceQueries finds queries ranking 11-20 (page 2)
func (a *OpportunityAnalyzer) findStrikingDistanceQueries(queries []domain.TopQuery) []Opportunity {
	var opportunities []Opportunity

	for _, query := range queries {
		if query.Position >= a.strikingDistanceMin && query.Position <= a.strikingDistanceMax {
			// Calculate potential: moving to position 5 vs current
			currentCTR := query.CTR
			potentialCTR := GetExpectedCTR(5.0) // Target position 5

			additionalClicks := 0
			if query.Impressions > 0 {
				additionalClicks = int(float64(query.Impressions) * (potentialCTR - currentCTR))
				if additionalClicks < 0 {
					additionalClicks = 0
				}
			}

			priority := "medium"
			if query.Impressions >= 50 || additionalClicks >= 10 {
				priority = "high"
			}

			opportunities = append(opportunities, Opportunity{
				Type:            "striking_distance",
				Description:     fmt.Sprintf("'%s' ranks at position %.1f - close to page 1", query.Query, query.Position),
				Query:           query.Query,
				CurrentPosition: query.Position,
				CurrentCTR:      query.CTR,
				CurrentClicks:   query.Clicks,
				Impressions:     query.Impressions,
				PotentialClicks: additionalClicks,
				Priority:        priority,
				Action:          "Optimize content and build internal links to push this query to page 1",
			})
		}
	}

	return opportunities
}

// findCTRImprovementOpportunities finds queries with CTR below benchmark
func (a *OpportunityAnalyzer) findCTRImprovementOpportunities(queries []domain.TopQuery) []Opportunity {
	var opportunities []Opportunity

	for _, query := range queries {
		if query.Impressions < 20 {
			continue // Skip low-volume queries
		}

		expectedCTR := GetExpectedCTR(query.Position)
		if expectedCTR == 0 {
			continue
		}

		ctrGap := (expectedCTR - query.CTR) / expectedCTR
		if ctrGap > a.ctrGapThreshold {
			// Calculate potential clicks if CTR improved to benchmark
			additionalClicks := int(float64(query.Impressions) * (expectedCTR - query.CTR))
			if additionalClicks < 0 {
				additionalClicks = 0
			}

			priority := "low"
			if additionalClicks >= 20 {
				priority = "high"
			} else if additionalClicks >= 10 {
				priority = "medium"
			}

			opportunities = append(opportunities, Opportunity{
				Type:            "ctr_improvement",
				Description:     fmt.Sprintf("'%s' has %.1f%% CTR vs %.1f%% expected for position %.0f", query.Query, query.CTR*100, expectedCTR*100, query.Position),
				Query:           query.Query,
				CurrentPosition: query.Position,
				CurrentCTR:      query.CTR,
				CurrentClicks:   query.Clicks,
				Impressions:     query.Impressions,
				PotentialClicks: additionalClicks,
				Priority:        priority,
				Action:          "Improve meta title and description to be more compelling and match search intent",
			})
		}
	}

	return opportunities
}

// findQuickWins finds high-impression, low-click opportunities
func (a *OpportunityAnalyzer) findQuickWins(queries []domain.TopQuery) []Opportunity {
	var opportunities []Opportunity

	for _, query := range queries {
		// Quick win criteria: good impressions, decent position, but low clicks
		if query.Impressions >= a.highImpressionThreshold &&
			query.Position <= 30 &&
			query.Clicks <= a.lowClicksThreshold {

			// This suggests CTR problem or intent mismatch
			expectedCTR := GetExpectedCTR(query.Position)
			additionalClicks := int(float64(query.Impressions) * expectedCTR * 0.5) // Conservative 50% of potential

			opportunities = append(opportunities, Opportunity{
				Type:            "quick_win",
				Description:     fmt.Sprintf("'%s' has %d impressions but only %d clicks", query.Query, query.Impressions, query.Clicks),
				Query:           query.Query,
				CurrentPosition: query.Position,
				CurrentCTR:      query.CTR,
				CurrentClicks:   query.Clicks,
				Impressions:     query.Impressions,
				PotentialClicks: additionalClicks,
				Priority:        "high",
				Action:          "Review search intent - your content may not match what users are looking for. Update meta description to better address user needs.",
			})
		}
	}

	return opportunities
}

// findPageOpportunities analyzes top pages for optimization opportunities
func (a *OpportunityAnalyzer) findPageOpportunities(pages []domain.TopPage) []Opportunity {
	var opportunities []Opportunity

	for _, page := range pages {
		// Page with good visibility but poor CTR
		if page.Impressions >= 50 && page.CTR < 0.02 && page.Position <= 20 {
			additionalClicks := int(float64(page.Impressions) * 0.03) // Target 3% CTR

			opportunities = append(opportunities, Opportunity{
				Type:            "page_ctr",
				Description:     fmt.Sprintf("Page has %d impressions but only %.1f%% CTR", page.Impressions, page.CTR*100),
				Page:            page.Page,
				CurrentPosition: page.Position,
				CurrentCTR:      page.CTR,
				CurrentClicks:   page.Clicks,
				Impressions:     page.Impressions,
				PotentialClicks: additionalClicks,
				Priority:        "medium",
				Action:          "Optimize this page's title tag and meta description. Consider adding structured data.",
			})
		}

		// Page ranking on page 2 with good impressions
		if page.Position >= 11 && page.Position <= 20 && page.Impressions >= 30 {
			// Not adding duplicate opportunities - handled in striking distance
		}
	}

	return opportunities
}

// findOverallOpportunities finds opportunities based on aggregate metrics
func (a *OpportunityAnalyzer) findOverallOpportunities(metrics *domain.AuditMetrics) []Opportunity {
	var opportunities []Opportunity

	// Overall CTR improvement opportunity
	if metrics.Impressions > 500 && metrics.CTR < 0.03 {
		currentClicks := metrics.Clicks
		potentialClicks := int(float64(metrics.Impressions) * 0.04) // Target 4% CTR
		additionalClicks := potentialClicks - currentClicks

		if additionalClicks > 0 {
			opportunities = append(opportunities, Opportunity{
				Type:            "overall_ctr",
				Description:     fmt.Sprintf("Site-wide CTR is %.1f%% - improving to 4%% would add ~%d clicks", metrics.CTR*100, additionalClicks),
				Impressions:     metrics.Impressions,
				CurrentCTR:      metrics.CTR,
				CurrentClicks:   metrics.Clicks,
				PotentialClicks: additionalClicks,
				Priority:        "high",
				Action:          "Conduct a site-wide audit of title tags and meta descriptions. Implement structured data where applicable.",
			})
		}
	}

	// Position improvement opportunity
	if metrics.Position > 15 && metrics.Impressions > 100 {
		// Estimate clicks at position 8 vs current
		currentCTR := metrics.CTR
		targetCTR := GetExpectedCTR(8.0)
		additionalClicks := int(float64(metrics.Impressions) * (targetCTR - currentCTR))

		if additionalClicks > 0 {
			opportunities = append(opportunities, Opportunity{
				Type:            "position_improvement",
				Description:     fmt.Sprintf("Average position is %.1f - improving to top 10 would significantly increase clicks", metrics.Position),
				CurrentPosition: metrics.Position,
				Impressions:     metrics.Impressions,
				PotentialClicks: additionalClicks,
				Priority:        "medium",
				Action:          "Focus on content quality, building authoritative backlinks, and improving page experience.",
			})
		}
	}

	return opportunities
}

// convertOpportunitiesToIssues converts top opportunities to audit issues
func (a *OpportunityAnalyzer) convertOpportunitiesToIssues(opportunities []Opportunity, auditID int64) []domain.AuditIssue {
	var issues []domain.AuditIssue

	// Group by type to avoid too many similar issues
	hasStrikingDistance := false
	hasCTRImprovement := false
	hasQuickWin := false
	hasOverallCTR := false

	// Sort by potential (highest first)
	sortedOpps := make([]Opportunity, len(opportunities))
	copy(sortedOpps, opportunities)
	for i := 0; i < len(sortedOpps)-1; i++ {
		for j := i + 1; j < len(sortedOpps); j++ {
			if sortedOpps[j].PotentialClicks > sortedOpps[i].PotentialClicks {
				sortedOpps[i], sortedOpps[j] = sortedOpps[j], sortedOpps[i]
			}
		}
	}

	for _, opp := range sortedOpps {
		if len(issues) >= 3 {
			break // Limit to top 3 opportunity issues
		}

		switch opp.Type {
		case "striking_distance":
			if !hasStrikingDistance && opp.Priority == "high" {
				hasStrikingDistance = true
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    "medium",
					Category:    "opportunity",
					Title:       "Page 1 Potential",
					Description: fmt.Sprintf("You have queries ranking at positions 11-20 that could move to page 1. Example: %s", opp.Description),
					Impact:      fmt.Sprintf("Moving these to page 1 could generate ~%d additional clicks.", opp.PotentialClicks),
					Recommendation:  opp.Action,
				})
			}

		case "ctr_improvement":
			if !hasCTRImprovement && opp.Priority != "low" {
				hasCTRImprovement = true
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    "medium",
					Category:    "opportunity",
					Title:       "CTR Improvement Opportunity",
					Description: opp.Description,
					Impact:      fmt.Sprintf("Improving CTR to benchmark levels could add ~%d clicks.", opp.PotentialClicks),
					Recommendation:  opp.Action,
				})
			}

		case "quick_win":
			if !hasQuickWin {
				hasQuickWin = true
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    "high",
					Category:    "opportunity",
					Title:       "Quick Win Available",
					Description: opp.Description,
					Impact:      "High impressions with low clicks indicates a mismatch between your content and user intent.",
					Recommendation:  opp.Action,
				})
			}

		case "overall_ctr":
			if !hasOverallCTR {
				hasOverallCTR = true
				issues = append(issues, domain.AuditIssue{
					AuditID:     auditID,
					Severity:    "medium",
					Category:    "opportunity",
					Title:       "Site-Wide CTR Optimization",
					Description: opp.Description,
					Impact:      fmt.Sprintf("A comprehensive CTR optimization could significantly increase organic traffic."),
					Recommendation:  opp.Action,
				})
			}
		}
	}

	return issues
}

// CalculateTotalPotential estimates total additional clicks possible from all opportunities
func (a *OpportunityAnalyzer) CalculateTotalPotential(opportunities []Opportunity) int {
	// Avoid double-counting by using diminishing returns
	total := 0
	seenQueries := make(map[string]bool)
	seenPages := make(map[string]bool)

	for _, opp := range opportunities {
		if opp.Query != "" && seenQueries[opp.Query] {
			continue
		}
		if opp.Page != "" && seenPages[opp.Page] {
			continue
		}

		if opp.Query != "" {
			seenQueries[opp.Query] = true
		}
		if opp.Page != "" {
			seenPages[opp.Page] = true
		}

		// Apply diminishing returns to avoid over-estimation
		adjustedPotential := int(math.Sqrt(float64(opp.PotentialClicks)) * 5)
		if adjustedPotential > opp.PotentialClicks {
			adjustedPotential = opp.PotentialClicks
		}
		total += adjustedPotential
	}

	return total
}
