-- ============================================================
-- Tutor Socrático Universal — MIGRACIÓN v5
-- RLS COMPLETA Y RECONCILIADA
-- Investigador principal: Jaime Andrés Vélez Zea
-- Pontificia Universidad Javeriana Cali, 2026
-- ============================================================
--
-- ⚠️  LEER ANTES DE EJECUTAR
--
-- ESTADO ENCONTRADO (verificado 2026-09-10 con pg_policies):
--   * `migration.sql` (el script base, con 41 políticas) NUNCA se aplicó.
--   * Solo se aplicaron v2, v3 y v4 → 14 políticas en total.
--   * La RLS estaba habilitada ÚNICAMENTE en `docente_cursos`.
--   * Las otras 8 tablas tenían RLS DESHABILITADA: sus políticas eran inertes.
--   * `config_sistema` no tenía RLS habilitada ni una sola política que la
--     leyera o escribiera (solo un DELETE).
--
-- QUÉ HACE ESTE SCRIPT:
--   Habilita RLS en las 9 tablas y crea TODAS las políticas que la aplicación
--   necesita, reconciliando base + v2 + v3 + v4 y añadiendo las que no existían
--   en ningún script. Es idempotente: puede ejecutarse varias veces.
--
-- ¿ES SEGURO EJECUTARLO AHORA?
--   SÍ. Hoy `SUPABASE_KEY` y `SUPABASE_SERVICE_KEY` tienen el mismo valor
--   (la clave service_role), y service_role SALTA la RLS por diseño. Por eso
--   este script no cambia el comportamiento actual de la aplicación.
--
-- ⛔ NO CAMBIE `SUPABASE_KEY` A LA CLAVE ANON DESPUÉS DE EJECUTAR ESTO
--   Hasta que la aplicación cree un cliente Supabase POR SESIÓN.
--   `auth.get_supabase()` está decorado con `@st.cache_resource`: es UN solo
--   cliente compartido por todo el proceso de Streamlit, y `login()` hace
--   `sign_in_with_password()` sobre ese mismo cliente. Con RLS activa y un
--   cliente compartido, cada consulta se evaluaría con la identidad del ÚLTIMO
--   usuario que inició sesión. Sería PEOR que no tener RLS.
--   Orden correcto: (1) cliente por sesión → (2) clave anon → (3) este script.
--
-- INSTRUCCIONES:
--   1. Supabase Dashboard → SQL Editor
--   2. Pegar TODO este archivo
--   3. Ejecutar (Ctrl+Enter)
--   4. Verificar con la consulta del final
-- ============================================================


-- ============================================================
-- 1. FUNCIONES AUXILIARES
--
-- Son SECURITY DEFINER a propósito, por dos razones:
--   a) Evitan la RECURSIÓN INFINITA: una política sobre `profiles` que
--      consultara `profiles` haría que Postgres abortara.
--   b) Hacen las políticas cortas, legibles y consistentes.
-- `SET search_path` fija el esquema para que no sean explotables.
-- ============================================================
CREATE OR REPLACE FUNCTION public.es_rol(roles text[])
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
         WHERE id = auth.uid() AND rol = ANY(roles)
    );
$$;

CREATE OR REPLACE FUNCTION public.es_admin() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT public.es_rol(ARRAY['admin']);
$$;

CREATE OR REPLACE FUNCTION public.es_docente() RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT public.es_rol(ARRAY['docente']);
$$;

-- ¿La cuenta `estudiante` pertenece al docente que hace la consulta?
CREATE OR REPLACE FUNCTION public.docente_de(estudiante uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
         WHERE id = estudiante AND creado_por = auth.uid()
    );
$$;

-- ¿Es mío este grupo?
CREATE OR REPLACE FUNCTION public.grupo_es_mio(grupo uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.grupos
         WHERE id = grupo AND creado_por = auth.uid()
    );
$$;

-- ¿Esta conversación es de un estudiante mío?
CREATE OR REPLACE FUNCTION public.conversacion_es_de_mi_estudiante(conv uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.conversaciones c
          JOIN public.profiles p ON p.id = c.estudiante_id
         WHERE c.id = conv AND p.creado_por = auth.uid()
    );
$$;


-- ============================================================
-- 2. HABILITAR RLS EN LAS 9 TABLAS
-- ============================================================
ALTER TABLE public.profiles            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grupos              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grupos_estudiantes  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversaciones      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mensajes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mensajes_docente    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.logs_sesiones       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.docente_cursos      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.config_sistema      ENABLE ROW LEVEL SECURITY;  -- faltaba


-- ============================================================
-- 3. PROFILES
-- ============================================================
DROP POLICY IF EXISTS "Usuarios ven su propio perfil"    ON public.profiles;
DROP POLICY IF EXISTS "Admin ve todos los perfiles"      ON public.profiles;
DROP POLICY IF EXISTS "Admin inserta perfiles"           ON public.profiles;
DROP POLICY IF EXISTS "Admin borra perfiles"             ON public.profiles;
DROP POLICY IF EXISTS "Docente ve sus estudiantes"       ON public.profiles;
DROP POLICY IF EXISTS "Docente borra sus estudiantes"    ON public.profiles;
DROP POLICY IF EXISTS "Docente actualiza sus estudiantes" ON public.profiles;
DROP POLICY IF EXISTS "Docente borra estudiantes"        ON public.profiles;  -- nombre antiguo (v1)

-- Cada usuario ve su propio perfil (lo necesita el login).
CREATE POLICY "Usuarios ven su propio perfil" ON public.profiles
    FOR SELECT TO authenticated USING (auth.uid() = id);

CREATE POLICY "Admin ve todos los perfiles" ON public.profiles
    FOR SELECT TO authenticated USING (public.es_admin());

CREATE POLICY "Admin inserta perfiles" ON public.profiles
    FOR INSERT TO authenticated WITH CHECK (public.es_admin());

CREATE POLICY "Admin borra perfiles" ON public.profiles
    FOR DELETE TO authenticated USING (public.es_admin() AND id <> auth.uid());

-- El docente ve, actualiza y borra SOLO los estudiantes que él creó.
-- Se exige coincidencia exacta: un estudiante huérfano (creado_por NULL)
-- tampoco es accesible para un docente.
CREATE POLICY "Docente ve sus estudiantes" ON public.profiles
    FOR SELECT TO authenticated USING (creado_por = auth.uid());

CREATE POLICY "Docente actualiza sus estudiantes" ON public.profiles
    FOR UPDATE TO authenticated
    USING (creado_por = auth.uid()) WITH CHECK (creado_por = auth.uid());

CREATE POLICY "Docente borra sus estudiantes" ON public.profiles
    FOR DELETE TO authenticated USING (creado_por = auth.uid());


-- ============================================================
-- 4. GRUPOS
-- (hoy: RLS deshabilitada y CERO políticas → la pestaña Grupos dependía
--  por completo del filtrado en Python)
-- ============================================================
DROP POLICY IF EXISTS "Docente ve sus grupos"     ON public.grupos;
DROP POLICY IF EXISTS "Docente inserta grupo"     ON public.grupos;
DROP POLICY IF EXISTS "Estudiante ve sus grupos"  ON public.grupos;
DROP POLICY IF EXISTS "Docente borra sus grupos"  ON public.grupos;
DROP POLICY IF EXISTS "Admin ve grupos"           ON public.grupos;
DROP POLICY IF EXISTS "Admin borra grupos"        ON public.grupos;

CREATE POLICY "Docente ve sus grupos" ON public.grupos
    FOR SELECT TO authenticated USING (creado_por = auth.uid());

CREATE POLICY "Docente inserta grupo" ON public.grupos
    FOR INSERT TO authenticated WITH CHECK (creado_por = auth.uid());

CREATE POLICY "Docente borra sus grupos" ON public.grupos
    FOR DELETE TO authenticated USING (creado_por = auth.uid());

-- El estudiante ve el grupo al que pertenece (lo necesita el selector de grupo).
CREATE POLICY "Estudiante ve sus grupos" ON public.grupos
    FOR SELECT TO authenticated USING (
        EXISTS (
            SELECT 1 FROM public.grupos_estudiantes ge
             WHERE ge.grupo_id = grupos.id AND ge.estudiante_id = auth.uid()
        )
    );

CREATE POLICY "Admin ve grupos" ON public.grupos
    FOR SELECT TO authenticated USING (public.es_admin());

CREATE POLICY "Admin borra grupos" ON public.grupos
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 5. GRUPOS_ESTUDIANTES
-- (hoy: solo 3 políticas SELECT; faltaban INSERT y DELETE)
-- ============================================================
DROP POLICY IF EXISTS "Estudiante ve sus membresias"          ON public.grupos_estudiantes;
DROP POLICY IF EXISTS "Docente ve miembros de sus grupos"     ON public.grupos_estudiantes;
DROP POLICY IF EXISTS "Admin ve membresias"                   ON public.grupos_estudiantes;
DROP POLICY IF EXISTS "Docente inserta miembros de sus grupos" ON public.grupos_estudiantes;
DROP POLICY IF EXISTS "Docente borra miembros de sus grupos"  ON public.grupos_estudiantes;
DROP POLICY IF EXISTS "Admin borra miembros de grupos"        ON public.grupos_estudiantes;

CREATE POLICY "Estudiante ve sus membresias" ON public.grupos_estudiantes
    FOR SELECT TO authenticated USING (estudiante_id = auth.uid());

CREATE POLICY "Docente ve miembros de sus grupos" ON public.grupos_estudiantes
    FOR SELECT TO authenticated USING (public.grupo_es_mio(grupo_id));

CREATE POLICY "Admin ve membresias" ON public.grupos_estudiantes
    FOR SELECT TO authenticated USING (public.es_admin());

-- FALTABA: sin esto, crear un grupo no puede añadir miembros con RLS activa.
CREATE POLICY "Docente inserta miembros de sus grupos" ON public.grupos_estudiantes
    FOR INSERT TO authenticated WITH CHECK (public.grupo_es_mio(grupo_id));

CREATE POLICY "Docente borra miembros de sus grupos" ON public.grupos_estudiantes
    FOR DELETE TO authenticated USING (public.grupo_es_mio(grupo_id));

CREATE POLICY "Admin borra miembros de grupos" ON public.grupos_estudiantes
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 6. CONVERSACIONES
-- (hoy: solo 2 políticas de docente; faltaban las del ESTUDIANTE, que es
--  justamente quien crea las conversaciones)
-- ============================================================
DROP POLICY IF EXISTS "Estudiante ve sus conversaciones"                    ON public.conversaciones;
DROP POLICY IF EXISTS "Estudiante inserta conversación"                     ON public.conversaciones;
DROP POLICY IF EXISTS "Estudiante borra sus conversaciones"                 ON public.conversaciones;
DROP POLICY IF EXISTS "Docente ve conversaciones de sus grupos"             ON public.conversaciones;
DROP POLICY IF EXISTS "Docente ve conversaciones de estudiantes creados"    ON public.conversaciones;
DROP POLICY IF EXISTS "Docente borra conversaciones de sus grupos"          ON public.conversaciones;
DROP POLICY IF EXISTS "Docente borra conversaciones de estudiantes creados" ON public.conversaciones;
DROP POLICY IF EXISTS "Admin ve todas las conversaciones"                   ON public.conversaciones;
DROP POLICY IF EXISTS "Admin borra conversaciones"                          ON public.conversaciones;

CREATE POLICY "Estudiante ve sus conversaciones" ON public.conversaciones
    FOR SELECT TO authenticated USING (estudiante_id = auth.uid());

CREATE POLICY "Estudiante inserta conversación" ON public.conversaciones
    FOR INSERT TO authenticated WITH CHECK (estudiante_id = auth.uid());

CREATE POLICY "Estudiante borra sus conversaciones" ON public.conversaciones
    FOR DELETE TO authenticated USING (estudiante_id = auth.uid());

-- El docente ve/borra las conversaciones de los estudiantes que creó.
CREATE POLICY "Docente ve conversaciones de estudiantes creados" ON public.conversaciones
    FOR SELECT TO authenticated USING (public.docente_de(estudiante_id));

CREATE POLICY "Docente borra conversaciones de estudiantes creados" ON public.conversaciones
    FOR DELETE TO authenticated USING (public.docente_de(estudiante_id));

-- Además, las de los miembros de sus grupos.
CREATE POLICY "Docente ve conversaciones de sus grupos" ON public.conversaciones
    FOR SELECT TO authenticated USING (public.grupo_es_mio(grupo_id));

CREATE POLICY "Docente borra conversaciones de sus grupos" ON public.conversaciones
    FOR DELETE TO authenticated USING (public.grupo_es_mio(grupo_id));

CREATE POLICY "Admin ve todas las conversaciones" ON public.conversaciones
    FOR SELECT TO authenticated USING (public.es_admin());

CREATE POLICY "Admin borra conversaciones" ON public.conversaciones
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 7. MENSAJES
-- ============================================================
DROP POLICY IF EXISTS "Estudiante ve mensajes de sus conversaciones"    ON public.mensajes;
DROP POLICY IF EXISTS "Estudiante inserta mensaje"                      ON public.mensajes;
DROP POLICY IF EXISTS "Estudiante borra sus mensajes"                   ON public.mensajes;
DROP POLICY IF EXISTS "Docente ve mensajes de sus estudiantes"          ON public.mensajes;
DROP POLICY IF EXISTS "Docente ve mensajes de estudiantes creados"      ON public.mensajes;
DROP POLICY IF EXISTS "Docente borra mensajes de sus estudiantes"       ON public.mensajes;
DROP POLICY IF EXISTS "Docente borra mensajes de estudiantes creados"   ON public.mensajes;
DROP POLICY IF EXISTS "Admin borra mensajes"                            ON public.mensajes;

CREATE POLICY "Estudiante ve mensajes de sus conversaciones" ON public.mensajes
    FOR SELECT TO authenticated USING (
        EXISTS (
            SELECT 1 FROM public.conversaciones c
             WHERE c.id = mensajes.conversacion_id
               AND c.estudiante_id = auth.uid()
        )
    );

CREATE POLICY "Estudiante inserta mensaje" ON public.mensajes
    FOR INSERT TO authenticated WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.conversaciones c
             WHERE c.id = mensajes.conversacion_id
               AND c.estudiante_id = auth.uid()
        )
    );

CREATE POLICY "Estudiante borra sus mensajes" ON public.mensajes
    FOR DELETE TO authenticated USING (
        EXISTS (
            SELECT 1 FROM public.conversaciones c
             WHERE c.id = mensajes.conversacion_id
               AND c.estudiante_id = auth.uid()
        )
    );

CREATE POLICY "Docente ve mensajes de estudiantes creados" ON public.mensajes
    FOR SELECT TO authenticated USING (
        public.conversacion_es_de_mi_estudiante(conversacion_id)
    );

CREATE POLICY "Docente borra mensajes de estudiantes creados" ON public.mensajes
    FOR DELETE TO authenticated USING (
        public.conversacion_es_de_mi_estudiante(conversacion_id)
    );

CREATE POLICY "Admin borra mensajes" ON public.mensajes
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 8. MENSAJES_DOCENTE
-- (hoy: RLS deshabilitada y CERO políticas → la bandeja del estudiante y la
--  pestaña Mensajes del docente dependían solo del filtrado en Python)
-- ============================================================
DROP POLICY IF EXISTS "Estudiante ve sus mensajes"           ON public.mensajes_docente;
DROP POLICY IF EXISTS "Estudiante marca sus mensajes leidos" ON public.mensajes_docente;
DROP POLICY IF EXISTS "Docente ve mensajes que envió"        ON public.mensajes_docente;
DROP POLICY IF EXISTS "Docente inserta mensaje"              ON public.mensajes_docente;
DROP POLICY IF EXISTS "Remitente borra su mensaje"           ON public.mensajes_docente;
DROP POLICY IF EXISTS "Admin ve mensajes docentes"           ON public.mensajes_docente;
DROP POLICY IF EXISTS "Admin borra mensajes docentes"        ON public.mensajes_docente;

CREATE POLICY "Estudiante ve sus mensajes" ON public.mensajes_docente
    FOR SELECT TO authenticated USING (
        para_estudiante_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.grupos_estudiantes ge
             WHERE ge.grupo_id = mensajes_docente.para_grupo_id
               AND ge.estudiante_id = auth.uid()
        )
    );

-- FALTABA POR COMPLETO: la bandeja marca `leido = true` al mostrar los
-- mensajes, y sin esta política esa actualización fallaría en silencio.
CREATE POLICY "Estudiante marca sus mensajes leidos" ON public.mensajes_docente
    FOR UPDATE TO authenticated
    USING (
        para_estudiante_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.grupos_estudiantes ge
             WHERE ge.grupo_id = mensajes_docente.para_grupo_id
               AND ge.estudiante_id = auth.uid()
        )
    )
    WITH CHECK (
        para_estudiante_id = auth.uid()
        OR EXISTS (
            SELECT 1 FROM public.grupos_estudiantes ge
             WHERE ge.grupo_id = mensajes_docente.para_grupo_id
               AND ge.estudiante_id = auth.uid()
        )
    );

CREATE POLICY "Docente ve mensajes que envió" ON public.mensajes_docente
    FOR SELECT TO authenticated USING (de_usuario_id = auth.uid());

CREATE POLICY "Docente inserta mensaje" ON public.mensajes_docente
    FOR INSERT TO authenticated WITH CHECK (
        de_usuario_id = auth.uid()
        AND (
            (para_estudiante_id IS NOT NULL AND public.docente_de(para_estudiante_id))
            OR (para_grupo_id IS NOT NULL AND public.grupo_es_mio(para_grupo_id))
        )
    );

CREATE POLICY "Remitente borra su mensaje" ON public.mensajes_docente
    FOR DELETE TO authenticated USING (de_usuario_id = auth.uid());

CREATE POLICY "Admin ve mensajes docentes" ON public.mensajes_docente
    FOR SELECT TO authenticated USING (public.es_admin());

CREATE POLICY "Admin borra mensajes docentes" ON public.mensajes_docente
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 9. LOGS_SESIONES
-- (hoy: RLS deshabilitada, CERO políticas → la telemetría se insertaba sin
--  ningún control)
-- ============================================================
DROP POLICY IF EXISTS "Sistema inserta logs"    ON public.logs_sesiones;
DROP POLICY IF EXISTS "Usuario ve sus propios logs" ON public.logs_sesiones;
DROP POLICY IF EXISTS "Admin ve logs"           ON public.logs_sesiones;
DROP POLICY IF EXISTS "Admin borra logs"        ON public.logs_sesiones;

-- Solo se pueden registrar logs a nombre propio (evita inyectar métricas
-- falsas atribuidas a otro usuario).
CREATE POLICY "Sistema inserta logs" ON public.logs_sesiones
    FOR INSERT TO authenticated WITH CHECK (usuario_id = auth.uid());

-- Necesaria: ControlAbuso cuenta las preguntas del día consultando esta tabla.
CREATE POLICY "Usuario ve sus propios logs" ON public.logs_sesiones
    FOR SELECT TO authenticated USING (usuario_id = auth.uid());

CREATE POLICY "Admin ve logs" ON public.logs_sesiones
    FOR SELECT TO authenticated USING (public.es_admin());

CREATE POLICY "Admin borra logs" ON public.logs_sesiones
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 10. DOCENTE_CURSOS
-- (la única tabla con RLS ya habilitada; se redefinen por consistencia)
-- ============================================================
DROP POLICY IF EXISTS "Docente ve sus cursos" ON public.docente_cursos;
DROP POLICY IF EXISTS "Admin ve cursos"       ON public.docente_cursos;
DROP POLICY IF EXISTS "Admin inserta cursos"  ON public.docente_cursos;
DROP POLICY IF EXISTS "Admin borra cursos"    ON public.docente_cursos;

CREATE POLICY "Docente ve sus cursos" ON public.docente_cursos
    FOR SELECT TO authenticated USING (docente_id = auth.uid());

CREATE POLICY "Admin ve cursos" ON public.docente_cursos
    FOR SELECT TO authenticated USING (public.es_admin());

CREATE POLICY "Admin inserta cursos" ON public.docente_cursos
    FOR INSERT TO authenticated WITH CHECK (public.es_admin());

CREATE POLICY "Admin borra cursos" ON public.docente_cursos
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 11. CONFIG_SISTEMA
-- (hoy: RLS deshabilitada. En NINGÚN script existía una política de SELECT ni
--  de UPDATE: solo un DELETE. Con RLS activa, la aplicación no habría podido
--  ni leer el modelo configurado ni cambiarlo.)
-- ============================================================
DROP POLICY IF EXISTS "Usuarios autenticados leen config" ON public.config_sistema;
DROP POLICY IF EXISTS "Admin inserta config"              ON public.config_sistema;
DROP POLICY IF EXISTS "Admin actualiza config"            ON public.config_sistema;
DROP POLICY IF EXISTS "Admin borra config"                ON public.config_sistema;

-- Lectura abierta a cualquier usuario autenticado: la app necesita conocer el
-- modelo activo para mostrarlo y para calcular costos.
CREATE POLICY "Usuarios autenticados leen config" ON public.config_sistema
    FOR SELECT TO authenticated USING (TRUE);

CREATE POLICY "Admin inserta config" ON public.config_sistema
    FOR INSERT TO authenticated WITH CHECK (public.es_admin());

CREATE POLICY "Admin actualiza config" ON public.config_sistema
    FOR UPDATE TO authenticated
    USING (public.es_admin()) WITH CHECK (public.es_admin());

CREATE POLICY "Admin borra config" ON public.config_sistema
    FOR DELETE TO authenticated USING (public.es_admin());


-- ============================================================
-- 12. ÍNDICES QUE FALTABAN
-- `ControlAbuso` filtra logs_sesiones por usuario_id y timestamp en cada
-- recarga de página; sin este índice la consulta recorre la tabla completa.
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_logs_usuario_timestamp
    ON public.logs_sesiones(usuario_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_sesiones_timestamp
    ON public.logs_sesiones(timestamp);
CREATE INDEX IF NOT EXISTS idx_mensajes_conversacion ON public.mensajes(conversacion_id);
CREATE INDEX IF NOT EXISTS idx_grupos_estudiantes_grupo ON public.grupos_estudiantes(grupo_id);
CREATE INDEX IF NOT EXISTS idx_grupos_estudiantes_estudiante ON public.grupos_estudiantes(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_conversaciones_estudiante ON public.conversaciones(estudiante_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_docente_para ON public.mensajes_docente(para_estudiante_id);
CREATE INDEX IF NOT EXISTS idx_mensajes_docente_grupo ON public.mensajes_docente(para_grupo_id);


-- ============================================================
-- 13. PERMISOS DE EJECUCIÓN DE LAS FUNCIONES AUXILIARES
-- ============================================================
GRANT EXECUTE ON FUNCTION public.es_rol(text[])   TO authenticated;
GRANT EXECUTE ON FUNCTION public.es_admin()       TO authenticated;
GRANT EXECUTE ON FUNCTION public.es_docente()     TO authenticated;
GRANT EXECUTE ON FUNCTION public.docente_de(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.grupo_es_mio(uuid) TO authenticated;
GRANT EXECUTE ON FUNCTION public.conversacion_es_de_mi_estudiante(uuid) TO authenticated;


-- ============================================================
-- 14. VERIFICACIÓN (ejecutar aparte, después de la migración)
-- ============================================================
-- Esperado: las 9 tablas con rls_activo = true y n_politicas > 0.
--
-- select c.relname             as tabla,
--        c.relrowsecurity      as rls_activo,
--        count(p.policyname)   as n_politicas
--   from pg_class c
--   left join pg_policies p
--          on p.schemaname = 'public' and p.tablename = c.relname
--  where c.relnamespace = 'public'::regnamespace
--    and c.relname in ('profiles','grupos','grupos_estudiantes','conversaciones',
--                      'mensajes','mensajes_docente','logs_sesiones',
--                      'docente_cursos','config_sistema')
--  group by c.relname, c.relrowsecurity
--  order by c.relname;
