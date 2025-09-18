-- Migration: Create trusted_devices table for device remembering
-- Date: 2025-09-15
-- Purpose: Enable "Remember this device" functionality to reduce 2FA friction

-- Create trusted_devices table
CREATE TABLE IF NOT EXISTS trusted_devices (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    device_fingerprint TEXT NOT NULL,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint to prevent duplicate entries
    UNIQUE(user_email, device_fingerprint)
);

-- Add RLS policy for trusted_devices
ALTER TABLE trusted_devices ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own trusted devices
CREATE POLICY "Users can manage their own trusted devices" ON trusted_devices
    FOR ALL USING (user_email = auth.email());

-- Create index for faster lookups
CREATE INDEX idx_trusted_devices_user_email ON trusted_devices(user_email);
CREATE INDEX idx_trusted_devices_fingerprint ON trusted_devices(device_fingerprint);
CREATE INDEX idx_trusted_devices_expires_at ON trusted_devices(expires_at);

-- Create function to clean up expired trusted devices
CREATE OR REPLACE FUNCTION cleanup_expired_trusted_devices()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM trusted_devices
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON trusted_devices TO authenticated;
GRANT USAGE ON SEQUENCE trusted_devices_id_seq TO authenticated;

-- Insert comment for documentation
COMMENT ON TABLE trusted_devices IS 'Stores device fingerprints for trusted devices to reduce 2FA friction';
COMMENT ON COLUMN trusted_devices.device_fingerprint IS 'SHA-256 hash of browser characteristics (user-agent, accept-language, etc.)';
COMMENT ON COLUMN trusted_devices.expires_at IS 'Device trust expires after 30 days';
COMMENT ON FUNCTION cleanup_expired_trusted_devices() IS 'Removes expired trusted device records';