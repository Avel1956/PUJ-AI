# PUJ-IA — Tutor Socrático

Asistente pedagógico basado en IA con RAG para estudiantes de ingeniería — Pontificia Universidad Javeriana Cali.

**Investigador principal:** Jaime Andrés Vélez Zea
**Proyecto de investigación:** Agentes IA como Asistentes Pedagógicos en Ingeniería
**Semestre:** 2026-2

---

## Arquitectura

```
Streamlit (frontend) ←→ Supabase (auth + DB + RLS) ←→ ChromaDB + LangChain (RAG) ←→ DeepSeek / OpenRouter (LLM)
```

- **Auth:** 3 roles — estudiante, docente, administrador (Supabase Auth)
- **RAG:** ChromaDB con su embedding por defecto (ONNX `all-MiniLM-L6-v2`); no requiere `torch`
- **LLM:** DeepSeek directo y OpenRouter (proveedor OpenAI-compatible)
- **Cursos:** estructura por carpetas (`asignaturas/<curso>/`)
- **Seguridad:** RLS activa en las 9 tablas + cliente Supabase por sesión

## Modelo multcurso

Cada curso es **una rama de Git y un despliegue de Streamlit Cloud independiente**, pero **todos comparten un único proyecto de Supabase** (misma base, mismas cuentas, misma tabla `config_sistema`).

| Rama | Curso |
|---|---|
| `main` | integración de los 4 cursos (multcurso) |
| `deploy-mecanica-solidos` | Mecánica de Sólidos |
| `deploy-metodos-numericos` | Métodos Numéricos |
| `deploy-proyecto-integrador-i` | Proyecto Integrador I |
| `deploy-disenio-mecanico` | Diseño Mecánico |

El código de la aplicación es **idéntico en las 5 ramas**; lo único que cambia es el contenido de `asignaturas/`. Por eso un cambio de código se hace en `main` y se propaga con `git cherry-pick` a cada rama `deploy-*`.

Consecuencias prácticas:

- El **modelo LLM es global**: se lee de `config_sistema.modelo_llm` (una sola fila), así que cambiarlo afecta a **todos los cursos a la vez**.
- El **límite diario de preguntas y el tope de costo también son globales**.
- Un estudiante inscrito en N cursos tiene **N cuentas**, una por curso, usando subdireccionamiento de correo: `ana@correo.com` → `ana+<curso>@correo.com` (cada una con su propia contraseña).

---

## Estructura del proyecto

```
├── app.py                  # Punto de entrada: sesión, ruteo por rol
├── config.py               # Secretos, catálogo de modelos y tarifas
├── auth.py                 # Supabase Auth + cliente POR SESIÓN
├── chat_core.py            # LLM, RAG, guardrails, persistencia del chat
├── prompts.py              # Guardrails socráticos + prompt por curso
├── rag_engine.py           # MotorRAG (ChromaDB + LangChain)
├── telemetry.py            # Registro de uso y control de abuso
├── pages_estudiante.py     # Chat · Historial · Bandeja
├── pages_docente.py        # Estudiantes · Grupos · Tracking · Mensajes · Descargas · Chat
├── pages_admin.py          # Docentes · Estudiantes · Modelos · Estadísticas · Datos · Chat
├── migration.sql           # Esquema base (tablas + datos semilla + RLS inicial)
├── migration_v2..v5.sql    # Migraciones incrementales, idempotentes
├── requirements.txt
├── asignaturas/
│   └── <curso>/
│       ├── prompt_sistema.txt   # Personalidad y guardrails del tutor del curso
│       └── documentos/          # Material que alimenta el RAG (recursivo)
└── README.md
```

El repositorio **no incluye** ningún archivo de secretos: en Streamlit Cloud se configuran en *Settings → Secrets*, y para ejecutar en local hay que crear `.streamlit/secrets.toml` con las mismas claves.

---

## Setup rápido

### 1. Supabase

1. Crear proyecto en [supabase.com](https://supabase.com) → guardar la URL y las llaves.
2. **SQL Editor** → ejecutar **en este orden**:

   ```
   migration.sql        -- esquema base + datos semilla
   migration_v2.sql     -- profiles.creado_por / asignatura, handle_new_user, RLS
   migration_v3.sql     -- tabla docente_cursos
   migration_v4.sql     -- RLS de conversaciones/mensajes/grupos_estudiantes
   migration_v5.sql     -- RLS COMPLETA en las 9 tablas (reconciliación)
   ```

   **`migration_v2..v5.sql` son idempotentes** y se pueden reejecutar sin daño.
   **`migration.sql` no lo es**: usa `CREATE POLICY` sin `DROP POLICY IF EXISTS`, así que reejecutarlo falla con `policy "..." already exists`. Créalo una sola vez al instalar; en una base que ya existe use solo las `v2`–`v5`. **`migration_v5.sql` es el que completa la RLS**: ejecutar solo parte de la secuencia deja la base peor que no tocarla.

   > **Verificado contra un PostgreSQL 16 real:** este orden deja las 9 tablas con RLS activa y **54 políticas**. La política de más, `Estudiante borra mensaje recibido` sobre `mensajes_docente`, es heredada de `migration.sql` y **no existe en las bases ya en operación** (que dan 53): es la diferencia entre una instalación nueva y las que se migraron sobre el esquema antiguo.

3. **Authentication → Settings → deshabilitar "Confirm email"** (los docentes crean cuentas de estudiantes por lotes, sin buzón verificado).

### 2. Claves de API

- [DeepSeek](https://platform.deepseek.com/api_keys) → `DEEPSEEK_API_KEY` (modelo por defecto)
- [OpenRouter](https://openrouter.ai/keys) → `OPENROUTER_API_KEY` (modelos alternativos: Gemini, Claude)

### 3. Streamlit Cloud

1. Subir el repositorio a GitHub y crear la app en [share.streamlit.io](https://share.streamlit.io) apuntando al `app.py` **de la rama del curso**.
2. **Settings → Secrets**:

```toml
SUPABASE_URL = "https://XXXXXXXX.supabase.co"

# Llave pública. Desde la migración v5 la RLS está activa y el cliente es por
# sesión, así que la app funciona con la llave anon; usar service_role aquí
# significa que cualquier consulta sin token de usuario se salta las políticas.
SUPABASE_KEY = "eyJhbGci...   (anon / publishable)"

# Llave secreta: SOLO para administrar cuentas (crear, borrar, restablecer
# contraseña). No se usa para leer datos.
SUPABASE_SERVICE_KEY = "eyJhbGci...   (service_role / secret)"

DEEPSEEK_API_KEY = "sk-..."
OPENROUTER_API_KEY = "sk-or-v1-..."
```

No hay otros secretos: la app **no** lee ninguna variable de entorno ni `ADMIN_EMAIL`.

### 4. Primer administrador

1. **Authentication → Add user** → correo y contraseña.
2. **SQL Editor:**

```sql
UPDATE profiles SET rol = 'admin' WHERE email = 'admin@tu-dominio.edu.co';
```

### 5. Elegir el modelo

`migration.sql` siembra `config_sistema.modelo_llm = 'gemini-2.0-flash'` (con `ON CONFLICT DO NOTHING`, así que no pisa un valor existente). Para usar el modelo recomendado, en **Panel admin → 🧠 Modelos**, o directamente:

```sql
UPDATE config_sistema SET valor = 'deepseek-flash' WHERE clave = 'modelo_llm';
```

---

## Roles y funcionalidad

| Rol | Puede |
|---|---|
| **Estudiante** | Conversar con el tutor de su curso, consultar su historial, recibir mensajes del docente |
| **Docente** | Ver **solo sus** estudiantes, crearles cuentas y **restablecer su contraseña**, agruparlos, ver su actividad, enviarles mensajes (individual o a un grupo), exportar su actividad en JSONL |
| **Admin** | Gestionar docentes y cursos, ver estadísticas globales, cambiar el modelo y los límites, restablecer cualquier contraseña, exportar datos |

Sobre las contraseñas: solo se guarda el hash. **No son recuperables**, solo restablecibles (desde el panel del docente, o masivamente con el script de administración).

---

## Agregar o modificar el contenido de un curso

1. Añadir los materiales en `asignaturas/<curso>/documentos/` (admite subcarpetas).
2. Ajustar `asignaturas/<curso>/prompt_sistema.txt` (personalidad del tutor y guardrails).
3. Hacer commit y push a la rama del curso — el RAG reindexa automáticamente al arrancar.

Para crear un curso nuevo: crear la rama `deploy-<curso>` desde `main`, dejar en `asignaturas/` **exactamente una** carpeta con su `prompt_sistema.txt` y sus `documentos/`, y crear el despliegue en Streamlit Cloud.

### Cómo funciona el RAG

- **Formatos admitidos:** `.pdf`, `.txt`, `.md`, `.docx`, `.pptx`. Cualquier otro se ignora.
- **Recorrido recursivo** de `documentos/` (las subcarpetas cuentan).
- Codificación de texto detectada automáticamente (utf-8, utf-8-sig, cp1252, latin-1).
- Troceado a 800 caracteres con 150 de solape.
- El índice se guarda en `.vectorstores/<curso>/`. Un **fingerprint** del contenido decide la reindexación: si el material cambia, se apunta a una colección nueva en lugar de acumular fragmentos duplicados.
- **Los PDF escaneados sin capa de texto no se pueden indexar.** Se cuentan como archivo no leído y el aviso aparece en pantalla («⚠️ N archivo(s) del curso no se pudieron leer»). Si un documento falta en las respuestas del tutor, es lo primero que hay que revisar.

---

## Configuración en caliente

Todo se edita desde el **panel de administración** y se lee en vivo (no hace falta redesplegar). Vive en la tabla `config_sistema` y es **común a todos los cursos**:

| Clave | Por defecto | Efecto |
|---|---|---|
| `modelo_llm` | `deepseek-flash` | Modelo activo, clave de `MODELOS_DISPONIBLES` |
| `max_preguntas_dia` | `50` | Preguntas por estudiante y día. Se cuentan **en la base de datos**, así que recargar la página no lo reinicia |
| `costo_maximo_sesion_usd` | `0.10` | Tope de costo estimado por sesión de chat |

`MODELOS_DISPONIBLES` (en `config.py`) es el **catálogo** de modelos con sus tarifas; el modelo efectivo es el de `config_sistema`. Añadir un modelo al catálogo no lo activa.

DeepSeek factura **el doble en horas peak** (01:00–04:00 y 06:00–10:00 UTC, de lunes a viernes). En hora Colombia eso es 20:00–23:00 y 01:00–05:00, así que las clases diurnas siempre caen en tarifa reducida; `config.tarifa_por_1k()` lo aplica automáticamente. El modo *thinking* de DeepSeek viene activado por defecto y **se desactiva** aquí (`DEEPSEEK_THINKING = False`): encarece, añade latencia e ignora la temperatura.

---

## Seguridad

- **RLS activa en las 9 tablas** (desde `migration_v5.sql`), con 53 políticas en las bases en operación.
- **`get_supabase()` devuelve un cliente por sesión de navegador**, con el token del usuario. Esto es imprescindible: el proceso de Streamlit sirve a todos los usuarios, así que un cliente compartido evaluaría la RLS con la identidad del último que inició sesión. **No volver a cachearlo con `@st.cache_resource`** — solo el cliente de administración (`get_supabase_admin`, que usa service_role) se cachea.
- La frontera es **doble**: la RLS *y* los filtros por `creado_por` / `estudiante_id` en el panel del docente. Ninguna de las dos se debe dar por supuesta.

---

## Costo estimado

Con **DeepSeek V4.1 Flash** en tarifa reducida (la de las clases diurnas), y suponiendo ~2.500 tokens de entrada y ~400 de salida por pregunta:

- **~USD 0.0006 por pregunta.**
- 50 preguntas (el tope diario), un estudiante: **~USD 0.03 al día**.
- Un curso de 60 estudiantes con el tope agotado: **~USD 1.80 al día**.
- Un semestre, con un uso real de ~300 preguntas por estudiante: **~USD 0.18 por estudiante**.

Las tarifas vigentes están en `config.MODELOS_DISPONIBLES` y deben **reverificarse** cuando el proveedor las cambie.

---

## Verificación

El proyecto no trae suite de pruebas. Las comprobaciones viven **fuera del repositorio**, junto a los scripts de administración que necesitan la llave `service_role`:

```bash
cd <carpeta-herramientas>

python verificar_app.py          # estática: compilación, invariantes, las 5 ramas
python test_auth_sesion.py       # cliente por sesión (simula 2 sesiones concurrentes)
uv run --with pgserver --with "psycopg[binary]" python test_migration_v5.py
                                 # RLS contra un PostgreSQL 16 real
```

Las tres terminan con código de salida 1 si algo falla.

---

## Licencia

Uso académico interno — Pontificia Universidad Javeriana Cali.
