package repository

import (
	"context"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/domain"
)

// DashboardRepository defines the interface for dashboard cache operations
type DashboardRepository interface {
	GetCache(ctx context.Context, userEmail, websiteURL string) (*domain.DashboardCache, error)
	SaveCache(ctx context.Context, cache *domain.DashboardCache) error
	ClearCache(ctx context.Context, userEmail, websiteURL string) error // 1:1 with Python clear_dashboard_cache
}
