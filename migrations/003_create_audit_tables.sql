-- Migration: 003_create_audit_tables
-- Description: Create SEO audit related tables
-- Created: 2025-11-30

-- Audit status enum
DO $$ BEGIN
    CREATE TYPE audit_status AS ENUM ('pending', 'processing', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- SEO stage enum
DO $$ BEGIN
    CREATE TYPE seo_stage AS ENUM ('hidden', 'emerging', 'discoverable', 'trusted');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Audits table
CREATE TABLE IF NOT EXISTS audits (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    website_url TEXT NOT NULL,
    status audit_status DEFAULT 'pending',
    seo_score DECIMAL(5,2) DEFAULT 25.0,
    seo_stage seo_stage DEFAULT 'hidden',
    pdf_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error TEXT
);

-- Create indexes for audits
CREATE INDEX IF NOT EXISTS idx_audits_user ON audits(user_email);
CREATE INDEX IF NOT EXISTS idx_audits_website ON audits(website_url);
CREATE INDEX IF NOT EXISTS idx_audits_status ON audits(status);
CREATE INDEX IF NOT EXISTS idx_audits_created ON audits(created_at DESC);

-- Audit Issues table
CREATE TABLE IF NOT EXISTS audit_issues (
    id BIGSERIAL PRIMARY KEY,
    audit_id BIGINT NOT NULL REFERENCES audits(id) ON DELETE CASCADE,
    severity VARCHAR(20) NOT NULL, -- high, medium, low
    category VARCHAR(50) NOT NULL, -- traffic, position, ctr, technical
    title VARCHAR(255) NOT NULL,
    description TEXT,
    impact TEXT,
    suggestion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for audit issues
CREATE INDEX IF NOT EXISTS idx_audit_issues_audit ON audit_issues(audit_id);
CREATE INDEX IF NOT EXISTS idx_audit_issues_severity ON audit_issues(severity);

COMMENT ON TABLE audits IS 'SEO audit records with PDF reports';
COMMENT ON TABLE audit_issues IS 'Critical SEO issues detected during audits';
