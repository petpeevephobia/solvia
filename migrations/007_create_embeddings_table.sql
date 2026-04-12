-- ============================================================================
-- EMBEDDINGS TABLE FOR RAG (1:1 with Python Supabase pgvector implementation)
-- ============================================================================

-- Enable pgvector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table for RAG document storage
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    website_url TEXT,
    collection_name TEXT NOT NULL,
    document_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- text-embedding-3-small produces 1536 dimensions
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint for deduplication
    UNIQUE(user_email, collection_name, document_id)
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_embeddings_user_email ON embeddings(user_email);
CREATE INDEX IF NOT EXISTS idx_embeddings_website_url ON embeddings(website_url);
CREATE INDEX IF NOT EXISTS idx_embeddings_collection ON embeddings(collection_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_user_website ON embeddings(user_email, website_url);

-- Create HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING hnsw (embedding vector_cosine_ops);

-- Enable RLS for user isolation
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- RLS policy: Users can only access their own embeddings
DROP POLICY IF EXISTS embeddings_user_policy ON embeddings;
CREATE POLICY embeddings_user_policy ON embeddings
    FOR ALL USING (user_email = current_setting('app.current_user_email', true));

-- Grant permissions (Supabase roles; skip on vanilla Postgres / local Docker)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    GRANT ALL ON embeddings TO authenticated;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    GRANT ALL ON embeddings TO service_role;
  END IF;
END $$;

-- Comment on table
COMMENT ON TABLE embeddings IS 'RAG embeddings table for semantic search (1:1 with Python Supabase implementation)';
COMMENT ON COLUMN embeddings.collection_name IS 'Collection categories: gsc_data, audit_results, seo_knowledge, user_interactions';
COMMENT ON COLUMN embeddings.embedding IS 'OpenAI text-embedding-3-small 1536-dimensional vector';
