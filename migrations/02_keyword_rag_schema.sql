-- =========================================
-- Keyword-Based RAG System Schema
-- =========================================
-- Alternative to vector embeddings using PostgreSQL full-text search
-- Run this in Supabase SQL Editor

-- =========================================
-- STEP 1: Create Keyword Documents Table
-- =========================================

-- Main documents table for keyword-based RAG
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

-- =========================================
-- STEP 2: Create Full-Text Search Indexes
-- =========================================

-- Full-text search index on search_vector
CREATE INDEX IF NOT EXISTS idx_keyword_documents_search 
ON keyword_documents 
USING GIN(search_vector);

-- Additional indexes for filtering
CREATE INDEX IF NOT EXISTS idx_keyword_documents_user_email ON keyword_documents(user_email);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_collection ON keyword_documents(collection_name);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_website ON keyword_documents(website_url);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_metadata ON keyword_documents USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_keyword_documents_created ON keyword_documents(created_at DESC);

-- =========================================
-- STEP 3: Auto-Update Search Vector Trigger
-- =========================================

-- Function to automatically update search_vector when content changes
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

-- =========================================
-- STEP 4: Enable Row Level Security (RLS)
-- =========================================

-- Enable RLS on keyword_documents table
ALTER TABLE keyword_documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own documents
CREATE POLICY "Users can view own keyword documents" 
ON keyword_documents FOR SELECT
USING (user_email = current_setting('app.current_user_email', true));

-- Policy: Users can insert their own documents
CREATE POLICY "Users can insert own keyword documents" 
ON keyword_documents FOR INSERT
WITH CHECK (user_email = current_setting('app.current_user_email', true));

-- Policy: Users can update their own documents
CREATE POLICY "Users can update own keyword documents" 
ON keyword_documents FOR UPDATE
USING (user_email = current_setting('app.current_user_email', true));

-- Policy: Users can delete their own documents
CREATE POLICY "Users can delete own keyword documents" 
ON keyword_documents FOR DELETE
USING (user_email = current_setting('app.current_user_email', true));

-- =========================================
-- STEP 5: Create Search Functions
-- =========================================

-- Function for full-text search with user isolation
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
    created_at TIMESTAMPTZ,
    matched_terms TEXT[]
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
        d.created_at,
        ARRAY[]::TEXT[] AS matched_terms  -- Placeholder for matched terms
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

-- Function to search across multiple collections with ranking
CREATE OR REPLACE FUNCTION search_documents_multi_collection(
    search_query TEXT,
    query_user_email TEXT,
    collections TEXT[] DEFAULT ARRAY['gsc_data', 'audit_results', 'seo_knowledge', 'user_interactions'],
    match_count INT DEFAULT 10,
    min_rank FLOAT DEFAULT 0.1
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
        AND d.collection_name = ANY(collections)
        AND d.search_vector @@ to_tsquery('english', search_query)
        AND ts_rank(d.search_vector, to_tsquery('english', search_query)) > min_rank
    ORDER BY rank_score DESC
    LIMIT match_count;
END;
$$;

-- Function to get user's document statistics
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
-- STEP 6: Search Enhancement Functions
-- =========================================

-- Function to suggest similar terms (for query expansion)
CREATE OR REPLACE FUNCTION get_similar_terms(
    search_term TEXT,
    query_user_email TEXT,
    limit_results INT DEFAULT 5
)
RETURNS TABLE (
    term TEXT,
    frequency BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Set the user context for RLS
    PERFORM set_config('app.current_user_email', query_user_email, true);
    
    RETURN QUERY
    SELECT 
        word,
        nentry as frequency
    FROM ts_stat(
        'SELECT search_vector FROM keyword_documents WHERE user_email = ''' || query_user_email || ''''
    )
    WHERE word ILIKE '%' || search_term || '%'
    ORDER BY frequency DESC
    LIMIT limit_results;
END;
$$;

-- Function to get document highlights (snippets with matched terms)
CREATE OR REPLACE FUNCTION get_search_highlights(
    search_query TEXT,
    document_content TEXT,
    max_words INT DEFAULT 50
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN ts_headline(
        'english',
        document_content,
        to_tsquery('english', search_query),
        'MaxWords=' || max_words || ', MinWords=20, StartSel=<mark>, StopSel=</mark>'
    );
END;
$$;

-- =========================================
-- STEP 7: Grant Permissions
-- =========================================

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON keyword_documents TO authenticated;
GRANT EXECUTE ON FUNCTION search_documents_fulltext TO authenticated;
GRANT EXECUTE ON FUNCTION search_documents_multi_collection TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_document_stats TO authenticated;
GRANT EXECUTE ON FUNCTION get_similar_terms TO authenticated;
GRANT EXECUTE ON FUNCTION get_search_highlights TO authenticated;
GRANT USAGE ON SEQUENCE keyword_documents_id_seq TO authenticated;

-- =========================================
-- STEP 8: Sample Data and Testing
-- =========================================

-- Insert sample SEO knowledge for testing
INSERT INTO keyword_documents (
    user_email, 
    collection_name, 
    document_id, 
    content, 
    search_content,
    metadata
) VALUES 
(
    'test@solvia.app',
    'seo_knowledge',
    'seo_basics_001',
    'SEO Fundamentals: Search Engine Optimization involves improving website visibility in search results through technical optimization, content quality, and link building strategies.',
    'seo search engine optimization website visibility search results technical optimization content quality link building strategies fundamentals',
    '{"type": "knowledge", "category": "fundamentals", "priority": "high"}'
),
(
    'test@solvia.app',
    'seo_knowledge',
    'technical_seo_002',
    'Technical SEO includes site speed optimization, mobile responsiveness, structured data implementation, XML sitemaps, and proper URL structure for better search engine crawling.',
    'technical seo site speed optimization mobile responsive structured data xml sitemaps url structure search engine crawling',
    '{"type": "knowledge", "category": "technical", "priority": "high"}'
)
ON CONFLICT (user_email, collection_name, document_id) DO NOTHING;

-- =========================================
-- VERIFICATION QUERIES
-- =========================================

-- Test full-text search function
SELECT * FROM search_documents_fulltext(
    'seo optimization',
    'test@solvia.app',
    'seo_knowledge',
    5,
    0.1
);

-- Check table creation
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name = 'keyword_documents';

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'keyword_documents';

-- Test search vector creation
SELECT 
    content,
    search_vector,
    ts_rank(search_vector, to_tsquery('english', 'seo & optimization')) as rank
FROM keyword_documents 
WHERE user_email = 'test@solvia.app'
ORDER BY rank DESC;