-- Migration: 002_create_gsc_tables
-- Description: Create Google Search Console related tables
-- Created: 2025-11-30

-- GSC Connections (websites connected to user accounts)
CREATE TABLE IF NOT EXISTS gsc_connections (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    website_url TEXT NOT NULL,
    permission_level VARCHAR(50),
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_email, website_url)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_gsc_connections_user ON gsc_connections(user_email);
CREATE INDEX IF NOT EXISTS idx_gsc_connections_website ON gsc_connections(website_url);

-- GSC Metrics Cache (aggregated metrics)
CREATE TABLE IF NOT EXISTS gsc_metrics_cache (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    website_url TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    seo_score DECIMAL(5,2) DEFAULT 25.0,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    ctr DECIMAL(10,6) DEFAULT 0,
    avg_position DECIMAL(10,2) DEFAULT 0,
    cache_date DATE DEFAULT CURRENT_DATE,
    UNIQUE(user_email, website_url, start_date, end_date, cache_date)
);

-- Create indexes for cache lookups
CREATE INDEX IF NOT EXISTS idx_gsc_metrics_cache_lookup 
    ON gsc_metrics_cache(user_email, website_url, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_gsc_metrics_cache_date ON gsc_metrics_cache(cache_date);

-- GSC Daily Summary (daily metrics for charts)
CREATE TABLE IF NOT EXISTS gsc_daily_summary (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    website_url TEXT NOT NULL,
    date DATE NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    ctr DECIMAL(10,6) DEFAULT 0,
    avg_position DECIMAL(10,2) DEFAULT 0,
    UNIQUE(user_email, website_url, date)
);

-- Create indexes for daily summary
CREATE INDEX IF NOT EXISTS idx_gsc_daily_summary_lookup 
    ON gsc_daily_summary(user_email, website_url, date);

COMMENT ON TABLE gsc_connections IS 'Websites connected from Google Search Console';
COMMENT ON TABLE gsc_metrics_cache IS 'Cached aggregated GSC metrics';
COMMENT ON TABLE gsc_daily_summary IS 'Daily GSC metrics for trend charts';
