package repository

import (
	"context"
	"encoding/json"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/website/domain"
)

// PostgresWebsiteRepository implements WebsiteRepository with PostgreSQL
type PostgresWebsiteRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresWebsiteRepository creates a new PostgreSQL website repository
func NewPostgresWebsiteRepository(pool *pgxpool.Pool) *PostgresWebsiteRepository {
	return &PostgresWebsiteRepository{pool: pool}
}

// GetContent retrieves stored website content (1:1 with Python)
func (r *PostgresWebsiteRepository) GetContent(ctx context.Context, userEmail, websiteURL string) (*domain.WebsiteContent, error) {
	query := `
		SELECT id, user_email, website_url, content_data, fetched_at
		FROM website_content
		WHERE user_email = $1 AND website_url = $2
		ORDER BY fetched_at DESC
		LIMIT 1
	`

	var content domain.WebsiteContent
	var contentDataJSON []byte

	err := r.pool.QueryRow(ctx, query, userEmail, websiteURL).Scan(
		&content.ID,
		&content.UserEmail,
		&content.WebsiteURL,
		&contentDataJSON,
		&content.FetchedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	// Parse JSON data
	var data map[string]interface{}
	if err := json.Unmarshal(contentDataJSON, &data); err != nil {
		return nil, err
	}

	// Extract fields
	if titleTags, ok := data["title_tags"].(map[string]interface{}); ok {
		content.TitleTags = make(map[string]string)
		for k, v := range titleTags {
			if s, ok := v.(string); ok {
				content.TitleTags[k] = s
			}
		}
	}
	if metaDescs, ok := data["meta_descriptions"].(map[string]interface{}); ok {
		content.MetaDescriptions = make(map[string]string)
		for k, v := range metaDescs {
			if s, ok := v.(string); ok {
				content.MetaDescriptions[k] = s
			}
		}
	}
	if pageContent, ok := data["page_content"].(map[string]interface{}); ok {
		content.PageContent = pageContent
	}

	return &content, nil
}

// SaveContent saves website content (1:1 with Python)
func (r *PostgresWebsiteRepository) SaveContent(ctx context.Context, content *domain.WebsiteContent) error {
	// Build content data JSON
	contentData := map[string]interface{}{
		"title_tags":        content.TitleTags,
		"meta_descriptions": content.MetaDescriptions,
		"page_content":      content.PageContent,
	}

	contentDataJSON, err := json.Marshal(contentData)
	if err != nil {
		return err
	}

	query := `
		INSERT INTO website_content (user_email, website_url, content_data, fetched_at)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (user_email, website_url)
		DO UPDATE SET content_data = EXCLUDED.content_data, fetched_at = EXCLUDED.fetched_at
	`

	_, err = r.pool.Exec(ctx, query,
		content.UserEmail,
		content.WebsiteURL,
		contentDataJSON,
		time.Now(),
	)

	return err
}
