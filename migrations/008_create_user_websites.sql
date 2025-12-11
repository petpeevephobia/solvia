-- Migration: 008_create_user_websites
-- Description: Create user_websites table for storing selected GSC website per user
-- 1:1 parity with Python version

-- Create user_websites table
CREATE TABLE IF NOT EXISTS user_websites (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL UNIQUE,
    website_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_websites_email ON user_websites(user_email);

-- Add comments
COMMENT ON TABLE user_websites IS 'Stores user selected website for GSC (1:1 with Python)';
COMMENT ON COLUMN user_websites.user_email IS 'User email - unique per user';
COMMENT ON COLUMN user_websites.website_url IS 'Selected GSC property URL';
