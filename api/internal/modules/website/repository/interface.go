package repository

import (
	"context"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/website/domain"
)

// WebsiteRepository defines the interface for website content operations
type WebsiteRepository interface {
	// GetContent retrieves stored website content
	GetContent(ctx context.Context, userEmail, websiteURL string) (*domain.WebsiteContent, error)
	// SaveContent saves website content
	SaveContent(ctx context.Context, content *domain.WebsiteContent) error
}
