package service

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/gemini"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/repository"
	apperrors "github.com/petpeevephobia/solvia-v2/api/internal/shared/errors"
)

const (
	maxContextMessages = 5  // 1:1 with Python routes.py:912 and supabase_rag_agent.py:509 - last 5 messages
	maxConversations   = 50 // Maximum conversations per user
)

// MetricsProvider provides website metrics for context (matching Python exactly)
type MetricsProvider interface {
	GetWebsiteContext(ctx context.Context, userEmail, websiteURL string) (*domain.WebsiteContext, error)
}

// AuditProvider provides audit data for context (matching Python exactly)
type AuditProvider interface {
	GetLatestAuditContext(ctx context.Context, userEmail, websiteURL string) (*domain.AuditContext, error)
}

// RAGProvider provides RAG context for enhanced responses (1:1 with Python)
type RAGProvider interface {
	GetRAGContext(ctx context.Context, userEmail, query, websiteURL string) (string, error)
	IndexInteraction(ctx context.Context, userEmail, websiteURL, query, response string) error
}

// ChatService handles chat business logic
type ChatService struct {
	repo            repository.ChatRepository
	aiClient        domain.AIClient // Interface for OpenAI or Gemini
	metricsProvider MetricsProvider
	auditProvider   AuditProvider
	ragProvider     RAGProvider // Optional RAG provider for enhanced context
}

// NewChatService creates a new chat service
// aiClient can be OpenAI or Gemini (implements domain.AIClient interface)
func NewChatService(
	repo repository.ChatRepository,
	aiClient domain.AIClient,
	metricsProvider MetricsProvider,
	auditProvider AuditProvider,
) *ChatService {
	return &ChatService{
		repo:            repo,
		aiClient:        aiClient,
		metricsProvider: metricsProvider,
		auditProvider:   auditProvider,
	}
}

// SetRAGProvider sets the RAG provider for enhanced context (1:1 with Python)
func (s *ChatService) SetRAGProvider(provider RAGProvider) {
	s.ragProvider = provider
}

// Audit trigger keywords (matching Python exactly from routes.py:848)
var auditTriggerKeywords = []string{
	"run audit",
	"run the audit",
	"new audit",
	"run a new audit",
	"generate report",
	"generate audit",
	"analyze my site",
	"run seo audit",
	"start audit",
	"perform audit",
	"trigger audit",
	"comprehensive audit",
}

// Exact match keywords (when message is exactly one of these)
var auditTriggerExact = []string{
	"audit",
	"run",
	"analyze",
}

// detectAuditTrigger checks if message contains audit trigger keywords (matching Python exactly)
func detectAuditTrigger(message string) bool {
	lowerMessage := strings.ToLower(strings.TrimSpace(message))

	// Check for exact matches first
	for _, exact := range auditTriggerExact {
		if lowerMessage == exact {
			return true
		}
	}

	// Check for keyword phrases
	for _, keyword := range auditTriggerKeywords {
		if strings.Contains(lowerMessage, keyword) {
			return true
		}
	}
	return false
}

// Chat processes a chat message and returns a response (1:1 with Python)
func (s *ChatService) Chat(ctx context.Context, userEmail string, req *domain.ChatRequest) (*domain.ChatResponse, error) {
	var conv *domain.Conversation
	var err error

	// Get or create conversation
	if req.ConversationID > 0 {
		conv, err = s.repo.GetConversation(ctx, req.ConversationID)
		if err != nil {
			return nil, apperrors.DatabaseError(err)
		}
		if conv == nil || conv.UserEmail != userEmail {
			return nil, apperrors.NotFoundError("Conversation", fmt.Sprintf("%d", req.ConversationID))
		}
	} else {
		// Create new conversation
		conv = &domain.Conversation{
			UserEmail:  userEmail,
			WebsiteURL: req.WebsiteURL,
			Title:      generateTitle(req.Message),
			CreatedAt:  time.Now(),
			UpdatedAt:  time.Now(),
		}
		if err := s.repo.CreateConversation(ctx, conv); err != nil {
			return nil, apperrors.DatabaseError(err)
		}
	}

	// Build enhanced system prompt with context injection and RAG (matching Python)
	systemPrompt := s.buildEnhancedSystemPrompt(ctx, userEmail, req.WebsiteURL, req.Message, req.IncludeMetrics)

	// Build messages for AI (provider-agnostic: OpenAI or Gemini)
	messages := []domain.AIMessage{
		{Role: "system", Content: systemPrompt},
	}

	// Get recent conversation history
	recentMsgs, _ := s.repo.GetRecentMessages(ctx, conv.ID, maxContextMessages)
	for _, msg := range recentMsgs {
		messages = append(messages, domain.AIMessage{
			Role:    string(msg.Role),
			Content: msg.Content,
		})
	}

	// Add current user message
	messages = append(messages, domain.AIMessage{
		Role:    "user",
		Content: req.Message,
	})

	// Save user message
	userMsg := &domain.Message{
		ConversationID: conv.ID,
		Role:           domain.RoleUser,
		Content:        req.Message,
		CreatedAt:      time.Now(),
	}
	if err := s.repo.SaveMessage(ctx, userMsg); err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	// Check for audit trigger (matching Python)
	triggerAudit := detectAuditTrigger(req.Message)

	// Call AI (OpenAI or Gemini) - use RAG-optimized settings when RAG context is available
	// 1:1 with Python: RAG uses lower temperature for deterministic responses
	var response *domain.AIResponse
	var aiErr error
	if s.ragProvider != nil && req.IncludeMetrics {
		// Use ChatWithRAG for lower temperature and higher tokens
		response, aiErr = s.aiClient.ChatWithRAG(ctx, messages)
	} else {
		// Use standard Chat for regular conversations
		response, aiErr = s.aiClient.Chat(ctx, messages)
	}
	if aiErr != nil {
		return nil, apperrors.ExternalServiceError("AI", aiErr)
	}

	assistantContent := response.Content

	// Save assistant message
	assistantMsg := &domain.Message{
		ConversationID: conv.ID,
		Role:           domain.RoleAssistant,
		Content:        assistantContent,
		TokensUsed:     response.TokensUsed,
		CreatedAt:      time.Now(),
	}
	if err := s.repo.SaveMessage(ctx, assistantMsg); err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	// Cleanup old conversations
	_ = s.repo.DeleteOldConversations(ctx, userEmail, maxConversations)

	// Index interaction for RAG (1:1 with Python - async indexing)
	s.indexInteraction(ctx, userEmail, req.WebsiteURL, req.Message, assistantContent)

	return &domain.ChatResponse{
		ConversationID: conv.ID,
		Message:        assistantContent,
		TokensUsed:     response.TokensUsed,
		AuditTriggered: triggerAudit,                // 1:1 with Python field name
		ActionButtons:  domain.DefaultActionButtons, // 1:1 with Python routes.py:933-938
	}, nil
}

// buildEnhancedSystemPrompt builds system prompt with GSC metrics, audit context, and RAG (matching Python)
// Enhanced with weekly and daily data for "last week" and "trends" queries
func (s *ChatService) buildEnhancedSystemPrompt(ctx context.Context, userEmail, websiteURL, userQuery string, includeMetrics bool) string {
	// Start with base system prompt
	if !includeMetrics || websiteURL == "" {
		return gemini.SEOSystemPrompt
	}

	// Fetch GSC metrics for context injection (now includes weekly and daily data)
	var metricsData *gemini.WebsiteMetrics
	if s.metricsProvider != nil {
		websiteCtx, err := s.metricsProvider.GetWebsiteContext(ctx, userEmail, websiteURL)
		if err == nil && websiteCtx != nil {
			metricsData = &gemini.WebsiteMetrics{
				Impressions:       websiteCtx.Impressions,
				Clicks:            websiteCtx.Clicks,
				CTR:               websiteCtx.CTR,
				Position:          websiteCtx.Position,
				SEOScore:          websiteCtx.SEOScore,
				ImpressionsChange: websiteCtx.ImpressionsChange,
				ClicksChange:      websiteCtx.ClicksChange,
				CTRChange:         websiteCtx.CTRChange,
				PositionChange:    websiteCtx.PositionChange,
			}

			// Add weekly data for "last week" queries
			if websiteCtx.WeeklyMetrics != nil {
				wm := websiteCtx.WeeklyMetrics
				metricsData.WeeklyData = &gemini.WeeklyData{
					LastWeekImpressions: wm.LastWeekImpressions,
					LastWeekClicks:      wm.LastWeekClicks,
					LastWeekCTR:         wm.LastWeekCTR,
					LastWeekPosition:    wm.LastWeekPosition,
					PrevWeekImpressions: wm.PrevWeekImpressions,
					PrevWeekClicks:      wm.PrevWeekClicks,
					PrevWeekCTR:         wm.PrevWeekCTR,
					PrevWeekPosition:    wm.PrevWeekPosition,
					ImpressionsChange:   wm.ImpressionsChange,
					ClicksChange:        wm.ClicksChange,
					CTRChange:           wm.CTRChange,
					PositionChange:      wm.PositionChange,
				}
			}

			// Add daily trend data for "show trends" queries
			if len(websiteCtx.DailyTrend) > 0 {
				for _, day := range websiteCtx.DailyTrend {
					metricsData.DailyTrend = append(metricsData.DailyTrend, gemini.DailyPoint{
						Date:        day.Date,
						Impressions: day.Impressions,
						Clicks:      day.Clicks,
						CTR:         day.CTR,
						Position:    day.Position,
					})
				}
			}
		}
	}

	// Fetch audit context for injection
	var auditData *gemini.AuditContext
	if s.auditProvider != nil {
		auditCtx, err := s.auditProvider.GetLatestAuditContext(ctx, userEmail, websiteURL)
		if err == nil && auditCtx != nil {
			auditData = &gemini.AuditContext{
				AuditDate: auditCtx.AuditDate,
				SEOScore:  auditCtx.SEOScore,
				SEOStage:  auditCtx.SEOStage,
			}
			// Convert issues
			for _, issue := range auditCtx.Issues {
				auditData.Issues = append(auditData.Issues, gemini.AuditIssue{
					Severity:    issue.Severity,
					Title:       issue.Title,
					Description: issue.Description,
				})
			}
		}
	}

	// Build base enhanced prompt
	basePrompt := gemini.BuildEnhancedSystemPrompt(websiteURL, metricsData, auditData)

	// Add RAG context if available (1:1 with Python)
	if s.ragProvider != nil && userQuery != "" {
		ragContext, err := s.ragProvider.GetRAGContext(ctx, userEmail, userQuery, websiteURL)
		if err == nil && ragContext != "" {
			basePrompt += "\n\n## RELEVANT KNOWLEDGE BASE CONTEXT:\n" + ragContext
		}
	}

	return basePrompt
}

// indexInteraction indexes the chat interaction for future RAG retrieval
func (s *ChatService) indexInteraction(ctx context.Context, userEmail, websiteURL, query, response string) {
	if s.ragProvider != nil {
		// Index asynchronously to not block response
		go func() {
			_ = s.ragProvider.IndexInteraction(context.Background(), userEmail, websiteURL, query, response)
		}()
	}
}

// GetConversation retrieves a conversation by ID
func (s *ChatService) GetConversation(ctx context.Context, id int64, userEmail string) (*domain.ConversationWithMessages, error) {
	conv, err := s.repo.GetConversation(ctx, id)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	if conv == nil {
		return nil, apperrors.NotFoundError("Conversation", fmt.Sprintf("%d", id))
	}

	if conv.UserEmail != userEmail {
		return nil, apperrors.ForbiddenError("Access denied")
	}

	messages, err := s.repo.GetMessagesByConversation(ctx, id, 100)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return &domain.ConversationWithMessages{
		Conversation: conv,
		Messages:     messages,
	}, nil
}

// GetConversations retrieves all conversations for a user
func (s *ChatService) GetConversations(ctx context.Context, userEmail string, limit int) ([]domain.Conversation, error) {
	if limit <= 0 || limit > 50 {
		limit = 20
	}

	conversations, err := s.repo.GetConversationsByUser(ctx, userEmail, limit)
	if err != nil {
		return nil, apperrors.DatabaseError(err)
	}

	return conversations, nil
}

// DeleteConversation deletes a conversation
func (s *ChatService) DeleteConversation(ctx context.Context, id int64, userEmail string) error {
	conv, err := s.repo.GetConversation(ctx, id)
	if err != nil {
		return apperrors.DatabaseError(err)
	}

	if conv == nil {
		return apperrors.NotFoundError("Conversation", fmt.Sprintf("%d", id))
	}

	if conv.UserEmail != userEmail {
		return apperrors.ForbiddenError("Access denied")
	}

	if err := s.repo.DeleteConversation(ctx, id); err != nil {
		return apperrors.DatabaseError(err)
	}

	return nil
}

// UpdateConversationTitle updates the title of a conversation
func (s *ChatService) UpdateConversationTitle(ctx context.Context, id int64, userEmail, title string) error {
	conv, err := s.repo.GetConversation(ctx, id)
	if err != nil {
		return apperrors.DatabaseError(err)
	}

	if conv == nil {
		return apperrors.NotFoundError("Conversation", fmt.Sprintf("%d", id))
	}

	if conv.UserEmail != userEmail {
		return apperrors.ForbiddenError("Access denied")
	}

	conv.Title = title
	if err := s.repo.UpdateConversation(ctx, conv); err != nil {
		return apperrors.DatabaseError(err)
	}

	return nil
}

// generateTitle generates a title from the first message
func generateTitle(message string) string {
	// Take first 50 chars or first sentence
	title := message
	if idx := strings.Index(title, "."); idx > 0 && idx < 50 {
		title = title[:idx]
	} else if idx := strings.Index(title, "?"); idx > 0 && idx < 50 {
		title = title[:idx+1]
	} else if len(title) > 50 {
		title = title[:47] + "..."
	}

	return strings.TrimSpace(title)
}
