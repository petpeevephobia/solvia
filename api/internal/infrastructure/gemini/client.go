package gemini

import (
	"context"
	"fmt"
	"time"

	"github.com/rs/zerolog/log"
	"google.golang.org/genai"
)

// ============================================================================
// GEMINI CLIENT (Replaces OpenAI - 1:1 parity with Python)
// ============================================================================

const (
	// Model constants
	DefaultChatModel      = "gemini-2.0-flash"      // Best balance of speed/quality
	DefaultEmbeddingModel = "text-embedding-004"    // Latest embedding model

	// Temperature settings
	// Note: Gemini 3 models recommend 1.0, but for RAG we use lower
	DefaultTemperature = 1.0  // Gemini recommended for creative tasks
	RAGTemperature     = 0.7  // Lower for more deterministic RAG responses (not as low as 0.3)
	ChatTemperature    = 0.9  // Slightly lower for chat

	// Token limits (enhanced for rich context with historical data)
	DefaultMaxTokens = 2000 // Default for most responses
	RAGMaxTokens     = 3000 // Higher for RAG responses with context
	ChatMaxTokens    = 3000 // Higher for chat with weekly/daily data context
	BenchmarkTokens  = 3000 // For benchmark analysis

	// Embedding dimension (configurable: 768, 1536, 3072)
	EmbeddingDimension = 768 // Optimized for efficiency, compatible with pgvector

	// Timeout
	DefaultTimeout = 60 * time.Second
)

// Client wraps the Google Generative AI client for Gemini
type Client struct {
	client     *genai.Client
	chatModel  string
	embedModel string
}

// Message represents a chat message (compatible interface with previous OpenAI)
type Message struct {
	Role    string `json:"role"`    // "system", "user", "assistant"
	Content string `json:"content"`
}

// ChatResponse represents a chat completion response
type ChatResponse struct {
	Content string
	Model   string
	Usage   UsageStats
}

// UsageStats represents token usage
type UsageStats struct {
	PromptTokens     int
	CompletionTokens int
	TotalTokens      int
}

// NewClient creates a new Gemini client
// API Key should be set via GEMINI_API_KEY env var or passed directly
func NewClient(ctx context.Context, apiKey string) (*Client, error) {
	if apiKey == "" {
		return nil, fmt.Errorf("Gemini API key is required")
	}

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		APIKey:  apiKey,
		Backend: genai.BackendGeminiAPI,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create Gemini client: %w", err)
	}

	return &Client{
		client:     client,
		chatModel:  DefaultChatModel,
		embedModel: DefaultEmbeddingModel,
	}, nil
}

// WithChatModel sets a custom chat model
func (c *Client) WithChatModel(model string) *Client {
	c.chatModel = model
	return c
}

// WithEmbeddingModel sets a custom embedding model
func (c *Client) WithEmbeddingModel(model string) *Client {
	c.embedModel = model
	return c
}

// Chat sends a chat completion request with default settings
// 1:1 with Python routes.py:952 - temperature 0.7 (adjusted for Gemini)
func (c *Client) Chat(ctx context.Context, messages []Message) (*ChatResponse, error) {
	return c.ChatWithOptions(ctx, messages, ChatMaxTokens, ChatTemperature)
}

// ChatWithRAG sends a chat completion request with RAG-optimized settings
// 1:1 with Python supabase_rag_agent.py - lower temperature for deterministic responses
func (c *Client) ChatWithRAG(ctx context.Context, messages []Message) (*ChatResponse, error) {
	return c.ChatWithOptions(ctx, messages, RAGMaxTokens, RAGTemperature)
}

// ChatWithBenchmark sends a chat for benchmark insights generation
// 1:1 with Python benchmark_analyzer.py - higher token limit for detailed analysis
func (c *Client) ChatWithBenchmark(ctx context.Context, messages []Message) (*ChatResponse, error) {
	return c.ChatWithOptions(ctx, messages, BenchmarkTokens, RAGTemperature)
}

// ChatWithOptions sends a chat completion request with custom options
func (c *Client) ChatWithOptions(ctx context.Context, messages []Message, maxTokens int, temperature float64) (*ChatResponse, error) {
	// Extract system instruction and convert messages to Gemini format
	var systemInstruction *genai.Content
	var contents []*genai.Content

	for _, msg := range messages {
		switch msg.Role {
		case "system":
			// Gemini uses SystemInstruction in config, not in messages
			// SystemInstruction should NOT have a Role - just Parts
			systemInstruction = &genai.Content{
				Parts: []*genai.Part{{Text: msg.Content}},
			}
		case "user":
			contents = append(contents, &genai.Content{
				Parts: []*genai.Part{{Text: msg.Content}},
				Role:  genai.RoleUser,
			})
		case "assistant", "model":
			contents = append(contents, &genai.Content{
				Parts: []*genai.Part{{Text: msg.Content}},
				Role:  genai.RoleModel,
			})
		}
	}

	// Build config
	temp := float32(temperature)
	tokens := int32(maxTokens)

	config := &genai.GenerateContentConfig{
		Temperature:     &temp,
		MaxOutputTokens: tokens,
	}

	// Add system instruction if present
	if systemInstruction != nil {
		config.SystemInstruction = systemInstruction
	}

	// Generate content
	result, err := c.client.Models.GenerateContent(ctx, c.chatModel, contents, config)
	if err != nil {
		return nil, fmt.Errorf("Gemini API error: %w", err)
	}

	// Extract response text - with debug logging
	responseText := ""

	// Debug: Log raw response structure
	log.Debug().
		Int("candidates_count", len(result.Candidates)).
		Bool("has_usage_metadata", result.UsageMetadata != nil).
		Str("model", c.chatModel).
		Msg("[GEMINI] Response received")

	// Try result.Text() first
	responseText = result.Text()

	// If Text() returns empty, manually extract from candidates
	if responseText == "" && len(result.Candidates) > 0 {
		log.Debug().Msg("[GEMINI] Text() returned empty, extracting from candidates manually")
		candidate := result.Candidates[0]

		// Log finish reason first
		if candidate.FinishReason != "" {
			log.Debug().Str("finish_reason", string(candidate.FinishReason)).Msg("[GEMINI] Candidate finish reason")
		}

		// Try to extract from content
		if candidate.Content != nil {
			log.Debug().
				Int("parts_count", len(candidate.Content.Parts)).
				Str("role", string(candidate.Content.Role)).
				Msg("[GEMINI] Candidate content structure")

			for i, part := range candidate.Content.Parts {
				// Log part details
				log.Debug().
					Int("part_index", i).
					Int("text_len", len(part.Text)).
					Msg("[GEMINI] Part details")

				if part.Text != "" {
					responseText += part.Text
				}
			}
		} else {
			log.Warn().Msg("[GEMINI] Candidate content is nil")
		}
	}

	// Log if still empty
	if responseText == "" {
		log.Warn().
			Int("candidates_count", len(result.Candidates)).
			Msg("[GEMINI] WARNING: Response text is empty after all extraction attempts")
	} else {
		log.Debug().
			Int("response_length", len(responseText)).
			Msg("[GEMINI] Successfully extracted response text")
	}

	// Build usage stats from response metadata
	var usage UsageStats
	if result.UsageMetadata != nil {
		usage = UsageStats{
			PromptTokens:     int(result.UsageMetadata.PromptTokenCount),
			CompletionTokens: int(result.UsageMetadata.CandidatesTokenCount),
			TotalTokens:      int(result.UsageMetadata.TotalTokenCount),
		}
	}

	return &ChatResponse{
		Content: responseText,
		Model:   c.chatModel,
		Usage:   usage,
	}, nil
}

// GetContent extracts the content from a response (compatibility method)
func (r *ChatResponse) GetContent() string {
	return r.Content
}

// Close closes the client connection
func (c *Client) Close() error {
	// genai.Client doesn't require explicit closing in current implementation
	// but we keep this for interface compatibility
	return nil
}
