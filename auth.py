"""auth.py — Supabase Auth con 3 roles (estudiante, docente, admin)."""
import streamlit as st
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, PerfilUsuario


# ============================================================
# Cliente Supabase (cacheado)
# ============================================================
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_resource
def get_supabase_admin() -> Client:
    """Cliente con service_role — solo para admin.create_user()."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ============================================================
# Sesión
# ============================================================
def hay_sesion() -> bool:
    return st.session_state.get("usuario") is not None


def usuario_actual() -> PerfilUsuario | None:
    return st.session_state.get("usuario")


def es_estudiante() -> bool:
    u = usuario_actual()
    return u is not None and u.es_estudiante


def es_docente() -> bool:
    u = usuario_actual()
    return u is not None and u.es_docente


def es_admin() -> bool:
    u = usuario_actual()
    return u is not None and u.es_admin


# ============================================================
# Login / Signup / Logout
# ============================================================
def login(email: str, password: str) -> tuple[bool, str]:
    """Retorna (éxito, mensaje_error)."""
    try:
        supabase = get_supabase()
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = resp.user

        perfil_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user.id)
            .single()
            .execute()
        )

        if not perfil_resp.data:
            return False, "Perfil no encontrado. Contacte al administrador."

        perfil = perfil_resp.data
        st.session_state.usuario = PerfilUsuario(
            id=user.id,
            email=user.email,
            nombre=perfil["nombre"],
            rol=perfil["rol"],
            auth_token=resp.session.access_token,
        )
        return True, ""

    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg:
            return False, "Credenciales inválidas. Verifique email y contraseña."
        return False, f"Error de conexión: {msg[:120]}"


def signup(email: str, password: str, nombre: str, rol: str = "estudiante") -> tuple[bool, str]:
    """Registro público (solo estudiantes se auto-registran)."""
    try:
        supabase = get_supabase()
        resp = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"nombre": nombre, "rol": rol}},
        })

        if resp.user:
            return True, "Cuenta creada. Revise su correo para confirmar (si está habilitado)."
        return False, "No se pudo crear la cuenta."

    except Exception as e:
        return False, str(e)[:200]


def crear_usuario_docente(email: str, password: str, nombre: str) -> tuple[bool, str]:
    """Solo admin puede crear docentes. Usa service_role."""
    try:
        supabase = get_supabase_admin()
        resp = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"nombre": nombre, "rol": "docente"},
        })
        return True, f"Docente {nombre} creado (ID: {resp.user.id[:8]}...)"
    except Exception as e:
        return False, str(e)[:200]


def crear_usuario_estudiante(email: str, password: str, nombre: str) -> tuple[bool, str]:
    """Docente crea estudiantes. Usa service_role."""
    try:
        supabase = get_supabase_admin()
        resp = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"nombre": nombre, "rol": "estudiante"},
        })
        return True, f"Estudiante {nombre} creado."
    except Exception as e:
        return False, str(e)[:200]


def logout():
    try:
        get_supabase().auth.sign_out()
    except Exception:
        pass
    for key in ["usuario", "messages", "motor_rag", "pagina_actual",
                "conversacion_activa", "total_tokens", "costo_total",
                "asignatura_actual", "grupo_actual"]:
        st.session_state.pop(key, None)
