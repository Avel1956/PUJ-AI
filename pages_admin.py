"""pages_admin.py — Panel de administración: docentes, modelos, logs, sistema."""
import streamlit as st
from auth import usuario_actual, get_supabase, get_supabase_admin, crear_usuario_docente
from config import MODELOS_DISPONIBLES, MODELO_POR_DEFECTO


def render_dashboard_admin():
    """Punto de entrada del dashboard de administrador."""
    usuario = usuario_actual()
    st.title(f"⚙️ Panel de Administración")
    st.caption(f"{usuario.nombre} — Administrador del Sistema")

    tab1, tab2, tab3, tab4 = st.tabs([
        "👨‍🏫 Docentes", "🧠 Modelos", "📊 Estadísticas", "🛡️ Sistema"
    ])

    with tab1:
        _tab_docentes()
    with tab2:
        _tab_modelos()
    with tab3:
        _tab_estadisticas()
    with tab4:
        _tab_sistema()


# ============================================================
# Tab: Gestión de Docentes
# ============================================================
def _tab_docentes():
    st.subheader("👨‍🏫 Gestión de Docentes")

    # --- Crear docente ---
    with st.expander("➕ Registrar nuevo docente", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre = st.text_input("Nombre completo", key="admin_nuevo_docente_nombre")
        with col2:
            email = st.text_input("Email institucional", key="admin_nuevo_docente_email")
        with col3:
            password = st.text_input("Contraseña inicial", type="password", key="admin_nuevo_docente_pass")

        if st.button("Crear docente", type="primary"):
            if nombre and email and password:
                ok, msg = crear_usuario_docente(email, password, nombre)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Complete todos los campos.")

    # --- Lista de docentes ---
    st.subheader("📋 Docentes registrados")
    supabase = get_supabase()
    resp = (
        supabase.table("profiles")
        .select("id, email, nombre, created_at")
        .eq("rol", "docente")
        .order("nombre")
        .execute()
    )

    if not resp.data:
        st.info("No hay docentes registrados aún.")
        return

    rows = []
    for p in resp.data:
        # Contar estudiantes creados por este docente (grupos como proxy)
        grupos = (
            supabase.table("grupos")
            .select("id", count="exact")
            .eq("creado_por", p["id"])
            .execute()
        )
        n_grupos = grupos.count if hasattr(grupos, "count") else "?"

        rows.append({
            "Nombre": p["nombre"],
            "Email": p["email"],
            "Grupos": n_grupos,
            "Registrado": p["created_at"][:10] if p["created_at"] else "",
        })

    st.dataframe(rows, hide_index=True, use_container_width=True)


# ============================================================
# Tab: Configuración de Modelos
# ============================================================
def _tab_modelos():
    st.subheader("🧠 Configuración de Modelos LLM")
    supabase = get_supabase()

    # Modelo actual
    modelo_actual = _get_modelo_actual_db()
    st.info(f"🔧 Modelo activo: **{modelo_actual}**")

    # Selector de modelo
    opciones = {
        f"{v['descripcion']} ({k})": k
        for k, v in MODELOS_DISPONIBLES.items()
    }

    # Encontrar la clave actual en las opciones
    actual_label = next(
        (label for label, key in opciones.items() if key == modelo_actual),
        list(opciones.keys())[0],
    )

    nuevo_modelo_label = st.selectbox(
        "Seleccionar nuevo modelo por defecto",
        options=list(opciones.keys()),
        index=list(opciones.keys()).index(actual_label) if actual_label in opciones else 0,
        key="admin_modelo_selector",
    )

    nuevo_modelo = opciones[nuevo_modelo_label]

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Cambiar modelo", type="primary"):
            try:
                supabase.table("config_sistema").update({
                    "valor": nuevo_modelo,
                }).eq("clave", "modelo_llm").execute()
                st.success(f"Modelo cambiado a **{nuevo_modelo}**. Los nuevos chats usarán este modelo.")
            except Exception as e:
                st.error(f"Error al cambiar modelo: {e}")

    with col2:
        if nuevo_modelo != modelo_actual:
            st.warning(f"⚠️ El cambio afectará a **todos** los estudiantes a partir de su siguiente mensaje.")

    # Tabla de costos
    st.subheader("💰 Tarifas de referencia (USD por 1K tokens)")
    costos = []
    for clave, info in MODELOS_DISPONIBLES.items():
        costos.append({
            "Modelo": clave,
            "Proveedor": info["provider"],
            "Input $/1K": f"${info['input_cost']:.5f}",
            "Output $/1K": f"${info['output_cost']:.5f}",
        })
    st.dataframe(costos, hide_index=True, use_container_width=True)


# ============================================================
# Tab: Estadísticas Globales
# ============================================================
def _tab_estadisticas():
    st.subheader("📊 Estadísticas Globales del Sistema")
    supabase = get_supabase()

    col1, col2, col3, col4 = st.columns(4)

    # Total estudiantes
    est_resp = (
        supabase.table("profiles")
        .select("id", count="exact")
        .eq("rol", "estudiante")
        .execute()
    )
    with col1:
        st.metric("👥 Estudiantes", est_resp.count if hasattr(est_resp, "count") else "?")

    # Total docentes
    doc_resp = (
        supabase.table("profiles")
        .select("id", count="exact")
        .eq("rol", "docente")
        .execute()
    )
    with col2:
        st.metric("👨‍🏫 Docentes", doc_resp.count if hasattr(doc_resp, "count") else "?")

    # Total conversaciones
    conv_resp = (
        supabase.table("conversaciones")
        .select("id", count="exact")
        .execute()
    )
    with col3:
        st.metric("💬 Conversaciones", conv_resp.count if hasattr(conv_resp, "count") else "?")

    # Total mensajes
    msg_resp = (
        supabase.table("mensajes")
        .select("id", count="exact")
        .execute()
    )
    with col4:
        st.metric("📝 Mensajes", msg_resp.count if hasattr(msg_resp, "count") else "?")

    # Logs recientes
    st.subheader("📋 Actividad reciente")
    logs = (
        supabase.table("logs_sesiones")
        .select("timestamp, asignatura, modelo, costo_usd, session_id")
        .order("timestamp", desc=True)
        .limit(20)
        .execute()
    )

    if logs.data:
        rows = []
        for l in logs.data:
            rows.append({
                "Fecha": l["timestamp"][:19].replace("T", " ") if l["timestamp"] else "",
                "Curso": l["asignatura"],
                "Modelo": l["modelo"],
                "Costo": f"${l['costo_usd']:.6f}" if l["costo_usd"] else "$0",
                "Sesión": l["session_id"][:8] if l["session_id"] else "",
            })
        st.dataframe(rows, hide_index=True, use_container_width=True)
    else:
        st.info("Aún no hay actividad registrada.")


# ============================================================
# Tab: Sistema
# ============================================================
def _tab_sistema():
    st.subheader("🛡️ Configuración del Sistema")
    supabase = get_supabase()

    configs = (
        supabase.table("config_sistema")
        .select("*")
        .order("id")
        .execute()
    )

    if not configs.data:
        st.info("No hay configuraciones del sistema.")
        return

    for c in configs.data:
        with st.expander(f"⚙️ {c['clave']} = **{c['valor']}**"):
            st.caption(c.get("descripcion", ""))
            nuevo_valor = st.text_input(
                f"Nuevo valor para '{c['clave']}'",
                value=c["valor"],
                key=f"cfg_{c['id']}",
            )
            if st.button(f"Actualizar {c['clave']}", key=f"btn_cfg_{c['id']}"):
                try:
                    supabase.table("config_sistema").update({
                        "valor": nuevo_valor,
                    }).eq("id", c["id"]).execute()
                    st.success(f"{c['clave']} actualizado a {nuevo_valor}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================
# Helpers
# ============================================================
def _get_modelo_actual_db() -> str:
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("config_sistema")
            .select("valor")
            .eq("clave", "modelo_llm")
            .single()
            .execute()
        )
        if resp.data:
            return resp.data["valor"]
    except Exception:
        pass
    return MODELO_POR_DEFECTO
