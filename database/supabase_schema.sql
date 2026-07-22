-- =============================================
-- Uni-App Supabase Database Schema
-- =============================================
-- Run this in your Supabase SQL Editor to create the required tables
-- This uses a simplified JSON storage approach for flexibility

-- =============================================
-- 1. PENSUMS TABLE (stores materias array)
-- =============================================
CREATE TABLE IF NOT EXISTS pensums (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    data JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE pensums ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own pensum" ON pensums
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own pensum" ON pensums
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own pensum" ON pensums
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own pensum" ON pensums
    FOR DELETE USING (auth.uid() = user_id);

-- =============================================
-- 2. CLASES TABLE (stores registered classes)
-- =============================================
CREATE TABLE IF NOT EXISTS clases (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    data JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE clases ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own clases" ON clases
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own clases" ON clases
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own clases" ON clases
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own clases" ON clases
    FOR DELETE USING (auth.uid() = user_id);

-- =============================================
-- 3. CALIFICACIONES TABLE (stores grades)
-- =============================================
CREATE TABLE IF NOT EXISTS calificaciones (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    data JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE calificaciones ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own calificaciones" ON calificaciones
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own calificaciones" ON calificaciones
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own calificaciones" ON calificaciones
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own calificaciones" ON calificaciones
    FOR DELETE USING (auth.uid() = user_id);

-- =============================================
-- 4. CONFIGURACIONES TABLE (stores user config)
-- =============================================
CREATE TABLE IF NOT EXISTS configuraciones (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE configuraciones ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own configuracion" ON configuraciones
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own configuracion" ON configuraciones
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own configuracion" ON configuraciones
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own configuracion" ON configuraciones
    FOR DELETE USING (auth.uid() = user_id);

-- =============================================
-- 5. FRANJAS TABLE (stores time preferences)
-- =============================================
CREATE TABLE IF NOT EXISTS franjas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    data JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE franjas ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own franjas" ON franjas
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own franjas" ON franjas
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own franjas" ON franjas
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own franjas" ON franjas
    FOR DELETE USING (auth.uid() = user_id);

-- =============================================
-- 6. ERRORS TABLE (stores user-submitted problem reports)
-- =============================================
CREATE TABLE IF NOT EXISTS errors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    message TEXT NOT NULL,
    steps TEXT,
    diagnostics JSONB,
    page TEXT,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE errors ENABLE ROW LEVEL SECURITY;

-- Anyone can report an error (even anonymous users)
CREATE POLICY "Anyone can report an error" ON errors
    FOR INSERT WITH CHECK (true);

-- Only authenticated users can view error reports
CREATE POLICY "Authenticated users can view errors" ON errors
    FOR SELECT USING (auth.role() = 'authenticated');

-- =============================================
-- 7. INDEXES FOR PERFORMANCE
-- =============================================
CREATE INDEX IF NOT EXISTS idx_pensums_user_id ON pensums(user_id);
CREATE INDEX IF NOT EXISTS idx_clases_user_id ON clases(user_id);
CREATE INDEX IF NOT EXISTS idx_calificaciones_user_id ON calificaciones(user_id);
CREATE INDEX IF NOT EXISTS idx_configuraciones_user_id ON configuraciones(user_id);
CREATE INDEX IF NOT EXISTS idx_franjas_user_id ON franjas(user_id);
CREATE INDEX IF NOT EXISTS idx_errors_created_at ON errors(created_at DESC);

-- =============================================
-- 7. UPDATED_AT TRIGGER FUNCTION
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_pensums_updated_at ON pensums;
CREATE TRIGGER update_pensums_updated_at BEFORE UPDATE ON pensums
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_clases_updated_at ON clases;
CREATE TRIGGER update_clases_updated_at BEFORE UPDATE ON clases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_calificaciones_updated_at ON calificaciones;
CREATE TRIGGER update_calificaciones_updated_at BEFORE UPDATE ON calificaciones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_configuraciones_updated_at ON configuraciones;
CREATE TRIGGER update_configuraciones_updated_at BEFORE UPDATE ON configuraciones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_franjas_updated_at ON franjas;
CREATE TRIGGER update_franjas_updated_at BEFORE UPDATE ON franjas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
