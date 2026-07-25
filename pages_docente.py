"""pages_docente.py — Dashboard del docente: estudiantes, grupos, tracking, mensajes."""
import streamlit as st
import datetime
from auth import usuario_actual, get_supabase, crear_usuario_estudiante


def render_dashboard_docente():
    """Punto de entrada del dashboard de docente."""
    usuario = usuario_actual()
    st.title(f"👨‍🏫 Panel Docente")
    st.caption(f"{usuario.nombre} — Profesor")

    tab1, tab2, tab3, tab4 = st.tabs([
        "👥 Estudiantes", "👥 Grupos", "📊 Tracking", "📬 Mensajes"
    ])

    with tab1:
        _tab_estudiantes(usuario)
    with tab2:
        _tab_grupos(usuario)
    with tab3:
        _tab_tracking(usuario)
    with tab4:
        _tab_mensajes(usuario)


# ============================================================
# Tab: Gestión de Estudiantes
# ============================================================
def _tab_estudiantes(usuario):
    st.subheader("👥 Gestión de Estudiantes")

    # --- Crear estudiante ---
    with st.expander("➕ Crear nuevo estudiante", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre = st.text_input("Nombre completo", key="nuevo_nombre")
        with col2:
            email = st.text_input("Email", key="nuevo_email")
        with col3:
            password = st.text_input("Contraseña", type="password", key="nuevo_pass")

        if st.button("Crear estudiante", type="primary"):
            if nombre and email and password:
                ok, msg = crear_usuario_estudiante(email, password, nombre)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Complete todos los campos.")

    # --- Lista de estudiantes ---
    st.subheader("📋 Lista de estudiantes")
    supabase = get_supabase()
    resp = (
        supabase.table("profiles")
        .select("id, email, nombre, created_at")
        .eq("rol", "estudiante")
        .order("nombre")
        .execute()
    )

    if not resp.data:
        st.info("No hay estudiantes registrados aún.")
        return

    # Tabla
    rows = []
    for p in resp.data:
        rows.append({
            "Nombre": p["nombre"],
            "Email": p["email"],
            "Registrado": p["created_at"][:10] if p["created_at"] else "",
            "ID": p["id"],
        })

    st.dataframe(
        rows,
        column_config={"ID": None},
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# Tab: Gestión de Grupos
# ============================================================
def _tab_grupos(usuario):
    st.subheader("👥 Grupos de Trabajo")
    supabase = get_supabase()

    # Lista de estudiantes para asignar
    estudiantes = (
        supabase.table("profiles")
        .select("id, nombre, email")
        .eq("rol", "estudiante")
        .order("nombre")
        .execute()
    )
    mapa_estudiantes = {p["nombre"]: p for p in (estudiantes.data or [])}

    # --- Crear grupo ---
    with st.expander("➕ Crear nuevo grupo", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            nombre_grp = st.text_input("Nombre del grupo", key="nuevo_grupo_nombre")
        with col2:
            asignatura_grp = st.text_input("Asignatura", key="nuevo_grupo_asignatura",
                                           placeholder="ej: mecanica-newtoniana")

        desc_grp = st.text_area("Descripción", key="nuevo_grupo_desc")

        miembros_sel = st.multiselect(
            "Miembros del grupo",
            options=list(mapa_estudiantes.keys()),
            key="nuevo_grupo_miembros",
        )

        if st.button("Crear grupo", type="primary"):
            if nombre_grp and miembros_sel:
                # Crear grupo
                resp = supabase.table("grupos").insert({
                    "nombre": nombre_grp,
                    "descripcion": desc_grp,
                    "creado_por": usuario.id,
                    "asignatura": asignatura_grp,
                }).execute()

                if resp.data:
                    grupo_id = resp.data[0]["id"]
                    # Asignar miembros
                    for nombre_m in miembros_sel:
                        est = mapa_estudiantes[nombre_m]
                        try:
                            supabase.table("grupos_estudiantes").insert({
                                "grupo_id": grupo_id,
                                "estudiante_id": est["id"],
                            }).execute()
                        except Exception:
                            pass  # Ya existe
                    st.success(f"Grupo '{nombre_grp}' creado con {len(miembros_sel)} miembros.")
                    st.rerun()
            else:
                st.warning("Nombre y al menos un miembro son obligatorios.")

    # --- Lista de grupos ---
    st.subheader("📋 Mis grupos")
    grupos_resp = (
        supabase.table("grupos")
        .select("*")
        .eq("creado_por", usuario.id)
        .order("created_at", desc=True)
        .execute()
    )

    if not grupos_resp.data:
        st.info("No has creado grupos aún.")
        return

    for g in grupos_resp.data:
        # Contar miembros
        miembros_resp = (
            supabase.table("grupos_estudiantes")
            .select("estudiante_id, profiles!estudiante_id(nombre, email)")
            .eq("grupo_id", g["id"])
            .execute()
        )
        miembros = [m.get("profiles", {}) for m in (miembros_resp.data or [])]
        nombres_m = [m.get("nombre", "?") for m in miembros if isinstance(m, dict)]

        with st.expander(f"📁 {g['nombre']} — {g.get('asignatura', 'sin asignatura')} ({len(nombres_m)} miembros)"):
            st.caption(g.get("descripcion", ""))
            st.markdown("**Miembros:** " + ", ".join(nombres_m))

            # Ver conversaciones del grupo
            if st.button(f"📊 Ver conversaciones", key=f"ver_conv_grupo_{g['id']}"):
                st.session_state._tracking_grupo = g["id"]
                st.session_state._tracking_tipo = "grupo"
                st.rerun()


# ============================================================
# Tab: Tracking de Conversaciones
# ============================================================
def _tab_tracking(usuario):
    st.subheader("📊 Seguimiento de Estudiantes")
    supabase = get_supabase()

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        estudiantes = (
            supabase.table("profiles")
            .select("id, nombre")
            .eq("rol", "estudiante")
            .order("nombre")
            .execute()
        )
        mapa_est = {p["nombre"]: p["id"] for p in (estudiantes.data or [])}

        estudiante_sel = st.selectbox(
            "Seleccionar estudiante",
            options=["(Todos)"] + list(mapa_est.keys()),
            key="tracking_estudiante",
        )
    with col2:
        # Obtener asignaturas únicas de las conversaciones
        asignaturas_resp = (
            supabase.table("conversaciones")
            .select("asignatura")
            .execute()
        )
        asigs = sorted(set(
            c["asignatura"] for c in (asignaturas_resp.data or []) if c["asignatura"]
        ))
        asignatura_sel = st.selectbox(
            "Filtrar por asignatura",
            options=["(Todas)"] + asigs,
            key="tracking_asignatura",
        )

    # Construir query
    query = supabase.table("conversaciones").select("*")
    if estudiante_sel != "(Todos)":
        query = query.eq("estudiante_id", mapa_est[estudiante_sel])
    if asignatura_sel != "(Todas)":
        query = query.eq("asignatura", asignatura_sel)

    convs_resp = query.order("created_at", desc=True).limit(50).execute()

    if not convs_resp.data:
        st.info("No se encontraron conversaciones con esos filtros.")
        return

    for conv in convs_resp.data:
        # Nombre del estudiante
        perfil_resp = (
            supabase.table("profiles")
            .select("nombre")
            .eq("id", conv["estudiante_id"])
            .single()
            .execute()
        )
        nombre_est = perfil_resp.data["nombre"] if perfil_resp.data else "?"

        # Contar mensajes
        count_resp = (
            supabase.table("mensajes")
            .select("id", count="exact")
            .eq("conversacion_id", conv["id"])
            .execute()
        )
        n_mensajes = count_resp.count if hasattr(count_resp, "count") else "?"

        grupo_info = ""
        if conv.get("grupo_id"):
            g_resp = (
                supabase.table("grupos")
                .select("nombre")
                .eq("id", conv["grupo_id"])
                .single()
                .execute()
            )
            if g_resp.data:
                grupo_info = f" — Grupo: {g_resp.data['nombre']}"

        fecha = conv["created_at"][:19].replace("T", " ") if conv["created_at"] else ""

        with st.expander(f"💬 {nombre_est}{grupo_info} — {conv['asignatura']} — {fecha} — {n_mensajes} msgs"):
            mensajes_resp = (
                supabase.table("mensajes")
                .select("rol, contenido, created_at")
                .eq("conversacion_id", conv["id"])
                .order("created_at")
                .limit(30)
                .execute()
            )
            if mensajes_resp.data:
                for m in mensajes_resp.data:
                    rol_icono = "🧑" if m["rol"] == "user" else "🤖"
                    st.caption(f"{rol_icono} {m['created_at'][:19]}")
                    st.markdown(m["contenido"][:600])
                    st.divider()

            # Botón para enviar mensaje al estudiante
            if st.button(f"📨 Enviar mensaje a {nombre_est}", key=f"msg_{conv['id']}"):
                st.session_state._mensaje_para = {
                    "estudiante_id": conv["estudiante_id"],
                    "estudiante_nombre": nombre_est,
                    "grupo_id": conv.get("grupo_id"),
                }
                st.rerun()


# ============================================================
# Tab: Mensajes a estudiantes
# ============================================================
def _tab_mensajes(usuario):
    st.subheader("📬 Enviar mensaje a estudiantes/grupos")
    supabase = get_supabase()

    # Destinatario
    destino_tipo = st.radio("Enviar a:", ["Estudiante individual", "Grupo"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        if destino_tipo == "Estudiante individual":
            estudiantes = (
                supabase.table("profiles")
                .select("id, nombre")
                .eq("rol", "estudiante")
                .order("nombre")
                .execute()
            )
            mapa_est = {p["nombre"]: p for p in (estudiantes.data or [])}
            destino_sel = st.selectbox(
                "Estudiante",
                options=list(mapa_est.keys()),
                key="msg_destino_estudiante",
            )
            estudiante_id = mapa_est[destino_sel]["id"] if destino_sel in mapa_est else None
            grupo_id = None
        else:
            grupos = (
                supabase.table("grupos")
                .select("id, nombre")
                .eq("creado_por", usuario.id)
                .order("nombre")
                .execute()
            )
            mapa_grp = {g["nombre"]: g for g in (grupos.data or [])}
            destino_sel = st.selectbox(
                "Grupo",
                options=list(mapa_grp.keys()),
                key="msg_destino_grupo",
            )
            grupo_id = mapa_grp[destino_sel]["id"] if destino_sel in mapa_grp else None
            estudiante_id = None

    with col2:
        asunto = st.text_input("Asunto", key="msg_asunto")

    contenido = st.text_area("Mensaje", key="msg_contenido", height=150)

    if st.button("📨 Enviar mensaje", type="primary"):
        if asunto and contenido and (estudiante_id or grupo_id):
            try:
                supabase.table("mensajes_docente").insert({
                    "de_usuario_id": usuario.id,
                    "para_estudiante_id": estudiante_id,
                    "para_grupo_id": grupo_id,
                    "asunto": asunto,
                    "contenido": contenido,
                }).execute()
                st.success(f"Mensaje enviado a {destino_sel}.")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Complete todos los campos.")

    # --- Mensajes enviados ---
    st.subheader("📤 Mensajes enviados")
    enviados = (
        supabase.table("mensajes_docente")
        .select("*")
        .eq("de_usuario_id", usuario.id)
        .order("created_at", desc=True)
        .limit(30)
        .execute()
    )

    if not enviados.data:
        st.info("No has enviado mensajes aún.")
        return

    for msg in enviados.data:
        destino_nombre = ""
        if msg.get("para_estudiante_id"):
            p_resp = (
                supabase.table("profiles")
                .select("nombre")
                .eq("id", msg["para_estudiante_id"])
                .single()
                .execute()
            )
            destino_nombre = p_resp.data["nombre"] if p_resp.data else "?"
        elif msg.get("para_grupo_id"):
            g_resp = (
                supabase.table("grupos")
                .select("nombre")
                .eq("id", msg["para_grupo_id"])
                .single()
                .execute()
            )
            destino_nombre = f"Grupo: {g_resp.data['nombre']}" if g_resp.data else "?"

        with st.expander(f"📨 {msg['asunto']} → {destino_nombre} — {msg['created_at'][:19]}"):
            st.markdown(msg["contenido"])
