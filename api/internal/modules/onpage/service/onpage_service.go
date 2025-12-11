package service

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/firecrawl"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/repository"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
)

// OnPageService handles on-page SEO analysis business logic
type OnPageService struct {
	repo            repository.OnPageRepository
	firecrawlClient *firecrawl.Client
	contentAnalyzer *ContentAnalyzer
}

// NewOnPageService creates a new on-page service
func NewOnPageService(
	repo repository.OnPageRepository,
	firecrawlClient *firecrawl.Client,
) *OnPageService {
	return &OnPageService{
		repo:            repo,
		firecrawlClient: firecrawlClient,
		contentAnalyzer: NewContentAnalyzer(),
	}
}

// AnalyzePage analyzes a single page
func (s *OnPageService) AnalyzePage(ctx context.Context, userEmail, url string) (*domain.PageAnalysis, error) {
	// Create initial analysis record
	analysis := &domain.PageAnalysis{
		UserEmail: userEmail,
		URL:       url,
		Status:    domain.AnalysisStatusPending,
		Score:     0,
		CreatedAt: time.Now(),
	}

	if err := s.repo.CreateAnalysis(ctx, analysis); err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	// Process analysis asynchronously
	go s.processAnalysis(context.Background(), analysis.ID, userEmail, url)

	return analysis, nil
}

// processAnalysis performs the actual analysis
func (s *OnPageService) processAnalysis(ctx context.Context, analysisID int64, userEmail, url string) {
	// Update status to processing
	_ = s.repo.UpdateAnalysisStatus(ctx, analysisID, domain.AnalysisStatusProcessing)

	// Scrape the page
	startTime := time.Now()
	scrapeResp, err := s.firecrawlClient.Scrape(ctx, url)
	loadTime := int(time.Since(startTime).Milliseconds())

	if err != nil {
		_ = s.repo.UpdateAnalysisError(ctx, analysisID, "Failed to scrape page: "+err.Error())
		return
	}

	if !scrapeResp.Success {
		_ = s.repo.UpdateAnalysisError(ctx, analysisID, "Scrape failed")
		return
	}

	// Extract page data
	pageData := s.extractPageData(scrapeResp, loadTime)

	// Save page data
	if err := s.repo.SavePageData(ctx, analysisID, pageData); err != nil {
		_ = s.repo.UpdateAnalysisError(ctx, analysisID, "Failed to save page data")
		return
	}

	// Analyze and detect issues
	issues := s.detectIssues(analysisID, url, pageData, &scrapeResp.Data.Metadata)

	// Save issues
	if len(issues) > 0 {
		_ = s.repo.SaveIssues(ctx, issues)
	}

	// Calculate score
	score := s.calculateScore(pageData, issues)

	// Update analysis with score
	_ = s.repo.UpdateAnalysisScore(ctx, analysisID, score)
	_ = s.repo.UpdateAnalysisStatus(ctx, analysisID, domain.AnalysisStatusCompleted)

	// Cleanup old analyses
	_ = s.repo.DeleteOldAnalyses(ctx, userEmail, 50)
}

// extractPageData extracts SEO-relevant data from scraped content
func (s *OnPageService) extractPageData(resp *firecrawl.ScrapeResponse, loadTime int) *domain.PageData {
	meta := resp.Data.Metadata
	content := resp.Data.Markdown

	// Count words
	words := strings.Fields(content)
	wordCount := len(words)

	// Count headings (approximate from markdown)
	h2Count := strings.Count(content, "\n## ")
	h3Count := strings.Count(content, "\n### ")

	// Count images (from markdown ![...](...)
	imgRegex := regexp.MustCompile(`!\[([^\]]*)\]\([^)]+\)`)
	images := imgRegex.FindAllStringSubmatch(content, -1)
	imageCount := len(images)
	imagesWithAlt := 0
	for _, img := range images {
		if len(img) > 1 && strings.TrimSpace(img[1]) != "" {
			imagesWithAlt++
		}
	}

	// Count links (from markdown [...](...)
	linkRegex := regexp.MustCompile(`\[([^\]]+)\]\(([^)]+)\)`)
	links := linkRegex.FindAllStringSubmatch(content, -1)
	internalLinks := 0
	externalLinks := 0
	for _, link := range links {
		if len(link) > 2 {
			href := link[2]
			if strings.HasPrefix(href, "http") && !strings.Contains(href, meta.SourceURL) {
				externalLinks++
			} else {
				internalLinks++
			}
		}
	}

	// Extract H1 (first # heading in markdown)
	h1 := ""
	h1Regex := regexp.MustCompile(`(?m)^# (.+)$`)
	if match := h1Regex.FindStringSubmatch(content); len(match) > 1 {
		h1 = match[1]
	}

	// Generate content hash
	hash := sha256.Sum256([]byte(content))
	contentHash := hex.EncodeToString(hash[:8])

	return &domain.PageData{
		Title:         meta.Title,
		Description:   meta.Description,
		H1:            h1,
		H2Count:       h2Count,
		H3Count:       h3Count,
		WordCount:     wordCount,
		ImageCount:    imageCount,
		ImagesWithAlt: imagesWithAlt,
		InternalLinks: internalLinks,
		ExternalLinks: externalLinks,
		HasCanonical:  true, // Firecrawl doesn't expose this directly
		HasRobots:     meta.Robots != "",
		HasOpenGraph:  meta.OGTitle != "" || meta.OGDescription != "",
		HasSchema:     false, // Would need HTML parsing for structured data
		LoadTimeMs:    loadTime,
		ContentHash:   contentHash,
	}
}

// detectIssues analyzes page data and detects SEO issues
func (s *OnPageService) detectIssues(analysisID int64, url string, data *domain.PageData, meta *firecrawl.Metadata) []domain.SEOIssue {
	var issues []domain.SEOIssue

	// Title issues
	if data.Title == "" {
		issues = append(issues, domain.SEOIssue{
			AnalysisID:  analysisID,
			Severity:    "critical",
			Category:    "title",
			Title:       "Missing Title Tag",
			Description: "The page has no title tag, which is critical for SEO.",
			Suggestion:  "Add a unique, descriptive title tag between 30-60 characters.",
		})
	} else {
		titleLen := len(data.Title)
		if titleLen < domain.MinTitleLength {
			issues = append(issues, domain.SEOIssue{
				AnalysisID:   analysisID,
				Severity:     "warning",
				Category:     "title",
				Title:        "Title Too Short",
				Description:  fmt.Sprintf("Title is %d characters. Recommended: 30-60 characters.", titleLen),
				CurrentValue: data.Title,
				Suggestion:   "Expand your title to include more relevant keywords.",
			})
		} else if titleLen > domain.MaxTitleLength {
			issues = append(issues, domain.SEOIssue{
				AnalysisID:   analysisID,
				Severity:     "warning",
				Category:     "title",
				Title:        "Title Too Long",
				Description:  fmt.Sprintf("Title is %d characters. May be truncated in search results.", titleLen),
				CurrentValue: data.Title,
				Suggestion:   "Shorten title to under 60 characters for full visibility.",
			})
		}
	}

	// Meta description issues
	if data.Description == "" {
		issues = append(issues, domain.SEOIssue{
			AnalysisID:  analysisID,
			Severity:    "critical",
			Category:    "meta",
			Title:       "Missing Meta Description",
			Description: "No meta description found. Search engines may use random page text.",
			Suggestion:  "Add a compelling meta description between 120-160 characters.",
		})
	} else {
		descLen := len(data.Description)
		if descLen < domain.MinDescriptionLength {
			issues = append(issues, domain.SEOIssue{
				AnalysisID:   analysisID,
				Severity:     "warning",
				Category:     "meta",
				Title:        "Meta Description Too Short",
				Description:  fmt.Sprintf("Description is %d characters. Recommended: 120-160.", descLen),
				CurrentValue: data.Description,
				Suggestion:   "Expand description with more details about the page content.",
			})
		} else if descLen > domain.MaxDescriptionLength {
			issues = append(issues, domain.SEOIssue{
				AnalysisID:   analysisID,
				Severity:     "info",
				Category:     "meta",
				Title:        "Meta Description May Be Truncated",
				Description:  fmt.Sprintf("Description is %d characters. May be cut off in results.", descLen),
				CurrentValue: data.Description,
				Suggestion:   "Keep meta description under 160 characters.",
			})
		}
	}

	// H1 issues
	if data.H1 == "" {
		issues = append(issues, domain.SEOIssue{
			AnalysisID:  analysisID,
			Severity:    "critical",
			Category:    "content",
			Title:       "Missing H1 Heading",
			Description: "No H1 heading found. H1 is crucial for page structure.",
			Suggestion:  "Add a single H1 heading that describes the main topic.",
		})
	}

	// Content length
	if data.WordCount < domain.MinWordCount {
		issues = append(issues, domain.SEOIssue{
			AnalysisID:   analysisID,
			Severity:     "warning",
			Category:     "content",
			Title:        "Thin Content",
			Description:  fmt.Sprintf("Page has only %d words. More content helps SEO.", data.WordCount),
			CurrentValue: fmt.Sprintf("%d words", data.WordCount),
			Suggestion:   "Aim for at least 300 words of quality, relevant content.",
		})
	}

	// Image alt text
	if data.ImageCount > 0 && data.ImagesWithAlt < data.ImageCount {
		missingAlt := data.ImageCount - data.ImagesWithAlt
		issues = append(issues, domain.SEOIssue{
			AnalysisID:   analysisID,
			Severity:     "warning",
			Category:     "images",
			Title:        "Images Missing Alt Text",
			Description:  fmt.Sprintf("%d of %d images are missing alt text.", missingAlt, data.ImageCount),
			CurrentValue: fmt.Sprintf("%d/%d have alt", data.ImagesWithAlt, data.ImageCount),
			Suggestion:   "Add descriptive alt text to all images for accessibility and SEO.",
		})
	}

	// Internal linking
	if data.InternalLinks < 3 {
		issues = append(issues, domain.SEOIssue{
			AnalysisID:   analysisID,
			Severity:     "info",
			Category:     "links",
			Title:        "Few Internal Links",
			Description:  fmt.Sprintf("Page has only %d internal links.", data.InternalLinks),
			CurrentValue: fmt.Sprintf("%d links", data.InternalLinks),
			Suggestion:   "Add more internal links to related content.",
		})
	}

	// Open Graph
	if !data.HasOpenGraph {
		issues = append(issues, domain.SEOIssue{
			AnalysisID:  analysisID,
			Severity:    "info",
			Category:    "technical",
			Title:       "Missing Open Graph Tags",
			Description: "No Open Graph tags found for social sharing.",
			Suggestion:  "Add og:title, og:description, and og:image tags.",
		})
	}

	// Load time
	if data.LoadTimeMs > 3000 {
		issues = append(issues, domain.SEOIssue{
			AnalysisID:   analysisID,
			Severity:     "warning",
			Category:     "technical",
			Title:        "Slow Page Load",
			Description:  fmt.Sprintf("Page took %dms to load. Fast pages rank better.", data.LoadTimeMs),
			CurrentValue: fmt.Sprintf("%dms", data.LoadTimeMs),
			Suggestion:   "Optimize images, enable caching, and minimize JavaScript.",
		})
	}

	return issues
}

// calculateScore calculates the overall SEO score
func (s *OnPageService) calculateScore(data *domain.PageData, issues []domain.SEOIssue) float64 {
	score := 100.0

	// Deduct for issues
	for _, issue := range issues {
		switch issue.Severity {
		case "critical":
			score -= 15
		case "warning":
			score -= 8
		case "info":
			score -= 3
		}
	}

	// Bonus points for good practices
	if data.WordCount >= domain.OptimalWordCount {
		score += 5
	}
	if data.HasOpenGraph {
		score += 3
	}
	if data.ImageCount > 0 && data.ImagesWithAlt == data.ImageCount {
		score += 5
	}
	if data.InternalLinks >= 5 {
		score += 3
	}

	// Clamp score
	if score < 0 {
		score = 0
	}
	if score > 100 {
		score = 100
	}

	return score
}

// GetAnalysis retrieves an analysis by ID
func (s *OnPageService) GetAnalysis(ctx context.Context, id int64, userEmail string) (*domain.AnalysisResult, error) {
	analysis, err := s.repo.GetAnalysis(ctx, id)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if analysis == nil {
		return nil, apperrors.NotFoundError("Analysis", fmt.Sprintf("%d", id))
	}

	if analysis.UserEmail != userEmail {
		return nil, apperrors.ForbiddenError("Access denied")
	}

	pageData, _ := s.repo.GetPageData(ctx, id)
	issues, _ := s.repo.GetIssuesByAnalysis(ctx, id)

	return &domain.AnalysisResult{
		Analysis: analysis,
		PageData: pageData,
		Issues:   issues,
	}, nil
}

// GetAnalysisHistory retrieves analysis history
func (s *OnPageService) GetAnalysisHistory(ctx context.Context, userEmail string, limit int) ([]domain.PageAnalysis, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}

	analyses, err := s.repo.GetAnalysesByUser(ctx, userEmail, limit)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return analyses, nil
}

// MapSite maps all URLs on a site
func (s *OnPageService) MapSite(ctx context.Context, userEmail, siteURL string, limit int) (*domain.SiteMapResult, error) {
	if limit <= 0 || limit > 100 {
		limit = 50
	}

	mapResp, err := s.firecrawlClient.MapSite(ctx, siteURL, limit)
	if err != nil {
		return nil, apperrors.ExternalServiceError("Firecrawl", err)
	}

	return &domain.SiteMapResult{
		UserEmail: userEmail,
		SiteURL:   siteURL,
		URLs:      mapResp.Links,
		Total:     len(mapResp.Links),
		ScannedAt: time.Now(),
	}, nil
}

// CrawlWebsite performs comprehensive website analysis (1:1 with Python website_crawler.py)
// This method fetches the page, analyzes content, and returns business context
func (s *OnPageService) CrawlWebsite(ctx context.Context, websiteURL string) (*domain.WebsiteAnalysis, error) {
	// Ensure proper URL format
	if !strings.HasPrefix(websiteURL, "http://") && !strings.HasPrefix(websiteURL, "https://") {
		websiteURL = "https://" + websiteURL
	}

	// Scrape the main page
	scrapeResp, err := s.firecrawlClient.Scrape(ctx, websiteURL)
	if err != nil {
		return s.getFallbackAnalysis(websiteURL), nil
	}

	if !scrapeResp.Success {
		return s.getFallbackAnalysis(websiteURL), nil
	}

	// Extract metadata
	meta := scrapeResp.Data.Metadata
	content := scrapeResp.Data.Markdown

	// Perform content analysis using the analyzer
	contentAnalysis := s.contentAnalyzer.AnalyzeContent(content, websiteURL)

	// Extract tech stack from content
	techStack := s.detectTechStack(content)

	// Extract social links from markdown
	socialLinks := s.extractSocialLinks(content)

	// Extract contact info
	contactInfo := s.extractContactInfo(content)

	// Get internal links via site mapping
	var internalLinks []string
	mapResp, mapErr := s.firecrawlClient.MapSite(ctx, websiteURL, 10)
	if mapErr == nil && mapResp.Success {
		internalLinks = mapResp.Links
	}

	return &domain.WebsiteAnalysis{
		URL:             websiteURL,
		CrawledAt:       time.Now(),
		Title:           meta.Title,
		MetaDescription: meta.Description,
		ContentSummary:  s.extractContentSummary(content),
		ContentAnalysis: contentAnalysis,
		PageCount:       1,
		InternalLinks:   internalLinks,
		TechStack:       techStack,
		SocialLinks:     socialLinks,
		ContactInfo:     contactInfo,
	}, nil
}

// getFallbackAnalysis provides fallback when crawling fails
func (s *OnPageService) getFallbackAnalysis(websiteURL string) *domain.WebsiteAnalysis {
	// Extract hostname for basic analysis
	hostname := websiteURL
	if strings.Contains(websiteURL, "://") {
		parts := strings.Split(websiteURL, "://")
		if len(parts) > 1 {
			hostname = strings.Split(parts[1], "/")[0]
		}
	}

	// Estimate business type from domain
	businessType := "general_business"
	hostnameLower := strings.ToLower(hostname)
	if strings.Contains(hostnameLower, "tech") || strings.Contains(hostnameLower, "dev") || strings.Contains(hostnameLower, "soft") {
		businessType = "technology_business"
	} else if strings.Contains(hostnameLower, "shop") || strings.Contains(hostnameLower, "store") {
		businessType = "ecommerce_business"
	}

	location := "Not specified"
	if strings.Contains(hostnameLower, ".sg") {
		location = "Singapore"
	}

	return &domain.WebsiteAnalysis{
		URL:             websiteURL,
		CrawledAt:       time.Now(),
		Title:           "Website at " + hostname,
		MetaDescription: "",
		ContentSummary:  "Unable to crawl " + websiteURL + " directly. Business type estimated based on domain analysis.",
		ContentAnalysis: &domain.ContentAnalysis{
			BusinessType: businessType,
			Keywords:     []string{},
			Services:     []string{},
			Location:     location,
			Summary:      fmt.Sprintf("Fallback analysis for %s. Business type: %s.", hostname, businessType),
		},
		PageCount: 0,
	}
}

// extractContentSummary extracts first 500 words from content
func (s *OnPageService) extractContentSummary(content string) string {
	words := strings.Fields(content)
	if len(words) > 500 {
		words = words[:500]
	}
	return strings.Join(words, " ")
}

// detectTechStack detects technology stack from content
func (s *OnPageService) detectTechStack(content string) []string {
	var techStack []string
	contentLower := strings.ToLower(content)

	techIndicators := map[string]string{
		"wp-content":  "WordPress",
		"wordpress":   "WordPress",
		"react":       "React",
		"vue":         "Vue.js",
		"angular":     "Angular",
		"bootstrap":   "Bootstrap",
		"tailwind":    "Tailwind CSS",
		"next.js":     "Next.js",
		"gatsby":      "Gatsby",
		"shopify":     "Shopify",
		"woocommerce": "WooCommerce",
	}

	for indicator, tech := range techIndicators {
		if strings.Contains(contentLower, indicator) {
			techStack = append(techStack, tech)
		}
	}

	// Deduplicate
	seen := make(map[string]bool)
	unique := make([]string, 0)
	for _, tech := range techStack {
		if !seen[tech] {
			seen[tech] = true
			unique = append(unique, tech)
		}
	}

	if len(unique) > 5 {
		unique = unique[:5]
	}
	return unique
}

// extractSocialLinks extracts social media links from content
func (s *OnPageService) extractSocialLinks(content string) []string {
	socialDomains := []string{
		"facebook.com", "twitter.com", "linkedin.com",
		"instagram.com", "youtube.com", "github.com",
	}

	linkRegex := regexp.MustCompile(`https?://[^\s\)]+`)
	links := linkRegex.FindAllString(content, -1)

	var socialLinks []string
	for _, link := range links {
		for _, domain := range socialDomains {
			if strings.Contains(link, domain) {
				socialLinks = append(socialLinks, link)
				break
			}
		}
	}

	// Deduplicate and limit
	seen := make(map[string]bool)
	unique := make([]string, 0)
	for _, link := range socialLinks {
		if !seen[link] {
			seen[link] = true
			unique = append(unique, link)
		}
	}

	if len(unique) > 5 {
		unique = unique[:5]
	}
	return unique
}

// extractContactInfo extracts contact information from content
func (s *OnPageService) extractContactInfo(content string) map[string]string {
	contact := make(map[string]string)

	// Extract email
	emailRegex := regexp.MustCompile(`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`)
	emails := emailRegex.FindAllString(content, -1)
	if len(emails) > 0 {
		contact["email"] = emails[0]
	}

	// Extract phone (simplified pattern)
	phoneRegex := regexp.MustCompile(`[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}`)
	phones := phoneRegex.FindAllString(content, -1)
	for _, phone := range phones {
		// Only include if it looks like a real phone number (at least 8 digits)
		digits := regexp.MustCompile(`\d`).FindAllString(phone, -1)
		if len(digits) >= 8 {
			contact["phone"] = phone
			break
		}
	}

	return contact
}
