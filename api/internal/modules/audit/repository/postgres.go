package repository

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/audit/domain"
)

// PostgresAuditRepository implements AuditRepository with PostgreSQL
type PostgresAuditRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresAuditRepository creates a new PostgreSQL audit repository
func NewPostgresAuditRepository(pool *pgxpool.Pool) *PostgresAuditRepository {
	return &PostgresAuditRepository{pool: pool}
}

// CreateAudit creates a new audit record
func (r *PostgresAuditRepository) CreateAudit(ctx context.Context, audit *domain.Audit) error {
	query := `
		INSERT INTO audits (user_email, website_url, status, seo_score, seo_stage, created_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id
	`

	return r.pool.QueryRow(ctx, query,
		audit.UserEmail,
		audit.WebsiteURL,
		audit.Status,
		audit.SEOScore,
		audit.SEOStage,
		time.Now(),
	).Scan(&audit.ID)
}

// GetAudit retrieves an audit by ID
func (r *PostgresAuditRepository) GetAudit(ctx context.Context, id int64) (*domain.Audit, error) {
	query := `
		SELECT id, user_email, website_url, status, seo_score, seo_stage, pdf_path, created_at, completed_at, error
		FROM audits
		WHERE id = $1
	`

	var audit domain.Audit
	var pdfPath, errMsg *string

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&audit.ID,
		&audit.UserEmail,
		&audit.WebsiteURL,
		&audit.Status,
		&audit.SEOScore,
		&audit.SEOStage,
		&pdfPath,
		&audit.CreatedAt,
		&audit.CompletedAt,
		&errMsg,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	if pdfPath != nil && *pdfPath != "" {
		audit.PDFPath = *pdfPath
		audit.PDFGenerated = true
	}
	if errMsg != nil {
		audit.Error = *errMsg
	}

	return &audit, nil
}

// GetAuditsByUser retrieves audits for a user
func (r *PostgresAuditRepository) GetAuditsByUser(ctx context.Context, userEmail string, limit int) ([]domain.Audit, error) {
	query := `
		SELECT id, user_email, website_url, status, seo_score, seo_stage, pdf_path, created_at, completed_at, error
		FROM audits
		WHERE user_email = $1
		ORDER BY created_at DESC
		LIMIT $2
	`

	rows, err := r.pool.Query(ctx, query, userEmail, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var audits []domain.Audit
	for rows.Next() {
		var audit domain.Audit
		var pdfPath, errMsg *string

		if err := rows.Scan(
			&audit.ID,
			&audit.UserEmail,
			&audit.WebsiteURL,
			&audit.Status,
			&audit.SEOScore,
			&audit.SEOStage,
			&pdfPath,
			&audit.CreatedAt,
			&audit.CompletedAt,
			&errMsg,
		); err != nil {
			return nil, err
		}

		if pdfPath != nil && *pdfPath != "" {
			audit.PDFPath = *pdfPath
			audit.PDFGenerated = true
		}
		if errMsg != nil {
			audit.Error = *errMsg
		}

		audits = append(audits, audit)
	}

	return audits, rows.Err()
}

// GetLatestAudit retrieves the most recent audit for a website
func (r *PostgresAuditRepository) GetLatestAudit(ctx context.Context, userEmail, websiteURL string) (*domain.Audit, error) {
	query := `
		SELECT id, user_email, website_url, status, seo_score, seo_stage, pdf_path, created_at, completed_at, error
		FROM audits
		WHERE user_email = $1 AND website_url = $2
		ORDER BY created_at DESC
		LIMIT 1
	`

	var audit domain.Audit
	var pdfPath, errMsg *string

	err := r.pool.QueryRow(ctx, query, userEmail, websiteURL).Scan(
		&audit.ID,
		&audit.UserEmail,
		&audit.WebsiteURL,
		&audit.Status,
		&audit.SEOScore,
		&audit.SEOStage,
		&pdfPath,
		&audit.CreatedAt,
		&audit.CompletedAt,
		&errMsg,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	if pdfPath != nil && *pdfPath != "" {
		audit.PDFPath = *pdfPath
		audit.PDFGenerated = true
	}
	if errMsg != nil {
		audit.Error = *errMsg
	}

	return &audit, nil
}

// UpdateAuditStatus updates audit status and PDF path
func (r *PostgresAuditRepository) UpdateAuditStatus(ctx context.Context, id int64, status domain.AuditStatus, pdfPath string) error {
	statusStr := string(status)

	// Simple query without CASE WHEN to avoid PostgreSQL type inference issues
	if statusStr == "completed" {
		query := `UPDATE audits SET status = $2, pdf_path = $3, completed_at = NOW() WHERE id = $1`
		_, err := r.pool.Exec(ctx, query, id, statusStr, pdfPath)
		return err
	}

	query := `UPDATE audits SET status = $2, pdf_path = $3 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, statusStr, pdfPath)
	return err
}

// UpdateAuditError updates audit with error
func (r *PostgresAuditRepository) UpdateAuditError(ctx context.Context, id int64, errorMsg string) error {
	query := `UPDATE audits SET status = 'failed', error = $2 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, errorMsg)
	return err
}

// UpdateAuditScore updates the SEO score and stage
func (r *PostgresAuditRepository) UpdateAuditScore(ctx context.Context, id int64, score float64, stage domain.SEOStage) error {
	query := `UPDATE audits SET seo_score = $2, seo_stage = $3 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, score, stage)
	return err
}

// SaveIssues saves audit issues
func (r *PostgresAuditRepository) SaveIssues(ctx context.Context, issues []domain.AuditIssue) error {
	for _, issue := range issues {
		query := `
			INSERT INTO audit_issues (audit_id, severity, category, title, description, impact, suggestion, created_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
		`

		if _, err := r.pool.Exec(ctx, query,
			issue.AuditID,
			issue.Severity,
			issue.Category,
			issue.Title,
			issue.Description,
			issue.Impact,
			issue.Recommendation, // DB column is 'suggestion', Go field is 'Recommendation' (1:1 with Python)
		); err != nil {
			return err
		}
	}

	return nil
}

// GetIssuesByAudit retrieves issues for an audit
func (r *PostgresAuditRepository) GetIssuesByAudit(ctx context.Context, auditID int64) ([]domain.AuditIssue, error) {
	query := `
		SELECT id, audit_id, severity, category, title, description, impact, suggestion, created_at
		FROM audit_issues
		WHERE audit_id = $1
		ORDER BY
			CASE severity
				WHEN 'critical' THEN 0
				WHEN 'high' THEN 1
				WHEN 'medium' THEN 2
				WHEN 'low' THEN 3
				ELSE 4
			END
	`

	rows, err := r.pool.Query(ctx, query, auditID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var issues []domain.AuditIssue
	for rows.Next() {
		var issue domain.AuditIssue
		if err := rows.Scan(
			&issue.ID,
			&issue.AuditID,
			&issue.Severity,
			&issue.Category,
			&issue.Title,
			&issue.Description,
			&issue.Impact,
			&issue.Recommendation, // DB column is 'suggestion', Go field is 'Recommendation' (1:1 with Python)
			&issue.CreatedAt,
		); err != nil {
			return nil, err
		}
		issues = append(issues, issue)
	}

	return issues, rows.Err()
}

// DeleteOldAudits deletes old audits keeping only the most recent ones
func (r *PostgresAuditRepository) DeleteOldAudits(ctx context.Context, userEmail string, keepCount int) error {
	query := `
		DELETE FROM audits
		WHERE user_email = $1
		AND id NOT IN (
			SELECT id FROM audits
			WHERE user_email = $1
			ORDER BY created_at DESC
			LIMIT $2
		)
	`

	_, err := r.pool.Exec(ctx, query, userEmail, keepCount)
	return err
}
