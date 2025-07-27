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

-- Create RLS policies
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

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_email ON user_sessions(email);
CREATE INDEX IF NOT EXISTS idx_chat_messages_user_email ON chat_messages(user_email);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at); 