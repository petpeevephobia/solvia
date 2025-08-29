-- ChromaDB RAG Chat Agent - Supabase Schema Extensions
-- This adds context storage for the enhanced chat agent

-- Create chat_contexts table for storing RAG context data
CREATE TABLE IF NOT EXISTS chat_contexts (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    message_id INTEGER REFERENCES chat_messages(id) ON DELETE CASCADE,
    
    -- Context data from RAG processing
    context_data JSONB NOT NULL DEFAULT '{}',  -- Stores semantic search results
    confidence_scores JSONB DEFAULT '{}',      -- Stores confidence metrics
    intent VARCHAR(50),                        -- Detected intent category
    website_url TEXT,                          -- Associated website
    
    -- Performance metrics
    processing_time_ms INTEGER,                -- Time to generate response
    vectors_searched INTEGER,                  -- Number of vectors searched
    relevance_threshold FLOAT,                 -- Minimum relevance used
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT fk_user_email FOREIGN KEY (user_email) 
        REFERENCES user_sessions(email) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_chat_contexts_user_email ON chat_contexts(user_email);
CREATE INDEX IF NOT EXISTS idx_chat_contexts_message_id ON chat_contexts(message_id);
CREATE INDEX IF NOT EXISTS idx_chat_contexts_intent ON chat_contexts(intent);
CREATE INDEX IF NOT EXISTS idx_chat_contexts_created_at ON chat_contexts(created_at DESC);

-- Enable Row Level Security
ALTER TABLE chat_contexts ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view their own chat contexts" ON chat_contexts
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own chat contexts" ON chat_contexts
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

-- Create vector_indexes table for tracking indexed data
CREATE TABLE IF NOT EXISTS vector_indexes (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    data_type VARCHAR(50) NOT NULL, -- 'gsc_data', 'audit_result', 'content'
    
    -- Indexing metadata
    chunk_count INTEGER DEFAULT 0,
    vector_ids TEXT[], -- Array of ChromaDB vector IDs
    source_data_id VARCHAR(255), -- Reference to source (audit_id, etc)
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending', -- pending, indexed, failed
    error_message TEXT,
    
    -- Timestamps
    indexed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure uniqueness per user/website/type combination
    UNIQUE(user_email, website_url, data_type, source_data_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_vector_indexes_user ON vector_indexes(user_email);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_website ON vector_indexes(website_url);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_type ON vector_indexes(data_type);
CREATE INDEX IF NOT EXISTS idx_vector_indexes_status ON vector_indexes(status);

-- Enable RLS
ALTER TABLE vector_indexes ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view their own vector indexes" ON vector_indexes
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can manage their own vector indexes" ON vector_indexes
    FOR ALL USING (auth.jwt() ->> 'email' = user_email);

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_vector_indexes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp update
CREATE TRIGGER update_vector_indexes_timestamp
    BEFORE UPDATE ON vector_indexes
    FOR EACH ROW
    EXECUTE FUNCTION update_vector_indexes_updated_at();

-- Add function to get chat statistics
CREATE OR REPLACE FUNCTION get_chat_statistics(p_user_email VARCHAR)
RETURNS TABLE(
    total_messages INTEGER,
    avg_confidence FLOAT,
    top_intents JSON,
    avg_response_time_ms FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as total_messages,
        AVG((confidence_scores->>'overall')::FLOAT) as avg_confidence,
        JSON_AGG(DISTINCT intent) as top_intents,
        AVG(processing_time_ms)::FLOAT as avg_response_time_ms
    FROM chat_contexts
    WHERE user_email = p_user_email
    AND created_at >= NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT SELECT, INSERT ON chat_contexts TO authenticated;
GRANT SELECT, INSERT, UPDATE ON vector_indexes TO authenticated;
GRANT EXECUTE ON FUNCTION get_chat_statistics TO authenticated;