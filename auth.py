"""auth.py — Supabase Auth con 3 roles (estudiante, docente, admin)."""
import random
import string

import streamlit as st
from supabase import create_client, Client

from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, PerfilUsuario


# ============================================================
# Cliente Supabase
#
# POR QUÉ EL CLIENTE DE USUARIO YA NO SE CACHEA CON @st.cache_resource
#   Un cliente cacheado a nivel de proceso es UNO SOLO para todos los usuarios
#   del servidor, y `login()` inicia sesión sobre él: su cabecera Authorization
#   pasa a ser la del ÚLTIMO usuario que entró. Con la RLS habilitada, cada
#   consulta se evaluaría con la identidad equivocada — el estudiante A podría
#   recibir filas autorizadas para el estudiante B.
#   Por eso el cliente vive en `st.session_state`: uno por sesión de navegador,
#   con la identidad de quien está conectado.
#
#   El cliente de service_role SÍ se cachea: no depende de ninguna identidad de
#   usuario y solo se usa para administrar cuentas (que exige service_role).
# ============================================================
_ESTADO_PROCESO: dict = {}  # respaldo cuando no hay un ciclo de Streamlit activo


def _estado() -> dict:
    """`st.session_state` si hay ciclo de Streamlit; si no, un diccionario del proceso."""
    try:
        return st.session_state
    except Exception:
        return _ESTADO_PROCESO


def _aplicar_token(cliente: Client, token: str) -> None:
    """Fija el token del usuario en el cliente.

    supabase-py ya reescribe la cabecera Authorization al emitir SIGNED_IN o
    TOKEN_REFRESHED, pero se reafirma en cada llamada: si el cliente se recrea
    (por ejemplo tras un cierre de sesión parcial) las consultas deben seguir
    viajando con la identidad correcta. Es lo que hace que la RLS evalúe
    `auth.uid()` con quien está realmente conectado.
    """
    if not token:
        return
    try:
        cliente.postgrest.auth(token)
    except Exception:
        pass


def get_supabase() -> Client:
    """Cliente Supabase DE ESTA SESIÓN (no compartido entre usuarios)."""
    estado = _estado()
    cliente = estado.get("_sb_cliente")
    if cliente is None:
        cliente = create_client(SUPABASE_URL, SUPABASE_KEY)
        estado["_sb_cliente"] = cliente

    _aplicar_token(cliente, estado.get("_sb_token", ""))
    return cliente


@st.cache_resource
def get_supabase_admin() -> Client:
    """Cliente con service_role — solo para administrar cuentas.

    SALTA la RLS por diseño, así que no debe usarse para leer datos de usuarios:
    solo para crear/borrar/restablecer cuentas en Supabase Auth.
    """
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

        if resp.session is None:
            # Ocurre si el correo no está confirmado y el proyecto exige
            # confirmación: hay usuario pero no sesión utilizable.
            return False, (
                "La cuenta existe pero no tiene sesión activa. Es probable que "
                "el correo no esté confirmado. Contacte al administrador."
            )

        # Fija la identidad de ESTA sesión antes de consultar: el perfil se lee
        # con el token del usuario recién conectado, no con la clave del cliente.
        _estado()["_sb_token"] = resp.session.access_token
        _aplicar_token(supabase, resp.session.access_token)

        perfil_resp = (
            supabase.table("profiles")
            .select("*")
            .eq("id", user.id)
            .single()
            .execute()
        )

        if not perfil_resp.data:
            _estado().pop("_sb_token", None)
            return False, "Perfil no encontrado. Contacte al administrador."

        perfil = perfil_resp.data
        _estado()["usuario"] = PerfilUsuario(
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


def _email_con_alias(email: str, asignatura: str) -> str:
    """Convierte ana@correo.com en ana+curso@correo.com (subaddressing).

    Permite que un mismo estudiante tenga una cuenta (y clave) distinta por curso,
    sin colisionar con el email único que exige Supabase Auth.
    Si el email ya lleva un '+' o no hay asignatura, se devuelve sin cambios.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return email
    if not asignatura:
        return email
    local, dominio = email.rsplit("@", 1)
    if "+" in local:
        return email
    slug = asignatura.strip().lower().replace(" ", "-")
    return f"{local}+{slug}@{dominio}"


def crear_usuario_estudiante(email: str, password: str, nombre: str,
                             docente_id: str = "", asignatura: str = "") -> tuple[bool, str]:
    """Docente crea estudiantes. Usa service_role y vincula (creado_por, asignatura)."""
    try:
        supabase = get_supabase_admin()
        email_efectivo = _email_con_alias(email, asignatura)
        resp = supabase.auth.admin.create_user({
            "email": email_efectivo,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "nombre": nombre,
                "rol": "estudiante",
                "creado_por": docente_id,
                "asignatura": asignatura,
            },
        })
        return True, f"Estudiante {nombre} creado (cuenta: {email_efectivo})."
    except Exception as e:
        return False, str(e)[:200]


def generar_password(length: int = 10) -> str:
    """Genera una contraseña aleatoria alfanumérica fácil de transcribir.

    Excluye los caracteres confundibles (0, O, 1, I, l) porque estas claves
    se entregan a los estudiantes en papel o por mensaje.
    """
    chars = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1Il")
    return "".join(random.choice(chars) for _ in range(length))


def restablecer_password(usuario_id: str, nueva_password: str = "",
                         docente_id: str = "") -> tuple[bool, str]:
    """Asigna una contraseña nueva a una cuenta. Requiere service_role.

    Las contraseñas se guardan en Supabase Auth solo como hash bcrypt, así que
    NO son recuperables: la única forma de desbloquear a un usuario es
    sobrescribirlas, que es lo que hace esta función.

    Si `docente_id` se especifica, exige que la cuenta le pertenezca
    (`profiles.creado_por == docente_id`). Una cuenta huérfana (creado_por
    NULL) tampoco es restablecible por un docente.

    Devuelve (éxito, mensaje). Si tuvo éxito, el mensaje ES la contraseña.
    """
    try:
        supabase = get_supabase_admin()

        if docente_id:
            perfil = (
                supabase.table("profiles")
                .select("creado_por")
                .eq("id", usuario_id)
                .single()
                .execute()
            )
            if not perfil.data:
                return False, "La cuenta no existe."
            if perfil.data.get("creado_por") != docente_id:
                return False, "No tiene permiso sobre esta cuenta."

        clave = nueva_password or generar_password()
        supabase.auth.admin.update_user_by_id(usuario_id, {"password": clave})
        return True, clave

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

    # El cliente y el token pertenecen a esta sesión: se descartan para que la
    # próxima entrada construya uno limpio, sin arrastrar la identidad anterior.
    for key in ("_sb_cliente", "_sb_token"):
        st.session_state.pop(key, None)
