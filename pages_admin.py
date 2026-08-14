"""pages_admin.py — Panel de administración: docentes, modelos, logs, sistema, chat."""
import streamlit as st
import datetime
import json
import uuid
from auth import usuario_actual, get_supabase, get_supabase_admin, crear_usuario_docente
from config import MODELOS_DISPONIBLES, MODELO_POR_DEFECTO
from rag_engine import GestorAsignaturas
from chat_core import (
    get_modelo_activo,
    inicializar_motor_rag,
    responder,
    crear_conversacion,
    cargar_conversacion_callback,
    nueva_conversacion_callback,
)


def render_dashboard_admin():
    """Punto de entrada del dashboard de administrador."""
    usuario = usuario_actual()
    st.title(f"⚙️ Panel de Administración")
    st.caption(f"{usuario.nombre} — Administrador del Sistema")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "👨‍🏫 Docentes", "👥 Estudiantes", "🧠 Modelos", "📊 Estadísticas", "📥 Datos", "💬 Chat"
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
    with tab6:
        _tab_chat_admin(usuario)


# ============================================================
# Tab: Gestión de Docentes
# ============================================================
def _tab_docentes():
    st.subheader("👨‍🏫 Gestión de Docentes")
    supabase = get_supabase()
    cursos_disponibles = _cursos_conocidos(supabase)

    # --- Crear docente ---
    with st.expander("➕ Registrar nuevo docente", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            nombre = st.text_input("Nombre completo", key="admin_nuevo_docente_nombre")
        with col2:
            email = st.text_input("Email institucional", key="admin_nuevo_docente_email")
        with col3:
            password = st.text_input("Contraseña inicial", type="password", key="admin_nuevo_docente_pass")

        cursos_sel = st.multiselect(
            "Cursos asignados",
            options=cursos_disponibles,
            format_func=GestorAsignaturas.nombre_legible,
            key="admin_nuevo_docente_cursos",
        )

        if st.button("Crear docente", type="primary"):
            if nombre and email and password:
                ok, msg = crear_usuario_docente(email, password, nombre)
                if ok:
                    resp_doc = supabase.table("profiles").select("id").eq("email", email.strip().lower()).single().execute()
                    if resp_doc.data:
                        doc_id = resp_doc.data["id"]
                        for curso in cursos_sel:
                            try:
                                _asignar_curso_docente(doc_id, curso)
                            except Exception:
                                pass
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Complete todos los campos.")

    # --- Lista de docentes ---
    st.subheader("📋 Docentes registrados")
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

    for p in resp.data:
        grupos = (
            supabase.table("grupos")
            .select("id", count="exact")
            .eq("creado_por", p["id"])
            .execute()
        )
        n_grupos = grupos.count if hasattr(grupos, "count") else 0
        cursos_doc = _cursos_del_docente(p["id"], supabase)

        with st.expander(f"👨‍🏫 {p['nombre']} — {p['email']} — {n_grupos} grupos"):
            st.caption(f"ID: {p['id']}")
            st.caption(f"Registrado: {p.get('created_at', '?')}")

            st.markdown("**📖 Cursos asignados:**")
            if cursos_doc:
                for c in sorted(cursos_doc):
                    col_c, col_q = st.columns([6, 1])
                    with col_c:
                        st.markdown(f"- {GestorAsignaturas.nombre_legible(c)} (`{c}`)")
                    with col_q:
                        if st.button("✖️", key=f"quitar_curso_{p['id']}_{c}", help="Quitar curso"):
                            _quitar_curso_docente(p["id"], c)
                            st.rerun()
            else:
                st.caption("Ninguno")

            no_asignados = [c for c in cursos_disponibles if c not in cursos_doc]
            if no_asignados:
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    nuevo_curso = st.selectbox(
                        "Añadir curso",
                        options=no_asignados,
                        format_func=GestorAsignaturas.nombre_legible,
                        key=f"add_curso_{p['id']}",
                    )
                with col_b:
                    st.write("")
                    st.write("")
                    if st.button("➕", key=f"btn_add_curso_{p['id']}", help="Añadir curso"):
                        _asignar_curso_docente(p["id"], nuevo_curso)
                        st.rerun()

            st.divider()
            if st.button("🗑️ Eliminar docente", key=f"del_doc_{p['id']}", type="secondary"):
                st.session_state[f"cf_adm_doc_{p['id']}"] = True
                st.rerun()
            _confirmar_y_borrar(
                f"cf_adm_doc_{p['id']}",
                f"¿Eliminar a {p['nombre']}? Se perderán sus grupos y mensajes.",
                lambda pid=p["id"]: _borrar_perfil(pid, "docente"),
            )


def _cursos_conocidos(supabase) -> list[str]:
    """Lista de cursos conocidos: carpeta asignaturas + docente_cursos + profiles.asignatura."""
    cursos = set(GestorAsignaturas.listar())
    dc = supabase.table("docente_cursos").select("asignatura").execute()
    for r in (dc.data or []):
        if r.get("asignatura"):
            cursos.add(r["asignatura"])
    pr = supabase.table("profiles").select("asignatura").execute()
    for r in (pr.data or []):
        if r.get("asignatura"):
            cursos.add(r["asignatura"])
    cursos.discard("")
    return sorted(cursos)


def _cursos_del_docente(docente_id: str, supabase) -> list[str]:
    resp = supabase.table("docente_cursos").select("asignatura").eq("docente_id", docente_id).execute()
    return [r["asignatura"] for r in (resp.data or [])]


def _asignar_curso_docente(docente_id: str, asignatura: str):
    supabase = get_supabase_admin()
    supabase.table("docente_cursos").insert({
        "docente_id": docente_id,
        "asignatura": asignatura,
    }).execute()


def _quitar_curso_docente(docente_id: str, asignatura: str):
    supabase = get_supabase_admin()
    supabase.table("docente_cursos").delete().eq("docente_id", docente_id).eq("asignatura", asignatura).execute()


# ============================================================
# Tab: Gestión de Estudiantes (Admin)
# ============================================================
def _tab_estudiantes():
    st.subheader("👥 Gestión de Estudiantes")
    supabase = get_supabase()

    # Mapa docente_id -> nombre
    docentes = supabase.table("profiles").select("id, nombre").eq("rol", "docente").order("nombre").execute()
    mapa_docentes = {d["id"]: d["nombre"] for d in (docentes.data or [])}

    resp = (
        supabase.table("profiles")
        .select("id, email, nombre, creado_por, asignatura, created_at")
        .eq("rol", "estudiante")
        .order("nombre")
        .execute()
    )
    estudiantes = resp.data or []

    if not estudiantes:
        st.info("No hay estudiantes registrados.")
        return

    st.caption(f"{len(estudiantes)} estudiantes encontrados")

    huerfanos = [p for p in estudiantes if not p.get("creado_por") or not p.get("asignatura")]
    asignados = [p for p in estudiantes if p.get("creado_por") and p.get("asignatura")]

    # --- Estudiantes sin asignar ---
    if huerfanos:
        st.subheader(f"🔧 Sin asignar ({len(huerfanos)})")
        st.caption("Estudiantes sin curso/docente. Reasígnelos a continuación.")
        _render_reasignacion(huerfanos, mapa_docentes)

    # --- Agrupados por curso → docente ---
    st.subheader("📚 Por curso")
    if not asignados:
        st.info("No hay estudiantes asignados a un curso todavía.")
        return

    por_curso = {}
    for p in asignados:
        por_curso.setdefault(p["asignatura"], []).append(p)

    for asignatura in sorted(por_curso.keys()):
        grupo = por_curso[asignatura]
        with st.expander(f"📖 {GestorAsignaturas.nombre_legible(asignatura)} (`{asignatura}`) — {len(grupo)} estudiantes"):
            por_docente = {}
            for p in grupo:
                por_docente.setdefault(p["creado_por"], []).append(p)
            for doc_id in sorted(por_docente.keys()):
                lista = por_docente[doc_id]
                doc_nombre = mapa_docentes.get(doc_id, "Docente desconocido")
                st.markdown(f"**👨‍🏫 {doc_nombre}** — {len(lista)} estudiantes")
                for p in lista:
                    _render_estudiante_admin(p)


def _render_estudiante_admin(p):
    supabase = get_supabase()
    convs = supabase.table("conversaciones").select("id", count="exact").eq("estudiante_id", p["id"]).execute()
    n_convs = convs.count if hasattr(convs, "count") else 0
    with st.expander(f"🧑 {p['nombre']} — {p['email']} — {n_convs} conv."):
        st.caption(f"Registrado: {p.get('created_at', '?')}")
        if st.button("🗑️ Eliminar estudiante", key=f"del_est_{p['id']}", type="secondary"):
            st.session_state[f"cf_adm_est_{p['id']}"] = True
            st.rerun()
        _confirmar_y_borrar(
            f"cf_adm_est_{p['id']}",
            f"¿Eliminar a {p['nombre']} y todas sus conversaciones?",
            lambda pid=p["id"]: _borrar_perfil(pid, "estudiante"),
        )


def _render_reasignacion(huerfanos, mapa_docentes):
    supabase = get_supabase()
    nombres_doc = list(mapa_docentes.values())
    asigs = set(GestorAsignaturas.listar())
    for p in huerfanos:
        if p.get("asignatura"):
            asigs.add(p["asignatura"])
    asigs.discard("")
    asigs_ordenadas = sorted(asigs)

    for p in huerfanos:
        with st.expander(f"🧑 {p['nombre']} — {p['email']}"):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                doc_sel = st.selectbox("Docente", ["(Seleccionar)"] + nombres_doc, key=f"rea_doc_{p['id']}")
            with col2:
                asig_sel = st.selectbox("Curso", asigs_ordenadas, key=f"rea_asig_{p['id']}")
            with col3:
                st.write("")
                st.write("")
                if doc_sel != "(Seleccionar)" and st.button("Asignar", key=f"rea_btn_{p['id']}"):
                    doc_id = next((k for k, v in mapa_docentes.items() if v == doc_sel), None)
                    if doc_id:
                        _reasignar_estudiante(p["id"], doc_id, asig_sel)
                        st.success("Reasignado correctamente.")
                        st.rerun()


def _reasignar_estudiante(estudiante_id: str, docente_id: str, asignatura: str):
    supabase = get_supabase_admin()
    supabase.table("profiles").update({
        "creado_por": docente_id,
        "asignatura": asignatura,
    }).eq("id", estudiante_id).execute()


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
    st.subheader("📥 Datos: Descargar, Cargar, Limpiar")

    # ─── Exportar ───
    with st.expander("📤 Exportar todo (JSONL)", expanded=True):
        st.caption("Descarga TODAS las conversaciones del sistema en formato JSONL. Cada línea es un mensaje con metadatos completos.")
        st.caption("El archivo puede ser leído por agentes IA para análisis posteriores.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Descargar TODO (JSONL)", type="primary", use_container_width=True):
                jsonl = _generar_jsonl_admin()
                st.download_button(
                    label="💾 Guardar archivo",
                    data=jsonl,
                    file_name=f"backup_completo_{datetime.date.today().isoformat()}.jsonl",
                    mime="application/x-ndjson",
                )

        with col2:
            if st.button("📥 Descargar solo mensajes (JSONL)", use_container_width=True):
                jsonl = _generar_jsonl_mensajes()
                st.download_button(
                    label="💾 Guardar archivo",
                    data=jsonl,
                    file_name=f"mensajes_{datetime.date.today().isoformat()}.jsonl",
                    mime="application/x-ndjson",
                )

    # ─── Importar / Restaurar ───
    with st.expander("📥 Importar / Restaurar conversaciones (JSONL)"):
        st.caption("Sube un archivo JSONL exportado previamente. Se restaurarán las conversaciones y mensajes en la base de datos.")
        st.warning("⚠️ Esto **agrega** datos — no reemplaza los existentes. Úselo para restaurar backups o migrar datos.")

        uploaded = st.file_uploader("Archivo JSONL", type=["jsonl", "json", "txt"], key="admin_upload")
        if uploaded is not None:
            contenido = uploaded.read().decode("utf-8")
            lineas = contenido.strip().split("\n")
            st.info(f"{len(lineas)} líneas detectadas. La primera debe ser metadata.")

            if st.button("🔄 Restaurar datos", type="primary"):
                with st.spinner("Restaurando..."):
                    ok, errores = _restaurar_desde_jsonl(lineas)
                if errores:
                    st.warning(f"Restaurado parcialmente: {ok} mensajes insertados, {len(errores)} errores.")
                    with st.expander("Ver errores"):
                        for e in errores[:20]:
                            st.caption(str(e)[:200])
                else:
                    st.success(f"✅ {ok} mensajes restaurados correctamente.")

    # ─── Limpiar ───
    with st.expander("🧹 Limpiar datos"):
        supabase = get_supabase()

        st.markdown("**Limpiar logs antiguos**")
        dias_logs = st.number_input("Eliminar logs con más de N días", min_value=1, value=90, key="admin_dias_logs")
        if st.button("🗑️ Borrar logs antiguos", key="btn_clean_logs"):
            try:
                cutoff = f"{(datetime.date.today() - datetime.timedelta(days=dias_logs)).isoformat()}T00:00:00"
                supabase.table("logs_sesiones").delete().lt("timestamp", cutoff).execute()
                st.success(f"Logs anteriores a {cutoff[:10]} eliminados.")
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("**Limpiar conversaciones antiguas**")
        dias_conv = st.number_input("Eliminar conversaciones con más de N días", min_value=1, value=180, key="admin_dias_conv")
        if st.button("🗑️ Borrar conversaciones antiguas", key="btn_clean_conv"):
            try:
                cutoff = f"{(datetime.date.today() - datetime.timedelta(days=dias_conv)).isoformat()}T00:00:00"
                supabase.table("conversaciones").delete().lt("updated_at", cutoff).execute()
                st.success(f"Conversaciones anteriores a {cutoff[:10]} eliminadas.")
            except Exception as e:
                st.error(f"Error: {e}")

        st.markdown("**Limpiar asignatura completa**")
        asigs_resp = supabase.table("conversaciones").select("asignatura").execute()
        asigs = sorted(set(c["asignatura"] for c in (asigs_resp.data or []) if c["asignatura"]))
        if asigs:
            asig_sel = st.selectbox("Asignatura a limpiar", asigs, key="admin_asig_clean")
            if st.button("🗑️ Borrar TODAS las conversaciones de esta asignatura", key="btn_clean_asig", type="secondary"):
                st.session_state["cf_adm_asig"] = True
                st.rerun()
            _confirmar_y_borrar(
                "cf_adm_asig",
                f"¿Eliminar TODAS las conversaciones de {asig_sel}?",
                lambda: _borrar_asignatura(asig_sel),
            )
        else:
            st.info("No hay asignaturas con conversaciones.")

    # ─── Config del sistema ───
    with st.expander("🛡️ Configuración del Sistema"):
        supabase = get_supabase()
        configs = supabase.table("config_sistema").select("*").order("id").execute()
        if not configs.data:
            st.info("No hay configuraciones del sistema.")
        else:
            for c in configs.data:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{c['clave']}** = `{c['valor']}` — {c.get('descripcion', '')}")
                with col2:
                    nuevo_valor = st.text_input("Nuevo", value=c["valor"], key=f"cfg_{c['id']}", label_visibility="collapsed")
                if nuevo_valor != c["valor"] and st.button("✏️ Guardar", key=f"save_cfg_{c['id']}"):
                    try:
                        supabase.table("config_sistema").update({"valor": nuevo_valor}).eq("id", c["id"]).execute()
                        st.success(f"{c['clave']} → {nuevo_valor}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# Helpers
# ============================================================
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


def _borrar_perfil(perfil_id: str, rol: str):
    """Borra un perfil y toda su data asociada, con cascada."""
    supabase_admin = get_supabase_admin()
    supabase = get_supabase()

    if rol == "docente":
        # 1. Encontrar todos los estudiantes en grupos de este docente
        grupos = supabase.table("grupos").select("id").eq("creado_por", perfil_id).execute()
        estudiantes_a_borrar = set()
        for g in (grupos.data or []):
            miembros = supabase.table("grupos_estudiantes").select("estudiante_id").eq("grupo_id", g["id"]).execute()
            for m in (miembros.data or []):
                estudiantes_a_borrar.add(m["estudiante_id"])
        # 2. Borrar cada estudiante encontrado (cascada)
        for est_id in estudiantes_a_borrar:
            try:
                _borrar_perfil(est_id, "estudiante")
            except Exception:
                pass
        # 3. Borrar grupos del docente
        for g in (grupos.data or []):
            try:
                supabase_admin.table("grupos_estudiantes").delete().eq("grupo_id", g["id"]).execute()
                supabase_admin.table("grupos").delete().eq("id", g["id"]).execute()
            except Exception:
                pass
        # 4. Borrar mensajes enviados por el docente
        try:
            supabase_admin.table("mensajes_docente").delete().eq("de_usuario_id", perfil_id).execute()
        except Exception:
            pass

    elif rol == "estudiante":
        # Borrar conversaciones y mensajes del estudiante
        tablas = ["mensajes", "conversaciones", "grupos_estudiantes", "mensajes_docente", "logs_sesiones"]
        for tabla in tablas:
            col = _columna_por_tabla(tabla, rol)
            if col:
                try:
                    supabase_admin.table(tabla).delete().eq(col, perfil_id).execute()
                except Exception:
                    pass

    # Borrar perfil
    try:
        supabase_admin.table("profiles").delete().eq("id", perfil_id).execute()
    except Exception:
        pass
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


# ============================================================
# Helpers de exportación / importación JSONL
# ============================================================
def _generar_jsonl_admin() -> str:
    """Exporta TODAS las conversaciones del sistema con metadatos completos."""
    supabase = get_supabase()
    lineas = [json.dumps({
        "tipo": "metadata",
        "version": "1.0",
        "fecha_exportacion": datetime.datetime.now().isoformat(),
        "origen": "admin_export",
    }, ensure_ascii=False)]

    estudiantes = supabase.table("profiles").select("id, nombre, email").eq("rol", "estudiante").execute()
    for est in (estudiantes.data or []):
        convs = supabase.table("conversaciones").select("*").eq("estudiante_id", est["id"]).order("created_at").execute()
        for conv in (convs.data or []):
            msgs = supabase.table("mensajes").select("*").eq("conversacion_id", conv["id"]).order("created_at").execute()
            for m in (msgs.data or []):
                lineas.append(json.dumps({
                    "tipo": "mensaje",
                    "conversacion_id": conv["id"],
                    "estudiante_id": est["id"],
                    "estudiante_nombre": est["nombre"],
                    "estudiante_email": est["email"],
                    "asignatura": conv.get("asignatura", ""),
                    "conversacion_titulo": conv.get("titulo", ""),
                    "conversacion_activa": conv.get("activa", True),
                    "grupo_id": conv.get("grupo_id"),
                    "rol": m["rol"],
                    "contenido": m["contenido"],
                    "tokens_input": m.get("tokens_input", 0),
                    "tokens_output": m.get("tokens_output", 0),
                    "costo_usd": str(m.get("costo_usd", 0)),
                    "timestamp": m["created_at"],
                }, ensure_ascii=False))

    # Incluir también perfiles para referencia
    for est in (estudiantes.data or []):
        lineas.append(json.dumps({
            "tipo": "perfil",
            "estudiante_id": est["id"],
            "estudiante_nombre": est["nombre"],
            "estudiante_email": est["email"],
        }, ensure_ascii=False))

    return "\n".join(lineas)


def _generar_jsonl_mensajes() -> str:
    """Exporta SOLO los mensajes (sin perfiles), más ligero."""
    supabase = get_supabase()
    lineas = [json.dumps({
        "tipo": "metadata",
        "version": "1.0",
        "fecha_exportacion": datetime.datetime.now().isoformat(),
        "origen": "admin_mensajes_export",
    }, ensure_ascii=False)]

    # Cache de nombres
    nombres = {}
    msgs = supabase.table("mensajes").select("*, conversaciones!inner(estudiante_id, asignatura, titulo, activa)").order("created_at").limit(10000).execute()

    for m in (msgs.data or []):
        conv = m.get("conversaciones", {})
        est_id = conv.get("estudiante_id", "") if isinstance(conv, dict) else ""
        if est_id and est_id not in nombres:
            pr = supabase.table("profiles").select("nombre").eq("id", est_id).single().execute()
            nombres[est_id] = pr.data["nombre"] if pr.data else "?"
        lineas.append(json.dumps({
            "tipo": "mensaje",
            "conversacion_id": m.get("conversacion_id", ""),
            "estudiante_id": est_id,
            "estudiante_nombre": nombres.get(est_id, "?"),
            "asignatura": conv.get("asignatura", "") if isinstance(conv, dict) else "",
            "conversacion_titulo": conv.get("titulo", "") if isinstance(conv, dict) else "",
            "rol": m["rol"],
            "contenido": m["contenido"],
            "tokens_input": m.get("tokens_input", 0),
            "tokens_output": m.get("tokens_output", 0),
            "costo_usd": str(m.get("costo_usd", 0)),
            "timestamp": m["created_at"],
        }, ensure_ascii=False))
    return "\n".join(lineas)


def _restaurar_desde_jsonl(lineas: list[str]) -> tuple[int, list]:
    """Restaura conversaciones desde un archivo JSONL. Retorna (ok_count, errores)."""
    supabase_admin = get_supabase_admin()
    ok = 0
    errores = []

    # Mapa de conversaciones ya creadas: clave -> conv_id
    convs_creadas = {}

    for i, linea in enumerate(lineas):
        try:
            obj = json.loads(linea.strip())
        except json.JSONDecodeError:
            continue

        if obj.get("tipo") != "mensaje":
            continue

        try:
            est_id = obj.get("estudiante_id", "")
            conv_id_orig = obj.get("conversacion_id", "")
            asignatura = obj.get("asignatura", "")

            # Crear conversación si no existe (usar clave compuesta para dedup)
            conv_key = f"{est_id}:{conv_id_orig}:{asignatura}"
            if conv_key not in convs_creadas:
                # Verificar si ya existe en DB
                existing = supabase_admin.table("conversaciones").select("id").eq("id", conv_id_orig).execute()
                if existing.data:
                    convs_creadas[conv_key] = conv_id_orig
                else:
                    resp = supabase_admin.table("conversaciones").insert({
                        "id": conv_id_orig,
                        "estudiante_id": est_id,
                        "asignatura": asignatura,
                        "titulo": obj.get("conversacion_titulo", "Importada"),
                        "activa": obj.get("conversacion_activa", False),
                    }).execute()
                    if resp.data:
                        convs_creadas[conv_key] = resp.data[0]["id"]
                    else:
                        convs_creadas[conv_key] = conv_id_orig

            nuevo_conv_id = convs_creadas.get(conv_key, conv_id_orig)

            # Insertar mensaje
            supabase_admin.table("mensajes").insert({
                "conversacion_id": nuevo_conv_id,
                "rol": obj["rol"],
                "contenido": obj.get("contenido", ""),
                "tokens_input": obj.get("tokens_input", 0),
                "tokens_output": obj.get("tokens_output", 0),
                "costo_usd": float(obj.get("costo_usd", 0)),
            }).execute()
            ok += 1
        except Exception as e:
            errores.append(f"Línea {i + 1}: {e}")

    return ok, errores


# ============================================================
# Tab: Chat (admin prueba el tutor)
# ============================================================
def _tab_chat_admin(usuario):
    st.subheader("💬 Chat con el Tutor")

    asignaturas = GestorAsignaturas.listar()
    if not asignaturas:
        st.info("No hay cursos configurados.")
        return

    opciones = {GestorAsignaturas.nombre_legible(a): a for a in asignaturas}
    sel = st.selectbox("📖 Asignatura", list(opciones.keys()), key="sel_asig_adm")
    asignatura = opciones[sel]

    modelo_actual = get_modelo_activo()
    st.caption(f"🧠 Modelo: **{modelo_actual}**")

    chat_key = f"chat_adm_{asignatura}"
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
            key=f"nueva_conv_adm_{asignatura}",
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
                    key=f"load_conv_adm_{c['id']}",
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

        if prompt := st.chat_input("Escribe tu pregunta...", key=f"chat_in_adm_{asignatura}"):
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
