-- Audit Engine Database Schema
-- Purpose: Store audit results, issues, and history for SEO health monitoring
-- Author: Solvia Alpha Development
-- Date: 2025-08-19

-- =====================================================
-- AUDIT RESULTS TABLE
-- Stores complete audit runs with JSON results
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_results (
    id SERIAL PRIMARY KEY,
    audit_id VARCHAR(100) UNIQUE NOT NULL, -- Unique identifier for each audit
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    
    -- Audit Metrics
    seo_score NUMERIC(5,2) NOT NULL, -- Overall SEO score (0-100)
    previous_score NUMERIC(5,2), -- Score from previous audit for delta
    score_delta NUMERIC(5,2), -- Change from previous audit
    
    -- Issue Counts
    critical_issues INTEGER DEFAULT 0,
    high_issues INTEGER DEFAULT 0,
    medium_issues INTEGER DEFAULT 0,
    low_issues INTEGER DEFAULT 0,
    total_issues INTEGER DEFAULT 0,
    
    -- Performance Metrics (30-day comparison)
    traffic_change NUMERIC(10,2), -- Percentage change in traffic
    position_change NUMERIC(5,2), -- Average position change
    ctr_change NUMERIC(5,2), -- CTR percentage change
    
    -- Audit Data
    audit_data JSONB NOT NULL, -- Complete audit results in JSON
    metrics_snapshot JSONB, -- GSC metrics at audit time
    
    -- Timestamps
    audit_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_time_ms INTEGER, -- Time taken to generate audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for audit_results table
CREATE INDEX idx_audit_user_email ON audit_results(user_email);
CREATE INDEX idx_audit_website ON audit_results(website_url);
CREATE INDEX idx_audit_date ON audit_results(audit_date DESC);
CREATE INDEX idx_audit_id ON audit_results(audit_id);

-- =====================================================
-- AUDIT ISSUES TABLE
-- Individual issues detected during audit
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_issues (
    id SERIAL PRIMARY KEY,
    audit_id VARCHAR(100) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    
    -- Issue Classification
    issue_type VARCHAR(100) NOT NULL, -- traffic_drop, position_loss, ctr_decline, etc.
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    category VARCHAR(50), -- technical, content, performance, opportunity
    
    -- Issue Details
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT,
    
    -- Impact Metrics
    affected_pages INTEGER DEFAULT 0,
    affected_queries INTEGER DEFAULT 0,
    traffic_impact NUMERIC(10,2), -- Estimated traffic loss/gain
    business_impact VARCHAR(20), -- high, medium, low
    
    -- Supporting Data
    evidence JSONB, -- Specific data points supporting the issue
    affected_urls TEXT[], -- Array of affected URLs
    affected_keywords TEXT[], -- Array of affected keywords
    
    -- Dates
    detected_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_date TIMESTAMP WITH TIME ZONE,
    is_resolved BOOLEAN DEFAULT FALSE,
    
    -- Foreign key
    FOREIGN KEY (audit_id) REFERENCES audit_results(audit_id) ON DELETE CASCADE
);

-- Create indexes for audit_issues table
CREATE INDEX idx_issue_audit_id ON audit_issues(audit_id);
CREATE INDEX idx_issue_severity ON audit_issues(severity);
CREATE INDEX idx_issue_type ON audit_issues(issue_type);
CREATE INDEX idx_issue_user ON audit_issues(user_email);

-- =====================================================
-- AUDIT BASELINES TABLE
-- Statistical baselines for anomaly detection
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_baselines (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    
    -- Statistical Measures
    mean_value NUMERIC(15,4),
    median_value NUMERIC(15,4),
    std_deviation NUMERIC(15,4),
    min_value NUMERIC(15,4),
    max_value NUMERIC(15,4),
    
    -- Percentiles for better anomaly detection
    percentile_25 NUMERIC(15,4),
    percentile_75 NUMERIC(15,4),
    percentile_90 NUMERIC(15,4),
    percentile_95 NUMERIC(15,4),
    
    -- Confidence Intervals
    confidence_lower NUMERIC(15,4), -- Lower bound of normal range
    confidence_upper NUMERIC(15,4), -- Upper bound of normal range
    confidence_level NUMERIC(3,2) DEFAULT 0.95, -- 95% confidence
    
    -- Thresholds
    critical_threshold NUMERIC(15,4), -- Value indicating critical issue
    warning_threshold NUMERIC(15,4), -- Value indicating warning
    
    -- Metadata
    data_points INTEGER, -- Number of data points used
    calculation_date DATE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Composite key
    UNIQUE(user_email, website_url, metric_name, calculation_date)
);

-- Create indexes for audit_baselines table
CREATE INDEX idx_baseline_user_website ON audit_baselines(user_email, website_url);
CREATE INDEX idx_baseline_metric ON audit_baselines(metric_name);

-- =====================================================
-- AUDIT ALERTS TABLE
-- Real-time alerts for significant changes
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(100) UNIQUE NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    
    -- Alert Classification
    alert_type VARCHAR(100) NOT NULL, -- anomaly, threshold_breach, trend_reversal
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    metric_name VARCHAR(100) NOT NULL,
    
    -- Alert Details
    current_value NUMERIC(15,4),
    expected_value NUMERIC(15,4),
    baseline_value NUMERIC(15,4),
    deviation_percentage NUMERIC(10,2),
    z_score NUMERIC(10,4), -- Statistical significance
    
    -- Context
    description TEXT NOT NULL,
    recommendation TEXT,
    affected_period VARCHAR(50), -- last_7_days, last_30_days, etc.
    
    -- Status
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved', 'false_positive')),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for audit_alerts table
CREATE INDEX idx_alert_user ON audit_alerts(user_email);
CREATE INDEX idx_alert_website ON audit_alerts(website_url);
CREATE INDEX idx_alert_status ON audit_alerts(status);
CREATE INDEX idx_alert_severity ON audit_alerts(severity);
CREATE INDEX idx_alert_detected ON audit_alerts(detected_at DESC);

-- =====================================================
-- AUDIT HISTORY VIEW
-- Simplified view for audit history page
-- =====================================================
CREATE OR REPLACE VIEW audit_history_view AS
SELECT 
    ar.audit_id,
    ar.user_email,
    ar.website_url,
    ar.seo_score,
    ar.score_delta,
    ar.critical_issues,
    ar.high_issues,
    ar.total_issues,
    ar.traffic_change,
    ar.audit_date,
    ar.processing_time_ms,
    CASE 
        WHEN ar.score_delta > 0 THEN 'improved'
        WHEN ar.score_delta < 0 THEN 'declined'
        ELSE 'stable'
    END as trend
FROM audit_results ar
ORDER BY ar.audit_date DESC;

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- Ensure users can only access their own audit data
-- =====================================================

-- Enable RLS on all audit tables
ALTER TABLE audit_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_issues ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_alerts ENABLE ROW LEVEL SECURITY;

-- RLS Policies for audit_results
CREATE POLICY "Users can view their own audit results" ON audit_results
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own audit results" ON audit_results
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own audit results" ON audit_results
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- RLS Policies for audit_issues
CREATE POLICY "Users can view their own audit issues" ON audit_issues
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own audit issues" ON audit_issues
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own audit issues" ON audit_issues
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- RLS Policies for audit_baselines
CREATE POLICY "Users can view their own baselines" ON audit_baselines
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own baselines" ON audit_baselines
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own baselines" ON audit_baselines
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- RLS Policies for audit_alerts
CREATE POLICY "Users can view their own alerts" ON audit_alerts
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own alerts" ON audit_alerts
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own alerts" ON audit_alerts
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to get latest audit for a website
CREATE OR REPLACE FUNCTION get_latest_audit(
    p_user_email VARCHAR(255),
    p_website_url TEXT
) RETURNS TABLE (
    audit_id VARCHAR(100),
    seo_score NUMERIC(5,2),
    audit_date TIMESTAMP WITH TIME ZONE,
    total_issues INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ar.audit_id,
        ar.seo_score,
        ar.audit_date,
        ar.total_issues
    FROM audit_results ar
    WHERE ar.user_email = p_user_email 
      AND ar.website_url = p_website_url
    ORDER BY ar.audit_date DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate issue trends
CREATE OR REPLACE FUNCTION calculate_issue_trends(
    p_user_email VARCHAR(255),
    p_website_url TEXT,
    p_days INTEGER DEFAULT 30
) RETURNS TABLE (
    issue_type VARCHAR(100),
    occurrences INTEGER,
    avg_severity VARCHAR(20),
    first_seen DATE,
    last_seen DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ai.issue_type,
        COUNT(*)::INTEGER as occurrences,
        MODE() WITHIN GROUP (ORDER BY ai.severity) as avg_severity,
        MIN(ai.detected_date::DATE) as first_seen,
        MAX(ai.detected_date::DATE) as last_seen
    FROM audit_issues ai
    WHERE ai.user_email = p_user_email 
      AND ai.website_url = p_website_url
      AND ai.detected_date >= NOW() - INTERVAL '1 day' * p_days
    GROUP BY ai.issue_type
    ORDER BY occurrences DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Trigger to update total_issues count
CREATE OR REPLACE FUNCTION update_issue_counts() RETURNS TRIGGER AS $$
BEGIN
    UPDATE audit_results
    SET 
        critical_issues = (SELECT COUNT(*) FROM audit_issues WHERE audit_id = NEW.audit_id AND severity = 'critical'),
        high_issues = (SELECT COUNT(*) FROM audit_issues WHERE audit_id = NEW.audit_id AND severity = 'high'),
        medium_issues = (SELECT COUNT(*) FROM audit_issues WHERE audit_id = NEW.audit_id AND severity = 'medium'),
        low_issues = (SELECT COUNT(*) FROM audit_issues WHERE audit_id = NEW.audit_id AND severity = 'low'),
        total_issues = (SELECT COUNT(*) FROM audit_issues WHERE audit_id = NEW.audit_id)
    WHERE audit_id = NEW.audit_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_issue_counts
AFTER INSERT OR UPDATE OR DELETE ON audit_issues
FOR EACH ROW
EXECUTE FUNCTION update_issue_counts();

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Composite indexes for common queries
CREATE INDEX idx_audit_results_user_website_date 
    ON audit_results(user_email, website_url, audit_date DESC);

CREATE INDEX idx_audit_issues_audit_severity 
    ON audit_issues(audit_id, severity);

CREATE INDEX idx_audit_baselines_user_metric_date 
    ON audit_baselines(user_email, website_url, metric_name, calculation_date DESC);

CREATE INDEX idx_audit_alerts_user_status_severity 
    ON audit_alerts(user_email, status, severity, detected_at DESC);

-- JSONB indexes for efficient JSON queries
CREATE INDEX idx_audit_data_gin ON audit_results USING GIN (audit_data);
CREATE INDEX idx_issue_evidence_gin ON audit_issues USING GIN (evidence);

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE audit_results IS 'Stores complete SEO audit results with scores and metrics';
COMMENT ON TABLE audit_issues IS 'Individual issues detected during SEO audits';
COMMENT ON TABLE audit_baselines IS 'Statistical baselines for anomaly detection';
COMMENT ON TABLE audit_alerts IS 'Real-time alerts for significant SEO changes';
COMMENT ON COLUMN audit_results.seo_score IS 'Overall SEO health score from 0-100';
COMMENT ON COLUMN audit_issues.severity IS 'Issue severity: critical, high, medium, or low';
COMMENT ON COLUMN audit_baselines.std_deviation IS 'Standard deviation for statistical analysis';
COMMENT ON COLUMN audit_alerts.z_score IS 'Statistical significance of the anomaly';