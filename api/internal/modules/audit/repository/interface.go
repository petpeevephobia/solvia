package repository

import (
	"context"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
)

// AuditRepository defines the interface for audit data operations
type AuditRepository interface {
	// Audit operations
	CreateAudit(ctx context.Context, audit *domain.Audit) error
	GetAudit(ctx context.Context, id int64) (*domain.Audit, error)
	GetAuditsByUser(ctx context.Context, userEmail string, limit int) ([]domain.Audit, error)
	GetLatestAudit(ctx context.Context, userEmail, websiteURL string) (*domain.Audit, error)
	UpdateAuditStatus(ctx context.Context, id int64, status domain.AuditStatus, pdfPath string) error
	UpdateAuditError(ctx context.Context, id int64, errorMsg string) error
	UpdateAuditScore(ctx context.Context, id int64, score float64, stage domain.SEOStage) error

	// Issue operations
	SaveIssues(ctx context.Context, issues []domain.AuditIssue) error
	GetIssuesByAudit(ctx context.Context, auditID int64) ([]domain.AuditIssue, error)

	// Cleanup
	DeleteOldAudits(ctx context.Context, userEmail string, keepCount int) error
}
