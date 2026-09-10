"""config.py — Configuración centralizada de PUJ-IA."""
from dataclasses import dataclass, field
from datetime import datetime, timezone

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
#
# Tarifas en USD por 1K tokens. DeepSeek factura precio DOBLE en horas peak;
# se guarda la tarifa peak en input_cost/output_cost y la mitad en
# *_cost_offpeak. Ver tarifa_por_1k().
#
# Peak: 01:00-04:00 y 06:00-10:00 UTC, lunes a viernes.
# En hora Colombia (UTC-5) eso es 20:00-23:00 y 01:00-05:00, así que las
# clases diurnas siempre caen en off-peak (mitad de precio).
#
# Precios verificados en https://api-docs.deepseek.com/quick_start/pricing
# el 2026-09-10, día del lanzamiento de DeepSeek V4.1 Flash.
# ============================================================
MODELOS_DISPONIBLES = {
    "deepseek-flash": {
        "provider": "deepseek",
        "model_id": "deepseek-flash",
        "input_cost": 0.00030,
        "output_cost": 0.00120,
        "input_cost_offpeak": 0.00015,
        "output_cost_offpeak": 0.00060,
        "descripcion": "DeepSeek V4.1 Flash — recomendado (1M contexto, multimodal)",
    },
    "deepseek-v4-pro": {
        "provider": "deepseek",
        "model_id": "deepseek-v4-pro",
        "input_cost": 0.00132,
        "output_cost": 0.00396,
        "input_cost_offpeak": 0.00066,
        "output_cost_offpeak": 0.00198,
        "descripcion": "DeepSeek V4 Pro — EN RETIRO: desde 2026-09-14 se enruta a V4.1 Flash",
    },
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
}

MODELO_POR_DEFECTO = "deepseek-flash"

# Modo "thinking" de DeepSeek (V4 y V4.1).
# Viene ACTIVADO por defecto con esfuerzo alto. En ese modo:
#   - la temperatura se ignora silenciosamente,
#   - los tokens de razonamiento se facturan como tokens de salida,
#   - la latencia sube de forma notable.
# Para un tutor socrático se desactiva: importa la latencia percibida por el
# estudiante y el costo por curso. Suba a True si quiere priorizar el
# razonamiento sobre la velocidad.
DEEPSEEK_THINKING = False

# Máximo de tokens de salida por respuesta del tutor.
MAX_TOKENS_RESPUESTA = 2048

MAX_PREGUNTAS_POR_DIA = 50
COSTO_MAXIMO_SESION = 0.10  # USD


# ============================================================
# Tarifas
# ============================================================
def tarifa_por_1k(info_modelo: dict, ahora: datetime | None = None) -> tuple[float, float]:
    """Devuelve (costo_input, costo_output) por 1K tokens para el modelo.

    Aplica la tarifa peak/off-peak de DeepSeek cuando el modelo la define.
    Los modelos sin tarifa off-peak declarada usan siempre su tarifa base.
    """
    if "input_cost_offpeak" not in info_modelo:
        return info_modelo["input_cost"], info_modelo["output_cost"]

    ahora = ahora or datetime.now(timezone.utc)
    es_peak = ahora.weekday() < 5 and any(
        inicio <= ahora.hour < fin for inicio, fin in ((1, 4), (6, 10))
    )
    if es_peak:
        return info_modelo["input_cost"], info_modelo["output_cost"]
    return info_modelo["input_cost_offpeak"], info_modelo["output_cost_offpeak"]

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
