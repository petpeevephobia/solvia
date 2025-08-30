-- =========================================
-- SAFE PGVECTOR MIGRATION 
-- =========================================
-- This migration avoids conflicts with existing tables
-- Run this in Supabase SQL Editor

-- =========================================
-- PHASE 1: ENABLE PGVECTOR (SAFE)
-- =========================================

-- Enable pgvector extension for vector similarity search
-- This is safe - it's just enabling an extension
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

-- =========================================
-- PHASE 2: CREATE NEW VECTOR TABLES (SAFE)
-- =========================================

-- Main embeddings table for vector RAG (NEW TABLE - NO CONFLICTS)
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

-- Vector similarity search index (using ivfflat for better performance)
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx 
ON embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Performance indexes for embeddings table
CREATE INDEX IF NOT EXISTS idx_embeddings_user_email ON embeddings(user_email);
CREATE INDEX IF NOT EXISTS idx_embeddings_collection ON embeddings(collection_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_website ON embeddings(website_url);
CREATE INDEX IF NOT EXISTS idx_embeddings_metadata ON embeddings USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_embeddings_created ON embeddings(created_at DESC);

-- =========================================
-- PHASE 3: COLLECTION TYPES TABLE (SAFE)
-- =========================================

-- Define the collection types (NEW TABLE - NO CONFLICTS)
CREATE TABLE IF NOT EXISTS embedding_collections (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default collections (safe - uses ON CONFLICT DO NOTHING)
INSERT INTO embedding_collections (name, description, metadata) VALUES
    ('gsc_data', 'Google Search Console metrics and performance data', '{"type": "performance", "source": "gsc"}'),
    ('audit_results', 'SEO audit results and recommendations', '{"type": "audit", "source": "analysis"}'),
    ('seo_knowledge', 'SEO best practices and educational content', '{"type": "knowledge", "source": "static"}'),
    ('user_interactions', 'User chat history and learned patterns', '{"type": "interaction", "source": "chat"}'),
    ('website_content', 'Indexed website content and pages', '{"type": "content", "source": "website"}')
ON CONFLICT (name) DO NOTHING;

-- =========================================
-- PHASE 4: KEYWORD RAG TABLE (SAFE)
-- =========================================

-- Keyword documents table for full-text search RAG (NEW TABLE - NO CONFLICTS)
CREATE TABLE IF NOT EXISTS keyword_documents (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    website_url TEXT,
    collection_name TEXT NOT NULL, -- Same as vector collections
    document_id TEXT NOT NULL,     -- Unique ID for deduplication
    content TEXT NOT NULL,         -- Original text content
    search_content TEXT NOT NULL,  -- Optimized content for search
    search_vector tsvector,        -- PostgreSQL full-text search vector
    metadata JSONB DEFAULT '{}',   -- Flexible metadata storage
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique documents per user/collection
    UNIQUE(user_email, collection_name, document_id)
);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_keyword_documents_search 
ON keyword_documents 
USING GIN(search_vector);

CREATE INDEX IF NOT EXISTS idx_keyword_documents_user_email ON keyword_documents(user_email);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_collection ON keyword_documents(collection_name);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_website ON keyword_documents(website_url);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_metadata ON keyword_documents USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_created ON keyword_documents(created_at DESC);

-- =========================================
-- PHASE 5: ENABLE ROW LEVEL SECURITY (SAFE)
-- =========================================

-- Enable RLS on embeddings table
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;

-- Embeddings table RLS policies
CREATE POLICY "Users can view own embeddings" 
ON embeddings FOR SELECT
USING (user_email = current_setting('app.current_user_email', true));

CREATE POLICY "Users can insert own embeddings" 
ON embeddings FOR INSERT
WITH CHECK (user_email = current_setting('app.current_user_email', true));

CREATE POLICY "Users can update own embeddings" 
ON embeddings FOR UPDATE
USING (user_email = current_setting('app.current_user_email', true));

CREATE POLICY "Users can delete own embeddings" 
ON embeddings FOR DELETE
USING (user_email = current_setting('app.current_user_email', true));

-- Enable RLS on keyword_documents table
ALTER TABLE keyword_documents ENABLE ROW LEVEL SECURITY;

-- Keyword documents table RLS policies
CREATE POLICY "Users can view own keyword documents" 
ON keyword_documents FOR SELECT
USING (user_email = current_setting('app.current_user_email', true));

CREATE POLICY "Users can insert own keyword documents" 
ON keyword_documents FOR INSERT
WITH CHECK (user_email = current_setting('app.current_user_email', true));

CREATE POLICY "Users can update own keyword documents" 
ON keyword_documents FOR UPDATE
USING (user_email = current_setting('app.current_user_email', true));

CREATE POLICY "Users can delete own keyword documents" 
ON keyword_documents FOR DELETE
USING (user_email = current_setting('app.current_user_email', true));

-- =========================================
-- PHASE 6: AUTO-UPDATE TRIGGERS (SAFE)
-- =========================================

-- Function to automatically update search_vector for keyword documents
CREATE OR REPLACE FUNCTION update_keyword_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the search vector using PostgreSQL's to_tsvector
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.search_content, ''));
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update search vector
CREATE TRIGGER update_keyword_search_vector_trigger
    BEFORE INSERT OR UPDATE ON keyword_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_keyword_search_vector();

-- Function to update embeddings updated_at timestamp
CREATE OR REPLACE FUNCTION update_embeddings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for embeddings timestamp update
CREATE TRIGGER update_embeddings_timestamp
    BEFORE UPDATE ON embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_embeddings_updated_at();

-- =========================================
-- PHASE 7: VECTOR SEARCH FUNCTIONS (SAFE)
-- =========================================

-- Function for vector similarity search with user isolation
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

-- Function for keyword full-text search with user isolation
CREATE OR REPLACE FUNCTION search_documents_fulltext(
    search_query TEXT,
    query_user_email TEXT,
    query_collection TEXT DEFAULT NULL,
    match_count INT DEFAULT 10,
    min_rank FLOAT DEFAULT 0.1,
    website_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    rank_score FLOAT,
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
        d.id,
        d.content,
        d.metadata,
        ts_rank(d.search_vector, to_tsquery('english', search_query)) AS rank_score,
        d.collection_name,
        d.created_at
    FROM keyword_documents d
    WHERE 
        d.user_email = query_user_email
        AND (query_collection IS NULL OR d.collection_name = query_collection)
        AND (website_filter IS NULL OR d.website_url = website_filter)
        AND d.search_vector @@ to_tsquery('english', search_query)
        AND ts_rank(d.search_vector, to_tsquery('english', search_query)) > min_rank
    ORDER BY rank_score DESC
    LIMIT match_count;
END;
$$;

-- Function to get user's embeddings statistics
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

-- Function to get user's keyword documents statistics
CREATE OR REPLACE FUNCTION get_user_document_stats(query_user_email TEXT)
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
        d.collection_name,
        COUNT(*) as document_count,
        MAX(d.updated_at) as last_updated
    FROM keyword_documents d
    WHERE d.user_email = query_user_email
    GROUP BY d.collection_name
    ORDER BY document_count DESC;
END;
$$;

-- =========================================
-- PHASE 8: GRANT PERMISSIONS (SAFE)
-- =========================================

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON embeddings TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON keyword_documents TO authenticated;
GRANT SELECT ON embedding_collections TO authenticated;
GRANT EXECUTE ON FUNCTION search_embeddings TO authenticated;
GRANT EXECUTE ON FUNCTION search_documents_fulltext TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_embeddings_stats TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_document_stats TO authenticated;
GRANT USAGE ON SEQUENCE embeddings_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE keyword_documents_id_seq TO authenticated;

-- =========================================
-- VERIFICATION QUERIES
-- =========================================

-- Check if pgvector is installed
SELECT 
    'pgvector extension' as component,
    CASE WHEN EXISTS (SELECT * FROM pg_extension WHERE extname = 'vector') 
         THEN '✅ Enabled' 
         ELSE '❌ Missing' 
    END as status;

-- Check new tables creation
SELECT 
    table_name,
    '✅ Created' as status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('embeddings', 'keyword_documents', 'embedding_collections')
ORDER BY table_name;

-- Check RLS policies
SELECT 
    tablename,
    COUNT(*) as policy_count
FROM pg_policies 
WHERE tablename IN ('embeddings', 'keyword_documents')
GROUP BY tablename
ORDER BY tablename;

-- Success message
SELECT '🎉 SAFE PGVECTOR MIGRATION COMPLETED SUCCESSFULLY!' as result;