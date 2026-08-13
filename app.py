"""app.py — PUJ-IA: Entry Point con Auth + Ruteo por Rol."""
import streamlit as st

# Configuración de página — DEBE ser la primera llamada
st.set_page_config(
    page_title="PUJ-IA",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth import (
    hay_sesion, es_estudiante, es_docente, es_admin,
    login, signup, logout, usuario_actual,
)
from pages_estudiante import render_dashboard_estudiante
from pages_docente import render_dashboard_docente
from pages_admin import render_dashboard_admin


# ============================================================
# CSS mínimo
# ============================================================
st.markdown("""
<style>
    .stApp { max-width: 100%; }
    .stChatMessage { padding: 0.5rem 1rem; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# Main
# ============================================================
def main():
    if not hay_sesion():
        _render_login_page()
    elif es_estudiante():
        _render_sidebar_logout()
        render_dashboard_estudiante()
    elif es_docente():
        _render_sidebar_logout()
        render_dashboard_docente()
    elif es_admin():
        _render_sidebar_logout()
        render_dashboard_admin()
    else:
        st.error("Rol no reconocido. Contacte al administrador.")
        logout()


# ============================================================
# Login / Signup
# ============================================================
def _render_login_page():
    st.title("🎓 PUJ-IA")
    st.caption("Asistente pedagógico para estudiantes de ingeniería — Pontificia Universidad Javeriana Cali")

    tab_login = st.tabs(["🔑 Iniciar sesión"])[0]

    with tab_login:
        st.subheader("Iniciar sesión")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")

        if st.button("Ingresar", type="primary", key="btn_login"):
            if email and password:
                ok, msg = login(email, password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Ingrese email y contraseña.")

    # El registro de estudiantes solo está disponible para docentes desde su panel.
    st.info("📝 **¿Eres estudiante?** Tu profesor debe crear tu cuenta e indicarte tus credenciales de acceso.")
    st.markdown("")
    with st.expander("ℹ️ ¿Olvidaste tu contraseña?"):
        st.markdown(
            "Comunícate con tu profesor para restablecerla. "
            "Los docentes pueden crear nuevas credenciales desde su panel de administración."
        )


# ============================================================
# Sidebar (cuando hay sesión)
# ============================================================
def _render_sidebar_logout():
    usuario = usuario_actual()
    with st.sidebar:
        st.markdown(f"**{usuario.nombre}**")
        st.caption(f"{usuario.rol.capitalize()} · {usuario.email}")
        st.divider()

        # Info de sesión
        if "session_id" in st.session_state:
            st.caption(f"Sesión: `{st.session_state.session_id[:8]}...`")
        if "total_tokens" in st.session_state and st.session_state.total_tokens > 0:
            st.caption(f"Tokens usados: {st.session_state.total_tokens:,}")
        if "costo_total" in st.session_state and st.session_state.costo_total > 0:
            st.caption(f"Costo est.: ${st.session_state.costo_total:.4f} USD")

        st.divider()

        if st.button("🚪 Cerrar sesión", use_container_width=True):
            logout()
            st.rerun()

        # Footer
        st.divider()
        st.caption("© 2026 · Pontificia Univ. Javeriana Cali")
        st.caption("Investigador: J. A. Vélez Zea")
        st.caption("v0.1.0 · PUJ-IA")


if __name__ == "__main__":
    main()
