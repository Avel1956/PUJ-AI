"""chat_core.py — Lógica de chat compartida entre paneles (estudiante, docente, admin)."""
import streamlit as st
import time
import uuid
import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from auth import get_supabase
from config import MODELOS_DISPONIBLES, MODELO_POR_DEFECTO
from prompts import construir_prompt_completo
from rag_engine import MotorRAG
from telemetry import registrar_log


def get_modelo_activo() -> str:
    """Devuelve el modelo LLM configurado por el admin, o el default."""
    try:
        supabase = get_supabase()
        resp = supabase.table("config_sistema").select("valor").eq("clave", "modelo_llm").single().execute()
        if resp.data:
            return resp.data["valor"]
    except Exception:
        pass
    return MODELO_POR_DEFECTO


def inicializar_motor_rag(asignatura: str) -> MotorRAG:
    """Crea e indexa el MotorRAG para una asignatura, con cache en session_state."""
    cache_key = f"_rag_{asignatura}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    with st.spinner("📚 Cargando documentos del curso..."):
        motor = MotorRAG(asignatura)
        motor.indexar()
        st.session_state[cache_key] = motor
        if motor.esta_listo():
            st.toast(f"✅ {len(motor.documents)} documentos cargados")
    return motor


def responder(prompt: str, motor: MotorRAG, asignatura: str, usuario, control=None) -> str:
    """Genera respuesta del tutor socrático. Retorna el contenido de la respuesta."""
    modelo_nombre = get_modelo_activo()
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

    # RAG (protegido)
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
    st.session_state.setdefault("total_tokens", 0)
    st.session_state.setdefault("costo_total", 0.0)
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
            session_id=st.session_state.get("session_id", "anon"),
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

    return contenido


def _guardar_mensaje_db(usuario, contenido: str, t_in: int, t_out: int,
                        costo: float, t_ms: int, modelo: str):
    """Guarda mensaje de usuario + respuesta en la BD (protegido)."""
    try:
        supabase = get_supabase()
        conv_id = st.session_state.get("conversacion_activa")
        if conv_id and not conv_id.startswith("local-"):
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


def crear_conversacion(usuario, asignatura: str) -> str:
    """Crea una conversación en la BD y retorna el ID."""
    try:
        supabase = get_supabase()
        resp = supabase.table("conversaciones").insert({
            "estudiante_id": usuario.id,
            "asignatura": asignatura,
            "titulo": f"Chat del {datetime.date.today().isoformat()}",
            "model_usado": get_modelo_activo(),
        }).execute()
        if resp.data:
            return resp.data[0]["id"]
    except Exception:
        pass
    return f"local-{uuid.uuid4().hex[:8]}"
