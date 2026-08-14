-- ============================================================
-- Tutor Socrático Universal — MIGRACIÓN v2
-- Vinculación de estudiantes a curso + docente (creado_por / asignatura)
-- Investigador principal: Jaime Andrés Vélez Zea
-- Pontificia Universidad Javeriana Cali, 2026
-- ============================================================
-- Instrucciones:
--   1. Ir a Supabase Dashboard → SQL Editor
--   2. Pegar TODO este archivo
--   3. Ejecutar (Ctrl+Enter o botón "Run")
--   Nota: es idempotente — puede ejecutarse varias veces sin daño.
-- ============================================================

-- 1. Nuevas columnas en profiles (identificador de pertenencia)
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS creado_por UUID REFERENCES profiles(id) ON DELETE SET NULL;

ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS asignatura TEXT NOT NULL DEFAULT '';

-- 2. Índice para búsquedas por docente
CREATE INDEX IF NOT EXISTS idx_profiles_creado_por ON profiles(creado_por);
CREATE INDEX IF NOT EXISTS idx_profiles_asignatura ON profiles(asignatura);

-- 3. Corregir políticas DELETE/UPDATE de profiles
--    (la política anterior permitía a CUALQUIER docente borrar CUALQUIER estudiante)
DROP POLICY IF EXISTS "Docente borra estudiantes" ON profiles;
DROP POLICY IF EXISTS "Docente borra sus estudiantes" ON profiles;
DROP POLICY IF EXISTS "Docente ve sus estudiantes" ON profiles;
DROP POLICY IF EXISTS "Docente actualiza sus estudiantes" ON profiles;

-- Docente solo ve los estudiantes que él creó
CREATE POLICY "Docente ve sus estudiantes" ON profiles
    FOR SELECT USING (creado_por = auth.uid());

-- Docente solo borra los estudiantes que él creó
CREATE POLICY "Docente borra sus estudiantes" ON profiles
    FOR DELETE USING (
        (SELECT rol FROM profiles WHERE id = auth.uid()) = 'docente'
        AND creado_por = auth.uid()
    );

-- Docente puede actualizar el perfil de sus estudiantes (p.ej. reasignar asignatura)
CREATE POLICY "Docente actualiza sus estudiantes" ON profiles
    FOR UPDATE USING (creado_por = auth.uid());

-- 4. Recrear trigger para poblar creado_por / asignatura desde el metadata de auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, nombre, rol, creado_por, asignatura)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'nombre', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'rol', 'estudiante'),
        NULLIF(NEW.raw_user_meta_data->>'creado_por', '')::uuid,
        COALESCE(NEW.raw_user_meta_data->>'asignatura', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
