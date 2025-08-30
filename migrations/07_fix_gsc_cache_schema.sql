-- =========================================
-- FIX GSC CACHE SCHEMA
-- =========================================
-- Add missing updated_at column to gsc_metrics_cache table

-- Add updated_at column if it doesn't exist
ALTER TABLE gsc_metrics_cache 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_gsc_cache_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS update_gsc_cache_timestamp ON gsc_metrics_cache;

-- Create new trigger
CREATE TRIGGER update_gsc_cache_timestamp
    BEFORE UPDATE ON gsc_metrics_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_gsc_cache_updated_at();

SELECT 'GSC cache schema fixed - updated_at column added' as status;