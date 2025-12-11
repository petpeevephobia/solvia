package pdf

import (
	"fmt"
	"math/rand"
	"time"
)

func init() {
	rand.Seed(time.Now().UnixNano())
}

// ============================================================================
// 1. SEO STAGE DESCRIPTIONS (1:1 with Python)
// ============================================================================

var StageDescriptions = map[string]string{
	"hidden":       "Your site is still hidden from most search results. Let's work on visibility by improving content and indexing.",
	"emerging":     "Your site is starting to gain visibility. Continue building quality content and improving technical SEO.",
	"discoverable": "Your site is becoming more discoverable. Focus on optimizing top-performing pages and expanding keyword coverage.",
	"trusted":      "Your site has strong search visibility. Maintain quality and explore new growth opportunities.",
}

// ============================================================================
// 2. MOTIVATIONAL QUOTES - PAGE 1 (1:1 with Python)
// ============================================================================

var MotivationalQuotesPage1 = map[string]string{
	"hidden":       "It's okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built.",
	"emerging":     "Visibility is growing. Each impression is a step toward discovery.",
	"discoverable": "You're building momentum. Consistency will accelerate your growth.",
	"trusted":      "You've established authority. Now focus on expanding your reach.",
}

// ============================================================================
// 3. MOTIVATIONAL QUOTES - PAGE 2 (1:1 with Python)
// ============================================================================

var MotivationalQuotesPage2 = map[string]string{
	"hidden":       "Your next step is clarity. Make Google's job easier by showing it what each page is about. That's how visibility starts to grow.",
	"emerging":     "Focus on content quality and consistency. Each piece of content builds your authority.",
	"discoverable": "Optimize your top performers. Small improvements compound into significant gains.",
	"trusted":      "Maintain your momentum while exploring new opportunities and keywords.",
}

// ============================================================================
// RANDOM MOTIVATIONAL QUOTES DATABASE (1:1 with Python pdf_data_processor.py:83-112)
// 5 quotes per stage with random selection
// ============================================================================

var MotivationalQuotesRandom = map[string][]string{
	"hidden": {
		"It's okay to be early! Every great site starts in the shadows before it shines. This is where your foundation is built.",
		"Small beginnings lead to great outcomes. Your journey to visibility starts here.",
		"Building visibility takes time. Every page you optimize brings you closer to discovery.",
		"Rome wasn't built in a day, and neither is SEO success. You're laying the groundwork.",
		"The fact that you're measuring means you're already ahead of most. Keep going!",
	},
	"emerging": {
		"You're on the right path! Consistency is key—keep publishing quality content.",
		"Great progress! Your site is starting to get noticed by search engines.",
		"You're building momentum. Stay focused on your SEO strategy.",
		"Every impression counts. You're moving in the right direction!",
		"Your efforts are paying off. Keep optimizing and watch your visibility grow.",
	},
	"discoverable": {
		"Impressive growth! Your efforts are paying off. Keep optimizing.",
		"You're in a great position. Focus on improving CTR to capture more clicks.",
		"Your visibility is strong. Time to refine and scale your content strategy.",
		"You've hit a sweet spot! Now focus on converting that visibility into clicks.",
		"Solid progress! You're competing on the first page—aim for the top 5.",
	},
	"trusted": {
		"Outstanding performance! You've built real authority in search.",
		"You've achieved excellent visibility. Now focus on maintaining quality.",
		"Your site is a trusted resource. Explore new keyword opportunities to grow further.",
		"Exceptional work! You're at the top. Keep innovating and stay ahead.",
		"You've mastered SEO basics. Time to explore advanced strategies and scale.",
	},
}

// GetRandomMotivationalQuote returns a random quote for the given stage (1:1 with Python random.choice())
func GetRandomMotivationalQuote(stage string) string {
	quotes, ok := MotivationalQuotesRandom[stage]
	if !ok || len(quotes) == 0 {
		quotes = MotivationalQuotesRandom["hidden"]
	}
	return quotes[rand.Intn(len(quotes))]
}

// ============================================================================
// 4. METRIC NOTES - CONDITIONAL TEXT (1:1 with Python)
// ============================================================================

// GetImpressionsNote returns conditional note for Total Impressions metric
func GetImpressionsNote(impressionsChange float64) string {
	if impressionsChange > 0 {
		return "Visibility increasing steadily"
	}
	return "Visibility needs improvement"
}

// GetClicksNote returns conditional note for Total Clicks metric
func GetClicksNote(clicks int, clicksChange float64) string {
	if clicks < 10 {
		return "Good start for early-stage SEO"
	} else if clicks >= 10 && clicksChange > 0 {
		return "Traffic growth is positive"
	} else if clicks >= 10 && clicksChange <= 0 {
		return "Traffic is declining"
	}
	return "Good start for early-stage SEO"
}

// GetCTRNote returns conditional note for Click-Through Rate metric
func GetCTRNote(ctr float64, ctrChange float64) string {
	if ctrChange < 0 {
		return "Slight dip — adjust titles"
	} else if ctrChange >= 0 && ctr < 2 {
		return "Low CTR — optimize meta descriptions"
	} else if ctrChange >= 0 && ctr >= 2 && ctr < 5 {
		return "CTR is improving!"
	} else if ctr >= 5 {
		return "Strong CTR performance"
	}
	return "Monitor CTR trends"
}

// GetPositionNote returns conditional note for Average Position metric
func GetPositionNote(position float64, positionChange float64) string {
	if absFloat64(positionChange) < 1 {
		return "Minor ranking fluctuation"
	} else if positionChange < -1 {
		return "Rankings improving"
	} else if positionChange > 1 {
		return "Rankings declining"
	} else if position > 20 {
		return "Pages appearing beyond page 2"
	}
	return "Minor ranking fluctuation"
}

// GetIndexedPagesNote returns conditional note for Indexed Pages metric
func GetIndexedPagesNote(unindexedCount int, indexedPagesChange int) string {
	if unindexedCount > 0 {
		return fmt.Sprintf("%d unindexed page(s)", unindexedCount)
	} else if unindexedCount == 0 && indexedPagesChange > 0 {
		return "More pages being indexed"
	}
	return "Indexing status stable"
}

// ============================================================================
// 5. NEXT STEPS - CONDITIONAL LOGIC (1:1 with Python)
// ============================================================================

var NextStepsAlways = []string{
	"Add internal links between your existing pages",
	"Generate another report after 14 days of these changes being made to track progress",
}

// GetConditionalNextSteps returns conditional next steps based on metrics
func GetConditionalNextSteps(sitemapSubmitted bool, ctr, avgPosition float64, totalImpressions, unindexedCount, totalClicks int) []string {
	var steps []string

	// Conditional - Sitemap
	if !sitemapSubmitted {
		steps = append(steps, "Submit sitemap to Google Search Console")
	}

	// Conditional - CTR/Position
	if ctr < 5 || avgPosition > 10 {
		steps = append(steps, "Optimize meta titles with emotional, relevant keywords")
	}

	// Conditional - Impressions
	if totalImpressions < 300 {
		steps = append(steps, "Write one blog post per week for the next month")
	}

	// Conditional - Indexing
	if unindexedCount > 0 {
		steps = append(steps, fmt.Sprintf("Fix indexing issues for %d page(s)", unindexedCount))
	}

	// Conditional - Low Traffic
	if totalClicks < 5 {
		steps = append(steps, "Focus on content quality and keyword research")
	}

	// Conditional - Position
	if avgPosition > 20 {
		steps = append(steps, "Improve on-page SEO for better rankings")
	}

	return steps
}

// GetAllNextSteps returns complete next steps list (always shown + conditional)
func GetAllNextSteps(sitemapSubmitted bool, ctr, avgPosition float64, totalImpressions, unindexedCount, totalClicks int) []string {
	// Get conditional steps first (higher priority)
	conditional := GetConditionalNextSteps(sitemapSubmitted, ctr, avgPosition, totalImpressions, unindexedCount, totalClicks)

	// Combine conditional + always shown
	steps := make([]string, 0, len(conditional)+len(NextStepsAlways))
	steps = append(steps, conditional...)
	steps = append(steps, NextStepsAlways...)

	return steps
}

// ============================================================================
// 6. SUMMARY STATEMENT VARIATIONS (1:1 with Python)
// ============================================================================

// GetImpressionsStatement returns impressions statement with conditional ending
func GetImpressionsStatement(impressions int) string {
	base := fmt.Sprintf("Your site appeared in front of **%d** people in Google search results this month", impressions)

	var ending string
	if impressions == 0 {
		ending = " — this means Google hasn't discovered your site yet. Submit your sitemap and check for indexing issues."
	} else if impressions > 0 && impressions < 50 {
		ending = " — that means Google recognizes your presence."
	} else { // impressions >= 50
		ending = " — that means Google recognizes your presence and you're building visibility."
	}

	return base + ending
}

// GetClicksCTRStatement returns clicks & CTR statement with conditional ending
func GetClicksCTRStatement(clicks int, ctr float64) string {
	base := fmt.Sprintf("Out of those impressions, **%d** visitors clicked through, giving you a CTR of **%.2f%%**.", clicks, ctr)

	var ending string
	if ctr < 2 {
		ending = " That's below average — focus on improving your titles and descriptions to increase click-through rates."
	} else if ctr >= 2 && ctr < 5 {
		ending = " That's a good early signal that your content is relevant, but there's still room to grow engagement through sharper titles and descriptions."
	} else { // ctr >= 5
		ending = " That's excellent! Your titles and descriptions are resonating with searchers."
	}

	return base + ending
}

// GetPositionStatement returns position statement with conditional advice
func GetPositionStatement(position float64) string {
	base := fmt.Sprintf("On average, your pages appeared in position **%.1f**", position)

	var ending string
	if position <= 3 {
		ending = ", which means you're ranking on the first page of results. Excellent work! Keep maintaining quality to stay at the top."
	} else if position > 3 && position <= 10 {
		ending = ", which means you're hovering on the first page of results. Getting to the top 3 will take consistency — adding fresh content, improving internal links, and keeping your meta details clear."
	} else if position > 10 && position <= 20 {
		ending = ", which means you're on page 2. Focus on improving on-page SEO and building quality backlinks to reach page 1."
	} else { // position > 20
		ending = ", which means you're beyond page 2. Prioritize technical SEO fixes and content optimization to improve visibility."
	}

	return base + ending
}

// ============================================================================
// 7. PROGRESS BAR LABELS (1:1 with Python)
// ============================================================================

var StageLabels = map[string]string{
	"hidden":       "Hidden",
	"emerging":     "Emerging",
	"discoverable": "Discoverable",
	"trusted":      "Trusted",
}

var ThresholdLabels = map[string]string{
	"hidden":       "1 impression",
	"emerging":     "50 impressions",
	"discoverable": "300 impressions",
	"trusted":      "2000+ impressions",
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// GetStageDescription returns stage description based on SEO stage
func GetStageDescription(stage string) string {
	if desc, ok := StageDescriptions[stage]; ok {
		return desc
	}
	return StageDescriptions["hidden"]
}

// GetMotivationalQuotePage1 returns Page 1 motivational quote based on SEO stage
func GetMotivationalQuotePage1(stage string) string {
	if quote, ok := MotivationalQuotesPage1[stage]; ok {
		return quote
	}
	return MotivationalQuotesPage1["hidden"]
}

// GetMotivationalQuotePage2 returns Page 2 motivational quote based on SEO stage
func GetMotivationalQuotePage2(stage string) string {
	if quote, ok := MotivationalQuotesPage2[stage]; ok {
		return quote
	}
	return MotivationalQuotesPage2["hidden"]
}

// absFloat64 returns absolute value of a float64
func absFloat64(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}
