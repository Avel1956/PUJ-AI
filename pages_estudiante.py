"""pages_estudiante.py — Dashboard del estudiante: chat + historial + bandeja."""
import streamlit as st
import uuid
import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from auth import usuario_actual, get_supabase
from config import MODELOS_DISPONIBLES, MODELO_POR_DEFECTO
from prompts import construir_prompt_completo
from rag_engine import MotorRAG, GestorAsignaturas
from telemetry import ControlAbuso
from chat_core import (
    get_modelo_activo,
    inicializar_motor_rag,
    responder,
    crear_conversacion,
)


def render_dashboard_estudiante():
    """Punto de entrada del dashboard de estudiante."""
    try:
        _render_dashboard_estudiante()
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        with st.expander("🔍 Detalles técnicos"):
            st.code(traceback.format_exc())


def _render_dashboard_estudiante():
    usuario = usuario_actual()
    st.title("🎓 PUJ-IA")
    st.caption(f"Bienvenido, {usuario.nombre} — Estudiante")

    # Sidebar
    with st.sidebar:
        _sidebar_estudiante(usuario)

    # Pestañas: Chat | Historial | Bandeja
    # Se usa un radio horizontal (en lugar de st.tabs) para poder saltar
    # programáticamente a la pestaña Chat al reanudar una conversación.
    opciones_tabs = ["💬 Chat", "📚 Historial", "📬 Bandeja"]
    if "tab_estudiante_activa" not in st.session_state:
        st.session_state.tab_estudiante_activa = "💬 Chat"
    tab_activa = st.radio(
        "",
        opciones_tabs,
        horizontal=True,
        key="tab_estudiante_activa",
        label_visibility="collapsed",
    )

    if tab_activa == "💬 Chat":
        _tab_chat(usuario)
    elif tab_activa == "📚 Historial":
        _tab_historial(usuario)
    else:
        _tab_bandeja(usuario)


# ============================================================
# Sidebar
# ============================================================
def _sidebar_estudiante(usuario):
    st.subheader("⚙️ Configuración")

    # Selección de asignatura
    asignaturas = GestorAsignaturas.listar()
    opciones = {GestorAsignaturas.nombre_legible(a): a for a in asignaturas}
    if not opciones:
        st.warning("No hay cursos disponibles aún.")
        return

    sel = st.selectbox(
        "📖 Asignatura",
        options=list(opciones.keys()),
        key="sel_asignatura_estudiante",
    )
    asignatura_slug = opciones[sel]
    st.session_state.asignatura_actual = asignatura_slug

    # Modelo (solo informativo — lo configura el admin)
    modelo_actual = get_modelo_activo()
    st.caption(f"🧠 Modelo: {modelo_actual}")

    # Grupo del estudiante
    grupos = _grupos_del_estudiante(usuario.id, asignatura_slug)
    if grupos:
        nombres_grupos = {g["nombre"]: g for g in grupos}
        sel_grupo = st.selectbox(
            "👥 Grupo de trabajo",
            options=["(Individual)"] + list(nombres_grupos.keys()),
            key="sel_grupo_estudiante",
        )
        st.session_state.grupo_actual = (
            nombres_grupos[sel_grupo] if sel_grupo != "(Individual)" else None
        )
    else:
        st.session_state.grupo_actual = None
        st.caption("Sin grupo asignado")

    # Control de abuso
    ctrl = ControlAbuso(st.session_state.get("session_id", "anon"))
    usadas = ctrl.contar()
    st.caption(f"📊 Preguntas hoy: {usadas}/{ctrl.max_dia}")


# ============================================================
# Tab: Chat
# ============================================================
def _tab_chat(usuario):
    asignatura = st.session_state.get("asignatura_actual", "")
    if not asignatura:
        st.info("Seleccione una asignatura en el panel lateral.")
        return

    # ── Aviso de grabación + reglas de juego ──
    with st.expander("📋 Aviso importante — Leer antes de usar el chat", expanded=False):
        st.markdown("""
### 🔒 Sus conversaciones son grabadas

Todas las conversaciones que mantenga con el tutor socrático quedan
registradas en la plataforma. Sus profesores pueden revisarlas con
fines exclusivamente pedagógicos:

- Evaluar su progreso y nivel de comprensión
- Identificar dificultades comunes en el curso
- Mejorar los materiales y las estrategias de enseñanza

### 📜 Reglas de juego

1. **Uso académico exclusivo** — Esta herramienta es para estudiar.
   No se permiten conversaciones ajenas a la asignatura.

2. **El tutor no da respuestas** — El agente usa el método socrático:
   le hará preguntas para guiarlo, no le dará la solución directa.

3. **Sea respetuoso** — Mantenga un tono cordial y académico.

4. **No comparta datos personales sensibles** — Aunque las
   conversaciones son privadas dentro de la plataforma, evite
   compartir información personal innecesaria.

5. **Revise sus conversaciones** — Use la pestaña **Historial**
   para repasar lo discutido. Es una herramienta de estudio, no un
   sustituto del pensamiento crítico.

6. **Reporte errores** — Si el tutor responde algo incorrecto o
   fuera de lugar, comuníqueselo a su profesor.
""")
    # ── Fin aviso ──

    # Inicializar estado
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:12]
    if "total_tokens" not in st.session_state:
        st.session_state.total_tokens = 0
    if "costo_total" not in st.session_state:
        st.session_state.costo_total = 0.0

    # Inicializar conversación en DB
    if "conversacion_activa" not in st.session_state:
        st.session_state.conversacion_activa = crear_conversacion(usuario, asignatura)

    # Botón para empezar una conversación nueva
    if st.button("➕ Nueva conversación", key="btn_nueva_conv_estudiante"):
        st.session_state.messages = []
        st.session_state.total_tokens = 0
        st.session_state.costo_total = 0.0
        st.session_state.conversacion_activa = crear_conversacion(usuario, asignatura)
        st.rerun()

    # Inicializar MotorRAG
    motor = inicializar_motor_rag(asignatura)

    # Mostrar historial de chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input del chat
    control = ControlAbuso(st.session_state.session_id)
    if not control.permitido():
        st.warning("⚠️ Has alcanzado el límite de preguntas por hoy. Intenta de nuevo mañana.")
        return

    if prompt := st.chat_input("Escribe tu pregunta...", key="chat_input_estudiante"):
        # Control de abuso (protegido)
        try:
            control.registrar()
        except Exception:
            pass

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                responder(prompt, motor, asignatura, usuario, control)
            except Exception as e:
                st.error(f"❌ Error: {e}")
                import traceback
                with st.expander("🔍 Detalles técnicos"):
                    st.code(traceback.format_exc())


# ============================================================
# Tab: Historial
# ============================================================
def _tab_historial(usuario):
    st.subheader("📚 Mis conversaciones")
    supabase = get_supabase()

    resp = (
        supabase.table("conversaciones")
        .select("*")
        .eq("estudiante_id", usuario.id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    if not resp.data:
        st.info("Aún no tienes conversaciones registradas.")
        return

    for conv in resp.data:
        fecha = conv["created_at"][:19].replace("T", " ") if conv["created_at"] else ""
        estado = "🟢" if conv["activa"] else "⚫"
        with st.expander(f"{estado} {conv['titulo']} — {fecha} ({conv['asignatura']})"):
            if st.button("💬 Reanudar esta conversación", key=f"reanudar_{conv['id']}", type="primary"):
                _reanudar_conversacion(conv["id"], conv.get("asignatura", ""))
                st.rerun()
            mensajes_resp = (
                supabase.table("mensajes")
                .select("rol,contenido,created_at")
                .eq("conversacion_id", conv["id"])
                .order("created_at")
                .limit(20)
                .execute()
            )
            if mensajes_resp.data:
                for m in mensajes_resp.data:
                    rol = "🧑" if m["rol"] == "user" else "🤖"
                    st.caption(f"{rol} {m['created_at'][:19]}")
                    st.markdown(m["contenido"][:500])
                    st.divider()
            # NOTA: Los estudiantes no pueden borrar conversaciones.
            # El docente y el admin gestionan los borrados desde sus paneles.


# ============================================================
# Tab: Bandeja de mensajes del docente
# ============================================================
def _tab_bandeja(usuario):
    st.subheader("📬 Mensajes del docente")
    supabase = get_supabase()

    # Obtener grupos del estudiante
    grupos_resp = (
        supabase.table("grupos_estudiantes")
        .select("grupo_id")
        .eq("estudiante_id", usuario.id)
        .execute()
    )
    grupo_ids = [g["grupo_id"] for g in (grupos_resp.data or [])]

    # Construir filtro
    if grupo_ids:
        ids_str = ",".join(grupo_ids)
        filtro = f"para_estudiante_id.eq.{usuario.id},para_grupo_id.in.({ids_str})"
    else:
        filtro = f"para_estudiante_id.eq.{usuario.id}"

    resp = (
        supabase.table("mensajes_docente")
        .select("*")
        .or_(filtro)
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )

    if not resp.data:
        st.info("No tienes mensajes del docente.")
        return

    for msg in resp.data:
        no_leido = "🔵" if not msg["leido"] else "⚪"
        with st.expander(f"{no_leido} {msg['asunto']} — {msg['created_at'][:19]}"):
            st.markdown(msg["contenido"])
            # NOTA: Los estudiantes no pueden borrar mensajes del docente.
            # El docente gestiona los mensajes desde su panel.


# ============================================================
# Helpers
# ============================================================
def _reanudar_conversacion(conv_id: str, asignatura: str):
    """Carga una conversación previa en el chat y salta a la pestaña Chat."""
    supabase = get_supabase()
    msgs_resp = (
        supabase.table("mensajes")
        .select("rol, contenido")
        .eq("conversacion_id", conv_id)
        .order("created_at")
        .execute()
    )
    st.session_state.messages = [
        {"role": m["rol"], "content": m["contenido"]}
        for m in (msgs_resp.data or [])
    ]
    st.session_state.conversacion_activa = conv_id

    # Sincronizar la asignatura del panel lateral (solo si el curso está disponible)
    if asignatura:
        opciones = {GestorAsignaturas.nombre_legible(a): a for a in GestorAsignaturas.listar()}
        for label, slug in opciones.items():
            if slug == asignatura:
                st.session_state.sel_asignatura_estudiante = label
                st.session_state.asignatura_actual = asignatura
                break

    st.session_state.tab_estudiante_activa = "💬 Chat"


def _grupos_del_estudiante(estudiante_id: str, asignatura: str) -> list[dict]:
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("grupos_estudiantes")
            .select("grupo_id, grupos!grupo_id(id, nombre, asignatura)")
            .eq("estudiante_id", estudiante_id)
            .execute()
        )
        grupos = []
        for row in (resp.data or []):
            g = row.get("grupos", {})
            if isinstance(g, dict) and g.get("asignatura") == asignatura:
                grupos.append(g)
        return grupos
    except Exception:
        return []
