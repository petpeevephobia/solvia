-- =========================================
-- OPTIMIZE SEARCH THRESHOLDS
-- =========================================
-- Update default thresholds for better search recall

-- Update vector search function with better defaults
CREATE OR REPLACE FUNCTION search_embeddings(
    query_embedding vector(1536),
    query_user_email TEXT,
    query_collection TEXT DEFAULT NULL,
    match_count INT DEFAULT 10,
    match_threshold FLOAT DEFAULT 0.3  -- Lowered from 0.7
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity DOUBLE PRECISION,
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
        (1 - (e.embedding <=> query_embedding))::DOUBLE PRECISION AS similarity,
        e.collection_name,
        e.created_at
    FROM embeddings e
    WHERE 
        e.user_email = query_user_email
        AND (query_collection IS NULL OR e.collection_name = query_collection)
        AND (1 - (e.embedding <=> query_embedding)) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Update keyword search function with better defaults
CREATE OR REPLACE FUNCTION search_documents_fulltext(
    search_query TEXT,
    query_user_email TEXT,
    query_collection TEXT DEFAULT NULL,
    match_count INT DEFAULT 10,
    min_rank FLOAT DEFAULT 0.01,  -- Lowered from 0.1
    website_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id BIGINT,
    content TEXT,
    metadata JSONB,
    rank_score DOUBLE PRECISION,
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
        ts_rank(d.search_vector, to_tsquery('english', search_query))::DOUBLE PRECISION AS rank_score,
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

-- Grant permissions
GRANT EXECUTE ON FUNCTION search_embeddings TO authenticated;
GRANT EXECUTE ON FUNCTION search_documents_fulltext TO authenticated;

SELECT 'Search thresholds optimized for better recall' as status;