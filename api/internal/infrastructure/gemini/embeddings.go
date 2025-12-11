package gemini

import (
	"context"
	"fmt"
	"math"

	"google.golang.org/genai"
)

// ============================================================================
// GEMINI EMBEDDINGS (1:1 with Python RAG implementation)
// ============================================================================

// EmbeddingTaskType defines the task type for embeddings
// This helps Gemini optimize the embedding for specific use cases
type EmbeddingTaskType string

const (
	// Task types supported by Gemini (1:1 with Python)
	TaskSemanticSimilarity EmbeddingTaskType = "SEMANTIC_SIMILARITY"
	TaskClassification     EmbeddingTaskType = "CLASSIFICATION"
	TaskClustering         EmbeddingTaskType = "CLUSTERING"
	TaskRetrievalDocument  EmbeddingTaskType = "RETRIEVAL_DOCUMENT"
	TaskRetrievalQuery     EmbeddingTaskType = "RETRIEVAL_QUERY"
	TaskQuestionAnswering  EmbeddingTaskType = "QUESTION_ANSWERING"
	TaskFactVerification   EmbeddingTaskType = "FACT_VERIFICATION"
	TaskCodeRetrieval      EmbeddingTaskType = "CODE_RETRIEVAL_QUERY"
)

// EmbeddingConfig holds configuration for embedding generation
type EmbeddingConfig struct {
	Model            string
	Dimension        int
	TaskType         EmbeddingTaskType
	MaxInputLength   int
}

// DefaultEmbeddingConfig returns default embedding configuration
// 1:1 with Python rag_factory.py settings
func DefaultEmbeddingConfig() *EmbeddingConfig {
	return &EmbeddingConfig{
		Model:          DefaultEmbeddingModel,
		Dimension:      EmbeddingDimension, // 768 for efficiency
		TaskType:       TaskRetrievalDocument,
		MaxInputLength: 8000, // Character limit
	}
}

// EmbeddingsClient handles Gemini embeddings generation
// Implements same interface as OpenAI embeddings for compatibility
type EmbeddingsClient struct {
	client *genai.Client
	config *EmbeddingConfig
}

// NewEmbeddingsClient creates a new embeddings client
func NewEmbeddingsClient(ctx context.Context, apiKey string) (*EmbeddingsClient, error) {
	if apiKey == "" {
		return nil, fmt.Errorf("Gemini API key is required for embeddings")
	}

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		APIKey:  apiKey,
		Backend: genai.BackendGeminiAPI,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create Gemini embeddings client: %w", err)
	}

	return &EmbeddingsClient{
		client: client,
		config: DefaultEmbeddingConfig(),
	}, nil
}

// WithDimension sets custom embedding dimension (768, 1536, or 3072)
func (c *EmbeddingsClient) WithDimension(dim int) *EmbeddingsClient {
	if dim == 768 || dim == 1536 || dim == 3072 {
		c.config.Dimension = dim
	}
	return c
}

// WithTaskType sets the task type for embedding optimization
func (c *EmbeddingsClient) WithTaskType(taskType EmbeddingTaskType) *EmbeddingsClient {
	c.config.TaskType = taskType
	return c
}

// GenerateEmbedding generates a single embedding vector for text
// 1:1 with Python supabase_rag_agent.py _generate_embedding()
func (c *EmbeddingsClient) GenerateEmbedding(ctx context.Context, text string) ([]float32, error) {
	// Limit input length (1:1 with Python)
	if len(text) > c.config.MaxInputLength {
		text = text[:c.config.MaxInputLength]
	}

	// Create content for embedding
	content := &genai.Content{
		Parts: []*genai.Part{{Text: text}},
	}

	// Configure embedding request
	dim := int32(c.config.Dimension)
	embedConfig := &genai.EmbedContentConfig{
		OutputDimensionality: &dim,
	}

	// Generate embedding
	result, err := c.client.Models.EmbedContent(ctx, c.config.Model, []*genai.Content{content}, embedConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to generate embedding: %w", err)
	}

	if len(result.Embeddings) == 0 || result.Embeddings[0] == nil || len(result.Embeddings[0].Values) == 0 {
		return nil, fmt.Errorf("no embedding returned from Gemini")
	}

	return result.Embeddings[0].Values, nil
}

// GenerateQueryEmbedding generates embedding optimized for search queries
// Use this for the query side of semantic search
func (c *EmbeddingsClient) GenerateQueryEmbedding(ctx context.Context, query string) ([]float32, error) {
	// Temporarily set task type for query
	originalTask := c.config.TaskType
	c.config.TaskType = TaskRetrievalQuery
	defer func() { c.config.TaskType = originalTask }()

	return c.GenerateEmbedding(ctx, query)
}

// GenerateDocumentEmbedding generates embedding optimized for documents
// Use this for the document side of semantic search
func (c *EmbeddingsClient) GenerateDocumentEmbedding(ctx context.Context, document string) ([]float32, error) {
	// Temporarily set task type for document
	originalTask := c.config.TaskType
	c.config.TaskType = TaskRetrievalDocument
	defer func() { c.config.TaskType = originalTask }()

	return c.GenerateEmbedding(ctx, document)
}

// GenerateBatchEmbeddings generates embeddings for multiple texts
// 1:1 with Python batch embedding functionality
func (c *EmbeddingsClient) GenerateBatchEmbeddings(ctx context.Context, texts []string) ([][]float32, error) {
	embeddings := make([][]float32, len(texts))

	// Gemini doesn't have native batch embedding in the same way as OpenAI
	// We process sequentially with the same configuration
	for i, text := range texts {
		// Limit input length
		if len(text) > c.config.MaxInputLength {
			text = text[:c.config.MaxInputLength]
		}

		embedding, err := c.GenerateEmbedding(ctx, text)
		if err != nil {
			return nil, fmt.Errorf("failed to generate embedding for text %d: %w", i, err)
		}
		embeddings[i] = embedding
	}

	return embeddings, nil
}

// PrepareVectorForPostgres converts embedding to PostgreSQL vector format
// 1:1 with Python _prepare_vector_for_postgres()
func PrepareVectorForPostgres(embedding []float32) string {
	// PostgreSQL pgvector expects format: [0.1, 0.2, 0.3, ...]
	result := "["
	for i, v := range embedding {
		if i > 0 {
			result += ","
		}
		result += fmt.Sprintf("%f", v)
	}
	result += "]"
	return result
}

// CosineSimilarity calculates cosine similarity between two vectors
// 1:1 with Python/previous Go implementation
func CosineSimilarity(a, b []float32) float32 {
	if len(a) != len(b) {
		return 0
	}

	var dotProduct, normA, normB float64
	for i := range a {
		dotProduct += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}

	if normA == 0 || normB == 0 {
		return 0
	}

	return float32(dotProduct / (math.Sqrt(normA) * math.Sqrt(normB)))
}

// NormalizeEmbedding normalizes an embedding vector to unit length
// Important for Gemini embeddings with non-3072 dimensions
func NormalizeEmbedding(embedding []float32) []float32 {
	var norm float64
	for _, v := range embedding {
		norm += float64(v) * float64(v)
	}
	norm = math.Sqrt(norm)

	if norm == 0 {
		return embedding
	}

	normalized := make([]float32, len(embedding))
	for i, v := range embedding {
		normalized[i] = float32(float64(v) / norm)
	}

	return normalized
}
