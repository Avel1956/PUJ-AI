-- ============================================================
-- Tutor Socrático Universal — Schema para Supabase
-- Proyecto de investigación: Agentes IA como Asistentes Pedagógicos
-- Investigador principal: Jaime Andrés Vélez Zea
-- Pontificia Universidad Javeriana Cali, 2026
-- ============================================================
-- Instrucciones:
--   1. Ir a Supabase Dashboard → SQL Editor
--   2. Pegar TODO este archivo
--   3. Ejecutar (Ctrl+Enter o botón "Run")
--   4. Deshabilitar "Confirm email" en Authentication → Settings
-- ============================================================

-- 0. Extensión UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. PROFILES — extiende auth.users con datos de la app
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    nombre TEXT NOT NULL DEFAULT '',
    rol TEXT NOT NULL DEFAULT 'estudiante'
        CHECK (rol IN ('estudiante', 'docente', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. GRUPOS — grupos de trabajo creados por docentes
CREATE TABLE IF NOT EXISTS grupos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre TEXT NOT NULL,
    descripcion TEXT DEFAULT '',
    creado_por UUID NOT NULL REFERENCES profiles(id),
    asignatura TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. N:M ESTUDIANTES ↔ GRUPOS
CREATE TABLE IF NOT EXISTS grupos_estudiantes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    grupo_id UUID NOT NULL REFERENCES grupos(id) ON DELETE CASCADE,
    estudiante_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(grupo_id, estudiante_id)
);

-- 4. CONVERSACIONES — sesiones de chat
CREATE TABLE IF NOT EXISTS conversaciones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estudiante_id UUID NOT NULL REFERENCES profiles(id),
    grupo_id UUID REFERENCES grupos(id) ON DELETE SET NULL,
    asignatura TEXT NOT NULL DEFAULT '',
    titulo TEXT DEFAULT 'Conversación',
    activa BOOLEAN DEFAULT TRUE,
    model_usado TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. MENSAJES — mensajes individuales dentro de conversaciones
CREATE TABLE IF NOT EXISTS mensajes (
    id BIGSERIAL PRIMARY KEY,
    conversacion_id UUID NOT NULL REFERENCES conversaciones(id) ON DELETE CASCADE,
    rol TEXT NOT NULL CHECK (rol IN ('user', 'assistant', 'system')),
    contenido TEXT NOT NULL,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    costo_usd NUMERIC(10,8) DEFAULT 0,
    tiempo_respuesta_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. MENSAJES DEL DOCENTE — bandeja de entrada para estudiantes/grupos
CREATE TABLE IF NOT EXISTS mensajes_docente (
    id BIGSERIAL PRIMARY KEY,
    de_usuario_id UUID NOT NULL REFERENCES profiles(id),
    para_estudiante_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    para_grupo_id UUID REFERENCES grupos(id) ON DELETE CASCADE,
    asunto TEXT NOT NULL DEFAULT '',
    contenido TEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT mensaje_tiene_destino CHECK (
        para_estudiante_id IS NOT NULL OR para_grupo_id IS NOT NULL
    )
);

-- 7. LOGS — telemetría para investigación
CREATE TABLE IF NOT EXISTS logs_sesiones (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    usuario_id UUID REFERENCES profiles(id),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    asignatura TEXT NOT NULL,
    modelo TEXT NOT NULL,
    mensaje_usuario TEXT,
    respuesta_agente TEXT,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    costo_usd NUMERIC(10,8) DEFAULT 0,
    tiempo_respuesta_ms INTEGER DEFAULT 0
);

-- 8. CONFIG SISTEMA — editable por admin desde la app
CREATE TABLE IF NOT EXISTS config_sistema (
    id SERIAL PRIMARY KEY,
    clave TEXT UNIQUE NOT NULL,
    valor TEXT NOT NULL,
    descripcion TEXT DEFAULT ''
);

INSERT INTO config_sistema (clave, valor, descripcion) VALUES
    ('max_preguntas_dia', '50', 'Límite de preguntas por estudiante por día'),
    ('modelo_llm', 'gemini-2.0-flash', 'Modelo LLM por defecto (clave de MODELOS_DISPONIBLES)'),
    ('costo_maximo_sesion_usd', '0.10', 'Costo máximo estimado por sesión en USD')
ON CONFLICT (clave) DO NOTHING;

-- 9. ROW LEVEL SECURITY — cada rol ve solo lo que le corresponde
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE grupos ENABLE ROW LEVEL SECURITY;
ALTER TABLE grupos_estudiantes ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE mensajes ENABLE ROW LEVEL SECURITY;
ALTER TABLE mensajes_docente ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs_sesiones ENABLE ROW LEVEL SECURITY;

-- Políticas: profiles
CREATE POLICY "Usuarios ven su propio perfil" ON profiles
    FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Admin ve todos los perfiles" ON profiles
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));
CREATE POLICY "Admin inserta perfiles" ON profiles
    FOR INSERT WITH CHECK (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));

-- Políticas: conversaciones (estudiantes ven las suyas, docentes las de sus grupos)
CREATE POLICY "Estudiante ve sus conversaciones" ON conversaciones
    FOR SELECT USING (estudiante_id = auth.uid());
CREATE POLICY "Docente ve conversaciones de sus grupos" ON conversaciones
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM grupos g
        JOIN grupos_estudiantes ge ON ge.grupo_id = g.id
        WHERE g.creado_por = auth.uid()
        AND ge.estudiante_id = conversaciones.estudiante_id
    ));
CREATE POLICY "Admin ve todas las conversaciones" ON conversaciones
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));
CREATE POLICY "Estudiante inserta conversación" ON conversaciones
    FOR INSERT WITH CHECK (estudiante_id = auth.uid());

-- Políticas: mensajes
CREATE POLICY "Estudiante ve mensajes de sus conversaciones" ON mensajes
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM conversaciones c
        WHERE c.id = mensajes.conversacion_id AND c.estudiante_id = auth.uid()
    ));
CREATE POLICY "Docente ve mensajes de sus estudiantes" ON mensajes
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM conversaciones c
        JOIN grupos g ON g.id = c.grupo_id
        WHERE c.id = mensajes.conversacion_id AND g.creado_por = auth.uid()
    ));
CREATE POLICY "Estudiante inserta mensaje" ON mensajes
    FOR INSERT WITH CHECK (EXISTS (
        SELECT 1 FROM conversaciones c
        WHERE c.id = mensajes.conversacion_id AND c.estudiante_id = auth.uid()
    ));

-- Políticas: mensajes_docente (estudiantes ven los suyos, docentes los que envían)
CREATE POLICY "Estudiante ve sus mensajes" ON mensajes_docente
    FOR SELECT USING (para_estudiante_id = auth.uid());
CREATE POLICY "Docente ve mensajes que envió" ON mensajes_docente
    FOR SELECT USING (de_usuario_id = auth.uid());
CREATE POLICY "Docente inserta mensaje" ON mensajes_docente
    FOR INSERT WITH CHECK (de_usuario_id = auth.uid());

-- Políticas: grupos (docentes ven los suyos)
CREATE POLICY "Docente ve sus grupos" ON grupos
    FOR SELECT USING (creado_por = auth.uid());
CREATE POLICY "Docente inserta grupo" ON grupos
    FOR INSERT WITH CHECK (creado_por = auth.uid());
CREATE POLICY "Estudiante ve sus grupos" ON grupos
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM grupos_estudiantes ge
        WHERE ge.grupo_id = grupos.id AND ge.estudiante_id = auth.uid()
    ));

-- Políticas: logs (solo admin)
CREATE POLICY "Admin ve logs" ON logs_sesiones
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM profiles WHERE id = auth.uid() AND rol = 'admin'
    ));
CREATE POLICY "Sistema inserta logs" ON logs_sesiones
    FOR INSERT WITH CHECK (TRUE);

-- 10. TRIGGER — auto-crear perfil al registrarse en auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, nombre, rol)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'nombre', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'rol', 'estudiante')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- 10. ÍNDICES
CREATE INDEX IF NOT EXISTS idx_profiles_rol ON profiles(rol);
CREATE INDEX IF NOT EXISTS idx_grupos_creador ON grupos(creado_por);
CREATE INDEX IF NOT EXISTS idx_grupos_estudiantes_grupo ON grupos_estudiantes(grupo_id);
CREATE INDEX IF NOT EXISTS idx_grupos_estudiantes_estudiante ON grupos_estudiantes(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_conversaciones_estudiante ON conversaciones(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_conversaciones_grupo ON conversaciones(grupo_id);
CREATE INDEX IF NOT EXISTS idx_conversaciones_asignatura ON conversaciones(asignatura);
CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion ON mensajes(conversacion_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_docente_para ON mensajes_docente(para_estudiante_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_docente_grupo ON mensajes_docente(para_grupo_id);
CREATE INDEX IF NOT EXISTS idx_logs_sesion ON logs_sesiones(session_id);
CREATE INDEX IF NOT EXISTS idx_logs_asignatura ON logs_sesiones(asignatura);
CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_sesiones(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs_sesiones(usuario_id);
