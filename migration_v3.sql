-- ============================================================
-- Tutor Socrático Universal — MIGRACIÓN v3
-- Autorización docente → cursos (tabla docente_cursos)
-- Investigador principal: Jaime Andrés Vélez Zea
-- Pontificia Universidad Javeriana Cali, 2026
-- ============================================================
-- Instrucciones:
--   1. Ir a Supabase Dashboard → SQL Editor
--   2. Pegar TODO este archivo
--   3. Ejecutar (Ctrl+Enter o botón "Run")
--   Nota: es idempotente — puede ejecutarse varias veces sin daño.
-- ============================================================

-- 1. Tabla docente_cursos — qué cursos puede administrar cada docente
CREATE TABLE IF NOT EXISTS docente_cursos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    docente_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    asignatura TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(docente_id, asignatura)
);

-- 2. Row Level Security
ALTER TABLE docente_cursos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Docente ve sus cursos" ON docente_cursos;
DROP POLICY IF EXISTS "Admin ve cursos" ON docente_cursos;
DROP POLICY IF EXISTS "Admin inserta cursos" ON docente_cursos;
DROP POLICY IF EXISTS "Admin borra cursos" ON docente_cursos;

-- Docente ve solo sus propios cursos
CREATE POLICY "Docente ve sus cursos" ON docente_cursos
    FOR SELECT USING (docente_id = auth.uid());

-- Admin ve todos los cursos
CREATE POLICY "Admin ve cursos" ON docente_cursos
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));

-- Solo el admin asigna cursos
CREATE POLICY "Admin inserta cursos" ON docente_cursos
    FOR INSERT WITH CHECK (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));

-- Solo el admin quita cursos
CREATE POLICY "Admin borra cursos" ON docente_cursos
    FOR DELETE USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));

-- 3. Índice
CREATE INDEX IF NOT EXISTS idx_docente_cursos_docente ON docente_cursos(docente_id);
CREATE INDEX IF NOT EXISTS idx_docente_cursos_asignatura ON docente_cursos(asignatura);
