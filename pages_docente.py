"""pages_docente.py — Dashboard del docente: estudiantes, grupos, tracking, mensajes, descargas, chat."""
import streamlit as st
import datetime
import json
import uuid
import io
import csv
import random
import string
import pandas as pd
from auth import usuario_actual, get_supabase, get_supabase_admin, crear_usuario_estudiante, _email_con_alias
from rag_engine import GestorAsignaturas
from chat_core import (
    get_modelo_activo,
    inicializar_motor_rag,
    responder,
    crear_conversacion,
    cargar_conversacion_callback,
    nueva_conversacion_callback,
)


def render_dashboard_docente():
    """Punto de entrada del dashboard de docente."""
    usuario = usuario_actual()
    st.title(f"👨‍🏫 Panel Docente")
    st.caption(f"{usuario.nombre} — Profesor")

    # Manejar navegación desde botones "Ver conversaciones"
    tab_idx = _resolver_tab_inicial()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👥 Estudiantes", "👥 Grupos", "📊 Tracking", "📬 Mensajes", "📥 Descargas", "💬 Chat"
    ])

    # Streamlit no permite setear tab activo directamente, usamos query params
    tab_labels = ["👥 Estudiantes", "👥 Grupos", "📊 Tracking", "📬 Mensajes", "📥 Descargas", "💬 Chat"]

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
    with tab6:
        _tab_chat_docente(usuario)


def _resolver_tab_inicial() -> int:
    """Si se clickeó 'Ver conversaciones', redirigir al tab tracking."""
    if st.query_params.get("tab") == "tracking":
        st.query_params.clear()
        # Mostrar aviso de navegación
        st.info("⬇️ Conversaciones cargadas en la pestaña **📊 Tracking** — desplácese hacia abajo para verlas.")
    return 0


def _asignatura_activa(key_prefix: str = "gestion") -> str:
    """Determina la asignatura del deploy. Si hay una sola, la usa; si hay varias, selector."""
    asignaturas = GestorAsignaturas.listar()
    if not asignaturas:
        return ""
    if len(asignaturas) == 1:
        return asignaturas[0]
    opciones = {GestorAsignaturas.nombre_legible(a): a for a in asignaturas}
    sel = st.selectbox("📖 Asignatura", list(opciones.keys()), key=f"sel_asig_{key_prefix}")
    return opciones[sel]


# ============================================================
# Tab: Gestión de Estudiantes
# ============================================================
def _tab_estudiantes(usuario):
    st.subheader("👥 Gestión de Estudiantes")

    asignatura = _asignatura_activa(key_prefix="estudiantes")
    if not asignatura:
        st.info("No hay cursos configurados.")
        return
    st.caption(f"Curso: **{GestorAsignaturas.nombre_legible(asignatura)}** (`{asignatura}`)")

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
                ok, msg = crear_usuario_estudiante(email, password, nombre, usuario.id, asignatura)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Complete todos los campos.")

    # --- Carga masiva de estudiantes ---
    with st.expander("📋 Subir estudiantes (Excel/CSV)", expanded=False):
        st.markdown(
            "Sube un archivo con las columnas **`nombre`**, **`email`** (requeridas) y "
            "**`grupo`** (opcional). Se generarán contraseñas aleatorias para cada estudiante."
        )
        st.markdown(
            "> 📎 [Descargar plantilla vacía](#) — Formato: `nombre`, `email`, `grupo`"
        )

        archivo = st.file_uploader(
            "Seleccionar archivo",
            type=["csv", "xlsx"],
            key="upload_estudiantes",
        )

        if archivo is not None:
            try:
                if archivo.name.endswith(".csv"):
                    df = pd.read_csv(archivo, dtype=str).fillna("")
                else:
                    df = pd.read_excel(archivo, dtype=str).fillna("")
            except Exception as e:
                st.error(f"❌ Error al leer el archivo: {e}")
                df = None

            if df is not None and not df.empty:
                # Normalizar columnas
                df.columns = [c.strip().lower() for c in df.columns]
                requeridas = {"nombre", "email"}
                faltantes = requeridas - set(df.columns)
                if faltantes:
                    st.error(f"❌ Faltan columnas requeridas: {', '.join(faltantes)}. Columnas detectadas: {', '.join(df.columns)}")
                else:
                    st.success(f"✅ {len(df)} estudiantes detectados")
                    st.dataframe(df[["nombre", "email"] + (["grupo"] if "grupo" in df.columns else [])], use_container_width=True)

                    if st.button("🚀 Crear todos los estudiantes", type="primary", key="btn_crear_masivo"):
                        resultados = []
                        credenciales = []
                        bar = st.progress(0, text="Creando estudiantes...")
                        total = len(df)
                        for i, row in df.iterrows():
                            nombre = str(row["nombre"]).strip()
                            email = str(row["email"]).strip()
                            grupo = str(row.get("grupo", "")).strip()
                            password = _generar_password()
                            ok, msg = crear_usuario_estudiante(email, password, nombre, usuario.id, asignatura)
                            email_efectivo = _email_con_alias(email, asignatura)
                            resultados.append({"nombre": nombre, "email": email_efectivo, "ok": ok, "msg": msg, "password": password, "grupo": grupo})
                            credenciales.append({"nombre": nombre, "email": email_efectivo, "password": password, "grupo": grupo})
                            bar.progress((i + 1) / total, text=f"{i + 1}/{total}: {nombre}")

                        bar.empty()
                        creados = sum(1 for r in resultados if r["ok"])
                        fallidos = total - creados

                        if creados > 0:
                            st.success(f"✅ {creados} estudiantes creados correctamente.")
                        if fallidos > 0:
                            st.warning(f"⚠️ {fallidos} errores (estudiantes que quizás ya existen).")

                        # Mostrar tabla de resultados
                        res_df = pd.DataFrame(resultados)
                        st.dataframe(
                            res_df[["nombre", "email", "ok", "msg"]].rename(
                                columns={"ok": "Éxito", "msg": "Mensaje"}
                            ),
                            use_container_width=True,
                        )

                        # Ofrecer descarga de credenciales
                        csv_buf = io.StringIO()
                        writer = csv.writer(csv_buf)
                        writer.writerow(["nombre", "email", "password", "grupo"])
                        for c in credenciales:
                            writer.writerow([c["nombre"], c["email"], c["password"], c["grupo"]])
                        csv_data = csv_buf.getvalue()

                        st.download_button(
                            label="📥 Descargar credenciales (CSV)",
                            data=csv_data,
                            file_name=f"credenciales_estudiantes_{datetime.date.today().isoformat()}.csv",
                            mime="text/csv",
                        )

                        # Guardar en session_state para la pestaña de descargas
                        st.session_state._ultimas_credenciales = credenciales
                        st.session_state._ultima_fecha_credenciales = datetime.date.today().isoformat()

    # --- Lista de estudiantes (solo los del docente y del curso actual) ---
    st.subheader("📋 Lista de estudiantes")
    supabase = get_supabase()
    resp = (
        supabase.table("profiles")
        .select("id, email, nombre, created_at")
        .eq("rol", "estudiante")
        .eq("creado_por", usuario.id)
        .eq("asignatura", asignatura)
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
                    lambda pid=p["id"]: _borrar_estudiante(pid, usuario.id),
                )


# ============================================================
# Tab: Gestión de Grupos
# ============================================================
def _tab_grupos(usuario):
    st.subheader("👥 Grupos de Trabajo")
    supabase = get_supabase()

    asignatura = _asignatura_activa(key_prefix="grupos")
    if not asignatura:
        st.info("No hay cursos configurados.")
        return

    # Solo estudiantes del docente y del curso actual
    estudiantes = (
        supabase.table("profiles")
        .select("id, nombre, email")
        .eq("rol", "estudiante")
        .eq("creado_por", usuario.id)
        .eq("asignatura", asignatura)
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
            st.text_input(
                "Asignatura",
                value=asignatura,
                disabled=True,
                key="nuevo_grupo_asignatura",
            )
        desc_grp = st.text_area("Descripción", key="nuevo_grupo_desc")
        if not mapa_estudiantes:
            st.info("No tiene estudiantes en este curso. Cree estudiantes primero en la pestaña **👥 Estudiantes**.")
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
                    "asignatura": asignatura,
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
        mis_estudiantes = _estudiantes_del_docente(usuario.id, supabase)
        mapa_est = {e["nombre"]: e["id"] for e in mis_estudiantes}
        if not mapa_est:
            st.info("👥 Aún no tienes grupos con estudiantes. Crea un grupo en la pestaña **👥 Grupos** para hacer seguimiento.")
            return

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

    # --- Estudiantes disponibles (solo los del docente) ---
    mis_estudiantes = _estudiantes_del_docente(usuario.id, supabase)
    mapa_est = {e["nombre"]: e for e in mis_estudiantes}

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

    # --- Asignaturas de los grupos del docente ---
    st.divider()
    st.markdown("**Por asignatura**")
    grupos = supabase.table("grupos").select("asignatura").eq("creado_por", usuario.id).execute()
    asigs = sorted(set(g["asignatura"] for g in (grupos.data or []) if g["asignatura"]))

    if asigs:
        col_asig, _ = st.columns([2, 4])
        with col_asig:
            asig_sel = st.selectbox("Asignatura", asigs, key="dl_asignatura")
            if st.button("📥 Descargar asignatura (JSONL)", key="btn_dl_asignatura"):
                jsonl = _generar_jsonl_asignatura(asig_sel, usuario.id)
                _ofrecer_descarga(jsonl, f"asignatura_{asig_sel}.jsonl")

    # --- Lista de estudiantes (CSV con claves) ---
    st.divider()
    st.subheader("🧑‍🤝‍🧑 Lista de estudiantes con credenciales")
    creds_disponibles = (
        st.session_state.get("_ultimas_credenciales") is not None
        or st.button("🔍 Generar lista de estudiantes", key="btn_gen_lista_est")
    )
    if creds_disponibles:
        # Si hay credenciales de la última carga masiva, usarlas
        if st.session_state.get("_ultimas_credenciales"):
            fecha = st.session_state.get("_ultima_fecha_credenciales", "?")
            st.info(f"📋 Credenciales de la carga masiva del {fecha}")
            csv_buf = io.StringIO()
            writer = csv.writer(csv_buf)
            writer.writerow(["nombre", "email", "password", "grupo"])
            for c in st.session_state._ultimas_credenciales:
                writer.writerow([c["nombre"], c["email"], c["password"], c["grupo"]])
            st.download_button(
                label="📥 Descargar credenciales (CSV)",
                data=csv_buf.getvalue(),
                file_name=f"credenciales_estudiantes_{fecha}.csv",
                mime="text/csv",
            )
        else:
            # Generar desde DB (sin passwords — no se almacenan)
            supabase = get_supabase()
            est_resp = (
                supabase.table("profiles")
                .select("nombre, email, created_at")
                .eq("rol", "estudiante")
                .order("nombre")
                .execute()
            )
            if est_resp.data:
                csv_buf = io.StringIO()
                writer = csv.writer(csv_buf)
                writer.writerow(["nombre", "email", "password", "fecha_registro"])
                for e in est_resp.data:
                    writer.writerow([
                        e["nombre"], e["email"],
                        "— (solo disponible al crear)",
                        e.get("created_at", "")[:10] if e.get("created_at") else "",
                    ])
                st.download_button(
                    label="📥 Descargar lista de estudiantes (CSV)",
                    data=csv_buf.getvalue(),
                    file_name=f"lista_estudiantes_{datetime.date.today().isoformat()}.csv",
                    mime="text/csv",
                )
                st.caption("💡 Las contraseñas solo se muestran al crear los estudiantes. Para estudiantes ya existentes, use 'Restablecer contraseña'.")
            else:
                st.info("No hay estudiantes registrados.")

    # --- Lista de grupos con estudiantes ---
    st.divider()
    st.subheader("👥 Grupos con estudiantes")
    if st.button("📥 Descargar lista de grupos (CSV)", key="btn_dl_grupos_csv"):
        supabase = get_supabase()
        grupos_resp = (
            supabase.table("grupos")
            .select("id, nombre, asignatura, descripcion")
            .eq("creado_por", usuario.id)
            .order("nombre")
            .execute()
        )
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["grupo", "asignatura", "estudiante_nombre", "estudiante_email"])
        for g in (grupos_resp.data or []):
            miembros = (
                supabase.table("grupos_estudiantes")
                .select("estudiante_id, profiles!estudiante_id(nombre, email)")
                .eq("grupo_id", g["id"])
                .execute()
            )
            for m in (miembros.data or []):
                p = m.get("profiles", {})
                if isinstance(p, dict):
                    writer.writerow([g["nombre"], g.get("asignatura", ""), p.get("nombre", "?"), p.get("email", "?")])
                else:
                    writer.writerow([g["nombre"], g.get("asignatura", ""), "?", "?"])
        _ofrecer_descarga(csv_buf.getvalue(), f"grupos_estudiantes_{datetime.date.today().isoformat()}.csv", "📥 Descargar grupos (CSV)")

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
def _estudiantes_del_docente(docente_id: str, supabase) -> list[dict]:
    """Retorna lista de estudiantes que pertenecen a grupos creados por el docente."""
    grupos = supabase.table("grupos").select("id").eq("creado_por", docente_id).execute()
    grupo_ids = [g["id"] for g in (grupos.data or [])]
    if not grupo_ids:
        return []
    miembros = (
        supabase.table("grupos_estudiantes")
        .select("estudiante_id, profiles!estudiante_id(id, nombre)")
        .in_("grupo_id", grupo_ids)
        .execute()
    )
    estudiantes = []
    vistos = set()
    for m in (miembros.data or []):
        p = m.get("profiles", {})
        if isinstance(p, dict) and p.get("id") and p["id"] not in vistos:
            vistos.add(p["id"])
            estudiantes.append({"id": p["id"], "nombre": p.get("nombre", "?")})
    return estudiantes


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
    """Genera JSONL con todas las conversaciones de los estudiantes del docente."""
    supabase = get_supabase()
    estudiantes = _estudiantes_del_docente(docente_id, supabase)
    lineas = [_linea_metadata(extra={"docente_id": docente_id})]
    for est in estudiantes:
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
    estudiantes = _estudiantes_del_docente(docente_id, supabase) if docente_id else None
    est_ids = set(e["id"] for e in estudiantes) if estudiantes else None
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
        if est_ids is not None and est_id not in est_ids:
            continue
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
    estudiantes = _estudiantes_del_docente(docente_id, supabase)
    if not estudiantes:
        return 0
    est_ids = [e["id"] for e in estudiantes]
    resp = supabase.table("conversaciones").select("id", count="exact").in_("estudiante_id", est_ids).execute()
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


def _borrar_estudiante(estudiante_id: str, docente_id: str = ""):
    """Borra un estudiante y todas sus conversaciones/mensajes (solo si pertenece al docente)."""
    supabase = get_supabase()
    supabase_admin = get_supabase_admin()

    # Verificación de pertenencia (defensa en profundidad)
    if docente_id:
        perfil = supabase.table("profiles").select("creado_por").eq("id", estudiante_id).single().execute()
        if perfil.data and perfil.data.get("creado_por") and perfil.data["creado_por"] != docente_id:
            raise PermissionError("No tiene permiso para borrar este estudiante.")

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


def _generar_password(length: int = 10) -> str:
    """Genera una contraseña aleatoria alfanumérica fácil de leer (sin confusos)."""
    chars = ''.join(c for c in string.ascii_letters + string.digits if c not in '0O1Il')
    return ''.join(random.choice(chars) for _ in range(length))


# ============================================================
# Tab: Chat (docente prueba el tutor)
# ============================================================
def _tab_chat_docente(usuario):
    st.subheader("💬 Chat con el Tutor")

    asignaturas = GestorAsignaturas.listar()
    if not asignaturas:
        st.info("No hay cursos configurados.")
        return

    opciones = {GestorAsignaturas.nombre_legible(a): a for a in asignaturas}
    sel = st.selectbox("📖 Asignatura", list(opciones.keys()), key="sel_asig_doc")
    asignatura = opciones[sel]

    modelo_actual = get_modelo_activo()
    st.caption(f"🧠 Modelo: **{modelo_actual}**")

    chat_key = f"chat_doc_{asignatura}"
    st.session_state.setdefault(f"{chat_key}_msgs", [])
    st.session_state.setdefault(f"{chat_key}_sid", uuid.uuid4().hex[:12])
    st.session_state.setdefault(f"{chat_key}_conv_id", None)

    col_hist, col_chat = st.columns([1, 3])

    with col_hist:
        st.markdown("**📋 Historial**")
        supabase = get_supabase()
        convs_resp = (
            supabase.table("conversaciones")
            .select("id,titulo,created_at")
            .eq("estudiante_id", usuario.id)
            .eq("asignatura", asignatura)
            .order("created_at", desc=True)
            .limit(30)
            .execute()
        )

        st.button(
            "➕ Nueva conversación",
            key=f"nueva_conv_doc_{asignatura}",
            on_click=nueva_conversacion_callback,
            args=(chat_key,),
            use_container_width=True,
        )

        if convs_resp.data:
            for c in convs_resp.data:
                label = f"{c['titulo'][:40]} — {c['created_at'][:10]}"
                activo = st.session_state.get(f"{chat_key}_conv_id") == c["id"]
                prefix = "▸ " if activo else ""
                st.button(
                    f"{prefix}{label}",
                    key=f"load_conv_doc_{c['id']}",
                    on_click=cargar_conversacion_callback,
                    args=(c["id"], chat_key),
                    use_container_width=True,
                    type="primary" if activo else "secondary",
                )
        else:
            st.caption("Sin conversaciones aún.")

    with col_chat:
        messages = st.session_state[f"{chat_key}_msgs"]
        session_id = st.session_state[f"{chat_key}_sid"]
        motor = inicializar_motor_rag(asignatura)

        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Escribe tu pregunta...", key=f"chat_in_doc_{asignatura}"):
            messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    old_msgs = st.session_state.get("messages")
                    old_sid = st.session_state.get("session_id")
                    st.session_state.messages = messages
                    st.session_state.session_id = session_id

                    if f"activa_{chat_key}" not in st.session_state:
                        st.session_state.conversacion_activa = crear_conversacion(usuario, asignatura)
                        st.session_state[f"activa_{chat_key}"] = True

                    responder(prompt, motor, asignatura, usuario)
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    import traceback
                    with st.expander("🔍 Detalles"):
                        st.code(traceback.format_exc())
                finally:
                    st.session_state[f"{chat_key}_msgs"] = st.session_state.messages
                    st.session_state[f"{chat_key}_sid"] = st.session_state.session_id
                    if old_msgs is not None:
                        st.session_state.messages = old_msgs
                        st.session_state.session_id = old_sid
