package repository

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/dashboard/domain"
)

// PostgresDashboardRepository implements DashboardRepository with PostgreSQL
type PostgresDashboardRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresDashboardRepository creates a new PostgreSQL dashboard repository
func NewPostgresDashboardRepository(pool *pgxpool.Pool) *PostgresDashboardRepository {
	return &PostgresDashboardRepository{pool: pool}
}

// GetCache retrieves cached dashboard data (1:1 with Python)
func (r *PostgresDashboardRepository) GetCache(ctx context.Context, userEmail, websiteURL string) (*domain.DashboardCache, error) {
	query := `
		SELECT id, user_email, website_url, data, cached_at
		FROM dashboard_cache
		WHERE user_email = $1 AND website_url = $2
		ORDER BY cached_at DESC
		LIMIT 1
	`

	var cache domain.DashboardCache
	var dataJSON []byte

	err := r.pool.QueryRow(ctx, query, userEmail, websiteURL).Scan(
		&cache.ID,
		&cache.UserEmail,
		&cache.WebsiteURL,
		&dataJSON,
		&cache.CachedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	// Parse JSON data
	if err := json.Unmarshal(dataJSON, &cache.Data); err != nil {
		return nil, err
	}

	return &cache, nil
}

// SaveCache saves dashboard cache (1:1 with Python)
func (r *PostgresDashboardRepository) SaveCache(ctx context.Context, cache *domain.DashboardCache) error {
	// Merge AI insights and keywords into data if present
	if cache.AIInsights != nil {
		cache.Data["ai_insights"] = cache.AIInsights
	}
	if cache.Keywords != nil {
		cache.Data["keywords"] = cache.Keywords
	}

	dataJSON, err := json.Marshal(cache.Data)
	if err != nil {
		return err
	}

	query := `
		INSERT INTO dashboard_cache (user_email, website_url, data, cached_at)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (user_email, website_url)
		DO UPDATE SET data = EXCLUDED.data, cached_at = EXCLUDED.cached_at
	`

	_, err = r.pool.Exec(ctx, query,
		cache.UserEmail,
		cache.WebsiteURL,
		dataJSON,
		time.Now(),
	)

	return err
}

// ClearCache removes cached dashboard data (1:1 with Python clear_dashboard_cache)
func (r *PostgresDashboardRepository) ClearCache(ctx context.Context, userEmail, websiteURL string) error {
	query := `DELETE FROM dashboard_cache WHERE user_email = $1 AND website_url = $2`
	_, err := r.pool.Exec(ctx, query, userEmail, websiteURL)
	return err
}
