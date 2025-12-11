-- Migration: Create trusted_devices table for device remembering (1:1 with Python)
-- Date: 2025-12-02
-- Purpose: Enable "Remember this device" functionality to reduce 2FA friction

-- Create trusted_devices table
CREATE TABLE IF NOT EXISTS trusted_devices (
    id BIGSERIAL PRIMARY KEY,
    user_email TEXT NOT NULL,
    device_fingerprint TEXT NOT NULL,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Unique constraint to prevent duplicate entries
    UNIQUE(user_email, device_fingerprint)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_trusted_devices_user_email ON trusted_devices(user_email);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_fingerprint ON trusted_devices(device_fingerprint);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_expires_at ON trusted_devices(expires_at);

-- Add comments for documentation
COMMENT ON TABLE trusted_devices IS 'Stores device fingerprints for trusted devices to reduce 2FA friction';
COMMENT ON COLUMN trusted_devices.device_fingerprint IS 'SHA-256 hash of browser characteristics (user-agent, accept-language, etc.)';
COMMENT ON COLUMN trusted_devices.expires_at IS 'Device trust expires after 30 days';
