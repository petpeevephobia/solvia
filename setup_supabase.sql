-- Solvia Supabase Database Setup
-- Run this SQL in your Supabase SQL editor

-- Create user_sessions table for storing user authentication data
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    picture TEXT,
    access_token TEXT,
    refresh_token TEXT,
    selected_website TEXT,
    last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_sessions
CREATE POLICY "Users can view their own session" ON user_sessions
    FOR SELECT USING (auth.jwt() ->> 'email' = email);

CREATE POLICY "Users can insert their own session" ON user_sessions
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = email);

CREATE POLICY "Users can update their own session" ON user_sessions
    FOR UPDATE USING (auth.jwt() ->> 'email' = email);

-- Create chat_messages table for storing chat history
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    message_content TEXT NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    sender_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for chat_messages
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for chat_messages
CREATE POLICY "Users can view their own messages" ON chat_messages
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own messages" ON chat_messages
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

-- Create gsc_connections table for storing Google OAuth credentials
-- Drop and recreate to ensure clean setup
DROP TABLE IF EXISTS gsc_connections CASCADE;

CREATE TABLE gsc_connections (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for gsc_connections
ALTER TABLE gsc_connections ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for gsc_connections
CREATE POLICY "Users can view their own GSC connections" ON gsc_connections
    FOR SELECT USING (auth.jwt() ->> 'email' = email);

CREATE POLICY "Users can insert their own GSC connections" ON gsc_connections
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = email);

CREATE POLICY "Users can update their own GSC connections" ON gsc_connections
    FOR UPDATE USING (auth.jwt() ->> 'email' = email);

-- Create gsc_metrics_cache table for caching GSC metrics
CREATE TABLE IF NOT EXISTS gsc_metrics_cache (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    seo_score NUMERIC(5,2),
    impressions INTEGER,
    clicks INTEGER,
    ctr NUMERIC(5,2),
    avg_position NUMERIC(5,2),
    cache_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for gsc_metrics_cache
ALTER TABLE gsc_metrics_cache ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for gsc_metrics_cache
CREATE POLICY "Users can view their own cached metrics" ON gsc_metrics_cache
    FOR SELECT USING (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can insert their own cached metrics" ON gsc_metrics_cache
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = user_email);

CREATE POLICY "Users can update their own cached metrics" ON gsc_metrics_cache
    FOR UPDATE USING (auth.jwt() ->> 'email' = user_email);

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_email ON user_sessions(email);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_email ON chat_messages(user_email);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_gsc_connections_email ON gsc_connections(email);
CREATE INDEX IF NOT EXISTS idx_gsc_cache_user_email ON gsc_metrics_cache(user_email);
CREATE INDEX IF NOT EXISTS idx_gsc_cache_website_date ON gsc_metrics_cache(website_url, cache_date);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at on user_sessions
DROP TRIGGER IF EXISTS update_user_sessions_updated_at ON user_sessions;
CREATE TRIGGER update_user_sessions_updated_at 
    BEFORE UPDATE ON user_sessions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create trigger to automatically update updated_at on gsc_connections
DROP TRIGGER IF EXISTS update_gsc_connections_updated_at ON gsc_connections;
CREATE TRIGGER update_gsc_connections_updated_at 
    BEFORE UPDATE ON gsc_connections 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create user_websites table for storing user's selected GSC properties
CREATE TABLE IF NOT EXISTS user_websites (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    website_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for user_websites
ALTER TABLE user_websites ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for user_websites
CREATE POLICY "Users can view their own websites" ON user_websites
    FOR SELECT USING (auth.jwt() ->> 'email' = email);

CREATE POLICY "Users can insert their own websites" ON user_websites
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = email);

CREATE POLICY "Users can update their own websites" ON user_websites
    FOR UPDATE USING (auth.jwt() ->> 'email' = email);

-- Add index for user_websites
CREATE INDEX IF NOT EXISTS idx_user_websites_email ON user_websites(email);

-- Create trigger to automatically update updated_at on user_websites
DROP TRIGGER IF EXISTS update_user_websites_updated_at ON user_websites;
CREATE TRIGGER update_user_websites_updated_at 
    BEFORE UPDATE ON user_websites 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create website_content table for storing website content analysis
CREATE TABLE IF NOT EXISTS website_content (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    title_tags JSONB,
    meta_descriptions JSONB,
    page_content JSONB,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for website_content
ALTER TABLE website_content ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for website_content
CREATE POLICY "Users can view their own website content" ON website_content
    FOR SELECT USING (auth.jwt() ->> 'email' = email);

CREATE POLICY "Users can insert their own website content" ON website_content
    FOR INSERT WITH CHECK (auth.jwt() ->> 'email' = email);

-- Add index for website_content
CREATE INDEX IF NOT EXISTS idx_website_content_email ON website_content(email);
CREATE INDEX IF NOT EXISTS idx_website_content_url ON website_content(website_url);

-- Optional: Create a view for user dashboard data
CREATE OR REPLACE VIEW user_dashboard_data AS
SELECT 
    us.email,
    us.name,
    us.selected_website,
    us.last_login,
    COUNT(cm.id) as total_messages,
    MAX(cm.created_at) as last_message_at
FROM user_sessions us
LEFT JOIN chat_messages cm ON us.email = cm.user_email
GROUP BY us.email, us.name, us.selected_website, us.last_login;

-- Grant necessary permissions (adjust as needed for your setup)
-- Note: These permissions depend on your Supabase setup and security requirements

-- Verify tables were created successfully
SELECT 'user_sessions' as table_name, COUNT(*) as row_count FROM user_sessions
UNION ALL
SELECT 'chat_messages' as table_name, COUNT(*) as row_count FROM chat_messages
UNION ALL
SELECT 'gsc_connections' as table_name, COUNT(*) as row_count FROM gsc_connections
UNION ALL
SELECT 'gsc_metrics_cache' as table_name, COUNT(*) as row_count FROM gsc_metrics_cache
UNION ALL
SELECT 'user_websites' as table_name, COUNT(*) as row_count FROM user_websites
UNION ALL
SELECT 'website_content' as table_name, COUNT(*) as row_count FROM website_content;
