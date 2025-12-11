-- Solvia V2 Database Schema Migration
-- Version: 001
-- Description: Initial schema setup for Solvia V2 Go API

-- Enable pgvector extension for RAG embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- USERS & AUTHENTICATION
-- ============================================================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    picture TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- OAuth tokens (Google OAuth)
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL UNIQUE REFERENCES users(email) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expiry TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_email ON oauth_tokens(user_email);

-- Trusted devices for session management
CREATE TABLE IF NOT EXISTS trusted_devices (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    device_fingerprint VARCHAR(255) NOT NULL,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(user_email, device_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_trusted_devices_user_email ON trusted_devices(user_email);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_expires_at ON trusted_devices(expires_at);

-- ============================================================================
-- GOOGLE SEARCH CONSOLE (GSC)
-- ============================================================================

-- GSC connected websites
CREATE TABLE IF NOT EXISTS gsc_connections (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    website_url VARCHAR(512) NOT NULL,
    permission_level VARCHAR(50),
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_email, website_url)
);

CREATE INDEX IF NOT EXISTS idx_gsc_connections_user_email ON gsc_connections(user_email);

-- User's selected website
CREATE TABLE IF NOT EXISTS user_websites (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL UNIQUE REFERENCES users(email) ON DELETE CASCADE,
    website_url VARCHAR(512) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- GSC metrics cache
CREATE TABLE IF NOT EXISTS gsc_metrics_cache (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url VARCHAR(512) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    seo_score DECIMAL(5,2),
    impressions INTEGER,
    clicks INTEGER,
    ctr DECIMAL(10,6),
    avg_position DECIMAL(10,2),
    cache_date DATE DEFAULT CURRENT_DATE,
    UNIQUE(user_email, website_url, start_date, end_date, cache_date)
);

CREATE INDEX IF NOT EXISTS idx_gsc_metrics_cache_lookup ON gsc_metrics_cache(user_email, website_url, start_date, end_date);

-- GSC daily summary for charts
CREATE TABLE IF NOT EXISTS gsc_daily_summary (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url VARCHAR(512) NOT NULL,
    date DATE NOT NULL,
    impressions INTEGER,
    clicks INTEGER,
    ctr DECIMAL(10,6),
    avg_position DECIMAL(10,2),
    UNIQUE(user_email, website_url, date)
);

CREATE INDEX IF NOT EXISTS idx_gsc_daily_summary_lookup ON gsc_daily_summary(user_email, website_url, date);

-- ============================================================================
-- CHAT / CONVERSATIONS
-- ============================================================================

-- Chat conversations
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    website_url VARCHAR(512),
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_email ON conversations(user_email);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);

-- Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- ============================================================================
-- AUDITS
-- ============================================================================

-- SEO Audits
CREATE TABLE IF NOT EXISTS audits (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    website_url VARCHAR(512) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    seo_score DECIMAL(5,2),
    seo_stage VARCHAR(20),
    pdf_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_audits_user_email ON audits(user_email);
CREATE INDEX IF NOT EXISTS idx_audits_website_url ON audits(website_url);
CREATE INDEX IF NOT EXISTS idx_audits_created_at ON audits(created_at DESC);

-- Audit issues
CREATE TABLE IF NOT EXISTS audit_issues (
    id BIGSERIAL PRIMARY KEY,
    audit_id BIGINT NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('high', 'medium', 'low')),
    category VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    impact TEXT,
    suggestion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_issues_audit_id ON audit_issues(audit_id);

-- ============================================================================
-- DASHBOARD CACHE
-- ============================================================================

-- Dashboard cache (stores AI insights, keywords, etc.)
CREATE TABLE IF NOT EXISTS dashboard_cache (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url VARCHAR(512) NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_email, website_url)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_cache_lookup ON dashboard_cache(user_email, website_url);

-- ============================================================================
-- RAG EMBEDDINGS (pgvector)
-- ============================================================================

-- Embeddings for RAG-powered chat
CREATE TABLE IF NOT EXISTS embeddings (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url VARCHAR(512),
    collection_name VARCHAR(100) NOT NULL,
    document_id VARCHAR(64) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768), -- Gemini embedding dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_email, collection_name, document_id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_user_collection ON embeddings(user_email, collection_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_website ON embeddings(user_email, website_url);

-- Vector similarity search index (HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
-- EMAIL LOGS
-- ============================================================================

-- Email logs for audit reports
CREATE TABLE IF NOT EXISTS email_logs (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    recipient VARCHAR(255) NOT NULL,
    subject VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_logs_user_email ON email_logs(user_email);

-- ============================================================================
-- DONE
-- ============================================================================
