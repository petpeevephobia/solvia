-- Migration: 001_create_users
-- Description: Create users and authentication tables
-- Created: 2025-11-30

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    picture TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for email lookup
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- OAuth tokens table
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL UNIQUE REFERENCES users(email) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expiry TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for user_email lookup
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_email ON oauth_tokens(user_email);

COMMENT ON TABLE users IS 'User accounts authenticated via Google OAuth';
COMMENT ON TABLE oauth_tokens IS 'OAuth tokens for Google API access';
