-- Email Logs Table (1:1 with Python email_logs)
-- Tracks all email sending activity for auditing and debugging

CREATE TABLE IF NOT EXISTS email_logs (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    email_type VARCHAR(50) NOT NULL,  -- 'audit_report', 'notification', etc.
    subject VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'sent', 'failed', 'skipped', 'pending'
    error_message TEXT,
    audit_id VARCHAR(100),
    attachment_name VARCHAR(255),
    smtp_server VARCHAR(255),
    sent_from VARCHAR(255),
    sent_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes for common queries
    CONSTRAINT email_logs_status_check CHECK (status IN ('sent', 'failed', 'skipped', 'pending'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_logs_user_email ON email_logs(user_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_recipient_email ON email_logs(recipient_email);
CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);
CREATE INDEX IF NOT EXISTS idx_email_logs_audit_id ON email_logs(audit_id);
CREATE INDEX IF NOT EXISTS idx_email_logs_created_at ON email_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_logs_email_type ON email_logs(email_type);
