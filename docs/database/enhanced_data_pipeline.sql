-- Enhanced Data Pipeline Schema for Detailed GSC Analytics
-- This extends the basic gsc_metrics_cache with query and page level data

-- Query-level performance data (individual keywords)
CREATE TABLE IF NOT EXISTS gsc_queries (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    query_text TEXT NOT NULL,
    date DATE NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr NUMERIC(6,4) DEFAULT 0,
    position NUMERIC(6,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_email, website_url, query_text, date)
);

-- Page-level performance data (individual URLs)
CREATE TABLE IF NOT EXISTS gsc_pages (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    page_url TEXT NOT NULL,
    date DATE NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr NUMERIC(6,4) DEFAULT 0,
    position NUMERIC(6,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_email, website_url, page_url, date)
);

-- Daily aggregated metrics (for fast dashboard queries)
CREATE TABLE IF NOT EXISTS gsc_daily_summary (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    date DATE NOT NULL,
    total_clicks INTEGER DEFAULT 0,
    total_impressions INTEGER DEFAULT 0,
    avg_ctr NUMERIC(6,4) DEFAULT 0,
    avg_position NUMERIC(6,2) DEFAULT 0,
    total_queries INTEGER DEFAULT 0,
    total_pages INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_email, website_url, date)
);

-- Data pipeline status tracking
CREATE TABLE IF NOT EXISTS gsc_pipeline_status (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    last_fetch_date DATE,
    last_success_date DATE,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    queries_processed INTEGER DEFAULT 0,
    pages_processed INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_email, website_url)
);

-- Enable RLS on all new tables
ALTER TABLE gsc_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_daily_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE gsc_pipeline_status ENABLE ROW LEVEL SECURITY;

-- RLS policies for gsc_queries
CREATE POLICY "Users can view their own query data" ON gsc_queries
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own query data" ON gsc_queries  
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own query data" ON gsc_queries
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- RLS policies for gsc_pages
CREATE POLICY "Users can view their own page data" ON gsc_pages
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own page data" ON gsc_pages
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own page data" ON gsc_pages
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- RLS policies for gsc_daily_summary
CREATE POLICY "Users can view their own daily summary" ON gsc_daily_summary
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own daily summary" ON gsc_daily_summary
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own daily summary" ON gsc_daily_summary
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- RLS policies for gsc_pipeline_status
CREATE POLICY "Users can view their own pipeline status" ON gsc_pipeline_status
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own pipeline status" ON gsc_pipeline_status
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own pipeline status" ON gsc_pipeline_status
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_gsc_queries_user_date ON gsc_queries(user_email, date DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_queries_website_date ON gsc_queries(website_url, date DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_queries_query_text ON gsc_queries(query_text);
CREATE INDEX IF NOT EXISTS idx_gsc_queries_position ON gsc_queries(position);
CREATE INDEX IF NOT EXISTS idx_gsc_queries_clicks ON gsc_queries(clicks DESC);

CREATE INDEX IF NOT EXISTS idx_gsc_pages_user_date ON gsc_pages(user_email, date DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_pages_website_date ON gsc_pages(website_url, date DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_pages_page_url ON gsc_pages(page_url);
CREATE INDEX IF NOT EXISTS idx_gsc_pages_clicks ON gsc_pages(clicks DESC);

CREATE INDEX IF NOT EXISTS idx_gsc_daily_summary_user_date ON gsc_daily_summary(user_email, date DESC);
CREATE INDEX IF NOT EXISTS idx_gsc_daily_summary_website_date ON gsc_daily_summary(website_url, date DESC);

CREATE INDEX IF NOT EXISTS idx_gsc_pipeline_status_user ON gsc_pipeline_status(user_email);
CREATE INDEX IF NOT EXISTS idx_gsc_pipeline_status_updated ON gsc_pipeline_status(updated_at DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_gsc_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_gsc_queries_updated_at BEFORE UPDATE ON gsc_queries
    FOR EACH ROW EXECUTE FUNCTION update_gsc_updated_at_column();

CREATE TRIGGER update_gsc_pages_updated_at BEFORE UPDATE ON gsc_pages
    FOR EACH ROW EXECUTE FUNCTION update_gsc_updated_at_column();

CREATE TRIGGER update_gsc_daily_summary_updated_at BEFORE UPDATE ON gsc_daily_summary
    FOR EACH ROW EXECUTE FUNCTION update_gsc_updated_at_column();

CREATE TRIGGER update_gsc_pipeline_status_updated_at BEFORE UPDATE ON gsc_pipeline_status
    FOR EACH ROW EXECUTE FUNCTION update_gsc_updated_at_column();

-- Function to get top queries for a website
CREATE OR REPLACE FUNCTION get_top_queries(
    p_user_email VARCHAR(255),
    p_website_url TEXT,
    p_start_date DATE,
    p_end_date DATE,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    query_text TEXT,
    total_clicks BIGINT,
    total_impressions BIGINT,
    avg_ctr NUMERIC,
    avg_position NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.query_text,
        SUM(q.clicks)::BIGINT as total_clicks,
        SUM(q.impressions)::BIGINT as total_impressions,
        ROUND(AVG(q.ctr), 4) as avg_ctr,
        ROUND(AVG(q.position), 2) as avg_position
    FROM gsc_queries q
    WHERE q.user_email = p_user_email
        AND q.website_url = p_website_url
        AND q.date >= p_start_date
        AND q.date <= p_end_date
    GROUP BY q.query_text
    ORDER BY total_clicks DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get top pages for a website
CREATE OR REPLACE FUNCTION get_top_pages(
    p_user_email VARCHAR(255),
    p_website_url TEXT,
    p_start_date DATE,
    p_end_date DATE,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    page_url TEXT,
    total_clicks BIGINT,
    total_impressions BIGINT,
    avg_ctr NUMERIC,
    avg_position NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.page_url,
        SUM(p.clicks)::BIGINT as total_clicks,
        SUM(p.impressions)::BIGINT as total_impressions,
        ROUND(AVG(p.ctr), 4) as avg_ctr,
        ROUND(AVG(p.position), 2) as avg_position
    FROM gsc_pages p
    WHERE p.user_email = p_user_email
        AND p.website_url = p_website_url
        AND p.date >= p_start_date
        AND p.date <= p_end_date
    GROUP BY p.page_url
    ORDER BY total_clicks DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate daily aggregates from detailed data
CREATE OR REPLACE FUNCTION calculate_daily_aggregates(
    p_user_email VARCHAR(255),
    p_website_url TEXT,
    p_date DATE
)
RETURNS VOID AS $$
DECLARE
    query_stats RECORD;
    page_stats RECORD;
BEGIN
    -- Calculate query aggregates for the date
    SELECT 
        COALESCE(SUM(clicks), 0) as total_clicks,
        COALESCE(SUM(impressions), 0) as total_impressions,
        COALESCE(AVG(ctr), 0) as avg_ctr,
        COALESCE(AVG(position), 0) as avg_position,
        COUNT(*) as total_queries
    INTO query_stats
    FROM gsc_queries
    WHERE user_email = p_user_email
        AND website_url = p_website_url
        AND date = p_date;

    -- Calculate page count for the date
    SELECT COUNT(*) as total_pages
    INTO page_stats
    FROM gsc_pages
    WHERE user_email = p_user_email
        AND website_url = p_website_url
        AND date = p_date;

    -- Insert or update daily summary
    INSERT INTO gsc_daily_summary (
        user_email, website_url, date,
        total_clicks, total_impressions, avg_ctr, avg_position,
        total_queries, total_pages
    ) VALUES (
        p_user_email, p_website_url, p_date,
        query_stats.total_clicks, query_stats.total_impressions,
        ROUND(query_stats.avg_ctr, 4), ROUND(query_stats.avg_position, 2),
        query_stats.total_queries, page_stats.total_pages
    )
    ON CONFLICT (user_email, website_url, date)
    DO UPDATE SET
        total_clicks = EXCLUDED.total_clicks,
        total_impressions = EXCLUDED.total_impressions,
        avg_ctr = EXCLUDED.avg_ctr,
        avg_position = EXCLUDED.avg_position,
        total_queries = EXCLUDED.total_queries,
        total_pages = EXCLUDED.total_pages,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;