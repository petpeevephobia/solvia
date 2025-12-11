package adapters

import (
	"context"

	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/gemini"
	"github.com/petpeevephobia/solvia-v2/api/internal/infrastructure/rag"
	"github.com/petpeevephobia/solvia-v2/api/internal/modules/chat/domain"
)

// ============================================================================
// AI CLIENT ADAPTERS (Clean Architecture - Dependency Inversion)
// ============================================================================

// GeminiClientAdapter adapts gemini.Client to domain.AIClient interface
type GeminiClientAdapter struct {
	client *gemini.Client
}

// NewGeminiClientAdapter creates a new Gemini client adapter
func NewGeminiClientAdapter(client *gemini.Client) *GeminiClientAdapter {
	return &GeminiClientAdapter{client: client}
}

// Chat implements domain.AIClient.Chat
func (a *GeminiClientAdapter) Chat(ctx context.Context, messages []domain.AIMessage) (*domain.AIResponse, error) {
	// Convert domain messages to gemini messages
	geminiMessages := make([]gemini.Message, len(messages))
	for i, msg := range messages {
		geminiMessages[i] = gemini.Message{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	// Call Gemini Chat
	response, err := a.client.Chat(ctx, geminiMessages)
	if err != nil {
		return nil, err
	}

	return &domain.AIResponse{
		Content:    response.Content,
		TokensUsed: response.Usage.TotalTokens,
	}, nil
}

// ChatWithRAG implements domain.AIClient.ChatWithRAG
func (a *GeminiClientAdapter) ChatWithRAG(ctx context.Context, messages []domain.AIMessage) (*domain.AIResponse, error) {
	// Convert domain messages to gemini messages
	geminiMessages := make([]gemini.Message, len(messages))
	for i, msg := range messages {
		geminiMessages[i] = gemini.Message{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	// Call Gemini ChatWithRAG
	response, err := a.client.ChatWithRAG(ctx, geminiMessages)
	if err != nil {
		return nil, err
	}

	return &domain.AIResponse{
		Content:    response.Content,
		TokensUsed: response.Usage.TotalTokens,
	}, nil
}

// ============================================================================
// EMBEDDING GENERATOR ADAPTERS
// ============================================================================

// GeminiEmbeddingsAdapter adapts gemini.EmbeddingsClient to rag.EmbeddingGenerator interface
type GeminiEmbeddingsAdapter struct {
	client *gemini.EmbeddingsClient
}

// NewGeminiEmbeddingsAdapter creates a new Gemini embeddings adapter
func NewGeminiEmbeddingsAdapter(client *gemini.EmbeddingsClient) *GeminiEmbeddingsAdapter {
	return &GeminiEmbeddingsAdapter{client: client}
}

// GenerateEmbedding implements rag.EmbeddingGenerator
func (a *GeminiEmbeddingsAdapter) GenerateEmbedding(ctx context.Context, text string) ([]float32, error) {
	return a.client.GenerateEmbedding(ctx, text)
}

// ============================================================================
// BENCHMARK AI CLIENT ADAPTER
// ============================================================================

// GeminiBenchmarkAdapter adapts gemini.Client to benchmark service interface
type GeminiBenchmarkAdapter struct {
	client *gemini.Client
}

// NewGeminiBenchmarkAdapter creates a new Gemini benchmark adapter
func NewGeminiBenchmarkAdapter(client *gemini.Client) *GeminiBenchmarkAdapter {
	return &GeminiBenchmarkAdapter{client: client}
}

// ChatWithBenchmark implements benchmark.BenchmarkAIClient
func (a *GeminiBenchmarkAdapter) ChatWithBenchmark(ctx context.Context, messages []gemini.Message) (*gemini.ChatResponse, error) {
	return a.client.ChatWithBenchmark(ctx, messages)
}

// Ensure adapters implement interfaces at compile time
var _ domain.AIClient = (*GeminiClientAdapter)(nil)
var _ rag.EmbeddingGenerator = (*GeminiEmbeddingsAdapter)(nil)
