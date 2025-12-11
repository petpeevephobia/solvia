package repository

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/onpage/domain"
)

// PostgresOnPageRepository implements OnPageRepository with PostgreSQL
type PostgresOnPageRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresOnPageRepository creates a new PostgreSQL on-page repository
func NewPostgresOnPageRepository(pool *pgxpool.Pool) *PostgresOnPageRepository {
	return &PostgresOnPageRepository{pool: pool}
}

// CreateAnalysis creates a new page analysis record
func (r *PostgresOnPageRepository) CreateAnalysis(ctx context.Context, analysis *domain.PageAnalysis) error {
	query := `
		INSERT INTO page_analyses (user_email, url, status, score, created_at)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id
	`

	return r.pool.QueryRow(ctx, query,
		analysis.UserEmail,
		analysis.URL,
		analysis.Status,
		analysis.Score,
		time.Now(),
	).Scan(&analysis.ID)
}

// GetAnalysis retrieves an analysis by ID
func (r *PostgresOnPageRepository) GetAnalysis(ctx context.Context, id int64) (*domain.PageAnalysis, error) {
	query := `
		SELECT id, user_email, url, status, score, created_at, completed_at, error
		FROM page_analyses
		WHERE id = $1
	`

	var analysis domain.PageAnalysis
	var errMsg *string

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&analysis.ID,
		&analysis.UserEmail,
		&analysis.URL,
		&analysis.Status,
		&analysis.Score,
		&analysis.CreatedAt,
		&analysis.CompletedAt,
		&errMsg,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	if errMsg != nil {
		analysis.Error = *errMsg
	}

	return &analysis, nil
}

// GetAnalysesByUser retrieves analyses for a user
func (r *PostgresOnPageRepository) GetAnalysesByUser(ctx context.Context, userEmail string, limit int) ([]domain.PageAnalysis, error) {
	query := `
		SELECT id, user_email, url, status, score, created_at, completed_at, error
		FROM page_analyses
		WHERE user_email = $1
		ORDER BY created_at DESC
		LIMIT $2
	`

	rows, err := r.pool.Query(ctx, query, userEmail, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var analyses []domain.PageAnalysis
	for rows.Next() {
		var analysis domain.PageAnalysis
		var errMsg *string

		if err := rows.Scan(
			&analysis.ID,
			&analysis.UserEmail,
			&analysis.URL,
			&analysis.Status,
			&analysis.Score,
			&analysis.CreatedAt,
			&analysis.CompletedAt,
			&errMsg,
		); err != nil {
			return nil, err
		}

		if errMsg != nil {
			analysis.Error = *errMsg
		}

		analyses = append(analyses, analysis)
	}

	return analyses, rows.Err()
}

// GetLatestAnalysis retrieves the most recent analysis for a URL
func (r *PostgresOnPageRepository) GetLatestAnalysis(ctx context.Context, userEmail, url string) (*domain.PageAnalysis, error) {
	query := `
		SELECT id, user_email, url, status, score, created_at, completed_at, error
		FROM page_analyses
		WHERE user_email = $1 AND url = $2
		ORDER BY created_at DESC
		LIMIT 1
	`

	var analysis domain.PageAnalysis
	var errMsg *string

	err := r.pool.QueryRow(ctx, query, userEmail, url).Scan(
		&analysis.ID,
		&analysis.UserEmail,
		&analysis.URL,
		&analysis.Status,
		&analysis.Score,
		&analysis.CreatedAt,
		&analysis.CompletedAt,
		&errMsg,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	if errMsg != nil {
		analysis.Error = *errMsg
	}

	return &analysis, nil
}

// UpdateAnalysisStatus updates analysis status
func (r *PostgresOnPageRepository) UpdateAnalysisStatus(ctx context.Context, id int64, status domain.AnalysisStatus) error {
	query := `
		UPDATE page_analyses
		SET status = $2, completed_at = CASE WHEN $2 IN ('completed', 'failed') THEN NOW() ELSE completed_at END
		WHERE id = $1
	`

	_, err := r.pool.Exec(ctx, query, id, status)
	return err
}

// UpdateAnalysisScore updates the analysis score
func (r *PostgresOnPageRepository) UpdateAnalysisScore(ctx context.Context, id int64, score float64) error {
	query := `UPDATE page_analyses SET score = $2 WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, score)
	return err
}

// UpdateAnalysisError updates analysis with error
func (r *PostgresOnPageRepository) UpdateAnalysisError(ctx context.Context, id int64, errorMsg string) error {
	query := `UPDATE page_analyses SET status = 'failed', error = $2, completed_at = NOW() WHERE id = $1`
	_, err := r.pool.Exec(ctx, query, id, errorMsg)
	return err
}

// SavePageData saves page data
func (r *PostgresOnPageRepository) SavePageData(ctx context.Context, analysisID int64, data *domain.PageData) error {
	query := `
		INSERT INTO page_data (
			analysis_id, title, description, h1, h2_count, h3_count,
			word_count, image_count, images_with_alt, internal_links, external_links,
			has_canonical, has_robots, has_open_graph, has_schema, load_time_ms, content_hash
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
		ON CONFLICT (analysis_id) DO UPDATE SET
			title = EXCLUDED.title,
			description = EXCLUDED.description,
			h1 = EXCLUDED.h1,
			h2_count = EXCLUDED.h2_count,
			h3_count = EXCLUDED.h3_count,
			word_count = EXCLUDED.word_count,
			image_count = EXCLUDED.image_count,
			images_with_alt = EXCLUDED.images_with_alt,
			internal_links = EXCLUDED.internal_links,
			external_links = EXCLUDED.external_links,
			has_canonical = EXCLUDED.has_canonical,
			has_robots = EXCLUDED.has_robots,
			has_open_graph = EXCLUDED.has_open_graph,
			has_schema = EXCLUDED.has_schema,
			load_time_ms = EXCLUDED.load_time_ms,
			content_hash = EXCLUDED.content_hash
	`

	_, err := r.pool.Exec(ctx, query,
		analysisID,
		data.Title,
		data.Description,
		data.H1,
		data.H2Count,
		data.H3Count,
		data.WordCount,
		data.ImageCount,
		data.ImagesWithAlt,
		data.InternalLinks,
		data.ExternalLinks,
		data.HasCanonical,
		data.HasRobots,
		data.HasOpenGraph,
		data.HasSchema,
		data.LoadTimeMs,
		data.ContentHash,
	)

	return err
}

// GetPageData retrieves page data for an analysis
func (r *PostgresOnPageRepository) GetPageData(ctx context.Context, analysisID int64) (*domain.PageData, error) {
	query := `
		SELECT title, description, h1, h2_count, h3_count,
			   word_count, image_count, images_with_alt, internal_links, external_links,
			   has_canonical, has_robots, has_open_graph, has_schema, load_time_ms, content_hash
		FROM page_data
		WHERE analysis_id = $1
	`

	var data domain.PageData
	err := r.pool.QueryRow(ctx, query, analysisID).Scan(
		&data.Title,
		&data.Description,
		&data.H1,
		&data.H2Count,
		&data.H3Count,
		&data.WordCount,
		&data.ImageCount,
		&data.ImagesWithAlt,
		&data.InternalLinks,
		&data.ExternalLinks,
		&data.HasCanonical,
		&data.HasRobots,
		&data.HasOpenGraph,
		&data.HasSchema,
		&data.LoadTimeMs,
		&data.ContentHash,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	return &data, nil
}

// SaveIssues saves SEO issues
func (r *PostgresOnPageRepository) SaveIssues(ctx context.Context, issues []domain.SEOIssue) error {
	for _, issue := range issues {
		query := `
			INSERT INTO onpage_issues (analysis_id, severity, category, title, description, current_value, suggestion, created_at)
			VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
		`

		if _, err := r.pool.Exec(ctx, query,
			issue.AnalysisID,
			issue.Severity,
			issue.Category,
			issue.Title,
			issue.Description,
			issue.CurrentValue,
			issue.Suggestion,
		); err != nil {
			return err
		}
	}

	return nil
}

// GetIssuesByAnalysis retrieves issues for an analysis
func (r *PostgresOnPageRepository) GetIssuesByAnalysis(ctx context.Context, analysisID int64) ([]domain.SEOIssue, error) {
	query := `
		SELECT id, analysis_id, severity, category, title, description, current_value, suggestion, created_at
		FROM onpage_issues
		WHERE analysis_id = $1
		ORDER BY
			CASE severity
				WHEN 'critical' THEN 1
				WHEN 'warning' THEN 2
				WHEN 'info' THEN 3
			END
	`

	rows, err := r.pool.Query(ctx, query, analysisID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var issues []domain.SEOIssue
	for rows.Next() {
		var issue domain.SEOIssue
		var currentValue *string
		if err := rows.Scan(
			&issue.ID,
			&issue.AnalysisID,
			&issue.Severity,
			&issue.Category,
			&issue.Title,
			&issue.Description,
			&currentValue,
			&issue.Suggestion,
			&issue.CreatedAt,
		); err != nil {
			return nil, err
		}
		if currentValue != nil {
			issue.CurrentValue = *currentValue
		}
		issues = append(issues, issue)
	}

	return issues, rows.Err()
}

// DeleteOldAnalyses deletes old analyses
func (r *PostgresOnPageRepository) DeleteOldAnalyses(ctx context.Context, userEmail string, keepCount int) error {
	query := `
		DELETE FROM page_analyses
		WHERE user_email = $1
		AND id NOT IN (
			SELECT id FROM page_analyses
			WHERE user_email = $1
			ORDER BY created_at DESC
			LIMIT $2
		)
	`

	_, err := r.pool.Exec(ctx, query, userEmail, keepCount)
	return err
}
