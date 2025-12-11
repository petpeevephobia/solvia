package repository

import (
	"context"

	"github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
)

// ChatRepository defines the interface for chat data operations
type ChatRepository interface {
	// Conversation operations
	CreateConversation(ctx context.Context, conv *domain.Conversation) error
	GetConversation(ctx context.Context, id int64) (*domain.Conversation, error)
	GetConversationsByUser(ctx context.Context, userEmail string, limit int) ([]domain.Conversation, error)
	UpdateConversation(ctx context.Context, conv *domain.Conversation) error
	DeleteConversation(ctx context.Context, id int64) error

	// Message operations
	SaveMessage(ctx context.Context, msg *domain.Message) error
	GetMessagesByConversation(ctx context.Context, conversationID int64, limit int) ([]domain.Message, error)
	GetRecentMessages(ctx context.Context, conversationID int64, limit int) ([]domain.Message, error)

	// Cleanup
	DeleteOldConversations(ctx context.Context, userEmail string, keepCount int) error
}
