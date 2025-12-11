package utils

import "strings"

// IndustryType represents the detected industry type
type IndustryType string

const (
	IndustryEcommerce     IndustryType = "e-commerce"
	IndustrySaaS          IndustryType = "saas"
	IndustryBlog          IndustryType = "blog"
	IndustryLocalBusiness IndustryType = "local_business"
	IndustryDefault       IndustryType = "default"
)

// DetectIndustryFromURL detects industry from website URL (1:1 with Python detect_industry_from_url)
func DetectIndustryFromURL(websiteURL string) IndustryType {
	urlLower := strings.ToLower(websiteURL)

	// E-commerce indicators
	ecommerceKeywords := []string{"shop", "store", "buy", "cart", "product"}
	for _, keyword := range ecommerceKeywords {
		if strings.Contains(urlLower, keyword) {
			return IndustryEcommerce
		}
	}

	// SaaS indicators
	saasKeywords := []string{"saas", "software", "app", "platform", "tool"}
	for _, keyword := range saasKeywords {
		if strings.Contains(urlLower, keyword) {
			return IndustrySaaS
		}
	}

	// Blog/content indicators
	blogKeywords := []string{"blog", "news", "article", "content", "media"}
	for _, keyword := range blogKeywords {
		if strings.Contains(urlLower, keyword) {
			return IndustryBlog
		}
	}

	// Local business indicators
	localKeywords := []string{"local", "restaurant", "service", "clinic", "lawyer"}
	for _, keyword := range localKeywords {
		if strings.Contains(urlLower, keyword) {
			return IndustryLocalBusiness
		}
	}

	return IndustryDefault
}

// GetIndustryPromptContext returns industry-specific context for AI prompts (1:1 with Python)
func GetIndustryPromptContext(industry IndustryType) string {
	switch industry {
	case IndustryEcommerce:
		return `E-commerce website context:
- Focus on product pages, category optimization, and conversion metrics
- Key metrics: product impressions, click-through rates, shopping intent keywords
- Common issues: duplicate product descriptions, thin category content, missing schema markup`

	case IndustrySaaS:
		return `SaaS/Software website context:
- Focus on feature pages, pricing, and documentation SEO
- Key metrics: feature-related searches, comparison keywords, documentation traffic
- Common issues: thin landing pages, poor internal linking, missing technical content`

	case IndustryBlog:
		return `Blog/Content website context:
- Focus on article optimization, topic clusters, and content freshness
- Key metrics: organic traffic, time on page, featured snippet opportunities
- Common issues: keyword cannibalization, outdated content, thin articles`

	case IndustryLocalBusiness:
		return `Local business website context:
- Focus on local SEO, Google Business Profile, and location-based optimization
- Key metrics: local search impressions, map pack visibility, local keywords
- Common issues: NAP consistency, missing local schema, poor local content`

	default:
		return `General website context:
- Focus on overall SEO health, technical issues, and content quality
- Key metrics: impressions, clicks, CTR, average position
- Common issues: indexing problems, poor mobile experience, slow page speed`
	}
}
