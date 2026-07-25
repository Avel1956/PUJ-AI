"""pages_admin.py — Panel de administración: docentes, modelos, logs, sistema."""
import streamlit as st
from auth import usuario_actual, get_supabase, get_supabase_admin, crear_usuario_docente
from config import MODELOS_DISPONIBLES, MODELO_POR_DEFECTO


def render_dashboard_admin():
    """Punto de entrada del dashboard de administrador."""
    usuario = usuario_actual()
    st.title(f"⚙️ Panel de Administración")
    st.caption(f"{usuario.nombre} — Administrador del Sistema")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👨‍🏫 Docentes", "👥 Estudiantes", "🧠 Modelos", "📊 Estadísticas", "🧹 Datos"
    ])

    with tab1:
        _tab_docentes()
    with tab2:
        _tab_estudiantes()
    with tab3:
        _tab_modelos()
    with tab4:
        _tab_estadisticas()
    with tab5:
        _tab_datos()


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
                    st.rerun()
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

    for i, p in enumerate(resp.data):
        grupos = (
            supabase.table("grupos")
            .select("id", count="exact")
            .eq("creado_por", p["id"])
            .execute()
        )
        n_grupos = grupos.count if hasattr(grupos, "count") else 0

        with st.expander(f"👨‍🏫 {p['nombre']} — {p['email']} — {n_grupos} grupos"):
            st.caption(f"ID: {p['id']}")
            st.caption(f"Registrado: {p.get('created_at', '?')}")
            if st.button("🗑️ Eliminar docente", key=f"del_doc_{p['id']}", type="secondary"):
                _confirmar_y_borrar(
                    f"¿Eliminar a {p['nombre']}? Se perderán sus grupos y mensajes.",
                    lambda pid=p["id"]: _borrar_perfil(pid, "docente"),
                    f"really_del_doc_{p['id']}",
                )


# ============================================================
# Tab: Gestión de Estudiantes (Admin)
# ============================================================
def _tab_estudiantes():
    st.subheader("👥 Gestión de Estudiantes")
    supabase = get_supabase()

    resp = (
        supabase.table("profiles")
        .select("id, email, nombre, created_at")
        .eq("rol", "estudiante")
        .order("nombre")
        .execute()
    )

    if not resp.data:
        st.info("No hay estudiantes registrados.")
        return

    st.caption(f"{len(resp.data)} estudiantes encontrados")

    for p in resp.data:
        # Contar conversaciones
        convs = (
            supabase.table("conversaciones")
            .select("id", count="exact")
            .eq("estudiante_id", p["id"])
            .execute()
        )
        n_convs = convs.count if hasattr(convs, "count") else 0

        with st.expander(f"🧑 {p['nombre']} — {p['email']} — {n_convs} conversaciones"):
            st.caption(f"Registrado: {p.get('created_at', '?')}")
            if st.button("🗑️ Eliminar estudiante", key=f"del_est_{p['id']}", type="secondary"):
                _confirmar_y_borrar(
                    f"¿Eliminar a {p['nombre']} y todas sus conversaciones?",
                    lambda pid=p["id"]: _borrar_perfil(pid, "estudiante"),
                    f"really_del_est_{p['id']}",
                )


# ============================================================
# Tab: Configuración de Modelos
# ============================================================
def _tab_modelos():
    st.subheader("🧠 Configuración de Modelos LLM")
    supabase = get_supabase()

    # Modelo actual
    modelo_actual = _get_modelo_actual_db()
    st.info(f"🔧 Modelo activo: **{modelo_actual}**")

    opciones = {
        f"{v['descripcion']} ({k})": k
        for k, v in MODELOS_DISPONIBLES.items()
    }

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
                st.success(f"Modelo cambiado a **{nuevo_modelo}**.")
            except Exception as e:
                st.error(f"Error al cambiar modelo: {e}")

    with col2:
        if nuevo_modelo != modelo_actual:
            st.warning("⚠️ El cambio afectará a **todos** los estudiantes.")

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

    est_resp = supabase.table("profiles").select("id", count="exact").eq("rol", "estudiante").execute()
    with col1:
        st.metric("👥 Estudiantes", est_resp.count if hasattr(est_resp, "count") else "?")

    doc_resp = supabase.table("profiles").select("id", count="exact").eq("rol", "docente").execute()
    with col2:
        st.metric("👨‍🏫 Docentes", doc_resp.count if hasattr(doc_resp, "count") else "?")

    conv_resp = supabase.table("conversaciones").select("id", count="exact").execute()
    with col3:
        st.metric("💬 Conversaciones", conv_resp.count if hasattr(conv_resp, "count") else "?")

    msg_resp = supabase.table("mensajes").select("id", count="exact").execute()
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
# Tab: Limpieza de Datos
# ============================================================
def _tab_datos():
    st.subheader("🧹 Limpieza de Datos")
    supabase = get_supabase()

    # --- Borrar logs viejos ---
    with st.expander("📋 Limpiar logs antiguos"):
        dias_logs = st.number_input("Eliminar logs con más de N días", min_value=1, value=90, key="admin_dias_logs")
        if st.button("🗑️ Borrar logs antiguos", key="btn_clean_logs"):
            try:
                cutoff = f"{(datetime.date.today() - datetime.timedelta(days=dias_logs)).isoformat()}T00:00:00"
                resp = supabase.table("logs_sesiones").delete().lt("timestamp", cutoff).execute()
                st.success(f"Logs anteriores a {cutoff[:10]} eliminados.")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- Borrar conversaciones viejas ---
    with st.expander("💬 Limpiar conversaciones antiguas"):
        dias_conv = st.number_input("Eliminar conversaciones con más de N días", min_value=1, value=180, key="admin_dias_conv")
        if st.button("🗑️ Borrar conversaciones antiguas", key="btn_clean_conv"):
            try:
                cutoff = f"{(datetime.date.today() - datetime.timedelta(days=dias_conv)).isoformat()}T00:00:00"
                resp = supabase.table("conversaciones").delete().lt("updated_at", cutoff).execute()
                st.success(f"Conversaciones anteriores a {cutoff[:10]} eliminadas.")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- Borrar todo de una asignatura ---
    with st.expander("📚 Limpiar asignatura completa"):
        asigs_resp = supabase.table("conversaciones").select("asignatura").execute()
        asigs = sorted(set(c["asignatura"] for c in (asigs_resp.data or []) if c["asignatura"]))
        if asigs:
            asig_sel = st.selectbox("Asignatura a limpiar", asigs, key="admin_asig_clean")
            if st.button("🗑️ Borrar TODAS las conversaciones de esta asignatura", key="btn_clean_asig", type="secondary"):
                _confirmar_y_borrar(
                    f"¿Eliminar TODAS las conversaciones de {asig_sel}? Esta acción NO se puede deshacer.",
                    lambda: _borrar_asignatura(asig_sel),
                    "really_clean_asig",
                )
        else:
            st.info("No hay asignaturas con conversaciones.")

    # --- Config del sistema ---
    with st.expander("🛡️ Configuración del Sistema"):
        configs = (
            supabase.table("config_sistema").select("*").order("id").execute()
        )
        if not configs.data:
            st.info("No hay configuraciones del sistema.")
        else:
            for c in configs.data:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{c['clave']}** = `{c['valor']}` — {c.get('descripcion', '')}")
                with col2:
                    nuevo_valor = st.text_input("Nuevo", value=c["valor"], key=f"cfg_{c['id']}", label_visibility="collapsed")
                if nuevo_valor != c["valor"] and st.button(f"✏️ Guardar", key=f"save_cfg_{c['id']}"):
                    try:
                        supabase.table("config_sistema").update({"valor": nuevo_valor}).eq("id", c["id"]).execute()
                        st.success(f"{c['clave']} → {nuevo_valor}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# Helpers
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


def _borrar_perfil(perfil_id: str, rol: str):
    """Borra un perfil y toda su data asociada."""
    supabase_admin = get_supabase_admin()
    # El trigger o las políticas cascadean — pero hacemos explícito
    tablas = ["mensajes", "conversaciones", "grupos_estudiantes", "grupos", "mensajes_docente", "logs_sesiones"]
    for tabla in tablas:
        col = _columna_por_tabla(tabla, rol)
        if col:
            try:
                supabase_admin.table(tabla).delete().eq(col, perfil_id).execute()
            except Exception:
                pass
    # Borrar perfil
    supabase_admin.table("profiles").delete().eq("id", perfil_id).execute()
    # Borrar usuario auth
    try:
        supabase_admin.auth.admin.delete_user(perfil_id)
    except Exception:
        pass


def _columna_por_tabla(tabla: str, rol: str) -> str | None:
    if tabla == "mensajes":
        return None  # se borran al borrar conversaciones
    if tabla == "conversaciones":
        return "estudiante_id" if rol == "estudiante" else None
    if tabla == "grupos_estudiantes":
        return "estudiante_id" if rol == "estudiante" else None
    if tabla == "grupos":
        return "creado_por" if rol == "docente" else None
    if tabla == "mensajes_docente":
        return "de_usuario_id" if rol == "docente" else "para_estudiante_id" if rol == "estudiante" else None
    if tabla == "logs_sesiones":
        return "usuario_id"
    return None


def _borrar_asignatura(asignatura: str):
    supabase = get_supabase()
    # Borrar mensajes de conversaciones de esa asignatura
    convs = supabase.table("conversaciones").select("id").eq("asignatura", asignatura).execute()
    for c in (convs.data or []):
        try:
            supabase.table("mensajes").delete().eq("conversacion_id", c["id"]).execute()
        except Exception:
            pass
    # Borrar conversaciones
    supabase.table("conversaciones").delete().eq("asignatura", asignatura).execute()


@st.cache_data(ttl=30)
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
