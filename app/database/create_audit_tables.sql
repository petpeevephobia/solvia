-- Create audit_results table for storing Solvia Agent audit data
CREATE TABLE IF NOT EXISTS audit_results (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    audit_data JSONB NOT NULL,  -- Store full audit JSON
    seo_score DECIMAL(5,2) DEFAULT 0,
    critical_issues INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    pdf_path TEXT,  -- Path to generated PDF if available
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Foreign key to user_sessions
    FOREIGN KEY (user_email) REFERENCES user_sessions(email) ON DELETE CASCADE,
    
    -- Index for faster queries
    INDEX idx_audit_user_email (user_email),
    INDEX idx_audit_website (website_url),
    INDEX idx_audit_created (created_at DESC),
    INDEX idx_audit_status (status)
);

-- Enable RLS
ALTER TABLE audit_results ENABLE ROW LEVEL SECURITY;

-- Create RLS policy: users can only see their own audit results
CREATE POLICY "Users can view own audits" ON audit_results
    FOR ALL USING (user_email = auth.jwt()->>'email');

-- Create function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_audit_results_updated_at 
    BEFORE UPDATE ON audit_results 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create table for storing current issues (for dashboard display)
CREATE TABLE IF NOT EXISTS current_issues (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    issue_title VARCHAR(255) NOT NULL,
    issue_description TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,  -- critical, high, medium, low
    impact_score DECIMAL(5,2),
    recommendations TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    audit_id UUID REFERENCES audit_results(id) ON DELETE CASCADE,
    
    -- Foreign key to user_sessions
    FOREIGN KEY (user_email) REFERENCES user_sessions(email) ON DELETE CASCADE,
    
    -- Indexes
    INDEX idx_issues_user (user_email),
    INDEX idx_issues_severity (severity),
    INDEX idx_issues_website (website_url)
);

-- Enable RLS on current_issues
ALTER TABLE current_issues ENABLE ROW LEVEL SECURITY;

-- RLS policy for current_issues
CREATE POLICY "Users can view own issues" ON current_issues
    FOR ALL USING (user_email = auth.jwt()->>'email');

-- Create audit_history view for easier querying
CREATE OR REPLACE VIEW audit_history_view AS
SELECT 
    ar.id,
    ar.user_email,
    ar.website_url,
    ar.seo_score,
    ar.critical_issues,
    ar.status,
    ar.created_at,
    ar.pdf_path,
    COUNT(ci.id) as total_issues,
    COUNT(CASE WHEN ci.severity = 'critical' THEN 1 END) as critical_count,
    COUNT(CASE WHEN ci.severity = 'high' THEN 1 END) as high_count,
    COUNT(CASE WHEN ci.severity = 'medium' THEN 1 END) as medium_count,
    COUNT(CASE WHEN ci.severity = 'low' THEN 1 END) as low_count
FROM audit_results ar
LEFT JOIN current_issues ci ON ar.id = ci.audit_id
GROUP BY ar.id, ar.user_email, ar.website_url, ar.seo_score, 
         ar.critical_issues, ar.status, ar.created_at, ar.pdf_path
ORDER BY ar.created_at DESC;

-- Grant permissions
GRANT ALL ON audit_results TO authenticated;
GRANT ALL ON current_issues TO authenticated;
GRANT SELECT ON audit_history_view TO authenticated;