package domain

import "time"

// WebsiteContent represents stored website content (1:1 with Python)
type WebsiteContent struct {
	ID               int64                  `json:"id,omitempty"`
	UserEmail        string                 `json:"user_email"`
	WebsiteURL       string                 `json:"website_url"`
	TitleTags        map[string]string      `json:"title_tags"`
	MetaDescriptions map[string]string      `json:"meta_descriptions"`
	PageContent      map[string]interface{} `json:"page_content"`
	FetchedAt        time.Time              `json:"fetched_at"`
}

// Heading represents a page heading
type Heading struct {
	Tag  string `json:"tag"`
	Text string `json:"text"`
}

// Link represents a page link
type Link struct {
	Text string `json:"text"`
	Href string `json:"href"`
}
