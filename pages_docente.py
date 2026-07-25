"""pages_docente.py — Dashboard del docente: estudiantes, grupos, tracking, mensajes, descargas."""
import streamlit as st
import datetime
import json
from auth import usuario_actual, get_supabase, get_supabase_admin, crear_usuario_estudiante


def render_dashboard_docente():
    """Punto de entrada del dashboard de docente."""
    usuario = usuario_actual()
    st.title(f"👨‍🏫 Panel Docente")
    st.caption(f"{usuario.nombre} — Profesor")

    # Manejar navegación desde botones "Ver conversaciones"
    tab_idx = _resolver_tab_inicial()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Estudiantes", "👥 Grupos", "📊 Tracking", "📬 Mensajes", "📥 Descargas"
    ])

    # Streamlit no permite setear tab activo directamente, usamos query params
    tab_labels = ["👥 Estudiantes", "👥 Grupos", "📊 Tracking", "📬 Mensajes", "📥 Descargas"]

    with tab1:
        _tab_estudiantes(usuario)
    with tab2:
        _tab_grupos(usuario)
    with tab3:
        _tab_tracking(usuario)
    with tab4:
        _tab_mensajes(usuario)
    with tab5:
        _tab_descargas(usuario)


def _resolver_tab_inicial() -> int:
    """Si se clickeó 'Ver conversaciones', redirigir al tab tracking."""
    if st.query_params.get("tab") == "tracking":
        st.query_params.clear()
        # Mostrar aviso de navegación
        st.info("⬇️ Conversaciones cargadas en la pestaña **📊 Tracking** — desplácese hacia abajo para verlas.")
    return 0


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
                    st.rerun()
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

    for p in resp.data:
        convs_resp = (
            supabase.table("conversaciones")
            .select("id", count="exact")
            .eq("estudiante_id", p["id"])
            .execute()
        )
        n_convs = convs_resp.count if hasattr(convs_resp, "count") else 0

        with st.expander(f"🧑 {p['nombre']} — {p['email']} — {n_convs} conversaciones"):
            st.caption(f"Registrado: {p.get('created_at', '?')}")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📊 Ver conversaciones", key=f"ver_conv_est_{p['id']}"):
                    st.query_params["tab"] = "tracking"
                    st.session_state._tracking_estudiante = p["id"]
                    st.session_state._tracking_nombre = p["nombre"]
                    st.rerun()
            with col2:
                if st.button("📥 Descargar JSONL", key=f"dl_est_{p['id']}"):
                    jsonl = _generar_jsonl_estudiante(p["id"], p["nombre"])
                    _ofrecer_descarga(jsonl, f"conversaciones_{p['nombre'].replace(' ', '_')}.jsonl")
            with col3:
                if st.button("🗑️ Eliminar", key=f"del_est_{p['id']}", type="secondary"):
                    st.session_state[f"cf_doc_est_{p['id']}"] = True
                    st.rerun()
                _confirmar_y_borrar(
                    f"cf_doc_est_{p['id']}",
                    f"¿Eliminar a {p['nombre']} y todas sus conversaciones?",
                    lambda pid=p["id"]: _borrar_estudiante(pid),
                )


# ============================================================
# Tab: Gestión de Grupos
# ============================================================
def _tab_grupos(usuario):
    st.subheader("👥 Grupos de Trabajo")
    supabase = get_supabase()

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
                resp = supabase.table("grupos").insert({
                    "nombre": nombre_grp,
                    "descripcion": desc_grp,
                    "creado_por": usuario.id,
                    "asignatura": asignatura_grp,
                }).execute()
                if resp.data:
                    grupo_id = resp.data[0]["id"]
                    for nombre_m in miembros_sel:
                        est = mapa_estudiantes[nombre_m]
                        try:
                            supabase.table("grupos_estudiantes").insert({
                                "grupo_id": grupo_id,
                                "estudiante_id": est["id"],
                            }).execute()
                        except Exception:
                            pass
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
        miembros_resp = (
            supabase.table("grupos_estudiantes")
            .select("estudiante_id, profiles!estudiante_id(nombre, email)")
            .eq("grupo_id", g["id"])
            .execute()
        )
        miembros = [m.get("profiles", {}) for m in (miembros_resp.data or [])]
        nombres_m = [m.get("nombre", "?") for m in miembros if isinstance(m, dict)]
        ids_m = [m.get("estudiante_id", "") for m in (miembros_resp.data or [])]

        with st.expander(f"📁 {g['nombre']} — {g.get('asignatura', 'sin asignatura')} ({len(nombres_m)} miembros)"):
            st.caption(g.get("descripcion", ""))
            st.markdown("**Miembros:** " + ", ".join(nombres_m))

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📊 Ver conversaciones", key=f"ver_conv_grp_{g['id']}"):
                    st.query_params["tab"] = "tracking"
                    st.session_state._tracking_grupo = g["id"]
                    st.session_state._tracking_nombre = g["nombre"]
                    st.session_state._tracking_tipo = "grupo"
                    st.rerun()
            with col2:
                if st.button("📥 Descargar JSONL", key=f"dl_grp_{g['id']}"):
                    jsonl = _generar_jsonl_grupo(g["id"], g["nombre"])
                    _ofrecer_descarga(jsonl, f"grupo_{g['nombre'].replace(' ', '_')}.jsonl")
            with col3:
                if st.button("🗑️ Eliminar grupo", key=f"del_grp_{g['id']}", type="secondary"):
                    st.session_state[f"cf_doc_grp_{g['id']}"] = True
                    st.rerun()
                _confirmar_y_borrar(
                    f"cf_doc_grp_{g['id']}",
                    f"¿Eliminar el grupo '{g['nombre']}' y desvincular a {len(nombres_m)} miembros?",
                    lambda gid=g["id"]: _borrar_grupo(gid),
                )

            # Quitar miembro
            if len(ids_m) > 0:
                quitar = st.selectbox(
                    "Quitar miembro", [""] + nombres_m,
                    key=f"quitar_miembro_{g['id']}",
                    label_visibility="collapsed",
                    placeholder="Quitar miembro...",
                )
                if quitar and st.button("✖️ Quitar", key=f"btn_quitar_{g['id']}"):
                    idx = nombres_m.index(quitar)
                    est_id = ids_m[idx]
                    try:
                        supabase.table("grupos_estudiantes").delete().eq("grupo_id", g["id"]).eq("estudiante_id", est_id).execute()
                        st.success(f"{quitar} removido del grupo.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


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

        # Determinar estudiante por defecto (desde navegación cruzada)
        default_idx = 0
        if "_tracking_estudiante" in st.session_state:
            nombre_track = st.session_state.get("_tracking_nombre", "")
            if nombre_track in mapa_est:
                default_idx = list(mapa_est.keys()).index(nombre_track) + 1
            del st.session_state._tracking_estudiante
            del st.session_state._tracking_nombre

        estudiante_sel = st.selectbox(
            "Seleccionar estudiante",
            options=["(Todos)"] + list(mapa_est.keys()),
            index=default_idx,
            key="tracking_estudiante",
        )
    with col2:
        asignaturas_resp = supabase.table("conversaciones").select("asignatura").execute()
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

    # Barra de acciones masivas
    if convs_resp.data:
        col_dl, _ = st.columns([2, 4])
        with col_dl:
            if estudiante_sel != "(Todos)":
                if st.button(f"📥 Descargar todas las de {estudiante_sel} (JSONL)", key="dl_tracking_estudiante"):
                    jsonl = _generar_jsonl_estudiante(mapa_est[estudiante_sel], estudiante_sel)
                    _ofrecer_descarga(jsonl, f"conversaciones_{estudiante_sel.replace(' ', '_')}.jsonl")
            else:
                if st.button("📥 Descargar TODO lo visible (JSONL)", key="dl_tracking_todo"):
                    jsonl = _generar_jsonl_docente(usuario.id)
                    _ofrecer_descarga(jsonl, f"todas_conversaciones_docente.jsonl")

    for conv in convs_resp.data:
        perfil_resp = (
            supabase.table("profiles")
            .select("nombre")
            .eq("id", conv["estudiante_id"])
            .single()
            .execute()
        )
        nombre_est = perfil_resp.data["nombre"] if perfil_resp.data else "?"

        count_resp = (
            supabase.table("mensajes")
            .select("id", count="exact")
            .eq("conversacion_id", conv["id"])
            .execute()
        )
        n_mensajes = count_resp.count if hasattr(count_resp, "count") else 0

        grupo_info = ""
        if conv.get("grupo_id"):
            g_resp = supabase.table("grupos").select("nombre").eq("id", conv["grupo_id"]).single().execute()
            if g_resp.data:
                grupo_info = f" — Grupo: {g_resp.data['nombre']}"

        fecha = conv["created_at"][:19].replace("T", " ") if conv["created_at"] else ""

        with st.expander(f"💬 {nombre_est}{grupo_info} — {conv['asignatura']} — {fecha} — {n_mensajes} msgs"):
            mensajes_resp = (
                supabase.table("mensajes")
                .select("rol, contenido, created_at, tokens_input, tokens_output, costo_usd")
                .eq("conversacion_id", conv["id"])
                .order("created_at")
                .limit(50)
                .execute()
            )
            if mensajes_resp.data:
                for m in mensajes_resp.data:
                    rol_icono = "🧑" if m["rol"] == "user" else "🤖"
                    st.caption(f"{rol_icono} {m['created_at'][:19]}")
                    st.markdown(m["contenido"][:600])
                    st.divider()

            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"📨 Enviar mensaje a {nombre_est}", key=f"msg_{conv['id']}"):
                    st.session_state._mensaje_para = {
                        "estudiante_id": conv["estudiante_id"],
                        "estudiante_nombre": nombre_est,
                        "grupo_id": conv.get("grupo_id"),
                    }
                    st.rerun()
            with col2:
                jsonl_conv = _generar_jsonl_conversacion(conv, nombre_est, mensajes_resp.data)
                _ofrecer_descarga(jsonl_conv, f"conv_{conv['id'][:8]}.jsonl", label=f"📥 JSONL")
            with col3:
                if st.button("🗑️ Eliminar conversación", key=f"del_conv_{conv['id']}", type="secondary"):
                    st.session_state[f"cf_doc_conv_{conv['id']}"] = True
                    st.rerun()
                _confirmar_y_borrar(
                    f"cf_doc_conv_{conv['id']}",
                    f"¿Eliminar conversación de {nombre_est} ({conv['asignatura']}, {n_mensajes} mensajes)?",
                    lambda cid=conv["id"]: _borrar_conversacion(cid),
                )


# ============================================================
# Tab: Mensajes a estudiantes
# ============================================================
def _tab_mensajes(usuario):
    st.subheader("📬 Enviar mensaje a estudiantes/grupos")
    supabase = get_supabase()

    if "_mensaje_para" in st.session_state:
        info = st.session_state._mensaje_para
        st.info(f"📨 Redactando mensaje para **{info.get('estudiante_nombre', info.get('estudiante_id', '?'))}**")
        del st.session_state._mensaje_para

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
            destino_sel = st.selectbox("Estudiante", options=list(mapa_est.keys()), key="msg_destino_estudiante")
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
            destino_sel = st.selectbox("Grupo", options=list(mapa_grp.keys()), key="msg_destino_grupo")
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
        destino_nombre = _nombre_destino(msg, supabase)

        with st.expander(f"📨 {msg['asunto']} → {destino_nombre} — {msg['created_at'][:19]}"):
            st.markdown(msg["contenido"])
            if st.button("🗑️ Eliminar mensaje", key=f"del_msg_{msg['id']}", type="secondary"):
                st.session_state[f"cf_doc_msg_{msg['id']}"] = True
                st.rerun()
            _confirmar_y_borrar(
                f"cf_doc_msg_{msg['id']}",
                f"¿Eliminar mensaje '{msg['asunto']}' enviado a {destino_nombre}?",
                lambda mid=msg["id"]: _borrar_mensaje_docente(mid),
            )



# Tab: Descargas (JSONL)
# ============================================================
def _tab_descargas(usuario):
    st.subheader("📥 Descargar Conversaciones (JSONL)")
    st.caption("Formato JSONL: una línea por mensaje. Incluye metadatos (estudiante, asignatura, tokens, costo). Ideal para análisis con otros agentes IA.")

    supabase = get_supabase()

    # --- Estudiantes disponibles ---
    estudiantes = (
        supabase.table("profiles")
        .select("id, nombre")
        .eq("rol", "estudiante")
        .order("nombre")
        .execute()
    )
    mapa_est = {p["nombre"]: p for p in (estudiantes.data or [])}

    # --- Grupos del docente ---
    grupos = (
        supabase.table("grupos")
        .select("id, nombre, asignatura")
        .eq("creado_por", usuario.id)
        .order("nombre")
        .execute()
    )
    mapa_grp = {g["nombre"]: g for g in (grupos.data or [])}

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Por estudiante**")
        est_nombre = st.selectbox("Estudiante", options=["(Seleccionar)"] + list(mapa_est.keys()), key="dl_estudiante")
        if est_nombre != "(Seleccionar)" and st.button("📥 Descargar JSONL", key="btn_dl_estudiante", use_container_width=True):
            est = mapa_est[est_nombre]
            jsonl = _generar_jsonl_estudiante(est["id"], est_nombre)
            _ofrecer_descarga(jsonl, f"conversaciones_{est_nombre.replace(' ', '_')}.jsonl")

    with col2:
        st.markdown("**Por grupo**")
        grp_nombre = st.selectbox("Grupo", options=["(Seleccionar)"] + list(mapa_grp.keys()), key="dl_grupo")
        if grp_nombre != "(Seleccionar)" and st.button("📥 Descargar JSONL", key="btn_dl_grupo", use_container_width=True):
            grp = mapa_grp[grp_nombre]
            jsonl = _generar_jsonl_grupo(grp["id"], grp_nombre)
            _ofrecer_descarga(jsonl, f"grupo_{grp_nombre.replace(' ', '_')}.jsonl")

    with col3:
        st.markdown("**Todo**")
        n_total = _contar_conversaciones_docente(usuario.id)
        st.metric("Conversaciones totales", n_total)
        if st.button("📥 Descargar TODO (JSONL)", key="btn_dl_todo", use_container_width=True, type="primary"):
            jsonl = _generar_jsonl_docente(usuario.id)
            _ofrecer_descarga(jsonl, "todas_conversaciones.jsonl")

    # --- Asignaturas ---
    st.divider()
    st.markdown("**Por asignatura**")
    asignaturas_resp = supabase.table("conversaciones").select("asignatura").execute()
    asigs = sorted(set(
        c["asignatura"] for c in (asignaturas_resp.data or []) if c["asignatura"]
    ))

    if asigs:
        col_asig, _ = st.columns([2, 4])
        with col_asig:
            asig_sel = st.selectbox("Asignatura", asigs, key="dl_asignatura")
            if st.button("📥 Descargar asignatura (JSONL)", key="btn_dl_asignatura"):
                jsonl = _generar_jsonl_asignatura(asig_sel, usuario.id)
                _ofrecer_descarga(jsonl, f"asignatura_{asig_sel}.jsonl")

    # --- Preview ---
    st.divider()
    st.subheader("🔍 Formato de ejemplo")
    st.code(
        '{"tipo":"metadata","version":"1.0","exportado_por":"docente@...","fecha":"2026-01-01T00:00:00"}\n'
        '{"tipo":"mensaje","conversacion_id":"uuid","estudiante_id":"uuid","estudiante_nombre":"Ana","asignatura":"mecanica","rol":"user","contenido":"¿Qué es una fuerza?","tokens_input":0,"tokens_output":0,"costo_usd":0,"timestamp":"2026-01-01T00:00:00"}\n'
        '{"tipo":"mensaje","conversacion_id":"uuid","estudiante_id":"uuid","estudiante_nombre":"Ana","asignatura":"mecanica","rol":"assistant","contenido":"Excelente pregunta. ¿Qué entiendes tú por fuerza?","tokens_input":150,"tokens_output":45,"costo_usd":0.0003,"timestamp":"2026-01-01T00:00:05"}',
        language="json",
    )


# ============================================================
# Helpers de descarga JSONL
# ============================================================
def _generar_jsonl_estudiante(estudiante_id: str, nombre: str) -> str:
    """Genera JSONL con todas las conversaciones de un estudiante."""
    supabase = get_supabase()
    convs = (
        supabase.table("conversaciones")
        .select("id, asignatura, titulo, created_at, activa")
        .eq("estudiante_id", estudiante_id)
        .order("created_at")
        .execute()
    )
    lineas = [_linea_metadata()]
    for conv in (convs.data or []):
        msgs = (
            supabase.table("mensajes")
            .select("rol, contenido, created_at, tokens_input, tokens_output, costo_usd")
            .eq("conversacion_id", conv["id"])
            .order("created_at")
            .execute()
        )
        for m in (msgs.data or []):
            lineas.append(json.dumps({
                "tipo": "mensaje",
                "conversacion_id": conv["id"],
                "estudiante_id": estudiante_id,
                "estudiante_nombre": nombre,
                "asignatura": conv["asignatura"],
                "conversacion_titulo": conv["titulo"],
                "conversacion_activa": conv["activa"],
                "rol": m["rol"],
                "contenido": m["contenido"],
                "tokens_input": m.get("tokens_input", 0),
                "tokens_output": m.get("tokens_output", 0),
                "costo_usd": str(m.get("costo_usd", 0)),
                "timestamp": m["created_at"],
            }, ensure_ascii=False))
    return "\n".join(lineas)


def _generar_jsonl_grupo(grupo_id: str, nombre_grupo: str) -> str:
    """Genera JSONL con todas las conversaciones de los miembros de un grupo."""
    supabase = get_supabase()
    miembros = (
        supabase.table("grupos_estudiantes")
        .select("estudiante_id, profiles!estudiante_id(nombre)")
        .eq("grupo_id", grupo_id)
        .execute()
    )
    lineas = [_linea_metadata(extra={"grupo_id": grupo_id, "grupo_nombre": nombre_grupo})]
    for mi in (miembros.data or []):
        est_id = mi["estudiante_id"]
        est_nombre = mi.get("profiles", {}).get("nombre", "?") if isinstance(mi.get("profiles"), dict) else "?"
        convs = (
            supabase.table("conversaciones")
            .select("id, asignatura, titulo, created_at, activa")
            .eq("estudiante_id", est_id)
            .order("created_at")
            .execute()
        )
        for conv in (convs.data or []):
            msgs = (
                supabase.table("mensajes")
                .select("rol, contenido, created_at, tokens_input, tokens_output, costo_usd")
                .eq("conversacion_id", conv["id"])
                .order("created_at")
                .execute()
            )
            for m in (msgs.data or []):
                lineas.append(json.dumps({
                    "tipo": "mensaje",
                    "conversacion_id": conv["id"],
                    "estudiante_id": est_id,
                    "estudiante_nombre": est_nombre,
                    "grupo_id": grupo_id,
                    "grupo_nombre": nombre_grupo,
                    "asignatura": conv["asignatura"],
                    "conversacion_titulo": conv["titulo"],
                    "conversacion_activa": conv["activa"],
                    "rol": m["rol"],
                    "contenido": m["contenido"],
                    "tokens_input": m.get("tokens_input", 0),
                    "tokens_output": m.get("tokens_output", 0),
                    "costo_usd": str(m.get("costo_usd", 0)),
                    "timestamp": m["created_at"],
                }, ensure_ascii=False))
    return "\n".join(lineas)


def _generar_jsonl_docente(docente_id: str) -> str:
    """Genera JSONL con todas las conversaciones de TODOS los estudiantes (global para docente)."""
    supabase = get_supabase()
    estudiantes = (
        supabase.table("profiles")
        .select("id, nombre")
        .eq("rol", "estudiante")
        .execute()
    )
    lineas = [_linea_metadata(extra={"docente_id": docente_id})]
    for est in (estudiantes.data or []):
        convs = (
            supabase.table("conversaciones")
            .select("id, asignatura, titulo, created_at, activa")
            .eq("estudiante_id", est["id"])
            .order("created_at")
            .execute()
        )
        for conv in (convs.data or []):
            msgs = (
                supabase.table("mensajes")
                .select("rol, contenido, created_at, tokens_input, tokens_output, costo_usd")
                .eq("conversacion_id", conv["id"])
                .order("created_at")
                .execute()
            )
            for m in (msgs.data or []):
                lineas.append(json.dumps({
                    "tipo": "mensaje",
                    "conversacion_id": conv["id"],
                    "estudiante_id": est["id"],
                    "estudiante_nombre": est["nombre"],
                    "asignatura": conv["asignatura"],
                    "conversacion_titulo": conv["titulo"],
                    "conversacion_activa": conv["activa"],
                    "rol": m["rol"],
                    "contenido": m["contenido"],
                    "tokens_input": m.get("tokens_input", 0),
                    "tokens_output": m.get("tokens_output", 0),
                    "costo_usd": str(m.get("costo_usd", 0)),
                    "timestamp": m["created_at"],
                }, ensure_ascii=False))
    return "\n".join(lineas)


def _generar_jsonl_asignatura(asignatura: str, docente_id: str = "") -> str:
    """Genera JSONL para una asignatura específica."""
    supabase = get_supabase()
    convs = (
        supabase.table("conversaciones")
        .select("id, estudiante_id, asignatura, titulo, created_at, activa")
        .eq("asignatura", asignatura)
        .order("created_at")
        .execute()
    )
    lineas = [_linea_metadata(extra={"asignatura": asignatura, "docente_id": docente_id})]
    est_cache = {}
    for conv in (convs.data or []):
        est_id = conv["estudiante_id"]
        if est_id not in est_cache:
            pr = supabase.table("profiles").select("nombre").eq("id", est_id).single().execute()
            est_cache[est_id] = pr.data["nombre"] if pr.data else "?"
        est_nombre = est_cache[est_id]
        msgs = (
            supabase.table("mensajes")
            .select("rol, contenido, created_at, tokens_input, tokens_output, costo_usd")
            .eq("conversacion_id", conv["id"])
            .order("created_at")
            .execute()
        )
        for m in (msgs.data or []):
            lineas.append(json.dumps({
                "tipo": "mensaje",
                "conversacion_id": conv["id"],
                "estudiante_id": est_id,
                "estudiante_nombre": est_nombre,
                "asignatura": conv["asignatura"],
                "conversacion_titulo": conv["titulo"],
                "conversacion_activa": conv["activa"],
                "rol": m["rol"],
                "contenido": m["contenido"],
                "tokens_input": m.get("tokens_input", 0),
                "tokens_output": m.get("tokens_output", 0),
                "costo_usd": str(m.get("costo_usd", 0)),
                "timestamp": m["created_at"],
            }, ensure_ascii=False))
    return "\n".join(lineas)


def _generar_jsonl_conversacion(conv: dict, nombre_est: str, mensajes: list) -> str:
    """Genera JSONL para una sola conversación."""
    lineas = [_linea_metadata(extra={"conversacion_id": conv["id"], "conversacion_titulo": conv.get("titulo", "")})]
    for m in (mensajes or []):
        lineas.append(json.dumps({
            "tipo": "mensaje",
            "conversacion_id": conv["id"],
            "estudiante_id": conv["estudiante_id"],
            "estudiante_nombre": nombre_est,
            "asignatura": conv["asignatura"],
            "conversacion_titulo": conv.get("titulo", ""),
            "conversacion_activa": conv.get("activa", True),
            "rol": m["rol"],
            "contenido": m["contenido"],
            "tokens_input": m.get("tokens_input", 0),
            "tokens_output": m.get("tokens_output", 0),
            "costo_usd": str(m.get("costo_usd", 0)),
            "timestamp": m["created_at"],
        }, ensure_ascii=False))
    return "\n".join(lineas)


def _contar_conversaciones_docente(docente_id: str) -> int:
    supabase = get_supabase()
    resp = supabase.table("conversaciones").select("id", count="exact").execute()
    return resp.count if hasattr(resp, "count") else 0


def _linea_metadata(extra: dict | None = None) -> str:
    obj = {
        "tipo": "metadata",
        "version": "1.0",
        "fecha_exportacion": datetime.datetime.now().isoformat(),
        **(extra or {}),
    }
    return json.dumps(obj, ensure_ascii=False)


def _ofrecer_descarga(jsonl: str, filename: str, label: str = "📥 Descargar"):
    """Muestra botón de descarga para contenido JSONL."""
    if jsonl.strip():
        st.download_button(
            label=label,
            data=jsonl,
            file_name=filename,
            mime="application/x-ndjson",
        )


# ============================================================
# CRUD Helpers
def _confirmar_y_borrar(confirm_key: str, mensaje: str, accion):
    """Confirmación 2 pasos. LLAMAR INCONDICIONALMENTE, no dentro de if st.button."""
    state = st.session_state.get(confirm_key, None)
    if state is None:
        return
    if state is True:
        st.warning(mensaje)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("⚠️ Sí, eliminar", key=f"{confirm_key}_yes"):
                st.session_state[confirm_key] = "execute"
                st.rerun()
        with c2:
            if st.button("Cancelar", key=f"{confirm_key}_no"):
                del st.session_state[confirm_key]
                st.rerun()
    elif state == "execute":
        try:
            accion()
            st.success("Eliminado correctamente.")
        except Exception as e:
            st.error(f"Error al eliminar: {e}")
        finally:
            del st.session_state[confirm_key]
            st.rerun()


def _borrar_grupo(grupo_id: str):
    supabase = get_supabase()
    supabase.table("grupos_estudiantes").delete().eq("grupo_id", grupo_id).execute()
    supabase.table("grupos").delete().eq("id", grupo_id).execute()


def _borrar_conversacion(conv_id: str):
    supabase = get_supabase()
    supabase.table("mensajes").delete().eq("conversacion_id", conv_id).execute()
    supabase.table("conversaciones").delete().eq("id", conv_id).execute()


def _borrar_estudiante(estudiante_id: str):
    """Borra un estudiante y todas sus conversaciones/mensajes."""
    supabase = get_supabase()
    supabase_admin = get_supabase_admin()
    # Borrar mensajes de todas sus conversaciones
    convs = supabase.table("conversaciones").select("id").eq("estudiante_id", estudiante_id).execute()
    for c in (convs.data or []):
        supabase.table("mensajes").delete().eq("conversacion_id", c["id"]).execute()
    # Borrar conversaciones
    supabase.table("conversaciones").delete().eq("estudiante_id", estudiante_id).execute()
    # Borrar membresías en grupos
    supabase.table("grupos_estudiantes").delete().eq("estudiante_id", estudiante_id).execute()
    # Borrar mensajes de docente dirigidos a este estudiante
    supabase.table("mensajes_docente").delete().eq("para_estudiante_id", estudiante_id).execute()
    # Borrar perfil
    supabase.table("profiles").delete().eq("id", estudiante_id).execute()
    # Borrar usuario auth
    try:
        supabase_admin.auth.admin.delete_user(estudiante_id)
    except Exception:
        pass


def _borrar_mensaje_docente(msg_id: str):
    supabase = get_supabase()
    supabase.table("mensajes_docente").delete().eq("id", msg_id).execute()


def _nombre_destino(msg, supabase) -> str:
    if msg.get("para_estudiante_id"):
        p_resp = supabase.table("profiles").select("nombre").eq("id", msg["para_estudiante_id"]).single().execute()
        return p_resp.data["nombre"] if p_resp.data else "?"
    if msg.get("para_grupo_id"):
        g_resp = supabase.table("grupos").select("nombre").eq("id", msg["para_grupo_id"]).single().execute()
        return f"Grupo: {g_resp.data['nombre']}" if g_resp.data else "?"
    return "?"
