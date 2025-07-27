-- Solvia User Sessions Table Setup
-- Run this in your Supabase SQL editor

-- Create user_sessions table for lightweight session storage
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    picture TEXT,
    last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster email lookups
CREATE INDEX IF NOT EXISTS idx_user_sessions_email ON user_sessions(email);

-- Create index for active sessions
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active);

-- Disable RLS for now to allow OAuth flow to work
ALTER TABLE user_sessions DISABLE ROW LEVEL SECURITY;

-- Grant necessary permissions
GRANT ALL ON user_sessions TO authenticated;
GRANT ALL ON user_sessions TO anon; 