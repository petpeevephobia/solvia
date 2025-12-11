package domain

import (
	"time"
)

// AnalysisStatus represents the status of an analysis
type AnalysisStatus string

const (
	AnalysisStatusPending    AnalysisStatus = "pending"
	AnalysisStatusProcessing AnalysisStatus = "processing"
	AnalysisStatusCompleted  AnalysisStatus = "completed"
	AnalysisStatusFailed     AnalysisStatus = "failed"
)

// PageAnalysis represents an on-page SEO analysis
type PageAnalysis struct {
	ID          int64          `json:"id"`
	UserEmail   string         `json:"user_email"`
	URL         string         `json:"url"`
	Status      AnalysisStatus `json:"status"`
	Score       float64        `json:"score"`
	CreatedAt   time.Time      `json:"created_at"`
	CompletedAt *time.Time     `json:"completed_at,omitempty"`
	Error       string         `json:"error,omitempty"`
}

// PageData contains scraped page data
type PageData struct {
	Title           string `json:"title"`
	Description     string `json:"description"`
	H1              string `json:"h1"`
	H2Count         int    `json:"h2_count"`
	H3Count         int    `json:"h3_count"`
	WordCount       int    `json:"word_count"`
	ImageCount      int    `json:"image_count"`
	ImagesWithAlt   int    `json:"images_with_alt"`
	InternalLinks   int    `json:"internal_links"`
	ExternalLinks   int    `json:"external_links"`
	HasCanonical    bool   `json:"has_canonical"`
	HasRobots       bool   `json:"has_robots"`
	HasOpenGraph    bool   `json:"has_open_graph"`
	HasSchema       bool   `json:"has_schema"`
	LoadTimeMs      int    `json:"load_time_ms"`
	ContentHash     string `json:"content_hash"`
}

// SEOIssue represents an on-page SEO issue
type SEOIssue struct {
	ID           int64     `json:"id"`
	AnalysisID   int64     `json:"analysis_id"`
	Severity     string    `json:"severity"` // critical, warning, info
	Category     string    `json:"category"` // title, meta, content, images, links, technical
	Title        string    `json:"title"`
	Description  string    `json:"description"`
	CurrentValue string    `json:"current_value,omitempty"`
	Suggestion   string    `json:"suggestion"`
	CreatedAt    time.Time `json:"created_at"`
}

// AnalysisResult contains the full analysis result
type AnalysisResult struct {
	Analysis *PageAnalysis `json:"analysis"`
	PageData *PageData     `json:"page_data"`
	Issues   []SEOIssue    `json:"issues"`
}

// AnalysisRequest represents a request to analyze a page
type AnalysisRequest struct {
	URL string `json:"url" binding:"required"`
}

// SiteMapResult contains site map results
type SiteMapResult struct {
	UserEmail string   `json:"user_email"`
	SiteURL   string   `json:"site_url"`
	URLs      []string `json:"urls"`
	Total     int      `json:"total"`
	ScannedAt time.Time `json:"scanned_at"`
}

// BulkAnalysisRequest represents a bulk analysis request
type BulkAnalysisRequest struct {
	URLs []string `json:"urls" binding:"required,min=1,max=10"`
}

// BulkAnalysisResult contains results for multiple pages
type BulkAnalysisResult struct {
	UserEmail string           `json:"user_email"`
	Total     int              `json:"total"`
	Completed int              `json:"completed"`
	Analyses  []AnalysisResult `json:"analyses"`
}

// CategoryScore represents score for a category
type CategoryScore struct {
	Category string  `json:"category"`
	Score    float64 `json:"score"`
	MaxScore float64 `json:"max_score"`
	Issues   int     `json:"issues"`
}

// PageScoreBreakdown provides detailed score breakdown
type PageScoreBreakdown struct {
	TotalScore float64         `json:"total_score"`
	Categories []CategoryScore `json:"categories"`
}

// Constants for scoring
const (
	MaxTitleLength       = 60
	MinTitleLength       = 30
	MaxDescriptionLength = 160
	MinDescriptionLength = 120
	MinWordCount         = 300
	OptimalWordCount     = 1500
)

// ContentAnalysis represents business context analysis (1:1 with Python website_crawler.py)
type ContentAnalysis struct {
	BusinessType string   `json:"business_type"` // personal_portfolio, technology_business, etc.
	Keywords     []string `json:"keywords"`      // Top extracted keywords
	Services     []string `json:"services"`      // Detected services/offerings
	Location     string   `json:"location"`      // Detected location
	Summary      string   `json:"summary"`       // AI-generated summary
}

// WebsiteAnalysis represents full website crawl analysis
type WebsiteAnalysis struct {
	URL             string           `json:"url"`
	CrawledAt       time.Time        `json:"crawled_at"`
	Title           string           `json:"title"`
	MetaDescription string           `json:"meta_description"`
	ContentSummary  string           `json:"content_summary"`
	ContentAnalysis *ContentAnalysis `json:"content_analysis"`
	PageCount       int              `json:"page_count"`
	InternalLinks   []string         `json:"internal_links,omitempty"`
	TechStack       []string         `json:"technology_stack,omitempty"`
	SocialLinks     []string         `json:"social_links,omitempty"`
	ContactInfo     map[string]string `json:"contact_info,omitempty"`
}
