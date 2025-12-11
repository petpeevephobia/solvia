package domain

import (
	"context"
	"fmt"
	"time"
)

// ============================================================================
// AI CLIENT INTERFACE (Supports OpenAI and Gemini)
// ============================================================================

// AIMessage represents a message for AI chat
type AIMessage struct {
	Role    string // "system", "user", "assistant"
	Content string
}

// AIResponse represents a response from AI
type AIResponse struct {
	Content    string
	TokensUsed int
}

// AIClient defines the interface for AI chat clients (OpenAI or Gemini)
// This allows swapping between providers via Clean Architecture DIP
type AIClient interface {
	// Chat generates a chat response with default settings
	Chat(ctx context.Context, messages []AIMessage) (*AIResponse, error)

	// ChatWithRAG generates a chat response with RAG-optimized settings
	ChatWithRAG(ctx context.Context, messages []AIMessage) (*AIResponse, error)
}

// MessageRole represents the role of a message sender
type MessageRole string

const (
	RoleUser      MessageRole = "user"
	RoleAssistant MessageRole = "assistant"
	RoleSystem    MessageRole = "system"
)

// Conversation represents a chat conversation
type Conversation struct {
	ID         int64     `json:"id"`
	UserEmail  string    `json:"user_email"`
	WebsiteURL string    `json:"website_url,omitempty"`
	Title      string    `json:"title"`
	CreatedAt  time.Time `json:"created_at"`
	UpdatedAt  time.Time `json:"updated_at"`
}

// Message represents a chat message
type Message struct {
	ID             int64       `json:"id"`
	ConversationID int64       `json:"conversation_id"`
	Role           MessageRole `json:"role"`
	Content        string      `json:"content"`
	TokensUsed     int         `json:"tokens_used,omitempty"`
	CreatedAt      time.Time   `json:"created_at"`
}

// ChatRequest represents a request to chat
type ChatRequest struct {
	ConversationID int64  `json:"conversation_id,omitempty"`
	Message        string `json:"message" binding:"required"`
	WebsiteURL     string `json:"website_url,omitempty"`
	IncludeMetrics bool   `json:"include_metrics,omitempty"`
}

// ChatResponse represents a chat response (1:1 with Python)
type ChatResponse struct {
	ConversationID int64    `json:"conversation_id"`
	Message        string   `json:"message"`
	TokensUsed     int      `json:"tokens_used"`
	AuditTriggered bool     `json:"audit_triggered,omitempty"` // 1:1 with Python field name
	AuditID        *string  `json:"audit_id,omitempty"`        // 1:1 with Python - audit ID if triggered
	ActionButtons  []string `json:"action_buttons,omitempty"`  // 1:1 with Python - suggested follow-up actions
}

// ConversationWithMessages includes conversation with its messages
type ConversationWithMessages struct {
	Conversation *Conversation `json:"conversation"`
	Messages     []Message     `json:"messages"`
}

// WebsiteContext provides SEO context for the chat (enhanced for historical queries)
type WebsiteContext struct {
	URL               string  `json:"url"`
	Impressions       int     `json:"impressions"`
	Clicks            int     `json:"clicks"`
	CTR               float64 `json:"ctr"`
	Position          float64 `json:"position"`
	SEOScore          float64 `json:"seo_score"`
	ImpressionsChange float64 `json:"impressions_change,omitempty"`
	ClicksChange      float64 `json:"clicks_change,omitempty"`
	CTRChange         float64 `json:"ctr_change,omitempty"`
	PositionChange    float64 `json:"position_change,omitempty"`

	// Weekly data for "last week" queries
	WeeklyMetrics *WeeklyMetrics `json:"weekly_metrics,omitempty"`

	// Daily data for trends
	DailyTrend []DailyPoint `json:"daily_trend,omitempty"`
}

// WeeklyMetrics provides week-over-week comparison (for "last week" queries)
type WeeklyMetrics struct {
	// Last 7 days
	LastWeekImpressions int     `json:"last_week_impressions"`
	LastWeekClicks      int     `json:"last_week_clicks"`
	LastWeekCTR         float64 `json:"last_week_ctr"`
	LastWeekPosition    float64 `json:"last_week_position"`

	// Previous 7 days (for comparison)
	PrevWeekImpressions int     `json:"prev_week_impressions"`
	PrevWeekClicks      int     `json:"prev_week_clicks"`
	PrevWeekCTR         float64 `json:"prev_week_ctr"`
	PrevWeekPosition    float64 `json:"prev_week_position"`

	// Week-over-week changes
	ImpressionsChange float64 `json:"impressions_change"`
	ClicksChange      float64 `json:"clicks_change"`
	CTRChange         float64 `json:"ctr_change"`
	PositionChange    float64 `json:"position_change"`
}

// DailyPoint represents a single day's metrics for trend visualization
type DailyPoint struct {
	Date        string  `json:"date"` // YYYY-MM-DD
	Impressions int     `json:"impressions"`
	Clicks      int     `json:"clicks"`
	CTR         float64 `json:"ctr"`
	Position    float64 `json:"position"`
}

// AuditContext provides audit data for chat context injection (1:1 with Python)
type AuditContext struct {
	AuditDate string       `json:"audit_date"`
	SEOScore  float64      `json:"seo_score"`
	SEOStage  string       `json:"seo_stage"`
	Issues    []AuditIssue `json:"issues,omitempty"`
}

// AuditIssue represents an issue for context
type AuditIssue struct {
	Severity    string `json:"severity"`
	Title       string `json:"title"`
	Description string `json:"description"`
}

// DefaultActionButtons are the hardcoded suggestion buttons (1:1 with Python routes.py:933-938)
var DefaultActionButtons = []string{
	"How was my SEO last week?",
	"Run a new audit",
	"What are my top issues?",
	"Show me traffic trends",
}

func formatInt(n int) string {
	return fmt.Sprintf("%d", n)
}

func formatFloat(f float64) string {
	return fmt.Sprintf("%.2f", f)
}
