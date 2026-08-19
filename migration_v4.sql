-- ============================================================
-- Tutor Socrático Universal — MIGRACIÓN v4
-- Visibilidad de conversaciones/mensajes para docentes sobre
-- los estudiantes que CREARON (creado_por), y políticas SELECT
-- faltantes en grupos_estudiantes.
-- Investigador principal: Jaime Andrés Vélez Zea
-- Pontificia Universidad Javeriana Cali, 2026
-- ============================================================
-- Instrucciones:
--   1. Ir a Supabase Dashboard → SQL Editor
--   2. Pegar TODO este archivo
--   3. Ejecutar (Ctrl+Enter o botón "Run")
--   Nota: es idempotente — puede ejecutarse varias veces sin daño.
-- ============================================================

-- 1. Políticas SELECT faltantes en grupos_estudiantes
--    (la migración base solo tenía INSERT/DELETE, por lo que ni docentes
--    ni estudiantes podían listar miembros de grupo).
DROP POLICY IF EXISTS "Docente ve miembros de sus grupos" ON grupos_estudiantes;
CREATE POLICY "Docente ve miembros de sus grupos" ON grupos_estudiantes
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM grupos g
        WHERE g.id = grupos_estudiantes.grupo_id
          AND g.creado_por = auth.uid()
    ));

DROP POLICY IF EXISTS "Estudiante ve sus membresias" ON grupos_estudiantes;
CREATE POLICY "Estudiante ve sus membresias" ON grupos_estudiantes
    FOR SELECT USING (estudiante_id = auth.uid());

DROP POLICY IF EXISTS "Admin ve membresias" ON grupos_estudiantes;
CREATE POLICY "Admin ve membresias" ON grupos_estudiantes
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));

-- 2. Docente ve conversaciones de los estudiantes que creó
--    (complementa la política existente basada en grupos).
DROP POLICY IF EXISTS "Docente ve conversaciones de estudiantes creados" ON conversaciones;
CREATE POLICY "Docente ve conversaciones de estudiantes creados" ON conversaciones
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM profiles p
        WHERE p.id = conversaciones.estudiante_id
          AND p.creado_por = auth.uid()
    ));

-- 3. Docente ve mensajes de conversaciones de los estudiantes que creó.
DROP POLICY IF EXISTS "Docente ve mensajes de estudiantes creados" ON mensajes;
CREATE POLICY "Docente ve mensajes de estudiantes creados" ON mensajes
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM conversaciones c
        JOIN profiles p ON p.id = c.estudiante_id
        WHERE c.id = mensajes.conversacion_id
          AND p.creado_por = auth.uid()
    ));

-- 4. Docente borra conversaciones/mensajes de los estudiantes que creó
--    (la política de borrado original solo cubría grupos).
DROP POLICY IF EXISTS "Docente borra conversaciones de estudiantes creados" ON conversaciones;
CREATE POLICY "Docente borra conversaciones de estudiantes creados" ON conversaciones
    FOR DELETE USING (EXISTS (
        SELECT 1 FROM profiles p
        WHERE p.id = conversaciones.estudiante_id
          AND p.creado_por = auth.uid()
    ));

DROP POLICY IF EXISTS "Docente borra mensajes de estudiantes creados" ON mensajes;
CREATE POLICY "Docente borra mensajes de estudiantes creados" ON mensajes
    FOR DELETE USING (EXISTS (
        SELECT 1 FROM conversaciones c
        JOIN profiles p ON p.id = c.estudiante_id
        WHERE c.id = mensajes.conversacion_id
          AND p.creado_por = auth.uid()
    ));
