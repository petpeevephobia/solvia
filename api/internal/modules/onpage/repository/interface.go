package repository

import (
	"context"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/domain"
)

// OnPageRepository defines the interface for on-page analysis data operations
type OnPageRepository interface {
	// Analysis operations
	CreateAnalysis(ctx context.Context, analysis *domain.PageAnalysis) error
	GetAnalysis(ctx context.Context, id int64) (*domain.PageAnalysis, error)
	GetAnalysesByUser(ctx context.Context, userEmail string, limit int) ([]domain.PageAnalysis, error)
	GetLatestAnalysis(ctx context.Context, userEmail, url string) (*domain.PageAnalysis, error)
	UpdateAnalysisStatus(ctx context.Context, id int64, status domain.AnalysisStatus) error
	UpdateAnalysisScore(ctx context.Context, id int64, score float64) error
	UpdateAnalysisError(ctx context.Context, id int64, errorMsg string) error

	// Page data operations
	SavePageData(ctx context.Context, analysisID int64, data *domain.PageData) error
	GetPageData(ctx context.Context, analysisID int64) (*domain.PageData, error)

	// Issue operations
	SaveIssues(ctx context.Context, issues []domain.SEOIssue) error
	GetIssuesByAnalysis(ctx context.Context, analysisID int64) ([]domain.SEOIssue, error)

	// Cleanup
	DeleteOldAnalyses(ctx context.Context, userEmail string, keepCount int) error
}
