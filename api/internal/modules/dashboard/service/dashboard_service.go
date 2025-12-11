package service

import (
	"context"
	"time"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/repository"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
)

// WebsiteGetter interface to get user's selected website
type WebsiteGetter interface {
	GetSelectedWebsite(ctx context.Context, userEmail string) (string, error)
}

// DashboardService handles dashboard business logic
type DashboardService struct {
	repo          repository.DashboardRepository
	websiteGetter WebsiteGetter
}

// NewDashboardService creates a new dashboard service
func NewDashboardService(
	repo repository.DashboardRepository,
	websiteGetter WebsiteGetter,
) *DashboardService {
	return &DashboardService{
		repo:          repo,
		websiteGetter: websiteGetter,
	}
}

// GetCache retrieves cached dashboard data (1:1 with Python /dashboard/cache GET)
func (s *DashboardService) GetCache(ctx context.Context, userEmail string) (*domain.DashboardCache, string, error) {
	// Get user's selected website
	websiteURL, err := s.websiteGetter.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return nil, "", apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return nil, "", nil // No website selected
	}

	cache, err := s.repo.GetCache(ctx, userEmail, websiteURL)
	if err != nil {
		return nil, websiteURL, apperrors.DatabaseError(err)
	}

	return cache, websiteURL, nil
}

// SaveCache saves dashboard cache (1:1 with Python /dashboard/cache POST)
func (s *DashboardService) SaveCache(ctx context.Context, userEmail string, req *domain.CacheDashboardRequest) error {
	// Get user's selected website
	websiteURL, err := s.websiteGetter.GetSelectedWebsite(ctx, userEmail)
	if err != nil {
		return apperrors.DatabaseError(err)
	}

	if websiteURL == "" {
		return apperrors.New(apperrors.CodeValidation, "No website property selected for user.", 400)
	}

	cache := &domain.DashboardCache{
		UserEmail:  userEmail,
		WebsiteURL: websiteURL,
		Data:       req.DashboardData,
		AIInsights: req.AIInsights,
		Keywords:   req.Keywords,
		CachedAt:   time.Now(),
	}

	if err := s.repo.SaveCache(ctx, cache); err != nil {
		return apperrors.DatabaseError(err)
	}

	return nil
}
