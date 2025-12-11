package repository

import (
	"context"
	"errors"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
)

// PostgresChatRepository implements ChatRepository with PostgreSQL
type PostgresChatRepository struct {
	pool *pgxpool.Pool
}

// NewPostgresChatRepository creates a new PostgreSQL chat repository
func NewPostgresChatRepository(pool *pgxpool.Pool) *PostgresChatRepository {
	return &PostgresChatRepository{pool: pool}
}

// CreateConversation creates a new conversation
func (r *PostgresChatRepository) CreateConversation(ctx context.Context, conv *domain.Conversation) error {
	query := `
		INSERT INTO conversations (user_email, website_url, title, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id
	`

	now := time.Now()
	return r.pool.QueryRow(ctx, query,
		conv.UserEmail,
		conv.WebsiteURL,
		conv.Title,
		now,
		now,
	).Scan(&conv.ID)
}

// GetConversation retrieves a conversation by ID
func (r *PostgresChatRepository) GetConversation(ctx context.Context, id int64) (*domain.Conversation, error) {
	query := `
		SELECT id, user_email, website_url, title, created_at, updated_at
		FROM conversations
		WHERE id = $1
	`

	var conv domain.Conversation
	var websiteURL *string

	err := r.pool.QueryRow(ctx, query, id).Scan(
		&conv.ID,
		&conv.UserEmail,
		&websiteURL,
		&conv.Title,
		&conv.CreatedAt,
		&conv.UpdatedAt,
	)

	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	if websiteURL != nil {
		conv.WebsiteURL = *websiteURL
	}

	return &conv, nil
}

// GetConversationsByUser retrieves conversations for a user
func (r *PostgresChatRepository) GetConversationsByUser(ctx context.Context, userEmail string, limit int) ([]domain.Conversation, error) {
	query := `
		SELECT id, user_email, website_url, title, created_at, updated_at
		FROM conversations
		WHERE user_email = $1
		ORDER BY updated_at DESC
		LIMIT $2
	`

	rows, err := r.pool.Query(ctx, query, userEmail, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var conversations []domain.Conversation
	for rows.Next() {
		var conv domain.Conversation
		var websiteURL *string

		if err := rows.Scan(
			&conv.ID,
			&conv.UserEmail,
			&websiteURL,
			&conv.Title,
			&conv.CreatedAt,
			&conv.UpdatedAt,
		); err != nil {
			return nil, err
		}

		if websiteURL != nil {
			conv.WebsiteURL = *websiteURL
		}

		conversations = append(conversations, conv)
	}

	return conversations, rows.Err()
}

// UpdateConversation updates a conversation
func (r *PostgresChatRepository) UpdateConversation(ctx context.Context, conv *domain.Conversation) error {
	query := `
		UPDATE conversations
		SET title = $2, website_url = $3, updated_at = NOW()
		WHERE id = $1
	`

	_, err := r.pool.Exec(ctx, query, conv.ID, conv.Title, conv.WebsiteURL)
	return err
}

// DeleteConversation deletes a conversation
func (r *PostgresChatRepository) DeleteConversation(ctx context.Context, id int64) error {
	// Delete messages first
	_, _ = r.pool.Exec(ctx, "DELETE FROM messages WHERE conversation_id = $1", id)

	// Delete conversation
	_, err := r.pool.Exec(ctx, "DELETE FROM conversations WHERE id = $1", id)
	return err
}

// SaveMessage saves a chat message
func (r *PostgresChatRepository) SaveMessage(ctx context.Context, msg *domain.Message) error {
	query := `
		INSERT INTO messages (conversation_id, role, content, tokens_used, created_at)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id
	`

	err := r.pool.QueryRow(ctx, query,
		msg.ConversationID,
		msg.Role,
		msg.Content,
		msg.TokensUsed,
		time.Now(),
	).Scan(&msg.ID)

	if err != nil {
		return err
	}

	// Update conversation timestamp
	_, _ = r.pool.Exec(ctx, "UPDATE conversations SET updated_at = NOW() WHERE id = $1", msg.ConversationID)

	return nil
}

// GetMessagesByConversation retrieves all messages for a conversation
func (r *PostgresChatRepository) GetMessagesByConversation(ctx context.Context, conversationID int64, limit int) ([]domain.Message, error) {
	query := `
		SELECT id, conversation_id, role, content, tokens_used, created_at
		FROM messages
		WHERE conversation_id = $1
		ORDER BY created_at ASC
		LIMIT $2
	`

	rows, err := r.pool.Query(ctx, query, conversationID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []domain.Message
	for rows.Next() {
		var msg domain.Message
		if err := rows.Scan(
			&msg.ID,
			&msg.ConversationID,
			&msg.Role,
			&msg.Content,
			&msg.TokensUsed,
			&msg.CreatedAt,
		); err != nil {
			return nil, err
		}
		messages = append(messages, msg)
	}

	return messages, rows.Err()
}

// GetRecentMessages retrieves recent messages for context
func (r *PostgresChatRepository) GetRecentMessages(ctx context.Context, conversationID int64, limit int) ([]domain.Message, error) {
	query := `
		SELECT id, conversation_id, role, content, tokens_used, created_at
		FROM messages
		WHERE conversation_id = $1
		ORDER BY created_at DESC
		LIMIT $2
	`

	rows, err := r.pool.Query(ctx, query, conversationID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []domain.Message
	for rows.Next() {
		var msg domain.Message
		if err := rows.Scan(
			&msg.ID,
			&msg.ConversationID,
			&msg.Role,
			&msg.Content,
			&msg.TokensUsed,
			&msg.CreatedAt,
		); err != nil {
			return nil, err
		}
		messages = append(messages, msg)
	}

	// Reverse to get chronological order
	for i, j := 0, len(messages)-1; i < j; i, j = i+1, j-1 {
		messages[i], messages[j] = messages[j], messages[i]
	}

	return messages, rows.Err()
}

// DeleteOldConversations deletes old conversations keeping recent ones
func (r *PostgresChatRepository) DeleteOldConversations(ctx context.Context, userEmail string, keepCount int) error {
	// Get IDs to delete
	query := `
		SELECT id FROM conversations
		WHERE user_email = $1
		ORDER BY updated_at DESC
		OFFSET $2
	`

	rows, err := r.pool.Query(ctx, query, userEmail, keepCount)
	if err != nil {
		return err
	}
	defer rows.Close()

	var idsToDelete []int64
	for rows.Next() {
		var id int64
		if err := rows.Scan(&id); err != nil {
			return err
		}
		idsToDelete = append(idsToDelete, id)
	}

	// Delete each conversation
	for _, id := range idsToDelete {
		if err := r.DeleteConversation(ctx, id); err != nil {
			return err
		}
	}

	return nil
}
