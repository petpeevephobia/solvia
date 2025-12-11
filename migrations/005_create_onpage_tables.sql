-- Migration: 005_create_onpage_tables
-- Description: Create on-page SEO analysis tables
-- Created: 2025-11-30

-- Analysis status enum
DO $$ BEGIN
    CREATE TYPE analysis_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Page Analyses table
CREATE TABLE IF NOT EXISTS page_analyses (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    url TEXT NOT NULL,
    status analysis_status DEFAULT 'pending',
    score DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error TEXT
);

-- Create indexes for page analyses
CREATE INDEX IF NOT EXISTS idx_page_analyses_user ON page_analyses(user_email);
CREATE INDEX IF NOT EXISTS idx_page_analyses_url ON page_analyses(url);
CREATE INDEX IF NOT EXISTS idx_page_analyses_status ON page_analyses(status);
CREATE INDEX IF NOT EXISTS idx_page_analyses_created ON page_analyses(created_at DESC);

-- Page Data table (extracted SEO data from pages)
CREATE TABLE IF NOT EXISTS page_data (
    id BIGSERIAL PRIMARY KEY,
    analysis_id BIGINT NOT NULL UNIQUE REFERENCES page_analyses(id) ON DELETE CASCADE,
    title VARCHAR(512),
    description TEXT,
    h1 VARCHAR(512),
    h2_count INTEGER DEFAULT 0,
    h3_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    image_count INTEGER DEFAULT 0,
    images_with_alt INTEGER DEFAULT 0,
    internal_links INTEGER DEFAULT 0,
    external_links INTEGER DEFAULT 0,
    has_canonical BOOLEAN DEFAULT FALSE,
    has_robots BOOLEAN DEFAULT FALSE,
    has_open_graph BOOLEAN DEFAULT FALSE,
    has_schema BOOLEAN DEFAULT FALSE,
    load_time_ms INTEGER DEFAULT 0,
    content_hash VARCHAR(64)
);

-- Create index for page data
CREATE INDEX IF NOT EXISTS idx_page_data_analysis ON page_data(analysis_id);

-- OnPage Issues table
CREATE TABLE IF NOT EXISTS onpage_issues (
    id BIGSERIAL PRIMARY KEY,
    analysis_id BIGINT NOT NULL REFERENCES page_analyses(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL, -- critical, warning, info
    category VARCHAR(50) NOT NULL, -- title, meta, content, images, links, technical
    title VARCHAR(255) NOT NULL,
    description TEXT,
    current_value TEXT,
    suggestion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for onpage issues
CREATE INDEX IF NOT EXISTS idx_onpage_issues_analysis ON onpage_issues(analysis_id);
CREATE INDEX IF NOT EXISTS idx_onpage_issues_severity ON onpage_issues(severity);

COMMENT ON TABLE page_analyses IS 'On-page SEO analysis records';
COMMENT ON TABLE page_data IS 'Extracted SEO data from analyzed pages';
COMMENT ON TABLE onpage_issues IS 'SEO issues found during page analysis';
