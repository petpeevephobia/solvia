package rag

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

// ============================================================================
// RAG AGENT (1:1 with Python supabase_rag_agent.py)
// ============================================================================

// Config holds RAG configuration
type Config struct {
	Model             string   // GPT model for responses
	EmbeddingModel    string   // Embedding model
	MaxContextLength  int      // Max context length
	MinRelevanceScore float64  // Minimum relevance threshold
	MaxResults        int      // Maximum search results
	Temperature       float64  // Response temperature
	CollectionsToSearch []string
}

// DefaultConfig returns the default RAG configuration (1:1 with Python)
// Updated for Gemini (replaces OpenAI)
func DefaultConfig() *Config {
	return &Config{
		Model:             "gemini-2.5-flash",       // Gemini chat model (replaces gpt-4o-mini)
		EmbeddingModel:    "gemini-embedding-001",   // Gemini embeddings (replaces text-embedding-3-small)
		MaxContextLength:  8000,
		MinRelevanceScore: 0.3, // Lowered from 0.7 for better recall
		MaxResults:        10,
		Temperature:       0.7, // Adjusted for Gemini (not as low as 0.3)
		CollectionsToSearch: []string{
			"gsc_data",
			"audit_results",
			"seo_knowledge",
			"user_interactions",
		},
	}
}

// SearchResult represents a search result from RAG (1:1 with Python)
type SearchResult struct {
	Content    string                 `json:"content"`
	Relevance  float64                `json:"relevance"`
	Collection string                 `json:"collection"`
	Metadata   map[string]interface{} `json:"metadata"`
	CreatedAt  time.Time              `json:"created_at"`
}

// Agent handles RAG operations with Supabase pgvector (1:1 with Python)
type Agent struct {
	db               *pgxpool.Pool
	embeddingGenerator EmbeddingGenerator // Interface for OpenAI or Gemini
	config           *Config
}

// NewAgent creates a new RAG agent
// embeddingGenerator can be OpenAI or Gemini embeddings client (implements EmbeddingGenerator interface)
func NewAgent(db *pgxpool.Pool, embeddingGenerator EmbeddingGenerator, config *Config) *Agent {
	if config == nil {
		config = DefaultConfig()
	}
	return &Agent{
		db:                 db,
		embeddingGenerator: embeddingGenerator,
		config:             config,
	}
}

// generateDocumentID generates deterministic document ID for deduplication (1:1 with Python)
func generateDocumentID(content, collection, userEmail string) string {
	idString := fmt.Sprintf("%s|%s|%s", userEmail, collection, content[:min(200, len(content))])
	hash := sha256.Sum256([]byte(idString))
	return hex.EncodeToString(hash[:])[:16]
}

// IndexDocument indexes a document into pgvector (1:1 with Python)
func (a *Agent) IndexDocument(
	ctx context.Context,
	userEmail string,
	content string,
	collectionName string,
	metadata map[string]interface{},
	websiteURL string,
) error {
	// Generate embedding
	embedding, err := a.embeddingGenerator.GenerateEmbedding(ctx, content)
	if err != nil {
		return fmt.Errorf("failed to generate embedding: %w", err)
	}

	// Generate unique document ID
	documentID := generateDocumentID(content, collectionName, userEmail)

	// Limit content size
	if len(content) > 10000 {
		content = content[:10000]
	}

	// Marshal metadata
	metadataJSON, err := json.Marshal(metadata)
	if err != nil {
		metadataJSON = []byte("{}")
	}

	// Convert embedding to pgvector format
	embeddingStr := float32SliceToVectorString(embedding)

	// Upsert into database
	query := `
		INSERT INTO embeddings (user_email, website_url, collection_name, document_id, content, embedding, metadata, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6::vector, $7::jsonb, NOW(), NOW())
		ON CONFLICT (user_email, collection_name, document_id)
		DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata, updated_at = NOW()
	`

	_, err = a.db.Exec(ctx, query, userEmail, websiteURL, collectionName, documentID, content, embeddingStr, metadataJSON)
	if err != nil {
		return fmt.Errorf("failed to index document: %w", err)
	}

	return nil
}

// SearchSimilar searches for similar documents (1:1 with Python)
func (a *Agent) SearchSimilar(
	ctx context.Context,
	userEmail string,
	query string,
	collections []string,
	websiteURL string,
	limit int,
) ([]SearchResult, error) {
	if collections == nil {
		collections = a.config.CollectionsToSearch
	}
	if limit == 0 {
		limit = a.config.MaxResults
	}

	// Generate query embedding
	embedding, err := a.embeddingGenerator.GenerateEmbedding(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("failed to generate query embedding: %w", err)
	}

	embeddingStr := float32SliceToVectorString(embedding)

	// Build SQL query with cosine similarity
	sqlQuery := `
		SELECT
			content,
			1 - (embedding <=> $1::vector) as relevance,
			collection_name,
			metadata,
			created_at
		FROM embeddings
		WHERE user_email = $2
		AND collection_name = ANY($3)
		AND ($4 = '' OR website_url = $4)
		AND 1 - (embedding <=> $1::vector) >= $5
		ORDER BY embedding <=> $1::vector
		LIMIT $6
	`

	rows, err := a.db.Query(ctx, sqlQuery,
		embeddingStr,
		userEmail,
		collections,
		websiteURL,
		a.config.MinRelevanceScore,
		limit,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to search embeddings: %w", err)
	}
	defer rows.Close()

	var results []SearchResult
	for rows.Next() {
		var result SearchResult
		var metadataJSON []byte

		if err := rows.Scan(&result.Content, &result.Relevance, &result.Collection, &metadataJSON, &result.CreatedAt); err != nil {
			continue
		}

		_ = json.Unmarshal(metadataJSON, &result.Metadata)
		results = append(results, result)
	}

	return results, rows.Err()
}

// BuildContext builds RAG context from search results (1:1 with Python)
func (a *Agent) BuildContext(results []SearchResult) string {
	if len(results) == 0 {
		return ""
	}

	var context string
	totalLength := 0

	for _, result := range results {
		if totalLength+len(result.Content) > a.config.MaxContextLength {
			break
		}

		context += fmt.Sprintf("\n[Source: %s, Relevance: %.2f]\n%s\n",
			result.Collection, result.Relevance, result.Content)
		totalLength += len(result.Content)
	}

	return context
}

// GetRAGContext gets relevant context for a query (1:1 with Python)
func (a *Agent) GetRAGContext(
	ctx context.Context,
	userEmail string,
	query string,
	websiteURL string,
) (string, interface{}, error) {
	results, err := a.SearchSimilar(ctx, userEmail, query, nil, websiteURL, 0)
	if err != nil {
		return "", nil, err
	}

	context := a.BuildContext(results)
	return context, results, nil
}

// IndexGSCData indexes GSC metrics data (1:1 with Python)
func (a *Agent) IndexGSCData(
	ctx context.Context,
	userEmail string,
	websiteURL string,
	metricsData map[string]interface{},
) error {
	content, _ := json.MarshalIndent(metricsData, "", "  ")

	metadata := map[string]interface{}{
		"type":       "gsc_metrics",
		"website":    websiteURL,
		"indexed_at": time.Now().Format(time.RFC3339),
	}

	return a.IndexDocument(ctx, userEmail, string(content), "gsc_data", metadata, websiteURL)
}

// IndexAuditResult indexes audit results (1:1 with Python)
func (a *Agent) IndexAuditResult(
	ctx context.Context,
	userEmail string,
	websiteURL string,
	auditData map[string]interface{},
) error {
	content, _ := json.MarshalIndent(auditData, "", "  ")

	metadata := map[string]interface{}{
		"type":       "audit_result",
		"website":    websiteURL,
		"indexed_at": time.Now().Format(time.RFC3339),
	}

	return a.IndexDocument(ctx, userEmail, string(content), "audit_results", metadata, websiteURL)
}

// IndexSEOKnowledge indexes SEO knowledge base content
func (a *Agent) IndexSEOKnowledge(
	ctx context.Context,
	userEmail string,
	topic string,
	content string,
) error {
	metadata := map[string]interface{}{
		"type":       "seo_knowledge",
		"topic":      topic,
		"indexed_at": time.Now().Format(time.RFC3339),
	}

	return a.IndexDocument(ctx, userEmail, content, "seo_knowledge", metadata, "")
}

// float32SliceToVectorString converts float32 slice to PostgreSQL vector string
func float32SliceToVectorString(v []float32) string {
	if len(v) == 0 {
		return "[]"
	}

	result := "["
	for i, val := range v {
		if i > 0 {
			result += ","
		}
		result += fmt.Sprintf("%f", val)
	}
	result += "]"
	return result
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
