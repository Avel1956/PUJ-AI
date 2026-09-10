"""telemetry.py — Logging en Supabase + control de uso por estudiante."""
import datetime
import json
import os

from config import MAX_PREGUNTAS_POR_DIA

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, ".logs")

# Colombia no aplica horario de verano: es UTC-5 todo el año.
ZONA_COLOMBIA = datetime.timezone(datetime.timedelta(hours=-5))


# ============================================================
# Configuración editable por el admin (tabla config_sistema)
# ============================================================
def get_config_valor(clave: str, por_defecto: str = "") -> str:
    """Lee un valor de `config_sistema`.

    Antes estos valores se podían editar en el panel de administración pero el
    código NUNCA los leía: usaba constantes de config.py, así que los cambios
    del admin no tenían ningún efecto.
    """
    try:
        from auth import get_supabase
        resp = (
            get_supabase().table("config_sistema")
            .select("valor")
            .eq("clave", clave)
            .single()
            .execute()
        )
        if resp.data and resp.data.get("valor") is not None:
            return str(resp.data["valor"]).strip()
    except Exception:
        pass
    return por_defecto


def limite_preguntas_dia() -> int:
    """Límite diario de preguntas por estudiante."""
    valor = get_config_valor("max_preguntas_dia", str(MAX_PREGUNTAS_POR_DIA))
    return int(valor) if valor.isdigit() else MAX_PREGUNTAS_POR_DIA


def costo_maximo_sesion_usd() -> float:
    """Costo máximo estimado por sesión, en USD."""
    try:
        return float(get_config_valor("costo_maximo_sesion_usd", "0.10"))
    except ValueError:
        return 0.10


# ============================================================
# Control de uso por estudiante
# ============================================================
class ControlAbuso:
    """Limita las preguntas por día y por ESTUDIANTE, contando en la base.

    La implementación anterior contaba por `session_id` de Streamlit, que se
    regenera al recargar la página: bastaba un F5 para reiniciar el contador,
    así que el límite diario no se cumplía nunca y las métricas de uso no eran
    fiables. Ahora la fuente de verdad es `logs_sesiones`, que ya registra una
    fila por cada respuesta del tutor.
    """

    def __init__(self, usuario_id: str, max_dia: int | None = None):
        self.usuario_id = usuario_id
        self.max_dia = max_dia if max_dia is not None else limite_preguntas_dia()

    @staticmethod
    def _rango_hoy() -> tuple[str, str]:
        """Inicio y fin del día de HOY en hora Colombia, expresados en UTC.

        `logs_sesiones.timestamp` está en UTC. Calcular el corte del día en
        Bogotá evita que las preguntas de la tarde-noche (después de las 19:00)
        se cuenten como del día siguiente.
        """
        ahora = datetime.datetime.now(ZONA_COLOMBIA)
        inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = inicio + datetime.timedelta(days=1)
        return (
            inicio.astimezone(datetime.timezone.utc).isoformat(),
            fin.astimezone(datetime.timezone.utc).isoformat(),
        )

    def contar(self) -> int:
        """Preguntas registradas hoy por este estudiante."""
        if not self.usuario_id:
            return 0
        try:
            from auth import get_supabase
            inicio, fin = self._rango_hoy()
            resp = (
                get_supabase().table("logs_sesiones")
                .select("id", count="exact")
                .eq("usuario_id", self.usuario_id)
                .gte("timestamp", inicio)
                .lt("timestamp", fin)
                .execute()
            )
            return resp.count if hasattr(resp, "count") else 0
        except Exception:
            return 0

    def permitido(self) -> bool:
        return self.contar() < self.max_dia

    def restantes(self) -> int:
        return max(0, self.max_dia - self.contar())


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
    """Registra una interacción en `logs_sesiones` de Supabase."""
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

    # Backup local (efímero en Streamlit Cloud: solo es una red de seguridad)
    _backup_local(session_id, usuario_id, asignatura, modelo,
                  mensaje_usuario, respuesta_agente,
                  tokens_input, tokens_output, costo_usd, tiempo_respuesta_ms)


def _backup_local(session_id, usuario_id, asignatura, modelo,
                  msg_user, msg_assistant, t_in, t_out, costo, t_ms):
    ruta = os.path.join(LOG_DIR, f"backup_{session_id}.jsonl")
    registro = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Sistema de archivos de solo lectura: no es crítico
