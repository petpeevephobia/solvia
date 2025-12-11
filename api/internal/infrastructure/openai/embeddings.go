package openai

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// EmbeddingModel constants (1:1 with Python rag_factory.py)
const (
	EmbeddingModelSmall = "text-embedding-3-small" // 1536 dimensions
	EmbeddingModelAda   = "text-embedding-ada-002" // 1536 dimensions (fallback)
	EmbeddingModelLarge = "text-embedding-3-large" // 3072 dimensions (last resort)
	EmbeddingDimension  = 1536
)

// EmbeddingModelFallbackChain is the fallback chain for embedding models (1:1 with Python)
var EmbeddingModelFallbackChain = []string{
	EmbeddingModelSmall,
	EmbeddingModelAda,
	EmbeddingModelLarge,
}

// EmbeddingsClient handles OpenAI embeddings generation (1:1 with Python)
type EmbeddingsClient struct {
	apiKey     string
	baseURL    string
	model      string
	httpClient *http.Client
}

// NewEmbeddingsClient creates a new embeddings client (1:1 with Python)
func NewEmbeddingsClient(apiKey string) *EmbeddingsClient {
	return &EmbeddingsClient{
		apiKey:     apiKey,
		baseURL:    defaultBaseURL,
		model:      EmbeddingModelSmall,
		httpClient: &http.Client{Timeout: defaultTimeout},
	}
}

// EmbeddingRequest represents an embedding API request
type EmbeddingRequest struct {
	Input interface{} `json:"input"` // string or []string
	Model string      `json:"model"`
}

// EmbeddingResponse represents an embedding API response
type EmbeddingResponse struct {
	Object string          `json:"object"`
	Data   []EmbeddingData `json:"data"`
	Model  string          `json:"model"`
	Usage  struct {
		PromptTokens int `json:"prompt_tokens"`
		TotalTokens  int `json:"total_tokens"`
	} `json:"usage"`
}

// EmbeddingData represents a single embedding result
type EmbeddingData struct {
	Object    string    `json:"object"`
	Embedding []float32 `json:"embedding"`
	Index     int       `json:"index"`
}

// GenerateEmbedding generates a single embedding vector for text (1:1 with Python)
// Uses fallback chain: text-embedding-3-small → text-embedding-ada-002 → text-embedding-3-large
func (c *EmbeddingsClient) GenerateEmbedding(ctx context.Context, text string) ([]float32, error) {
	// Limit input length to 8000 characters (OpenAI recommendation)
	if len(text) > 8000 {
		text = text[:8000]
	}

	// Try each model in the fallback chain (1:1 with Python rag_factory.py)
	var lastErr error
	for _, model := range EmbeddingModelFallbackChain {
		embedding, err := c.generateEmbeddingWithModel(ctx, text, model)
		if err == nil {
			return embedding, nil
		}
		lastErr = err
	}

	return nil, fmt.Errorf("all embedding models failed, last error: %w", lastErr)
}

// generateEmbeddingWithModel generates embedding with a specific model
func (c *EmbeddingsClient) generateEmbeddingWithModel(ctx context.Context, text, model string) ([]float32, error) {
	req := EmbeddingRequest{
		Input: text,
		Model: model,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/embeddings", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		var errResp ErrorResponse
		if err := json.Unmarshal(respBody, &errResp); err == nil {
			return nil, fmt.Errorf("OpenAI API error: %s", errResp.Error.Message)
		}
		return nil, fmt.Errorf("OpenAI API error: status %d", resp.StatusCode)
	}

	var embResp EmbeddingResponse
	if err := json.Unmarshal(respBody, &embResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	if len(embResp.Data) == 0 {
		return nil, fmt.Errorf("no embedding returned")
	}

	return embResp.Data[0].Embedding, nil
}

// GenerateBatchEmbeddings generates embeddings for multiple texts (1:1 with Python)
func (c *EmbeddingsClient) GenerateBatchEmbeddings(ctx context.Context, texts []string) ([][]float32, error) {
	// Limit each text to 8000 characters
	limitedTexts := make([]string, len(texts))
	for i, t := range texts {
		if len(t) > 8000 {
			limitedTexts[i] = t[:8000]
		} else {
			limitedTexts[i] = t
		}
	}

	req := EmbeddingRequest{
		Input: limitedTexts,
		Model: c.model,
	}

	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/embeddings", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	httpReq.Header.Set("Authorization", "Bearer "+c.apiKey)
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("OpenAI API error: status %d", resp.StatusCode)
	}

	var embResp EmbeddingResponse
	if err := json.Unmarshal(respBody, &embResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %w", err)
	}

	embeddings := make([][]float32, len(embResp.Data))
	for i, data := range embResp.Data {
		embeddings[i] = data.Embedding
	}

	return embeddings, nil
}

// CosineSimilarity calculates cosine similarity between two vectors
func CosineSimilarity(a, b []float32) float32 {
	if len(a) != len(b) {
		return 0
	}

	var dotProduct, normA, normB float32
	for i := range a {
		dotProduct += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}

	if normA == 0 || normB == 0 {
		return 0
	}

	return dotProduct / (sqrt(normA) * sqrt(normB))
}

// sqrt helper for float32
func sqrt(x float32) float32 {
	if x < 0 {
		return 0
	}
	// Newton-Raphson iteration
	z := x / 2
	for i := 0; i < 10; i++ {
		z = (z + x/z) / 2
	}
	return z
}
