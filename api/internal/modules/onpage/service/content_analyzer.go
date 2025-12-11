package service

import (
	"regexp"
	"strings"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/domain"
)

// ContentAnalyzer analyzes website content to detect business type and extract keywords
// 1:1 parity with Python's website_crawler.py functionality
type ContentAnalyzer struct {
	// Industry keywords for detection
	industries map[string][]string

	// Personal portfolio indicators
	personalIndicators []string

	// Business indicators
	businessIndicators []string

	// Stop words for keyword extraction
	stopWords map[string]bool
}

// NewContentAnalyzer creates a new content analyzer
func NewContentAnalyzer() *ContentAnalyzer {
	return &ContentAnalyzer{
		industries: map[string][]string{
			"technology":   {"software", "technology", "it services", "development", "programming", "coding", "api", "cloud"},
			"construction": {"construction", "building", "contractor", "renovation", "architecture", "engineering"},
			"healthcare":   {"health", "medical", "clinic", "hospital", "doctor", "patient", "treatment"},
			"education":    {"education", "learning", "school", "university", "course", "training", "student"},
			"ecommerce":    {"shop", "store", "buy", "cart", "product", "price", "checkout", "shipping"},
			"consulting":   {"consulting", "advisory", "strategy", "management", "business solutions"},
			"finance":      {"finance", "investment", "banking", "insurance", "loan", "credit"},
			"marketing":    {"marketing", "advertising", "seo", "digital", "social media", "branding"},
		},
		personalIndicators: []string{
			"portfolio", "resume", "cv", "about me", "my projects",
			"personal", "freelancer", "developer", "designer",
			"software engineer", "web developer", "full-stack",
			"years of experience", "skills", "github", "linkedin",
		},
		businessIndicators: []string{
			"services", "solutions", "products", "pricing",
			"contact us", "our team", "company", "corporation",
			"ltd", "llc", "inc", "pte", "about us",
		},
		stopWords: map[string]bool{
			"the": true, "a": true, "an": true, "and": true, "or": true,
			"but": true, "in": true, "on": true, "at": true, "to": true,
			"for": true, "of": true, "with": true, "by": true, "from": true,
			"about": true, "as": true, "is": true, "was": true, "are": true,
			"were": true, "be": true, "been": true, "being": true, "have": true,
			"has": true, "had": true, "do": true, "does": true, "did": true,
			"will": true, "would": true, "could": true, "should": true, "may": true,
			"might": true, "must": true, "can": true, "this": true, "that": true,
			"these": true, "those": true, "it": true, "its": true, "i": true,
			"you": true, "your": true, "we": true, "our": true, "they": true,
			"their": true, "what": true, "which": true, "who": true, "when": true,
			"where": true, "how": true, "all": true, "each": true, "every": true,
			"both": true, "few": true, "more": true, "most": true, "other": true,
			"some": true, "such": true, "no": true, "nor": true, "not": true,
			"only": true, "own": true, "same": true, "so": true, "than": true,
			"too": true, "very": true, "just": true, "also": true, "now": true,
		},
	}
}

// AnalyzeContent performs comprehensive content analysis
// Returns business type, keywords, and services detected
func (a *ContentAnalyzer) AnalyzeContent(content string, url string) *domain.ContentAnalysis {
	contentLower := strings.ToLower(content)

	// Detect business type
	businessType := a.detectBusinessType(contentLower, url)

	// Extract keywords
	keywords := a.extractKeywords(contentLower)

	// Extract services
	services := a.extractServices(content)

	// Extract location
	location := a.extractLocation(content)

	// Generate summary
	summary := a.generateSummary(businessType, keywords, services, location)

	return &domain.ContentAnalysis{
		BusinessType: businessType,
		Keywords:     keywords,
		Services:     services,
		Location:     location,
		Summary:      summary,
	}
}

// detectBusinessType detects the type of business from content
// 1:1 with Python's _detect_business_type
func (a *ContentAnalyzer) detectBusinessType(content string, url string) string {
	// Count personal indicators
	personalScore := 0
	for _, indicator := range a.personalIndicators {
		if strings.Contains(content, indicator) {
			personalScore++
		}
	}

	// Count business indicators
	businessScore := 0
	for _, indicator := range a.businessIndicators {
		if strings.Contains(content, indicator) {
			businessScore++
		}
	}

	// Detect industry
	detectedIndustry := "general"
	maxIndustryScore := 0

	for industry, keywords := range a.industries {
		score := 0
		for _, keyword := range keywords {
			if strings.Contains(content, keyword) {
				score++
			}
		}
		if score > maxIndustryScore {
			maxIndustryScore = score
			detectedIndustry = industry
		}
	}

	// Determine if personal or business
	if personalScore > businessScore && personalScore > 3 {
		if strings.Contains(content, "developer") || strings.Contains(content, "engineer") || strings.Contains(content, "programmer") {
			return "personal_portfolio_developer"
		} else if strings.Contains(content, "designer") {
			return "personal_portfolio_designer"
		}
		return "personal_portfolio"
	} else if detectedIndustry != "general" {
		return detectedIndustry + "_business"
	}

	return "general_business"
}

// extractKeywords extracts important keywords from content
// 1:1 with Python's _extract_keywords
func (a *ContentAnalyzer) extractKeywords(content string) []string {
	// Extract words
	wordRegex := regexp.MustCompile(`\b[a-z]+\b`)
	words := wordRegex.FindAllString(content, -1)

	// Count word frequency
	wordFreq := make(map[string]int)
	for _, word := range words {
		if len(word) > 3 && !a.stopWords[word] {
			wordFreq[word]++
		}
	}

	// Sort by frequency and get top 20
	type wordCount struct {
		word  string
		count int
	}
	var sorted []wordCount
	for word, count := range wordFreq {
		sorted = append(sorted, wordCount{word, count})
	}

	// Simple bubble sort for top N (good enough for small dataset)
	for i := 0; i < len(sorted)-1; i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[j].count > sorted[i].count {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}

	// Return top 20 keywords
	keywords := make([]string, 0, 20)
	for i := 0; i < len(sorted) && i < 20; i++ {
		keywords = append(keywords, sorted[i].word)
	}

	return keywords
}

// extractServices extracts services or offerings from content
// 1:1 with Python's _extract_services
func (a *ContentAnalyzer) extractServices(content string) []string {
	services := make([]string, 0)
	serviceKeywords := []string{"service", "offer", "provide", "solution", "help"}

	// Split content into sentences
	sentences := regexp.MustCompile(`[.!?]+`).Split(content, -1)

	for _, sentence := range sentences {
		sentence = strings.TrimSpace(sentence)
		if len(sentence) < 5 || len(sentence) > 150 {
			continue
		}

		sentenceLower := strings.ToLower(sentence)
		for _, keyword := range serviceKeywords {
			if strings.Contains(sentenceLower, keyword) {
				// Extract a clean service description
				services = append(services, sentence)
				break
			}
		}

		if len(services) >= 10 {
			break
		}
	}

	return services
}

// extractLocation extracts location information
// 1:1 with Python's _extract_location
func (a *ContentAnalyzer) extractLocation(content string) string {
	contentLower := strings.ToLower(content)
	locations := make([]string, 0)

	// Check for Singapore
	if strings.Contains(contentLower, "singapore") {
		locations = append(locations, "Singapore")
	}

	// Check for major cities
	cities := []string{
		"kuala lumpur", "jakarta", "bangkok", "manila", "hong kong",
		"tokyo", "sydney", "melbourne", "london", "new york",
	}

	for _, city := range cities {
		if strings.Contains(contentLower, city) {
			locations = append(locations, strings.Title(city))
		}
	}

	// Check for address patterns
	addressRegex := regexp.MustCompile(`(?i)\b\d{1,5}\s+\w+\s+(street|road|avenue|lane|drive|place|boulevard)\b`)
	if addressRegex.MatchString(content) {
		locations = append(locations, "Address found")
	}

	if len(locations) > 0 {
		if len(locations) > 3 {
			locations = locations[:3]
		}
		return strings.Join(locations, ", ")
	}

	return "Not specified"
}

// generateSummary generates an intelligent summary
// 1:1 with Python's _generate_summary
func (a *ContentAnalyzer) generateSummary(businessType string, keywords, services []string, location string) string {
	var summary strings.Builder

	if strings.Contains(businessType, "personal_portfolio") {
		summary.WriteString("This is a personal portfolio website. ")
		if strings.Contains(businessType, "developer") {
			summary.WriteString("The site showcases software development skills and projects. ")
		} else if strings.Contains(businessType, "designer") {
			summary.WriteString("The site showcases design work and creative projects. ")
		}
	} else {
		industry := strings.Replace(businessType, "_business", "", 1)
		summary.WriteString("This is a " + industry + " business website. ")
	}

	if location != "Not specified" {
		summary.WriteString("The business appears to be based in " + location + ". ")
	}

	if len(services) > 0 {
		servicesStr := make([]string, 0, 3)
		for i := 0; i < len(services) && i < 3; i++ {
			servicesStr = append(servicesStr, services[i])
		}
		summary.WriteString("Key offerings: " + strings.Join(servicesStr, "; ") + ". ")
	}

	if len(keywords) >= 5 {
		summary.WriteString("Main content themes: " + strings.Join(keywords[:5], ", ") + ".")
	}

	return summary.String()
}
