package repository

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/gsc/domain"
)

// PostgresGSCRepository implements GSCRepository with PostgreSQL
type PostgresGSCRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresGSCRepository creates a new PostgreSQL GSC repository
func NewPostgresGSCRepository(pool *pgxpool.Pool) *PostgresGSCRepository {
	return &PostgresGSCRepository{pool: pool}
}

// GetWebsites returns all connected websites for a user
func (r *PostgresGSCRepository) GetWebsites(ctx context.Context, userEmail string) ([]domain.Website, error) {
	query := `
		SELECT id, user_email, website_url, permission_level, connected_at, last_sync_at
		FROM gsc_connections
		WHERE user_email = $1
		ORDER BY connected_at DESC
	`

	rows, err := r.pool.Query(ctx, query, userEmail)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var websites []domain.Website
	for rows.Next() {
		var w domain.Website
		var lastSync *time.Time
		if err := rows.Scan(&w.ID, &w.UserEmail, &w.SiteURL, &w.PermissionLevel, &w.ConnectedAt, &lastSync); err != nil {
			return nil, err
		}
		if lastSync != nil {
			w.LastSyncAt = *lastSync
		}
		websites = append(websites, w)
	}

	return websites, rows.Err()
}

// SaveWebsite saves or updates a website connection
func (r *PostgresGSCRepository) SaveWebsite(ctx context.Context, website *domain.Website) error {
	query := `
		INSERT INTO gsc_connections (user_email, website_url, permission_level, connected_at)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (user_email, website_url)
		DO UPDATE SET permission_level = EXCLUDED.permission_level
		RETURNING id
	`

	return r.pool.QueryRow(ctx, query,
		website.UserEmail,
		website.SiteURL,
		website.PermissionLevel,
		time.Now(),
	).Scan(&website.ID)
}

// UpdateLastSync updates the last sync timestamp
func (r *PostgresGSCRepository) UpdateLastSync(ctx context.Context, userEmail, siteURL string) error {
	query := `UPDATE gsc_connections SET last_sync_at = NOW() WHERE user_email = $1 AND website_url = $2`
	_, err := r.pool.Exec(ctx, query, userEmail, siteURL)
	return err
}

// GetSelectedWebsite returns the user's selected website URL (1:1 parity with original Python)
func (r *PostgresGSCRepository) GetSelectedWebsite(ctx context.Context, userEmail string) (string, error) {
	query := `SELECT website_url FROM user_websites WHERE user_email = $1`

	var websiteURL string
	err := r.pool.QueryRow(ctx, query, userEmail).Scan(&websiteURL)

	if errors.Is(err, pgx.ErrNoRows) {
		return "", nil // No website selected, return empty string
	}
	if err != nil {
		return "", err
	}

	return websiteURL, nil
}

// SetSelectedWebsite sets the user's selected website URL (1:1 parity with original Python)
func (r *PostgresGSCRepository) SetSelectedWebsite(ctx context.Context, userEmail, websiteURL string) error {
	query := `
		INSERT INTO user_websites (user_email, website_url, created_at, updated_at)
		VALUES ($1, $2, NOW(), NOW())
		ON CONFLICT (user_email)
		DO UPDATE SET website_url = EXCLUDED.website_url, updated_at = NOW()
	`

	_, err := r.pool.Exec(ctx, query, userEmail, websiteURL)
	return err
}

// GetCachedMetrics retrieves cached metrics if available
func (r *PostgresGSCRepository) GetCachedMetrics(ctx context.Context, userEmail, websiteURL string, startDate, endDate time.Time) (*domain.Metrics, error) {
	query := `
		SELECT user_email, website_url, start_date, end_date, seo_score, impressions, clicks, ctr, avg_position, cache_date
		FROM gsc_metrics_cache
		WHERE user_email = $1 AND website_url = $2 AND start_date = $3 AND end_date = $4
		AND cache_date >= CURRENT_DATE
	`

	var m domain.Metrics
	err := r.pool.QueryRow(ctx, query, userEmail, websiteURL, startDate.Format("2006-01-02"), endDate.Format("2006-01-02")).Scan(
		&m.UserEmail, &m.WebsiteURL, &m.StartDate, &m.EndDate, &m.SEOScore, &m.Impressions, &m.Clicks, &m.CTR, &m.Position, &m.CacheDate,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	return &m, nil
}

// SaveMetrics caches metrics
func (r *PostgresGSCRepository) SaveMetrics(ctx context.Context, metrics *domain.Metrics) error {
	query := `
		INSERT INTO gsc_metrics_cache (user_email, website_url, start_date, end_date, seo_score, impressions, clicks, ctr, avg_position, cache_date)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, CURRENT_DATE)
		ON CONFLICT (user_email, website_url, start_date, end_date, cache_date)
		DO UPDATE SET seo_score = EXCLUDED.seo_score, impressions = EXCLUDED.impressions, clicks = EXCLUDED.clicks, ctr = EXCLUDED.ctr, avg_position = EXCLUDED.avg_position
	`

	_, err := r.pool.Exec(ctx, query,
		metrics.UserEmail,
		metrics.WebsiteURL,
		metrics.StartDate.Format("2006-01-02"),
		metrics.EndDate.Format("2006-01-02"),
		metrics.SEOScore,
		metrics.Impressions,
		metrics.Clicks,
		metrics.CTR,
		metrics.Position,
	)

	return err
}

// InvalidateMetricsCache removes cached metrics for a user/website (for refresh)
func (r *PostgresGSCRepository) InvalidateMetricsCache(ctx context.Context, userEmail, websiteURL string) error {
	query := `DELETE FROM gsc_metrics_cache WHERE user_email = $1 AND website_url = $2`
	_, err := r.pool.Exec(ctx, query, userEmail, websiteURL)
	return err
}

// GetDailySummary retrieves daily metrics
func (r *PostgresGSCRepository) GetDailySummary(ctx context.Context, userEmail, websiteURL string, startDate, endDate time.Time) ([]domain.DailyMetric, error) {
	query := `
		SELECT date, impressions, clicks, ctr, avg_position
		FROM gsc_daily_summary
		WHERE user_email = $1 AND website_url = $2 AND date BETWEEN $3 AND $4
		ORDER BY date ASC
	`

	rows, err := r.pool.Query(ctx, query, userEmail, websiteURL, startDate, endDate)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var metrics []domain.DailyMetric
	for rows.Next() {
		var m domain.DailyMetric
		if err := rows.Scan(&m.Date, &m.Impressions, &m.Clicks, &m.CTR, &m.Position); err != nil {
			return nil, err
		}
		metrics = append(metrics, m)
	}

	return metrics, rows.Err()
}

// SaveDailySummary saves daily metrics
func (r *PostgresGSCRepository) SaveDailySummary(ctx context.Context, userEmail, websiteURL string, metrics []domain.DailyMetric) error {
	for _, m := range metrics {
		query := `
			INSERT INTO gsc_daily_summary (user_email, website_url, date, impressions, clicks, ctr, avg_position)
			VALUES ($1, $2, $3, $4, $5, $6, $7)
			ON CONFLICT (user_email, website_url, date)
			DO UPDATE SET impressions = EXCLUDED.impressions, clicks = EXCLUDED.clicks, ctr = EXCLUDED.ctr, avg_position = EXCLUDED.avg_position
		`

		if _, err := r.pool.Exec(ctx, query, userEmail, websiteURL, m.Date, m.Impressions, m.Clicks, m.CTR, m.Position); err != nil {
			return err
		}
	}

	return nil
}
