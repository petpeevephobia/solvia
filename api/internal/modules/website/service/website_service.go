package service

import (
	"context"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"time"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/website/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/website/repository"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
	"golang.org/x/net/html"
)

// WebsiteGetter interface to get user's selected website
type WebsiteGetter interface {
	GetSelectedWebsite(ctx context.Context, userEmail string) (string, error)
}

// WebsiteService handles website content business logic
type WebsiteService struct {
	repo          repository.WebsiteRepository
	websiteGetter WebsiteGetter
	httpClient    *http.Client
}

// NewWebsiteService creates a new website service
func NewWebsiteService(
	repo repository.WebsiteRepository,
	websiteGetter WebsiteGetter,
) *WebsiteService {
	return &WebsiteService{
		repo:          repo,
		websiteGetter: websiteGetter,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// FetchContent fetches website content and stores it (1:1 with Python /website/content/fetch)
func (s *WebsiteService) FetchContent(ctx context.Context, userEmail string) (*domain.WebsiteContent, error) {
	// Get user's selected website
	websiteURL, err := s.websiteGetter.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return nil, apperrors.New(apperrors.CodeValidation, "No website property selected. Please select a property first.", 404)
	}

	// Convert sc-domain format to actual URL if needed
	if strings.HasPrefix(websiteURL, "sc-domain:") {
		domainName := strings.TrimPrefix(websiteURL, "sc-domain:")
		websiteURL = "https://" + domainName
	}

	// Ensure URL has scheme
	if !strings.HasPrefix(websiteURL, "http://") && !strings.HasPrefix(websiteURL, "https://") {
		websiteURL = "https://" + websiteURL
	}

	// Fetch the website
	req, err := http.NewRequestWithContext(ctx, "GET", websiteURL, nil)
	if err != nil {
		return nil, apperrors.ExternalServiceError("HTTP", err)
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (compatible; Solvia/2.0; +https://solvia.app)")

	resp, err := s.httpClient.Do(req)
	if err != nil {
		return nil, apperrors.ExternalServiceError("HTTP", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, apperrors.New(apperrors.CodeExternalService, "Failed to fetch website content. Status: "+resp.Status, 400)
	}

	// Read and parse HTML
	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, apperrors.ExternalServiceError("HTTP", err)
	}

	htmlContent := string(bodyBytes)

	// Parse HTML
	doc, err := html.Parse(strings.NewReader(htmlContent))
	if err != nil {
		return nil, apperrors.ExternalServiceError("HTML Parser", err)
	}

	// Extract content
	content := s.extractContent(doc, websiteURL)
	content.UserEmail = userEmail
	content.WebsiteURL = websiteURL
	content.FetchedAt = time.Now()

	// Store content
	if err := s.repo.SaveContent(ctx, content); err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return content, nil
}

// GetContent retrieves stored website content (1:1 with Python /website/content)
func (s *WebsiteService) GetContent(ctx context.Context, userEmail string) (*domain.WebsiteContent, string, error) {
	// Get user's selected website
	websiteURL, err := s.websiteGetter.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return nil, "", apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return nil, "", apperrors.New(apperrors.CodeValidation, "No website property selected. Please select a property first.", 404)
	}

	content, err := s.repo.GetContent(ctx, userEmail, websiteURL)
	if err != nil {
		return nil, websiteURL, apperrors.DatabaseError(err)
	}

	return content, websiteURL, nil
}

// extractContent extracts SEO-relevant content from HTML
func (s *WebsiteService) extractContent(doc *html.Node, baseURL string) *domain.WebsiteContent {
	content := &domain.WebsiteContent{
		TitleTags:        make(map[string]string),
		MetaDescriptions: make(map[string]string),
		PageContent:      make(map[string]interface{}),
	}

	var headings []domain.Heading
	var links []domain.Link
	var mainContent string
	var headerContent string
	var footerContent string
	var pageTitle string
	var metaDesc string

	// Recursive function to traverse HTML
	var traverse func(*html.Node)
	traverse = func(n *html.Node) {
		if n.Type == html.ElementNode {
			switch n.Data {
			case "title":
				if n.FirstChild != nil {
					text := getTextContent(n)
					pageTitle = strings.TrimSpace(text)
					content.TitleTags["default"] = pageTitle
				}

			case "meta":
				var name, ctnt string
				for _, attr := range n.Attr {
					if attr.Key == "name" {
						name = attr.Val
					}
					if attr.Key == "content" {
						ctnt = attr.Val
					}
				}
				if name == "description" && ctnt != "" {
					metaDesc = ctnt
					content.MetaDescriptions["default"] = metaDesc
				}

			case "h1", "h2", "h3", "h4", "h5", "h6":
				text := strings.TrimSpace(getTextContent(n))
				if text != "" && len(text) > 2 {
					headings = append(headings, domain.Heading{
						Tag:  n.Data,
						Text: text,
					})
				}

			case "a":
				href := ""
				for _, attr := range n.Attr {
					if attr.Key == "href" {
						href = attr.Val
						break
					}
				}
				text := strings.TrimSpace(getTextContent(n))
				if text != "" && href != "" && len(text) > 1 {
					// Skip common navigation/footer links
					skipKeywords := []string{"privacy", "terms", "cookie", "login", "sign up"}
					skip := false
					textLower := strings.ToLower(text)
					for _, kw := range skipKeywords {
						if strings.Contains(textLower, kw) {
							skip = true
							break
						}
					}
					if !skip {
						// Resolve relative URLs
						if !strings.HasPrefix(href, "http") {
							if parsedBase, err := url.Parse(baseURL); err == nil {
								if parsedHref, err := url.Parse(href); err == nil {
									href = parsedBase.ResolveReference(parsedHref).String()
								}
							}
						}
						if len(text) > 100 {
							text = text[:100]
						}
						links = append(links, domain.Link{
							Text: text,
							Href: href,
						})
					}
				}

			case "main", "article":
				if mainContent == "" {
					mainContent = extractCleanText(n)
				}

			// Extract header content (1:1 with Python)
			case "header", "nav":
				if headerContent == "" {
					headerContent = extractCleanText(n)
				}

			// Extract footer content (1:1 with Python)
			case "footer":
				if footerContent == "" {
					footerContent = extractCleanText(n)
				}
			}
		}

		for c := n.FirstChild; c != nil; c = c.NextSibling {
			traverse(c)
		}
	}

	traverse(doc)

	// If no main content found, try body
	if mainContent == "" {
		var findBody func(*html.Node)
		findBody = func(n *html.Node) {
			if n.Type == html.ElementNode && n.Data == "body" {
				mainContent = extractCleanText(n)
				return
			}
			for c := n.FirstChild; c != nil; c = c.NextSibling {
				findBody(c)
			}
		}
		findBody(doc)
	}

	// Limit content (1:1 with Python)
	if len(mainContent) > 2000 {
		mainContent = mainContent[:2000]
	}
	if len(headerContent) > 500 {
		headerContent = headerContent[:500]
	}
	if len(footerContent) > 500 {
		footerContent = footerContent[:500]
	}

	// Limit headings and links (1:1 with Python)
	if len(headings) > 15 {
		headings = headings[:15]
	}
	if len(links) > 25 {
		links = links[:25]
	}

	content.PageContent["main"] = mainContent
	content.PageContent["header"] = headerContent
	content.PageContent["footer"] = footerContent
	content.PageContent["headings"] = headings
	content.PageContent["links"] = links
	content.PageContent["page_title"] = pageTitle
	content.PageContent["meta_description"] = metaDesc

	return content
}

// getTextContent extracts all text from a node and its children
func getTextContent(n *html.Node) string {
	var sb strings.Builder
	var extract func(*html.Node)
	extract = func(node *html.Node) {
		if node.Type == html.TextNode {
			sb.WriteString(node.Data)
		}
		for c := node.FirstChild; c != nil; c = c.NextSibling {
			extract(c)
		}
	}
	extract(n)
	return sb.String()
}

// extractCleanText extracts clean text, removing scripts and styles
func extractCleanText(n *html.Node) string {
	var sb strings.Builder
	var extract func(*html.Node)
	extract = func(node *html.Node) {
		// Skip script, style, nav, header, footer
		if node.Type == html.ElementNode {
			switch node.Data {
			case "script", "style", "nav", "header", "footer":
				return
			}
		}
		if node.Type == html.TextNode {
			text := strings.TrimSpace(node.Data)
			if text != "" {
				sb.WriteString(text)
				sb.WriteString(" ")
			}
		}
		for c := node.FirstChild; c != nil; c = c.NextSibling {
			extract(c)
		}
	}
	extract(n)

	// Clean up whitespace
	result := sb.String()
	spaceRegex := regexp.MustCompile(`\s+`)
	result = spaceRegex.ReplaceAllString(result, " ")
	return strings.TrimSpace(result)
}
