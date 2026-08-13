# Agent Builder — Plan de Implementación

> **Para Hermes:** Usar `plan` + `streamlit-rag-app` skills. Implementar task-por-task con TDD.

**Goal:** Crear una web app (Streamlit) que permita a docentes construir agentes IA pedagógicos mediante un wizard guiado: setup base → Q&A → ingesta de contenido → digestión LLM → preguntas de refinamiento → generación de system prompt + archivos de soporte. El output debe ser compatible con la estructura `asignaturas/` del Tutor Socrático (PUJ-IA).

**Architecture:** Streamlit (frontend + hosting) + Supabase (auth + persistencia de agentes) + OpenRouter/DeepSeek (LLM para análisis de contenido y generación). Flujo tipo wizard multi-paso (no chat). El docente sube documentos → un LLM "arquitecto de agentes" los analiza, hace preguntas de refinamiento, y genera el prompt de sistema final.

**Tech Stack:** Python 3.11+, Streamlit, Supabase (auth + DB + storage), LangChain (document loaders para PDF/DOCX/PPTX), OpenRouter/DeepSeek API, ChromaDB (análisis semántico opcional).

---

## 1. Contraste: Tutor Socrático vs. Agent Builder

| Dimensión | Tutor Socrático (PUJ-IA) | Agent Builder |
|-----------|--------------------------|---------------|
| **Propósito** | Estudiantes chatean con un agente ya construido | Docentes **crean** nuevos agentes desde cero |
| **Usuarios** | Estudiante, Docente, Admin | **Docente** (único rol, el autor del agente) |
| **Interfaz** | Chat conversacional (st.chat_message) | **Wizard multi-paso** (st.form, st.stepper) |
| **Flujo de contenido** | **Consume** `asignaturas/<curso>/prompt_sistema.txt + documentos/` | **Produce** esa misma estructura |
| **Rol del LLM** | Tutor socrático (responde preguntas) | **Arquitecto de agentes** (analiza, pregunta, genera) |
| **Documentos** | Indexados para RAG (búsqueda semántica) | **Analizados en profundidad** por el LLM para entender el curso |
| **Output** | Mensajes de chat | `prompt_sistema.txt` + `config.yaml` + `resumen_contenido.md` + log de Q&A |
| **Auth requerida** | 3 roles (RLS complejo) | 1 rol (docente), más simple |
| **Storage** | Supabase DB (mensajes, grupos, logs) | Supabase DB (agentes, sesiones de creación) + Storage (documentos subidos) |

### Lo que se reutiliza del Tutor Socrático

| Componente | Reutilización |
|-----------|---------------|
| `config.py` — estructura de modelos, dataclasses | ✅ Con adaptaciones (menos modelos, solo docente) |
| `auth.py` — Supabase Auth | ✅ Simplificado (solo login docente, sin admin/estudiante) |
| `prompts.py` — PROMPT_BASE, `construir_prompt_completo()` | 🔄 El Agent Builder **genera** lo que `prompts.py` **consume** |
| `rag_engine.py` — MotorRAG, ChromaDB | 🔄 No se usa RAG; se usa **análisis completo** de documentos vía LLM |
| `telemetry.py` — logging | ✅ Adaptado para loggear sesiones de creación |
| `chat_core.py` — lógica de chat compartida | ❌ No aplica — el Agent Builder usa wizard, no chat |
| `pages_*.py` — dashboards por rol | ❌ No aplica — un solo flujo de wizard |
| `migration.sql` — schema Supabase | 🔄 Schema nuevo, más simple, enfocado en agentes |

---

## 2. Diseño del Agent Builder

### 2.1 Flujo del Wizard (6 pasos)

```
PASO 1: BASE DEL AGENTE
├── Seleccionar arquetipo (Tutor Socrático, Evaluador, Guía de Proyectos, 
│   Asistente de Laboratorio, Personalizado)
├── Nombre del agente (slug automático)
├── Materia/curso destino
└── Nivel académico (pregrado temprano, pregrado avanzado, posgrado)

PASO 2: PREGUNTAS DE SETUP (dinámicas según arquetipo)
├── Objetivos de aprendizaje del curso
├── Perfil del estudiante típico
├── Estilo de interacción deseado (formal, cercano, técnico, conceptual)
├── Restricciones especiales (ej: "nunca mencionar el examen final")
└── ¿Debe poder evaluar? ¿Calificar? ¿Solo guiar?

PASO 3: SUBIDA DE CONTENIDO
├── Upload múltiple: PDF, DOCX, PPTX, TXT, MD
├── Previsualización de cada archivo subido
├── Opcional: pegar texto directamente
└── Barra de progreso de subida a Supabase Storage

PASO 4: DIGESTIÓN DEL CONTENIDO (LLM-powered)
├── El LLM lee TODOS los documentos (extracción completa de texto)
├── Genera un mapa de conceptos, temas, jerarquía
├── Identifica nivel de dificultad del material
├── Detecta prerequisites implícitos
├── Produce: resumen_contenido.md
└── Muestra al docente: "¿Es correcto este análisis?"

PASO 5: PREGUNTAS DE REFINAMIENTO (LLM-generated)
├── El LLM genera 5-10 preguntas basadas en LO QUE VIÓ en el contenido
├── Ej: "En el capítulo 3 de mecánica.pdf habla de fatiga de materiales,
│   ¿quieres que el agente use el enfoque de Goodman o Soderberg?"
├── Ej: "Detecté que tu curso cubre tanto teoría como laboratorio.
│   ¿El agente debe tratar ambos por igual o priorizar el lab?"
├── El docente responde las que quiera (no obligatorio)
└── Las respuestas alimentan la generación final

PASO 6: GENERACIÓN Y ENTREGA
├── El LLM ensambla el system prompt final combinando:
│   - Plantilla del arquetipo
│   - Respuestas de setup (Paso 2)
│   - Análisis del contenido (Paso 4)
│   - Refinamientos (Paso 5)
├── Vista previa del prompt generado (editable)
├── El docente puede editar manualmente antes de finalizar
├── Botón "Finalizar Agente" → escribe archivos a carpeta
└── Opción: descargar como ZIP o desplegar directo al Tutor Socrático
```

### 2.2 Estructura de archivos del proyecto

```
agent-builder/
├── app.py                    # Entry point Streamlit — wizard principal
├── auth.py                   # Supabase Auth simplificado (solo docentes)
├── config.py                 # Configuración centralizada
├── database.py               # CRUD Supabase para agentes y sesiones
├── arquitecto.py             # "Arquitecto de Agentes" — LLM para análisis y generación
├── arquetipos.py             # Plantillas base por tipo de agente
├── procesador_docs.py        # Carga y extracción de texto de PDF/DOCX/PPTX/TXT/MD
├── wizard_paso1_base.py      # UI: Paso 1 — base del agente
├── wizard_paso2_setup.py     # UI: Paso 2 — preguntas de setup
├── wizard_paso3_contenido.py # UI: Paso 3 — subida de documentos
├── wizard_paso4_digestion.py # UI: Paso 4 — análisis LLM del contenido
├── wizard_paso5_refinar.py   # UI: Paso 5 — preguntas de refinamiento
├── wizard_paso6_generar.py   # UI: Paso 6 — generación y entrega
├── requirements.txt          # Dependencias pineadas
├── .streamlit/
│   └── secrets.toml          # Template
├── agentes_output/           # Output generado (en .gitignore)
│   └── <nombre_agente>/
│       ├── config.yaml
│       ├── prompt_sistema.txt
│       ├── resumen_contenido.md
│       ├── preguntas_respuestas.json
│       └── documentos/       # Copia de referencia
├── supabase/
│   └── migration_agent_builder.sql  # Schema para Agent Builder
└── README.md
```

### 2.3 Schema Supabase (Agent Builder)

```sql
-- Tabla: agentes (metadata de cada agente creado)
CREATE TABLE agentes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    docente_id UUID REFERENCES auth.users(id) NOT NULL,
    nombre TEXT NOT NULL,                    -- nombre del agente
    slug TEXT NOT NULL,                      -- nombre_agente (para carpeta)
    arquetipo TEXT NOT NULL,                 -- 'tutor_socratico', 'evaluador', etc.
    asignatura TEXT NOT NULL,                -- materia/curso destino
    nivel TEXT NOT NULL,                     -- 'pregrado_temprano', 'pregrado_avanzado', 'posgrado'
    config JSONB DEFAULT '{}',              -- todas las respuestas del wizard
    prompt_final TEXT,                       -- system prompt generado
    estado TEXT DEFAULT 'borrador',          -- 'borrador', 'finalizado', 'desplegado'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Tabla: sesiones_creacion (log de cada sesión de creación)
CREATE TABLE sesiones_creacion (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agente_id UUID REFERENCES agentes(id),
    paso TEXT NOT NULL,                      -- 'base', 'setup', 'contenido', 'digestion', 'refinar', 'generar'
    datos JSONB DEFAULT '{}',               -- datos del paso
    tokens_usados INT DEFAULT 0,
    costo_usd NUMERIC(10,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Tabla: documentos_agente (referencia a archivos subidos en Storage)
CREATE TABLE documentos_agente (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agente_id UUID REFERENCES agentes(id) NOT NULL,
    nombre_original TEXT NOT NULL,
    storage_path TEXT NOT NULL,              -- ruta en Supabase Storage
    tipo_mime TEXT,                          -- 'application/pdf', etc.
    tamano_bytes INT,
    texto_extraido TEXT,                     -- texto completo extraído
    token_count INT,                         -- estimación de tokens
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: docente solo ve sus propios agentes
ALTER TABLE agentes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "docente ve sus agentes" ON agentes
    FOR ALL USING (docente_id = auth.uid());

ALTER TABLE sesiones_creacion ENABLE ROW LEVEL SECURITY;
CREATE POLICY "docente ve sus sesiones" ON sesiones_creacion
    FOR ALL USING (agente_id IN (SELECT id FROM agentes WHERE docente_id = auth.uid()));

ALTER TABLE documentos_agente ENABLE ROW LEVEL SECURITY;
CREATE POLICY "docente ve sus docs" ON documentos_agente
    FOR ALL USING (agente_id IN (SELECT id FROM agentes WHERE docente_id = auth.uid()));
```

### 2.4 Arquetipos de Agentes

```python
# arquetipos.py

ARQUETIPOS = {
    "tutor_socratico": {
        "nombre": "Tutor Socrático",
        "descripcion": "Guía al estudiante con preguntas, nunca da respuestas directas. "
                       "Ideal para cursos teóricos y de proyecto.",
        "icono": "🦉",
        "prompt_base": """Eres un tutor socrático para {asignatura}...
[plantilla base del tutor — similar a PROMPT_BASE actual]""",
        "preguntas_setup": [
            "¿Qué tan estricto debe ser el agente al negar respuestas directas?",
            "¿Debe el agente sugerir bibliografía adicional?",
            "¿Hay temas que el agente NUNCA debe abordar?",
        ],
    },
    "evaluador": {
        "nombre": "Evaluador Formativo",
        "descripcion": "Evalúa el trabajo del estudiante con rúbricas y retroalimentación "
                       "constructiva. No asigna notas, solo criterios cualitativos.",
        "icono": "📋",
        "prompt_base": """Eres un evaluador formativo para {asignatura}...""",
        "preguntas_setup": [
            "¿El agente debe usar rúbricas numéricas o cualitativas?",
            "¿Debe comparar contra un estándar predefinido o solo dar feedback?",
        ],
    },
    "guia_proyectos": {
        "nombre": "Guía de Proyectos",
        "descripcion": "Acompaña al estudiante en el ciclo de vida de un proyecto de "
                       "ingeniería: definición, planificación, ejecución, presentación.",
        "icono": "🚀",
        "prompt_base": """Eres un guía de proyectos de ingeniería para {asignatura}...""",
        "preguntas_setup": [
            "¿El proyecto es individual o en equipo?",
            "¿Qué metodología de proyecto se usa? (Design Thinking, Scrum, cascada...)",
        ],
    },
    "asistente_lab": {
        "nombre": "Asistente de Laboratorio",
        "descripcion": "Guía la preparación, ejecución y análisis de prácticas de "
                       "laboratorio. Enfatiza seguridad y método científico.",
        "icono": "🔬",
        "prompt_base": """Eres un asistente de laboratorio para {asignatura}...""",
        "preguntas_setup": [
            "¿Qué normas de seguridad son obligatorias?",
            "¿El agente debe verificar cálculos o solo guiar el procedimiento?",
        ],
    },
    "personalizado": {
        "nombre": "Personalizado",
        "descripcion": "Agente completamente libre. El docente define todas las reglas.",
        "icono": "✨",
        "prompt_base": "",
        "preguntas_setup": [],
    },
}
```

### 2.5 Motor de Análisis de Contenido (`arquitecto.py`)

El corazón del Agent Builder: un LLM que actúa como "arquitecto de agentes".

```python
# arquitecto.py — funciones principales

def analizar_documentos(textos: list[dict]) -> dict:
    """
    Envía TODOS los textos extraídos al LLM para análisis profundo.
    Retorna:
    {
        "temas_principales": ["tema1", "tema2", ...],
        "mapa_conceptos": { "concepto": ["subconcepto1", ...], ... },
        "nivel_dificultad": "intermedio",
        "prerequisites": ["cálculo vectorial", "estática"],
        "enfoque": "teórico-práctico con énfasis en simulación",
        "resumen_ejecutivo": "Este curso cubre...",
        "terminos_clave": [...],
        "estructura_tematica": [
            {"unidad": 1, "titulo": "...", "conceptos": [...], "dificultad": "..."},
        ],
    }
    """

def generar_preguntas_refinamiento(analisis: dict, arquetipo: str) -> list[str]:
    """
    Genera preguntas contextuales basadas en el contenido real.
    Las preguntas son específicas: citan capítulos, conceptos, ejemplos
    que el LLM encontró en los documentos.
    """

def generar_prompt_final(
    arquetipo: str,
    respuestas_setup: dict,
    analisis_contenido: dict,
    respuestas_refinamiento: dict,
    preferencias: dict,
) -> str:
    """
    Ensambla el system prompt final combinando todas las capas.
    La estructura del prompt generado sigue el formato de prompt_sistema.txt
    que el Tutor Socrático ya sabe consumir.
    """
```

---

## 3. Plan de Implementación (Tareas)

### Fase 0: Setup del Proyecto

#### Task 0.1: Inicializar repo y estructura de archivos
**Files:** `agent-builder/` (worktree actual)

```bash
# Crear estructura de carpetas vacía
mkdir -p agentes_output .streamlit supabase
```

#### Task 0.2: Crear `config.py`
**Files:** `config.py`

Configuración centralizada: Supabase secrets, modelos disponibles, constantes del wizard.

#### Task 0.3: Crear `auth.py`
**Files:** `auth.py`

Simplificado del Tutor Socrático: solo login de docentes. Sin admin ni estudiante.

#### Task 0.4: Crear `requirements.txt`
**Files:** `requirements.txt`

Dependencias: streamlit, supabase, langchain, langchain-openai, langchain-community, python-docx, python-pptx, pymupdf, pyyaml.

#### Task 0.5: Crear `migration_agent_builder.sql`
**Files:** `supabase/migration_agent_builder.sql`

Schema de 3 tablas + RLS policies + trigger auto-profile.

#### Task 0.6: Crear `.streamlit/secrets.toml` template
**Files:** `.streamlit/secrets.toml`

Template con placeholders. Las reales van en Streamlit Cloud.

---

### Fase 1: Motor de Análisis

#### Task 1.1: Crear `procesador_docs.py` — Extracción de texto
**Files:** `procesador_docs.py`

Funciones para extraer texto de PDF (pymupdf), DOCX (python-docx), PPTX (python-pptx), TXT, MD.

#### Task 1.2: Crear `arquetipos.py` — Plantillas de agentes
**Files:** `arquetipos.py`

Los 5 arquetipos con sus prompts base y preguntas de setup.

#### Task 1.3: Crear `arquitecto.py` — LLM Architect
**Files:** `arquitecto.py`

Funciones core: `analizar_documentos()`, `generar_preguntas_refinamiento()`, `generar_prompt_final()`. Cada una llama al LLM con prompts especializados.

#### Task 1.4: Crear `database.py` — Operaciones Supabase
**Files:** `database.py`

CRUD para agentes, sesiones_creacion, documentos_agente. Upload a Supabase Storage.

---

### Fase 2: UI del Wizard

#### Task 2.1: Crear `app.py` — Entry point y navegación del wizard
**Files:** `app.py`

Login → wizard con barra de progreso. Manejo de estado `st.session_state.wizard_paso`.

#### Task 2.2: Crear `wizard_paso1_base.py` — Paso 1
**Files:** `wizard_paso1_base.py`

Selección de arquetipo, nombre, slug, materia, nivel. Preview de la plantilla base.

#### Task 2.3: Crear `wizard_paso2_setup.py` — Paso 2
**Files:** `wizard_paso2_setup.py`

Preguntas dinámicas según arquetipo. Respuestas en texto libre + opciones.

#### Task 2.4: Crear `wizard_paso3_contenido.py` — Paso 3
**Files:** `wizard_paso3_contenido.py`

Upload múltiple de archivos. Previsualización. Texto pegado manualmente. Barra de progreso de subida a Supabase Storage.

#### Task 2.5: Crear `wizard_paso4_digestion.py` — Paso 4
**Files:** `wizard_paso4_digestion.py`

Llama a `arquitecto.analizar_documentos()`. Muestra mapa de conceptos, resumen, nivel de dificultad. Pide confirmación al docente ("¿Es correcto este análisis?"). Permite correcciones.

#### Task 2.6: Crear `wizard_paso5_refinar.py` — Paso 5
**Files:** `wizard_paso5_refinar.py`

Muestra preguntas generadas por el LLM (basadas en contenido real). El docente responde las que quiera.

#### Task 2.7: Crear `wizard_paso6_generar.py` — Paso 6
**Files:** `wizard_paso6_generar.py`

Genera prompt final vía `arquitecto.generar_prompt_final()`. Vista previa editable. Botón "Finalizar" → guarda en `agentes_output/<slug>/` + Supabase. Opción de descarga ZIP.

---

### Fase 3: Integración y Pulido

#### Task 3.1: Agregar control de costos y telemetría
**Files:** `app.py`, `arquitecto.py`

Mostrar tokens usados y costo estimado en cada paso. Loggear sesiones_creacion.

#### Task 3.2: Agregar dashboard "Mis Agentes"
**Files:** `app.py` + nueva sección

Lista de agentes creados por el docente. Permite reabrir, editar, descargar, desplegar.

#### Task 3.3: Agregar exportación ZIP
**Files:** `wizard_paso6_generar.py`

Generar ZIP del agente para descarga directa (para deploy en Tutor Socrático).

#### Task 3.4: README y documentación
**Files:** `README.md`

Guía de uso para docentes: cómo crear un agente paso a paso.

---

### Fase 4: Compatibilidad con Tutor Socrático

#### Task 4.1: Verificar formato de output
Asegurar que `agentes_output/<slug>/prompt_sistema.txt` sea compatible con `prompts.py::cargar_prompt_curso()` del Tutor Socrático.

#### Task 4.2: Opción "Desplegar en PUJ-IA"
Botón que copia (o symlink) la carpeta del agente a `tutor-socratico/asignaturas/<slug>/`.

---

## 4. Decisiones de Diseño Pendientes

> **Profesor, necesito su input en estas decisiones antes de implementar:**

1. **Auth:** ¿Los docentes se autentican con el mismo Supabase del Tutor Socrático o es un proyecto Supabase separado? Si es el mismo, los docentes que ya existen en PUJ-IA pueden entrar directo al Agent Builder.

2. **Storage de documentos:** ¿Supabase Storage (gratis hasta 1GB) o solo procesamiento en memoria sin persistir los archivos? La ventaja de Storage es que el docente puede volver a editar el agente después sin re-subir todo.

3. **Modalidad de despliegue:** ¿El Agent Builder es una app Streamlit separada del Tutor Socrático (otro repo, otro deploy) o es parte de la misma app con otra página/ruta?

4. **Idioma de la UI:** ¿Español? (asumo que sí, dado el contexto)

5. **Nivel de complejidad MVP:** ¿Los 5 arquetipos desde el inicio, o empezamos solo con "Tutor Socrático" + "Personalizado" e iteramos?

---

## 5. Tiempo Estimado

| Fase | Tareas | Estimación |
|------|--------|-----------|
| Fase 0 — Setup | 0.1–0.6 | 1-2 horas |
| Fase 1 — Motor de Análisis | 1.1–1.4 | 2-3 horas |
| Fase 2 — UI Wizard | 2.1–2.7 | 3-4 horas |
| Fase 3 — Integración | 3.1–3.4 | 1-2 horas |
| Fase 4 — Compatibilidad | 4.1–4.2 | 30 min |
| **Total** | | **8-12 horas** |

---

## 6. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Documentos muy grandes (>100K tokens) no caben en ventana de contexto del LLM | Chunking + resúmenes incrementales, o usar modelos de 1M contexto (Gemini) |
| El LLM "alucina" contenido que no está en los documentos | Mostrar siempre el análisis al docente para verificación humana |
| Costos de API al procesar documentos extensos | Usar Gemini Flash (barato, $0.15/M tokens) para análisis; DeepSeek para generación |
| DOCX/PPTX con imágenes y ecuaciones no se extraen bien | Advertir al docente; sugerir PDFs o Markdown para ecuaciones |
