"""telemetry.py — Logging en Supabase + control de abuso por estudiante."""
import json
import os
import uuid
import time
import datetime
import streamlit as st
from config import MODELO_POR_DEFECTO, MAX_PREGUNTAS_POR_DIA

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, ".logs")


# ============================================================
# Control de abuso (rate limiting local)
# ============================================================
class ControlAbuso:
    """Limita preguntas por día por sesión (fallback local)."""

    def __init__(self, session_id: str, max_dia: int = MAX_PREGUNTAS_POR_DIA):
        self.session_id = session_id
        self.max_dia = max_dia
        self.ruta = os.path.join(LOG_DIR, f"abuso_{session_id}.json")
        self._cargar()

    def _cargar(self):
        if os.path.exists(self.ruta):
            with open(self.ruta, "r") as f:
                data = json.load(f)
        else:
            data = {}
        self.data = data

    def _guardar(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(self.ruta, "w") as f:
            json.dump(self.data, f)

    def contar(self) -> int:
        hoy = datetime.date.today().isoformat()
        return self.data.get(hoy, 0)

    def permitido(self) -> bool:
        return self.contar() < self.max_dia

    def registrar(self):
        hoy = datetime.date.today().isoformat()
        self.data[hoy] = self.data.get(hoy, 0) + 1
        self._guardar()


# ============================================================
# Logging en Supabase
# ============================================================
def registrar_log(
    session_id: str,
    usuario_id: str,
    asignatura: str,
    modelo: str,
    mensaje_usuario: str,
    respuesta_agente: str,
    tokens_input: int = 0,
    tokens_output: int = 0,
    costo_usd: float = 0.0,
    tiempo_respuesta_ms: int = 0,
):
    """Registra una interacción en logs_sesiones de Supabase."""
    try:
        from auth import get_supabase
        supabase = get_supabase()
        supabase.table("logs_sesiones").insert({
            "session_id": session_id,
            "usuario_id": usuario_id,
            "asignatura": asignatura,
            "modelo": modelo,
            "mensaje_usuario": mensaje_usuario,
            "respuesta_agente": respuesta_agente,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "costo_usd": costo_usd,
            "tiempo_respuesta_ms": tiempo_respuesta_ms,
        }).execute()
    except Exception:
        pass  # Si Supabase falla, no interrumpir al estudiante

    # Backup local siempre
    _backup_local(session_id, usuario_id, asignatura, modelo,
                  mensaje_usuario, respuesta_agente,
                  tokens_input, tokens_output, costo_usd, tiempo_respuesta_ms)


def _backup_local(session_id, usuario_id, asignatura, modelo,
                  msg_user, msg_assistant, t_in, t_out, costo, t_ms):
    os.makedirs(LOG_DIR, exist_ok=True)
    ruta = os.path.join(LOG_DIR, f"backup_{session_id}.jsonl")
    registro = {
        "timestamp": datetime.datetime.now().isoformat(),
        "session_id": session_id,
        "usuario_id": usuario_id,
        "asignatura": asignatura,
        "modelo": modelo,
        "mensaje_usuario": msg_user,
        "respuesta_agente": msg_assistant,
        "tokens_input": t_in,
        "tokens_output": t_out,
        "costo_usd": costo,
        "tiempo_respuesta_ms": t_ms,
    }
    with open(ruta, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
