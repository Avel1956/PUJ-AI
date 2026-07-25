# Tutor Socrático Universal

Asistente pedagógico basado en IA con RAG para estudiantes de ingeniería — Pontificia Universidad Javeriana Cali.

**Investigador principal:** Jaime Andrés Vélez Zea  
**Proyecto de investigación:** Agentes IA como Asistentes Pedagógicos en Ingeniería  
**Semestre:** 2026-2

---

## Arquitectura

```
Streamlit (frontend) ←→ Supabase (auth + DB) ←→ LangChain + ChromaDB (RAG) ←→ OpenRouter / DeepSeek (LLM)
```

- **Auth:** 3 roles — estudiante, docente, administrador
- **RAG:** ChromaDB + sentence-transformers (all-MiniLM-L6-v2)
- **Modelos:** OpenRouter (Gemini Flash, Claude) + DeepSeek directo
- **Cursos:** Estructura por carpetas (`asignaturas/<curso>/documentos/`)

---

## Setup rápido

### 1. Supabase

1. Crear cuenta en [supabase.com](https://supabase.com)
2. Crear proyecto → guardar URL y keys (anon + service_role)
3. SQL Editor → pegar TODO el contenido de `migration.sql` → Run
4. Authentication → Settings → **deshabilitar "Confirm email"** (para estudiantes creados por docentes)

### 2. API Keys

- [OpenRouter](https://openrouter.ai/keys) → crear key, añadir $5 crédito
- [DeepSeek](https://platform.deepseek.com/api_keys) → crear key

### 3. Streamlit Cloud

1. Subir este repo a GitHub (público o privado)
2. Ir a [share.streamlit.io](https://share.streamlit.io) → New app
3. Conectar repo → configurar secrets en Settings → Secrets:

```toml
SUPABASE_URL = "https://XXXXXXXX.supabase.co"
SUPABASE_KEY = "eyJhbGci... (anon key)"
SUPABASE_SERVICE_KEY = "eyJhbGci... (service_role key)"
OPENROUTER_API_KEY = "sk-or-v1-..."
DEEPSEEK_API_KEY = "sk-..."
ADMIN_EMAIL = "admin@javerianacali.edu.co"
```

### 4. Primer admin

Crear manualmente el primer usuario admin desde Supabase:

1. Authentication → Add user → email + password
2. SQL Editor → `UPDATE profiles SET rol = 'admin' WHERE email = 'admin@javerianacali.edu.co';`

---

## Estructura del proyecto

```
tutor-socratico/
├── app.py                 # Entry point + auth + ruteo por rol
├── config.py              # Configuración, modelos, dataclasses
├── auth.py                # Supabase Auth (login, signup, admin.create_user)
├── prompts.py             # Guardrails socráticos + prompts por curso
├── rag_engine.py          # MotorRAG (ChromaDB + LangChain)
├── telemetry.py           # Logging en Supabase + rate limiting
├── pages_estudiante.py    # Dashboard estudiante (chat, historial, bandeja)
├── pages_docente.py       # Dashboard docente (estudiantes, grupos, tracking, msgs)
├── pages_admin.py         # Dashboard admin (docentes, modelos, estadísticas, sistema)
├── migration.sql          # Schema completo para Supabase
├── requirements.txt       # Dependencias para Streamlit Cloud
├── .streamlit/
│   └── secrets.toml       # Template (no contiene keys reales)
├── asignaturas/
│   └── <curso>/
│       ├── prompt_sistema.txt
│       └── documentos/
│           ├── *.pdf
│           ├── *.txt
│           └── *.md
└── README.md
```

---

## Agregar un curso nuevo

1. Crear carpeta `asignaturas/<nombre-curso>/`
2. Agregar `prompt_sistema.txt` con el contenido del curso
3. Poner PDFs, .txt y .md en `documentos/`
4. Hacer push — el RAG indexa automáticamente al iniciar

---

## Costo estimado

Con 200 estudiantes, 50 preguntas cada uno, usando **Gemini 2.0 Flash**:

- ~1M tokens input + ~500K tokens output por estudiante
- Costo: ~$0.10 por estudiante
- **Total semestre: ~$10 USD**

---

## Licencia

Uso académico interno — Pontificia Universidad Javeriana Cali.
