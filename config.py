"""config.py — Configuración centralizada del Tutor Socrático Universal."""
from dataclasses import dataclass, field
import streamlit as st

# ============================================================
# Secretos (desde st.secrets en Streamlit Cloud / secrets.toml local)
# ============================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", "")

# ============================================================
# Modelos disponibles
# ============================================================
MODELOS_DISPONIBLES = {
    "gemini-2.0-flash": {
        "provider": "openrouter",
        "model_id": "google/gemini-2.0-flash-001",
        "input_cost": 0.00010,
        "output_cost": 0.00040,
        "descripcion": "Google Gemini Flash — rápido, barato, buen RAG",
    },
    "gemini-2.5-flash": {
        "provider": "openrouter",
        "model_id": "google/gemini-2.5-flash",
        "input_cost": 0.00015,
        "output_cost": 0.00060,
        "descripcion": "Google Gemini 2.5 Flash — mejor razonamiento, igual rápido",
    },
    "claude-3-haiku": {
        "provider": "openrouter",
        "model_id": "anthropic/claude-3-haiku",
        "input_cost": 0.00025,
        "output_cost": 0.00125,
        "descripcion": "Anthropic Claude Haiku — conciso, bueno en tutorías",
    },
    "claude-sonnet-4": {
        "provider": "openrouter",
        "model_id": "anthropic/claude-sonnet-4",
        "input_cost": 0.003,
        "output_cost": 0.015,
        "descripcion": "Claude Sonnet 4 — alta calidad, mayor costo",
    },
    "deepseek-chat": {
        "provider": "deepseek",
        "model_id": "deepseek-chat",
        "input_cost": 0.00014,
        "output_cost": 0.00028,
        "descripcion": "DeepSeek V3 — alternativa directa, buen rendimiento/costo",
    },
}

MODELO_POR_DEFECTO = "deepseek-chat"
MAX_PREGUNTAS_POR_DIA = 50
COSTO_MAXIMO_SESION = 0.10  # USD

# ============================================================
# Data classes
# ============================================================
@dataclass
class PerfilUsuario:
    id: str
    email: str
    nombre: str
    rol: str  # 'estudiante', 'docente', 'admin'
    auth_token: str = ""

    @property
    def es_estudiante(self) -> bool:
        return self.rol == "estudiante"

    @property
    def es_docente(self) -> bool:
        return self.rol == "docente"

    @property
    def es_admin(self) -> bool:
        return self.rol == "admin"


@dataclass
class SesionChat:
    id: str
    titulo: str
    asignatura: str
    grupo_id: str | None = None
    activa: bool = True


@dataclass
class InfoGrupo:
    id: str
    nombre: str
    descripcion: str
    asignatura: str
    miembros: list[dict] = field(default_factory=list)
