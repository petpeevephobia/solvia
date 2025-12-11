package firecrawl

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const (
	defaultBaseURL = "https://api.firecrawl.dev/v1"
	defaultTimeout = 120 * time.Second
)

// Client is a Firecrawl API client
type Client struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
}

// NewClient creates a new Firecrawl client
func NewClient(apiKey string) *Client {
	return &Client{
		apiKey:  apiKey,
		baseURL: defaultBaseURL,
		httpClient: &http.Client{
			Timeout: defaultTimeout,
		},
	}
}

// WithBaseURL sets a custom base URL
func (c *Client) WithBaseURL(url string) *Client {
	c.baseURL = url
	return c
}

// ScrapeRequest represents a scrape request
type ScrapeRequest struct {
	URL     string   `json:"url"`
	Formats []string `json:"formats,omitempty"`
}

// ScrapeResponse represents a scrape response
type ScrapeResponse struct {
	Success bool       `json:"success"`
	Data    ScrapeData `json:"data"`
}

// ScrapeData contains the scraped data
type ScrapeData struct {
	Content  string   `json:"content,omitempty"`
	Markdown string   `json:"markdown,omitempty"`
	HTML     string   `json:"html,omitempty"`
	Metadata Metadata `json:"metadata"`
}

// Metadata contains page metadata
type Metadata struct {
	Title             string   `json:"title"`
	Description       string   `json:"description"`
	Language          string   `json:"language"`
	Keywords          string   `json:"keywords"`
	Robots            string   `json:"robots"`
	OGTitle           string   `json:"ogTitle"`
	OGDescription     string   `json:"ogDescription"`
	OGImage           string   `json:"ogImage"`
	OGLocaleAlternate []string `json:"ogLocaleAlternate"`
	SourceURL         string   `json:"sourceURL"`
	StatusCode        int      `json:"statusCode"`
}

// CrawlRequest represents a crawl request
type CrawlRequest struct {
	URL            string            `json:"url"`
	Limit          int               `json:"limit,omitempty"`
	MaxDepth       int               `json:"maxDepth,omitempty"`
	ScrapeOptions  *ScrapeOptions    `json:"scrapeOptions,omitempty"`
	IncludePaths   []string          `json:"includePaths,omitempty"`
	ExcludePaths   []string          `json:"excludePaths,omitempty"`
	AllowBackward  bool              `json:"allowBackwardCrawling,omitempty"`
	AllowExternal  bool              `json:"allowExternalContentLinks,omitempty"`
	Webhook        string            `json:"webhook,omitempty"`
}

// ScrapeOptions for crawl requests
type ScrapeOptions struct {
	Formats        []string `json:"formats,omitempty"`
	OnlyMainContent bool    `json:"onlyMainContent,omitempty"`
}

// CrawlResponse represents a crawl start response
type CrawlResponse struct {
	Success bool   `json:"success"`
	ID      string `json:"id"`
	URL     string `json:"url"`
}

// CrawlStatusResponse represents crawl status
type CrawlStatusResponse struct {
	Success    bool         `json:"success"`
	Status     string       `json:"status"`
	Completed  int          `json:"completed"`
	Total      int          `json:"total"`
	Data       []ScrapeData `json:"data"`
	ExpiresAt  string       `json:"expiresAt"`
	NextURL    string       `json:"next"`
}

// MapRequest represents a site map request
type MapRequest struct {
	URL          string `json:"url"`
	Search       string `json:"search,omitempty"`
	IgnoreSitemap bool   `json:"ignoreSitemap,omitempty"`
	Limit        int    `json:"limit,omitempty"`
}

// MapResponse represents a site map response
type MapResponse struct {
	Success bool     `json:"success"`
	Links   []string `json:"links"`
}

// ErrorResponse represents an API error
type ErrorResponse struct {
	Success bool   `json:"success"`
	Error   string `json:"error"`
}

// Scrape scrapes a single URL
func (c *Client) Scrape(ctx context.Context, url string) (*ScrapeResponse, error) {
	req := ScrapeRequest{
		URL:     url,
		Formats: []string{"markdown"},
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/scrape", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var errResp ErrorResponse
		if err := json.Unmarshal(respBody, &errResp); err == nil {
			return nil, fmt.Errorf("API error: %s", errResp.Error)
		}
		return nil, fmt.Errorf("API error: status %d", resp.StatusCode)
	}

	var scrapeResp ScrapeResponse
	if err := json.Unmarshal(respBody, &scrapeResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &scrapeResp, nil
}

// StartCrawl starts a crawl job
func (c *Client) StartCrawl(ctx context.Context, req *CrawlRequest) (*CrawlResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/crawl", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var errResp ErrorResponse
		if err := json.Unmarshal(respBody, &errResp); err == nil {
			return nil, fmt.Errorf("API error: %s", errResp.Error)
		}
		return nil, fmt.Errorf("API error: status %d", resp.StatusCode)
	}

	var crawlResp CrawlResponse
	if err := json.Unmarshal(respBody, &crawlResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &crawlResp, nil
}

// GetCrawlStatus gets the status of a crawl job
func (c *Client) GetCrawlStatus(ctx context.Context, crawlID string) (*CrawlStatusResponse, error) {
	httpReq, err := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/crawl/"+crawlID, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var errResp ErrorResponse
		if err := json.Unmarshal(respBody, &errResp); err == nil {
			return nil, fmt.Errorf("API error: %s", errResp.Error)
		}
		return nil, fmt.Errorf("API error: status %d", resp.StatusCode)
	}

	var statusResp CrawlStatusResponse
	if err := json.Unmarshal(respBody, &statusResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &statusResp, nil
}

// MapSite maps all URLs on a site
func (c *Client) MapSite(ctx context.Context, url string, limit int) (*MapResponse, error) {
	req := MapRequest{
		URL:   url,
		Limit: limit,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/map", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var errResp ErrorResponse
		if err := json.Unmarshal(respBody, &errResp); err == nil {
			return nil, fmt.Errorf("API error: %s", errResp.Error)
		}
		return nil, fmt.Errorf("API error: status %d", resp.StatusCode)
	}

	var mapResp MapResponse
	if err := json.Unmarshal(respBody, &mapResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	return &mapResp, nil
}
