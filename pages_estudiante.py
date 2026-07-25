"""pages_estudiante.py — Dashboard del estudiante: chat + historial + bandeja."""
import streamlit as st
import time
import uuid
import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from auth import usuario_actual, get_supabase
from config import MODELOS_DISPONIBLES, MODELO_POR_DEFECTO
from prompts import construir_prompt_completo
from rag_engine import MotorRAG, GestorAsignaturas
from telemetry import registrar_log, ControlAbuso


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

    # Pestañas: Chat | Historial | Bandeja del docente
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📚 Historial", "📬 Bandeja"])

    with tab1:
        _tab_chat(usuario)

    with tab2:
        _tab_historial(usuario)

    with tab3:
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
    modelo_actual = _get_modelo_activo()
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
        _crear_conversacion(usuario, asignatura)

    # Inicializar MotorRAG
    if "motor_rag" not in st.session_state or st.session_state.get("_rag_asignatura") != asignatura:
        with st.spinner("📚 Cargando documentos del curso..."):
            motor = MotorRAG(asignatura)
            motor.indexar()
            st.session_state.motor_rag = motor
            st.session_state._rag_asignatura = asignatura
            if motor.esta_listo():
                st.toast(f"✅ {len(motor.documents)} documentos cargados")

    motor: MotorRAG = st.session_state.motor_rag

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
        # --- control de abuso (protegido) ---
        try:
            control.registrar()
        except Exception:
            pass  # no bloquear al estudiante por file I/O

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                _responder(prompt, motor, asignatura, usuario, control)
            except Exception as e:
                st.error(f"❌ Error: {e}")
                import traceback
                with st.expander("🔍 Detalles técnicos"):
                    st.code(traceback.format_exc())


# ============================================================
# Responder (sin crash)
# ============================================================
def _responder(prompt, motor, asignatura, usuario, control):
    modelo_nombre = _get_modelo_activo()
    info_modelo = MODELOS_DISPONIBLES.get(modelo_nombre, MODELOS_DISPONIBLES[MODELO_POR_DEFECTO])

    # Configurar LLM
    if info_modelo["provider"] == "openrouter":
        api_key = st.secrets["OPENROUTER_API_KEY"]
        base_url = "https://openrouter.ai/api/v1"
        default_headers = {"HTTP-Referer": "https://puj-ia.streamlit.app", "X-Title": "PUJ-IA"}
    else:
        api_key = st.secrets["DEEPSEEK_API_KEY"]
        base_url = "https://api.deepseek.com"
        default_headers = None

    llm = ChatOpenAI(
        model=info_modelo["model_id"],
        api_key=api_key,
        base_url=base_url,
        temperature=0.7,
        max_tokens=2048,
        default_headers=default_headers,
    )

    # RAG (protegido — ChromaDB puede fallar en Cloud)
    fragmentos = []
    try:
        if motor.esta_listo():
            fragmentos = motor.recuperar(prompt, k=4)
    except Exception as e:
        st.warning(f"⚠️ RAG no disponible: {e}")

    # System prompt (protegido)
    try:
        system_prompt = construir_prompt_completo(asignatura)
    except Exception:
        system_prompt = "Eres un tutor socrático experto. Responde con preguntas que guíen al estudiante hacia la comprensión profunda."

    if fragmentos:
        system_prompt += f"\n\n## Documentos del curso:\n\n" + "\n\n---\n\n".join(fragmentos)

    # Historial de mensajes
    mensajes = [SystemMessage(content=system_prompt)]
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            mensajes.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            mensajes.append(AIMessage(content=msg["content"]))

    # Generar respuesta
    status_widget = st.status("🧠 Razonando...", expanded=True)
    if fragmentos:
        status_widget.write(f"📖 {len(fragmentos)} fragmentos del curso")
    status_widget.write("💭 Generando respuesta...")
    t0 = time.time()

    respuesta = llm.invoke(mensajes)
    contenido = respuesta.content if hasattr(respuesta, "content") else str(respuesta)
    elapsed_ms = int((time.time() - t0) * 1000)

    status_widget.update(label=f"✅ Listo ({elapsed_ms}ms)", state="complete")
    st.markdown(contenido)
    st.session_state.messages.append({"role": "assistant", "content": contenido})

    # Tokens y costo
    t_in = respuesta.usage_metadata.get("input_tokens", 0) if hasattr(respuesta, "usage_metadata") else 0
    t_out = respuesta.usage_metadata.get("output_tokens", 0) if hasattr(respuesta, "usage_metadata") else 0
    costo = (t_in * info_modelo["input_cost"] + t_out * info_modelo["output_cost"]) / 1000
    st.session_state.total_tokens += t_in + t_out
    st.session_state.costo_total += costo
    st.caption(f"Tokens: {t_in}→{t_out} | Costo: ${costo:.4f} | Modelo: {modelo_nombre}")

    # Guardar en BD (protegido)
    try:
        _guardar_mensaje_db(usuario, contenido, t_in, t_out, costo, elapsed_ms, modelo_nombre)
    except Exception:
        pass
    try:
        registrar_log(
            session_id=st.session_state.session_id,
            usuario_id=usuario.id,
            asignatura=asignatura,
            modelo=modelo_nombre,
            mensaje_usuario=prompt,
            respuesta_agente=contenido,
            tokens_input=t_in,
            tokens_output=t_out,
            costo_usd=costo,
            tiempo_respuesta_ms=elapsed_ms,
        )
    except Exception:
        pass


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
            if st.button("🗑️ Eliminar conversación", key=f"del_conv_{conv['id']}", type="secondary"):
                _confirmar_y_borrar(
                    f"¿Eliminar conversación '{conv['titulo']}'?",
                    lambda cid=conv["id"]: _borrar_conversacion(cid),
                    f"really_del_conv_{conv['id']}",
                )


# ============================================================
# Tab: Bandeja del docente
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
            if st.button("🗑️ Eliminar mensaje", key=f"del_bandeja_{msg['id']}", type="secondary"):
                _confirmar_y_borrar(
                    f"¿Eliminar mensaje '{msg['asunto']}'?",
                    lambda mid=msg["id"]: _borrar_mensaje_docente(mid),
                    f"really_del_bandeja_{msg['id']}",
                )


# ============================================================
# Helpers
# ============================================================
def _get_modelo_activo() -> str:
    try:
        supabase = get_supabase()
        resp = supabase.table("config_sistema").select("valor").eq("clave", "modelo_llm").single().execute()
        if resp.data:
            return resp.data["valor"]
    except Exception:
        pass
    return MODELO_POR_DEFECTO


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


def _crear_conversacion(usuario, asignatura: str):
    try:
        supabase = get_supabase()
        grupo = st.session_state.get("grupo_actual")
        resp = supabase.table("conversaciones").insert({
            "estudiante_id": usuario.id,
            "grupo_id": grupo["id"] if grupo else None,
            "asignatura": asignatura,
            "titulo": f"Chat del {datetime.date.today().isoformat()}",
            "model_usado": _get_modelo_activo(),
        }).execute()
        if resp.data:
            st.session_state.conversacion_activa = resp.data[0]["id"]
    except Exception:
        st.session_state.conversacion_activa = f"local-{uuid.uuid4().hex[:8]}"


def _guardar_mensaje_db(usuario, contenido: str, t_in: int, t_out: int,
                        costo: float, t_ms: int, modelo: str):
    try:
        supabase = get_supabase()
        conv_id = st.session_state.get("conversacion_activa")
        if conv_id and not conv_id.startswith("local-"):
            # Guardar último mensaje del usuario
            user_msg = st.session_state.messages[-2]["content"] if len(st.session_state.messages) >= 2 else ""
            supabase.table("mensajes").insert({
                "conversacion_id": conv_id,
                "rol": "user",
                "contenido": user_msg,
                "tokens_input": t_in,
                "tokens_output": 0,
                "costo_usd": 0,
                "tiempo_respuesta_ms": 0,
            }).execute()
            # Guardar respuesta del asistente
            supabase.table("mensajes").insert({
                "conversacion_id": conv_id,
                "rol": "assistant",
                "contenido": contenido,
                "tokens_input": 0,
                "tokens_output": t_out,
                "costo_usd": costo,
                "tiempo_respuesta_ms": t_ms,
            }).execute()
    except Exception:
        pass


# ============================================================
# Helpers de borrado
# ============================================================
def _confirmar_y_borrar(mensaje: str, accion, confirm_key: str):
    """Confirmación en 2 pasos antes de borrar."""
    if confirm_key not in st.session_state:
        st.session_state[confirm_key] = False
    if not st.session_state[confirm_key]:
        st.warning(mensaje)
        if st.button("⚠️ Sí, eliminar definitivamente", key=f"confirm_{confirm_key}", type="secondary"):
            st.session_state[confirm_key] = True
            st.rerun()
    else:
        try:
            accion()
            st.success("Eliminado correctamente.")
            del st.session_state[confirm_key]
            st.rerun()
        except Exception as e:
            st.error(f"Error al eliminar: {e}")
            del st.session_state[confirm_key]


def _borrar_conversacion(conv_id: str):
    supabase = get_supabase()
    supabase.table("mensajes").delete().eq("conversacion_id", conv_id).execute()
    supabase.table("conversaciones").delete().eq("id", conv_id).execute()


def _borrar_mensaje_docente(msg_id: str):
    supabase = get_supabase()
    supabase.table("mensajes_docente").delete().eq("id", msg_id).execute()
