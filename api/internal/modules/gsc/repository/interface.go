package repository

import (
	"context"
	"time"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/domain"
)

// GSCRepository defines the interface for GSC data operations
type GSCRepository interface {
	// Website operations
	GetWebsites(ctx context.Context, userEmail string) ([]domain.Website, error)
	SaveWebsite(ctx context.Context, website *domain.Website) error
	UpdateLastSync(ctx context.Context, userEmail, siteURL string) error

	// Selected website operations (1:1 parity with original Python)
	GetSelectedWebsite(ctx context.Context, userEmail string) (string, error)
	SetSelectedWebsite(ctx context.Context, userEmail, websiteURL string) error

	// Metrics cache operations
	GetCachedMetrics(ctx context.Context, userEmail, websiteURL string, startDate, endDate time.Time) (*domain.Metrics, error)
	SaveMetrics(ctx context.Context, metrics *domain.Metrics) error
	InvalidateMetricsCache(ctx context.Context, userEmail, websiteURL string) error

	// Daily summary operations
	GetDailySummary(ctx context.Context, userEmail, websiteURL string, startDate, endDate time.Time) ([]domain.DailyMetric, error)
	SaveDailySummary(ctx context.Context, userEmail, websiteURL string, metrics []domain.DailyMetric) error
}
