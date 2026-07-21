-- ============================================================
-- UniApp-ACM: Supabase schema for user_data storage
-- ============================================================
-- Run this in the Supabase SQL Editor to create the table
-- and enable Row Level Security (RLS).
-- ============================================================

-- 1. Create the user_data table
CREATE TABLE IF NOT EXISTS user_data (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    data_type   TEXT NOT NULL,
    data        JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One row per (user, data_type)
    UNIQUE (user_id, data_type)
);

-- 2. Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_data_user_id ON user_data (user_id);

-- 3. Enable Row Level Security
ALTER TABLE user_data ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies
--    - Users can only read their own rows
--    - Users can only insert/update/delete their own rows

DROP POLICY IF EXISTS "Users can read own data" ON user_data;
CREATE POLICY "Users can read own data"
    ON user_data FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own data" ON user_data;
CREATE POLICY "Users can insert own data"
    ON user_data FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own data" ON user_data;
CREATE POLICY "Users can update own data"
    ON user_data FOR UPDATE
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete own data" ON user_data;
CREATE POLICY "Users can delete own data"
    ON user_data FOR DELETE
    USING (auth.uid() = user_id);

-- 5. Auto-update updated_at on row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_updated_at ON user_data;
CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON user_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
