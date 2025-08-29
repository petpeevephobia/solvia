-- =========================================
-- STEP 1: Enable pgvector Extension
-- =========================================
-- Run this in Supabase SQL Editor

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

-- =========================================
-- STEP 2: Create Embeddings Tables
-- =========================================

-- Main embeddings table for all vector data
CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    website_url TEXT,
    collection_name TEXT NOT NULL, -- Replaces ChromaDB collections
    document_id TEXT NOT NULL,     -- Unique ID for deduplication
    content TEXT NOT NULL,         -- Original text content
    embedding vector(1536),        -- OpenAI text-embedding-3-small dimensions
    metadata JSONB DEFAULT '{}',   -- Flexible metadata storage
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique documents per user/collection
    UNIQUE(user_email, collection_name, document_id)
);

-- Index for vector similarity search (using ivfflat for better performance)
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
ON embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for filtering
CREATE INDEX IF NOT EXISTS idx_embeddings_user_email ON embeddings(user_email);
CREATE INDEX IF NOT EXISTS idx_embeddings_collection ON embeddings(collection_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_website ON embeddings(website_url);
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata ON embeddings USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_embeddings_created ON embeddings(created_at DESC);

-- =========================================
-- STEP 3: Collection Types Table
-- =========================================

-- Define the collection types (replaces ChromaDB collections)
CREATE TABLE IF NOT EXISTS embedding_collections (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default collections
INSERT INTO embedding_collections (name, description, metadata) VALUES
    ('gsc_data', 'Google Search Console metrics and performance data', '{"type": "performance", "source": "gsc"}'),
    ('audit_results', 'SEO audit results and recommendations', '{"type": "audit", "source": "analysis"}'),
    ('seo_knowledge', 'SEO best practices and educational content', '{"type": "knowledge", "source": "static"}'),
    ('user_interactions', 'User chat history and learned patterns', '{"type": "interaction", "source": "chat"}'),
    ('website_content', 'Indexed website content and pages', '{"type": "content", "source": "website"}')
ON CONFLICT (name) DO NOTHING;

-- =========================================
-- STEP 4: Enable Row Level Security (RLS)
-- =========================================

-- Enable RLS on embeddings table
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own embeddings
CREATE POLICY "Users can view own embeddings" 
ON embeddings FOR SELECT
USING (user_email = current_setting('app.current_user_email', true));

-- Policy: Users can insert their own embeddings
CREATE POLICY "Users can insert own embeddings" 
ON embeddings FOR INSERT
WITH CHECK (user_email = current_setting('app.current_user_email', true));

-- Policy: Users can update their own embeddings
CREATE POLICY "Users can update own embeddings" 
ON embeddings FOR UPDATE
USING (user_email = current_setting('app.current_user_email', true));

-- Policy: Users can delete their own embeddings
CREATE POLICY "Users can delete own embeddings" 
ON embeddings FOR DELETE
USING (user_email = current_setting('app.current_user_email', true));

-- =========================================
-- STEP 5: Create Helper Functions
-- =========================================

-- Function to search similar vectors with user isolation
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(1536),
    query_user_email TEXT,
    query_collection TEXT DEFAULT NULL,
    match_count INT DEFAULT 10,
    match_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    collection_name TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Set the user context for RLS
    PERFORM set_config('app.current_user_email', query_user_email, true);
    
    RETURN QUERY
    SELECT 
        e.id,
        e.content,
        e.metadata,
        1 - (e.embedding <=> query_embedding) AS similarity,
        e.collection_name,
        e.created_at
    FROM embeddings e
    WHERE 
        e.user_email = query_user_email
        AND (query_collection IS NULL OR e.collection_name = query_collection)
        AND 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to get user's collection statistics
CREATE OR REPLACE FUNCTION get_user_embeddings_stats(query_user_email TEXT)
RETURNS TABLE (
    collection_name TEXT,
    document_count BIGINT,
    last_updated TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.collection_name,
        COUNT(*) as document_count,
        MAX(e.updated_at) as last_updated
    FROM embeddings e
    WHERE e.user_email = query_user_email
    GROUP BY e.collection_name
    ORDER BY document_count DESC;
END;
$$;

-- =========================================
-- STEP 6: Create Update Trigger
-- =========================================

CREATE OR REPLACE FUNCTION update_embeddings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_embeddings_timestamp
    BEFORE UPDATE ON embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_embeddings_updated_at();

-- =========================================
-- STEP 7: Grant Permissions
-- =========================================

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON embeddings TO authenticated;
GRANT SELECT ON embedding_collections TO authenticated;
GRANT EXECUTE ON FUNCTION search_embeddings TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_embeddings_stats TO authenticated;
GRANT USAGE ON SEQUENCE embeddings_id_seq TO authenticated;

-- =========================================
-- VERIFICATION QUERIES
-- =========================================

-- Check if pgvector is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check table creation
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('embeddings', 'embedding_collections');

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'embeddings';