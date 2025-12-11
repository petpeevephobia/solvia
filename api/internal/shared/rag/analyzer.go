package rag

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"strings"
	"time"
)

// IssueSeverity represents issue severity levels
type IssueSeverity string

const (
	SeverityCritical IssueSeverity = "critical" // >50% traffic loss or complete failure
	SeverityHigh     IssueSeverity = "high"     // 20-50% performance impact
	SeverityMedium   IssueSeverity = "medium"   // 10-20% performance impact
	SeverityLow      IssueSeverity = "low"      // <10% performance impact
)

// PatternType represents detected SEO patterns
type PatternType string

const (
	PatternTrafficDrop     PatternType = "traffic_drop"
	PatternAlgorithmUpdate PatternType = "algorithm_update"
	PatternTechnicalIssue  PatternType = "technical_issue"
	PatternContentDecay    PatternType = "content_decay"
	PatternSeasonalTrend   PatternType = "seasonal_trend"
	PatternCompetitorSurge PatternType = "competitor_surge"
	PatternHighVolatility  PatternType = "high_volatility"
	PatternRankingIssues   PatternType = "severe_ranking_issues"
)

// SEOIssue represents a detected SEO issue (1:1 with Python)
type SEOIssue struct {
	Title           string                 `json:"title"`
	Description     string                 `json:"description"`
	Severity        IssueSeverity          `json:"severity"`
	Impact          string                 `json:"impact"`
	Recommendation  string                 `json:"recommendation"`
	Category        string                 `json:"category"`
	DataPoints      map[string]interface{} `json:"data_points"`
	ConfidenceScore float64                `json:"confidence_score"`
	ExpectedOutcome string                 `json:"expected_outcome,omitempty"`
}

// SEOPattern represents a detected pattern in the data
type SEOPattern struct {
	PatternType     PatternType            `json:"pattern_type"`
	Confidence      float64                `json:"confidence"`
	AffectedMetrics []string               `json:"affected_metrics"`
	TimeRange       *TimeRange             `json:"time_range,omitempty"`
	Severity        IssueSeverity          `json:"severity"`
	Evidence        map[string]interface{} `json:"evidence,omitempty"`
}

// TimeRange represents a time period
type TimeRange struct {
	Start time.Time `json:"start"`
	End   time.Time `json:"end"`
}

// SEOMetrics represents extracted metrics for analysis
type SEOMetrics struct {
	SEOScore          float64 `json:"seo_score"`
	Clicks            int     `json:"clicks"`
	Impressions       int     `json:"impressions"`
	CTR               float64 `json:"ctr"`
	AvgPosition       float64 `json:"avg_position"`
	ClicksChange      float64 `json:"clicks_change"`
	ImpressionsChange float64 `json:"impressions_change"`
	PositionChange    float64 `json:"position_change"`
	VisibilityScore   float64 `json:"visibility_score"`
	EngagementScore   float64 `json:"engagement_score"`
}

// IndustryBenchmarks represents industry-specific benchmarks
type IndustryBenchmarks struct {
	AvgCTR         float64 `json:"avg_ctr"`
	AvgPosition    float64 `json:"avg_position"`
	ConversionRate float64 `json:"conversion_rate"`
	BounceRate     float64 `json:"bounce_rate"`
	PageSession    float64 `json:"page_session"`
}

// IssueTemplate represents a template for common issues
type IssueTemplate struct {
	Title          string `json:"title"`
	Impact         string `json:"impact"`
	Recommendation string `json:"recommendation"`
}

// RAGAnalyzer implements intelligent SEO issue detection (1:1 with Python)
type RAGAnalyzer struct {
	knowledgeBase *SEOKnowledgeBase
}

// SEOKnowledgeBase contains SEO best practices and rules
type SEOKnowledgeBase struct {
	IssueTemplates     map[string]IssueTemplate
	IndustryBenchmarks map[string]IndustryBenchmarks
	CTRBenchmarks      map[int]float64
}

// NewRAGAnalyzer creates a new RAG analyzer
func NewRAGAnalyzer() *RAGAnalyzer {
	return &RAGAnalyzer{
		knowledgeBase: newSEOKnowledgeBase(),
	}
}

// newSEOKnowledgeBase creates the SEO knowledge base with best practices
func newSEOKnowledgeBase() *SEOKnowledgeBase {
	return &SEOKnowledgeBase{
		IssueTemplates: map[string]IssueTemplate{
			"low_traffic": {
				Title:          "Low Organic Traffic",
				Impact:         "Your website is missing potential customers",
				Recommendation: "Focus on content optimization and keyword targeting",
			},
			"poor_ctr": {
				Title:          "Poor Click-Through Rate",
				Impact:         "Users see your site but aren't clicking",
				Recommendation: "Improve meta titles and descriptions to be more compelling",
			},
			"high_position": {
				Title:          "Poor Search Rankings",
				Impact:         "Your content appears too far down in search results",
				Recommendation: "Improve content quality and build authoritative backlinks",
			},
			"no_impressions": {
				Title:          "Minimal Search Visibility",
				Impact:         "Your website isn't appearing in search results",
				Recommendation: "Submit sitemap to Google and create targeted content",
			},
			"declining_traffic": {
				Title:          "Traffic Decline Detected",
				Impact:         "Your organic traffic is dropping significantly",
				Recommendation: "Check for algorithm updates, technical issues, or content decay",
			},
			"ctr_below_benchmark": {
				Title:          "CTR Below Industry Standards",
				Impact:         "You're losing clicks to competitors",
				Recommendation: "A/B test meta descriptions and add emotional triggers",
			},
		},
		IndustryBenchmarks: map[string]IndustryBenchmarks{
			"e-commerce": {
				AvgCTR:         2.69,
				AvgPosition:    15.2,
				ConversionRate: 2.86,
				BounceRate:     45.0,
				PageSession:    3.2,
			},
			"saas": {
				AvgCTR:         3.12,
				AvgPosition:    12.8,
				ConversionRate: 7.0,
				BounceRate:     55.0,
				PageSession:    2.8,
			},
			"blog": {
				AvgCTR:         2.35,
				AvgPosition:    18.5,
				ConversionRate: 1.5,
				BounceRate:     65.0,
				PageSession:    1.9,
			},
			"local_business": {
				AvgCTR:         4.21,
				AvgPosition:    8.3,
				ConversionRate: 5.0,
				BounceRate:     40.0,
				PageSession:    2.5,
			},
			"default": {
				AvgCTR:         2.5,
				AvgPosition:    15.0,
				ConversionRate: 3.0,
				BounceRate:     50.0,
				PageSession:    2.5,
			},
		},
		// CTR benchmarks by position (2024 standards)
		CTRBenchmarks: map[int]float64{
			1:  27.6,
			2:  15.8,
			3:  11.0,
			4:  8.4,
			5:  6.3,
			6:  4.9,
			7:  4.0,
			8:  3.3,
			9:  2.8,
			10: 2.5,
		},
	}
}

// AnalyzeAuditData analyzes audit data and generates intelligent issues (1:1 with Python)
func (a *RAGAnalyzer) AnalyzeAuditData(ctx context.Context, metrics *SEOMetrics, industry string) ([]SEOIssue, error) {
	// Get benchmarks for industry
	benchmarks, ok := a.knowledgeBase.IndustryBenchmarks[industry]
	if !ok {
		benchmarks = a.knowledgeBase.IndustryBenchmarks["default"]
	}

	// Detect issues with confidence scoring
	issues := a.detectIssues(metrics, benchmarks)

	// Detect patterns
	patterns := a.detectPatterns(metrics)

	// Add pattern-based issues
	for _, pattern := range patterns {
		if pattern.Severity == SeverityCritical || pattern.Severity == SeverityHigh {
			issue := SEOIssue{
				Title:           a.patternToTitle(pattern.PatternType),
				Description:     a.patternToDescription(pattern.PatternType, pattern.Evidence),
				Severity:        pattern.Severity,
				Impact:          a.patternToImpact(pattern.PatternType),
				Recommendation:  a.patternToRecommendation(pattern.PatternType),
				Category:        a.patternToCategory(pattern.PatternType),
				DataPoints:      pattern.Evidence,
				ConfidenceScore: pattern.Confidence,
			}
			issues = append(issues, issue)
		}
	}

	// Sort by severity and confidence
	a.sortIssuesByImpact(issues)

	// Return top 3 issues
	if len(issues) > 3 {
		issues = issues[:3]
	}

	return issues, nil
}

// detectIssues detects issues from metrics using rules (1:1 with Python)
func (a *RAGAnalyzer) detectIssues(metrics *SEOMetrics, benchmarks IndustryBenchmarks) []SEOIssue {
	var issues []SEOIssue

	// CRITICAL: No impressions (zero visibility)
	if metrics.Impressions == 0 {
		template := a.knowledgeBase.IssueTemplates["no_impressions"]
		issues = append(issues, SEOIssue{
			Title:           "Zero Search Visibility",
			Description:     "Your website is not appearing in any search results. This could indicate indexing issues or a very new site.",
			Severity:        SeverityCritical,
			Impact:          template.Impact,
			Recommendation:  "1. Check if your site is indexed using 'site:yourdomain.com' in Google\n2. Submit sitemap to Google Search Console\n3. Verify robots.txt isn't blocking crawlers",
			Category:        "visibility",
			DataPoints:      map[string]interface{}{"impressions": 0, "expected_minimum": 100},
			ConfidenceScore: 1.0,
		})
	}

	// CRITICAL: Very low traffic
	if metrics.Clicks < 10 && metrics.Impressions > 100 {
		template := a.knowledgeBase.IssueTemplates["low_traffic"]
		issues = append(issues, SEOIssue{
			Title:           "Critically Low Organic Traffic",
			Description:     fmt.Sprintf("Your site received only %d clicks despite %d impressions. Users are seeing your site but not clicking.", metrics.Clicks, metrics.Impressions),
			Severity:        SeverityCritical,
			Impact:          "You're missing nearly all potential organic traffic. At current rates, you're losing hundreds of potential visitors monthly.",
			Recommendation:  template.Recommendation,
			Category:        "traffic",
			DataPoints:      map[string]interface{}{"clicks": metrics.Clicks, "impressions": metrics.Impressions, "threshold": 10},
			ConfidenceScore: 0.95,
		})
	} else if metrics.Clicks < 100 && metrics.Impressions > 0 {
		template := a.knowledgeBase.IssueTemplates["low_traffic"]
		issues = append(issues, SEOIssue{
			Title:           template.Title,
			Description:     fmt.Sprintf("Your site receives only %d monthly clicks. Most healthy sites get 100+ clicks per month.", metrics.Clicks),
			Severity:        SeverityHigh,
			Impact:          template.Impact,
			Recommendation:  template.Recommendation,
			Category:        "traffic",
			DataPoints:      map[string]interface{}{"clicks": metrics.Clicks, "threshold": 100},
			ConfidenceScore: 0.9,
		})
	}

	// HIGH: Poor CTR compared to benchmark
	ctrPct := metrics.CTR * 100
	if metrics.Impressions > 100 && ctrPct < benchmarks.AvgCTR*0.7 { // 30% below benchmark
		template := a.knowledgeBase.IssueTemplates["poor_ctr"]
		gap := benchmarks.AvgCTR - ctrPct
		confidence := math.Min(0.95, gap/benchmarks.AvgCTR)

		issues = append(issues, SEOIssue{
			Title:           template.Title,
			Description:     fmt.Sprintf("Your CTR of %.2f%% is below the industry average of %.2f%%. This means %d fewer clicks per 1000 impressions.", ctrPct, benchmarks.AvgCTR, int(gap*10)),
			Severity:        SeverityHigh,
			Impact:          fmt.Sprintf("You're losing approximately %d potential visitors monthly due to poor click-through rates.", int(float64(metrics.Impressions)*gap/100)),
			Recommendation:  "1. Rewrite meta titles with power words (Ultimate, Essential, Complete)\n2. Add emotional triggers to meta descriptions\n3. Use schema markup for rich snippets",
			Category:        "engagement",
			DataPoints:      map[string]interface{}{"current_ctr": ctrPct, "benchmark_ctr": benchmarks.AvgCTR, "gap": gap},
			ConfidenceScore: confidence,
		})
	}

	// HIGH: Poor rankings
	if metrics.AvgPosition > 20 {
		template := a.knowledgeBase.IssueTemplates["high_position"]
		issues = append(issues, SEOIssue{
			Title:           template.Title,
			Description:     fmt.Sprintf("Your average position is %.1f, which means you're on page 2-3 of search results. 92%% of clicks go to page 1.", metrics.AvgPosition),
			Severity:        SeverityHigh,
			Impact:          template.Impact,
			Recommendation:  "1. Improve content depth and quality\n2. Build high-quality backlinks\n3. Optimize for featured snippets\n4. Improve page speed and Core Web Vitals",
			Category:        "visibility",
			DataPoints:      map[string]interface{}{"current_position": metrics.AvgPosition, "target_position": 10},
			ConfidenceScore: 0.85,
		})
	} else if metrics.AvgPosition > 10 && metrics.AvgPosition <= 20 {
		issues = append(issues, SEOIssue{
			Title:           "Second Page Rankings",
			Description:     fmt.Sprintf("Your average position of %.1f puts you on page 2. Page 2 gets less than 6%% of all search clicks.", metrics.AvgPosition),
			Severity:        SeverityMedium,
			Impact:          "You're visible but missing out on significant traffic by not being on page 1.",
			Recommendation:  "Focus on building 5-10 quality backlinks and updating content with more comprehensive information.",
			Category:        "visibility",
			DataPoints:      map[string]interface{}{"current_position": metrics.AvgPosition, "target_position": 10},
			ConfidenceScore: 0.8,
		})
	}

	// MEDIUM: Traffic declining
	if metrics.ClicksChange < -20 {
		template := a.knowledgeBase.IssueTemplates["declining_traffic"]
		issues = append(issues, SEOIssue{
			Title:           template.Title,
			Description:     fmt.Sprintf("Your organic traffic dropped by %.1f%% compared to the previous period.", math.Abs(metrics.ClicksChange)),
			Severity:        SeverityHigh,
			Impact:          template.Impact,
			Recommendation:  "1. Check Google Search Console for manual actions\n2. Review recent algorithm updates\n3. Audit recently changed pages\n4. Monitor competitor activity",
			Category:        "traffic",
			DataPoints:      map[string]interface{}{"change_percent": metrics.ClicksChange},
			ConfidenceScore: 0.9,
		})
	} else if metrics.ClicksChange < -10 {
		issues = append(issues, SEOIssue{
			Title:           "Traffic Showing Decline",
			Description:     fmt.Sprintf("Your organic traffic decreased by %.1f%% compared to the previous period.", math.Abs(metrics.ClicksChange)),
			Severity:        SeverityMedium,
			Impact:          "Minor traffic decline that should be monitored.",
			Recommendation:  "Monitor trends over the next 2 weeks and investigate if decline continues.",
			Category:        "traffic",
			DataPoints:      map[string]interface{}{"change_percent": metrics.ClicksChange},
			ConfidenceScore: 0.7,
		})
	}

	return issues
}

// detectPatterns detects patterns in the metrics data
func (a *RAGAnalyzer) detectPatterns(metrics *SEOMetrics) []SEOPattern {
	var patterns []SEOPattern

	// Pattern: Significant traffic drop
	if metrics.ClicksChange < -30 {
		patterns = append(patterns, SEOPattern{
			PatternType:     PatternTrafficDrop,
			Confidence:      math.Min(0.95, math.Abs(metrics.ClicksChange)/100*2),
			AffectedMetrics: []string{"clicks", "impressions"},
			TimeRange:       &TimeRange{Start: time.Now().AddDate(0, 0, -30), End: time.Now()},
			Severity:        SeverityHigh,
			Evidence:        map[string]interface{}{"change_rate": metrics.ClicksChange},
		})
	}

	// Pattern: Ranking issues
	if metrics.AvgPosition > 30 {
		patterns = append(patterns, SEOPattern{
			PatternType:     PatternRankingIssues,
			Confidence:      0.85,
			AffectedMetrics: []string{"position", "visibility"},
			TimeRange:       &TimeRange{Start: time.Now().AddDate(0, 0, -30), End: time.Now()},
			Severity:        SeverityCritical,
			Evidence:        map[string]interface{}{"avg_position": metrics.AvgPosition},
		})
	}

	// Pattern: Content decay (gradual decline over time)
	if metrics.ImpressionsChange < -10 && metrics.ImpressionsChange > -30 {
		patterns = append(patterns, SEOPattern{
			PatternType:     PatternContentDecay,
			Confidence:      0.75,
			AffectedMetrics: []string{"impressions", "position"},
			TimeRange:       &TimeRange{Start: time.Now().AddDate(0, 0, -90), End: time.Now()},
			Severity:        SeverityMedium,
			Evidence:        map[string]interface{}{"impressions_change": metrics.ImpressionsChange},
		})
	}

	// Pattern: High volatility in position
	if math.Abs(metrics.PositionChange) > 5 {
		patterns = append(patterns, SEOPattern{
			PatternType:     PatternHighVolatility,
			Confidence:      0.7,
			AffectedMetrics: []string{"position"},
			TimeRange:       &TimeRange{Start: time.Now().AddDate(0, 0, -14), End: time.Now()},
			Severity:        SeverityMedium,
			Evidence:        map[string]interface{}{"position_change": metrics.PositionChange},
		})
	}

	return patterns
}

// sortIssuesByImpact sorts issues by severity and confidence
func (a *RAGAnalyzer) sortIssuesByImpact(issues []SEOIssue) {
	severityOrder := map[IssueSeverity]int{
		SeverityCritical: 0,
		SeverityHigh:     1,
		SeverityMedium:   2,
		SeverityLow:      3,
	}

	// Bubble sort by severity then confidence
	for i := 0; i < len(issues)-1; i++ {
		for j := i + 1; j < len(issues); j++ {
			iRank := severityOrder[issues[i].Severity]
			jRank := severityOrder[issues[j].Severity]

			// Sort by severity first, then by confidence
			if jRank < iRank || (jRank == iRank && issues[j].ConfidenceScore > issues[i].ConfidenceScore) {
				issues[i], issues[j] = issues[j], issues[i]
			}
		}
	}
}

// Pattern helper functions
func (a *RAGAnalyzer) patternToTitle(pt PatternType) string {
	titles := map[PatternType]string{
		PatternTrafficDrop:     "Significant Traffic Decline Detected",
		PatternAlgorithmUpdate: "Possible Algorithm Impact",
		PatternTechnicalIssue:  "Technical SEO Problems",
		PatternContentDecay:    "Content Performance Decay",
		PatternSeasonalTrend:   "Seasonal Traffic Pattern",
		PatternCompetitorSurge: "Competitive Pressure Increasing",
		PatternHighVolatility:  "Unstable Performance Metrics",
		PatternRankingIssues:   "Critical Ranking Problems",
	}
	if title, ok := titles[pt]; ok {
		return title
	}
	return "Performance Issue Detected"
}

func (a *RAGAnalyzer) patternToDescription(pt PatternType, evidence map[string]interface{}) string {
	evidenceJSON, _ := json.Marshal(evidence)
	descriptions := map[PatternType]string{
		PatternTrafficDrop:     "Your traffic has dropped significantly, indicating a potential issue that needs immediate attention.",
		PatternAlgorithmUpdate: "Your metrics suggest possible impact from a Google algorithm update.",
		PatternTechnicalIssue:  "Technical problems may be preventing your site from performing optimally.",
		PatternContentDecay:    "Your content is showing signs of decay - freshness and updates are needed.",
		PatternSeasonalTrend:   "This appears to be a seasonal pattern in your traffic.",
		PatternCompetitorSurge: "Competitors may be outranking you with new or improved content.",
		PatternHighVolatility:  "Your rankings are fluctuating significantly, indicating instability.",
		PatternRankingIssues:   fmt.Sprintf("Critical ranking issues detected. Evidence: %s", string(evidenceJSON)),
	}
	if desc, ok := descriptions[pt]; ok {
		return desc
	}
	return "Issue detected in your SEO performance."
}

func (a *RAGAnalyzer) patternToImpact(pt PatternType) string {
	impacts := map[PatternType]string{
		PatternTrafficDrop:     "Lost traffic directly impacts potential customers and revenue.",
		PatternAlgorithmUpdate: "Algorithm changes can significantly affect your search visibility.",
		PatternTechnicalIssue:  "Technical issues prevent proper indexing and ranking of your pages.",
		PatternContentDecay:    "Outdated content loses relevance and rankings over time.",
		PatternSeasonalTrend:   "Seasonal patterns affect traffic predictability but are normal.",
		PatternCompetitorSurge: "Increased competition requires content and SEO improvements.",
		PatternHighVolatility:  "Unstable rankings make traffic prediction difficult.",
		PatternRankingIssues:   "Poor rankings mean your content isn't reaching potential visitors.",
	}
	if impact, ok := impacts[pt]; ok {
		return impact
	}
	return "May affect your SEO performance."
}

func (a *RAGAnalyzer) patternToRecommendation(pt PatternType) string {
	recommendations := map[PatternType]string{
		PatternTrafficDrop:     "Audit recent changes, check for technical issues, and review competitor activity.",
		PatternAlgorithmUpdate: "Review Google's recent updates and adjust content strategy accordingly.",
		PatternTechnicalIssue:  "Run a technical SEO audit and fix crawl errors in Search Console.",
		PatternContentDecay:    "Update and refresh your top-performing content with new information.",
		PatternSeasonalTrend:   "Plan content strategy around seasonal patterns for your industry.",
		PatternCompetitorSurge: "Analyze competitor content and improve your content depth and quality.",
		PatternHighVolatility:  "Improve content quality and build consistent backlink growth.",
		PatternRankingIssues:   "Focus on comprehensive content improvements and quality backlinks.",
	}
	if rec, ok := recommendations[pt]; ok {
		return rec
	}
	return "Review and optimize based on SEO best practices."
}

func (a *RAGAnalyzer) patternToCategory(pt PatternType) string {
	categories := map[PatternType]string{
		PatternTrafficDrop:     "traffic",
		PatternAlgorithmUpdate: "algorithm",
		PatternTechnicalIssue:  "technical",
		PatternContentDecay:    "content",
		PatternSeasonalTrend:   "seasonal",
		PatternCompetitorSurge: "competition",
		PatternHighVolatility:  "stability",
		PatternRankingIssues:   "visibility",
	}
	if cat, ok := categories[pt]; ok {
		return cat
	}
	return "general"
}

// GetSEOContext returns SEO best practices context for AI (1:1 with Python)
func GetSEOContext() string {
	return `
SEO Best Practices Knowledge Base (2024 Standards):

1. TRAFFIC ANALYSIS:
- Healthy sites show consistent growth in organic traffic
- Sudden drops (>20%) indicate potential penalties or technical issues
- CTR below 2% suggests poor meta descriptions or titles

2. POSITION METRICS:
- Average position > 20 means poor visibility
- Position improvements correlate with content quality
- Positions 1-3 get 60% of clicks

3. CTR BENCHMARKS BY POSITION (2024):
- Position 1: 27.6% CTR
- Position 2: 15.8% CTR
- Position 3: 11.0% CTR
- Position 4-10: 2-8% CTR
- Below Position 10: <2% CTR

4. TECHNICAL SEO:
- Page speed affects rankings (Core Web Vitals)
- Mobile-friendliness is crucial (60%+ traffic is mobile)
- HTTPS is a ranking factor

5. CONTENT ISSUES:
- Thin content (<300 words) ranks poorly
- Missing meta descriptions hurt CTR
- Duplicate content causes ranking issues

6. RECOVERY TIMEFRAMES:
- Technical fixes: 1-2 weeks
- Content improvements: 2-8 weeks
- Penalty recovery: 3-6 months
- Brand building: 6-12 months
`
}

// FormatIssuesForChat formats issues for chat context injection
func FormatIssuesForChat(issues []SEOIssue) string {
	if len(issues) == 0 {
		return "No critical SEO issues detected."
	}

	var sb strings.Builder
	sb.WriteString("Current SEO Issues:\n\n")

	for i, issue := range issues {
		sb.WriteString(fmt.Sprintf("%d. [%s] %s\n", i+1, strings.ToUpper(string(issue.Severity)), issue.Title))
		sb.WriteString(fmt.Sprintf("   Description: %s\n", issue.Description))
		sb.WriteString(fmt.Sprintf("   Impact: %s\n", issue.Impact))
		sb.WriteString(fmt.Sprintf("   Recommendation: %s\n\n", issue.Recommendation))
	}

	return sb.String()
}
