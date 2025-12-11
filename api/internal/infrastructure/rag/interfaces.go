package rag

import (
	"context"
)

// ============================================================================
// RAG INTERFACES (Clean Architecture - Dependency Inversion)
// ============================================================================

// EmbeddingGenerator defines the interface for generating embeddings
// This allows swapping between OpenAI and Gemini (or any other provider)
type EmbeddingGenerator interface {
	// GenerateEmbedding generates a single embedding vector for text
	GenerateEmbedding(ctx context.Context, text string) ([]float32, error)
}

// ChatGenerator defines the interface for chat completions
// This allows swapping between OpenAI and Gemini
type ChatGenerator interface {
	// Chat generates a chat response from messages
	Chat(ctx context.Context, messages []ChatMessage) (*ChatResult, error)

	// ChatWithRAG generates a chat response with RAG-optimized settings
	ChatWithRAG(ctx context.Context, messages []ChatMessage) (*ChatResult, error)
}

// ChatMessage represents a chat message (provider-agnostic)
type ChatMessage struct {
	Role    string // "system", "user", "assistant"
	Content string
}

// ChatResult represents a chat response (provider-agnostic)
type ChatResult struct {
	Content string
	Model   string
	Usage   struct {
		PromptTokens     int
		CompletionTokens int
		TotalTokens      int
	}
}
