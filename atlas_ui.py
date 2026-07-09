"""
╔════════════════════════════════════════════════════════════╗
║  🧠 ATLAS UI v3.7 - Interfaz Gráfica Híbrida Completa      ║
║  09/07/2026 - Atlas + Prometeo + RAG Semántico             ║
║  + Reglas Temporales + Diario + Memoria Persistente        ║
║  + Modo Examen Interactivo + Chats Múltiples               ║
╚════════════════════════════════════════════════════════════╝
"""
import streamlit as st
import os
import time
import json
import threading
from queue import Queue, Empty
from datetime import datetime

# Importar módulos de Atlas
from core.brain import pensar_con_streaming, limpiar_historial, ver_historial, HISTORIAL, set_historial, get_historial
from core.vision import analizar_pantalla
from core.speech_input import escuchar, probar_microfono
from core.speech_output import hablar, listar_voces_disponibles
from core.memory_manager import listar_categorias, guardar_en_memoria, procesar_historial_para_memoria, CATEGORIAS
from core.router import listar_agentes
from core.security import reporte_seguridad_completo
from core.diary_manager import agregar_entrada, leer_diario_hoy, buscar_en_diario
from core.temp_rules import agregar_regla, listar_reglas, limpiar_reglas
from core.vector_store import obtener_estadisticas
from core.exam_mode import ejecutar_examen_completo, corregir_respuesta, generar_informe_final
from core.chat_manager import (
    listar_chats, crear_chat, activar_chat, eliminar_chat,
    chat_activo_id, chat_activo_datos, agregar_mensaje,
    guardar_chat, renombrar_chat,
    obtener_historial_brain, guardar_historial_brain
)
from core.config import (
    obtener_catalogo_completo,
    verificar_modelo_local,
    descargar_modelo_local,
    eliminar_modelo_local,
    set_modelo_local,
    detectar_hardware,
    MODELO_LOCAL,
    MODELOS_LOCALES_DISPONIBLES
)

# ============================================
# CONFIGURACIÓN DE PÁGINA
# ============================================
st.set_page_config(
    page_title="Atlas v3.7",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# INICIALIZACIÓN ROBUSTA DE ESTADO
# ============================================
def _ensure_state():
    """Garantiza que TODAS las variables de st.session_state existan.
    Puede llamarse desde el flujo principal, callbacks, dialogs o modales.
    Usa 'not in' para no sobrescribir valores ya establecidos."""
    defaults = {
        "motor_activo": os.getenv("MOTOR_POR_DEFECTO", "atlas").lower(),
        "modelo_nube": "meta/llama-3.1-70b-instruct",
        "modelo_local": os.getenv("MODELO_LOCAL", "qwen3:8b"),
        "modelo_groq": "llama-3.3-70b-versatile",
        "voz_activa": False,
        "agente_actual": "general",
        "autoconocimiento_cache": None,
        "examen_activo": None,
        "mostrar_gestion_modelos": False,
        "motor_ingestion": "atlas",
        "modelo_ingestion_nube": "meta/llama-3.1-70b-instruct",
        "modelo_ingestion_local": "qwen3:8b",
        "modelo_ingestion_groq": "llama-3.3-70b-versatile",
        "_mostrar_ayuda": False,
        "messages": [],
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # Validar motor_activo contra opciones válidas
    if st.session_state["motor_activo"] not in ("atlas", "prometeo", "groq"):
        st.session_state["motor_activo"] = "atlas"

    # Inicialización de chats (una sola vez por sesión)
    if "chat_activo" not in st.session_state:
        chats_existentes = listar_chats()
        if chats_existentes:
            datos = activar_chat(chats_existentes[0]["id"])
            st.session_state["chat_activo"] = chats_existentes[0]["id"]
            st.session_state["messages"] = datos.get("messages", []) if datos else []
            hb = obtener_historial_brain()
            set_historial(hb)
        else:
            nuevo_id = crear_chat("Chat principal")
            datos = activar_chat(nuevo_id)
            st.session_state["chat_activo"] = nuevo_id
            st.session_state["messages"] = datos.get("messages", []) if datos else []
            limpiar_historial()

_ensure_state()

# ============================================
# CSS PERSONALIZADO
# ============================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}
.stButton>button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; border: none; border-radius: 10px;
    padding: 10px 20px; font-weight: bold;
    transition: all 0.3s; width: 100%;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}
[data-testid="stSidebar"] { background: rgba(22, 33, 62, 0.95); }
h1, h2, h3 { color: #e94560; }
.metric-card {
    background: rgba(255, 255, 255, 0.05);
    padding: 15px; border-radius: 10px;
    border-left: 3px solid #667eea;
}
.agent-badge {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 5px 15px; border-radius: 20px;
    color: white; font-size: 0.9em; display: inline-block;
}
.rules-badge {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    padding: 3px 10px; border-radius: 15px;
    color: white; font-size: 0.8em; display: inline-block;
}
.model-badge {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    padding: 3px 10px; border-radius: 15px;
    color: white; font-size: 0.8em; display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    _ensure_state()
    st.image("https://img.icons8.com/fluency/96/brain.png", width=100)
    st.title("Atlas v3.8")
    st.caption("Sistema Híbrido + RAG Semántico + Chats Múltiples")

    # ========================================
    # SECCIÓN: CHATS (Pestañas múltiples)
    # ========================================
    st.subheader("🗂️ Chats")
    col_chats1, col_chats2 = st.columns([4, 1])
    with col_chats2:
        if st.button("➕ Nuevo", use_container_width=True, help="Crear nuevo chat"):
            nuevo_id = crear_chat("Nuevo chat")
            # Guardar chat actual antes de cambiar
            guardar_historial_brain(get_historial(), st.session_state.chat_activo)
            # Cargar el nuevo
            datos = activar_chat(nuevo_id)
            st.session_state.chat_activo = nuevo_id
            st.session_state.messages = datos.get("messages", []) if datos else []
            set_historial(obtener_historial_brain())
            st.rerun()

    chats = listar_chats()
    for chat in chats:
        cols = st.columns([5, 1])
        indicador = "🟢" if chat["activo"] else "⚪"
        label = f"{indicador} {chat['nombre']}"
        msg_info = f" ({chat['total_mensajes']} msgs)" if chat['total_mensajes'] else ""
        with cols[0]:
            if st.button(label + msg_info, key=f"sel_{chat['id']}", use_container_width=True):
                if chat["id"] != st.session_state.chat_activo:
                    # Guardar el chat actual antes de cambiar
                    guardar_historial_brain(get_historial(), st.session_state.chat_activo)
                    datos = activar_chat(chat["id"])
                    st.session_state.chat_activo = chat["id"]
                    st.session_state.messages = datos.get("messages", []) if datos else []
                    set_historial(obtener_historial_brain())
                    st.rerun()
        with cols[1]:
            if st.button("✕", key=f"del_{chat['id']}", help="Cerrar chat"):
                if len(chats) > 1:
                    eliminar_chat(chat["id"])
                    # Si eliminamos el chat activo, activar el más reciente
                    if chat["id"] == st.session_state.chat_activo:
                        restantes = listar_chats()
                        if restantes:
                            datos = activar_chat(restantes[0]["id"])
                            st.session_state.chat_activo = restantes[0]["id"]
                            st.session_state.messages = datos.get("messages", []) if datos else []
                            set_historial(obtener_historial_brain())
                    st.rerun()
                else:
                    st.toast("No podés eliminar el último chat")

    st.divider()

    # ========================================
    # SECCIÓN: Estado
    # ========================================
    st.subheader("📊 Estado")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Historial", len(st.session_state.messages))
    with col2:
        info = ver_historial()
        st.metric("Memoria", info['cantidad'])
    with col3:
        try:
            stats = obtener_estadisticas()
            st.metric("Chunks", stats['total_chunks'])
            if stats['total_chunks'] == 0:
                st.caption("⚠️ RAG vacío: ejecutá `!indexar`")
        except Exception as e:
            st.metric("Chunks", "?")
            st.caption(f"RAG no inicializado: {type(e).__name__}")

    reglas_activas = listar_reglas()
    if reglas_activas:
        st.markdown(f"<span class='rules-badge'>📏 {len(reglas_activas)} reglas activas</span>", unsafe_allow_html=True)

    st.divider()

    # ========================================
    # SECCIÓN: Sentidos
    # ========================================
    st.subheader("👁️👂🗣️ Sentidos")
    if st.button("👁️ Mirar Pantalla", use_container_width=True):
        with st.spinner("Capturando..."):
            ruta, texto = analizar_pantalla()
            if ruta and texto:
                st.success(f"✅ Capturado ({len(texto)} caracteres)")
                with st.expander("📝 Ver texto extraído"):
                    st.text_area("", texto, height=200)
                if st.button("🧠 Analizar con Atlas"):
                    pregunta = f"Analizá este texto de mi pantalla:\n\n{texto}"
                    st.session_state.messages.append({"role": "user", "content": pregunta})
                    st.rerun()
            else:
                st.error(f"❌ {texto}")

    if st.button("🎤 Escuchar Voz", use_container_width=True):
        with st.spinner("🎤 Hablá ahora..."):
            texto = escuchar(duracion=5)
            if texto and not texto.startswith("Error") and "No escuché" not in texto:
                st.success(f"🎤 Dijiste: {texto}")
                if st.button("✅ Usar como pregunta"):
                    st.session_state.messages.append({"role": "user", "content": texto})
                    st.rerun()
            else:
                st.warning(texto)

    if st.button("🎤 Probar Micrófono", use_container_width=True):
        with st.spinner("Probando..."):
            resultado = probar_microfono()
            if resultado:
                st.success("✅ Micrófono funciona")
            else:
                st.error("❌ Error con el micrófono")

    st.divider()

    # ========================================
    # SECCIÓN: Voz
    # ========================================
    st.subheader("🔊 Voz")
    if st.toggle("Respuesta en voz alta", value=st.session_state.voz_activa):
        st.session_state.voz_activa = True
        st.info("🔊 Atlas hablará cada respuesta")
    else:
        st.session_state.voz_activa = False
        st.info("🔇 Modo silencioso")

    if st.button("🗣️ Listar Voces", use_container_width=True):
        with st.expander("Voces disponibles"):
            listar_voces_disponibles()

    st.divider()

    # ========================================
    # 🧠⚡ MOTOR DE IA (Selector principal)
    # ========================================
    st.subheader("🧠⚡ Motor de IA")
    motor_opciones = {
        "atlas": "🧠 Atlas Local (Privacidad 100%)",
        "prometeo": "⚡ Prometeo Nube (NVIDIA API)",
        "groq": "🚀 Groq Cloud (Ultra Rápido)"
    }

    motor_activo = st.session_state.get("motor_activo", "atlas")
    if motor_activo not in motor_opciones:
        motor_activo = "atlas"
        st.session_state["motor_activo"] = "atlas"

    motor_seleccionado = st.selectbox(
        "Elegí el cerebro:",
        options=list(motor_opciones.keys()),
        format_func=lambda x: motor_opciones[x],
        index=list(motor_opciones.keys()).index(motor_activo),
        key="selector_motor"
    )

    if motor_seleccionado != motor_activo:
        st.session_state["motor_activo"] = motor_seleccionado
        if motor_seleccionado == "atlas":
            st.success("🧠 Modo Atlas activado")
        elif motor_seleccionado == "prometeo":
            st.success("⚡ Modo Prometeo activado")
        else:
            st.success("🚀 Modo Groq activado")
        st.rerun()

    # ========================================
    # 🏠 MODELO LOCAL (solo si Atlas está activo)
    # ========================================
    if motor_activo == "atlas":
        st.markdown("---")
        st.markdown("**🏠 Modelo local:**")

        # Obtener catálogo completo con estado de descarga
        catalogo = obtener_catalogo_completo()

        # Lista de modelos oficiales en orden de prioridad
        modelos_oficiales_ids = [
            "qwen3:30b-a3b",  # Destacado primero
            "qwen3:8b",
            "qwen3:14b",
            "gemma3:12b",
            "deepseek-r1:14b",
            "mistral-small:22b",
            "llama3.1:8b",
            "phi4:14b"
        ]

        # Construir opciones para el selector
        opciones_modelos = {}
        for modelo_id in modelos_oficiales_ids:
            if modelo_id in catalogo:
                info = catalogo[modelo_id]
                descargado = "✅" if info.get("descargado") else "❌"
                destacado = " ⭐" if info.get("destacado") else ""
                label = f"{descargado} {info['descripcion']} ({info.get('velocidad', '?')}){destacado}"
                opciones_modelos[modelo_id] = label

        # Agregar modelos descargados no catalogados
        for nombre, info in catalogo.items():
            if nombre not in opciones_modelos and info.get("descargado"):
                opciones_modelos[nombre] = f"✅ {nombre} (Descargado)"

        # Selector de modelo local
        modelo_actual = st.session_state.modelo_local
        opciones_lista = list(opciones_modelos.keys())
        indice_actual = opciones_lista.index(modelo_actual) if modelo_actual in opciones_lista else 0

        modelo_seleccionado = st.selectbox(
            "Seleccioná un modelo:",
            options=opciones_lista,
            format_func=lambda x: opciones_modelos[x],
            index=indice_actual,
            key="selector_modelo_local"
        )

        if modelo_seleccionado != st.session_state.modelo_local:
            st.session_state.modelo_local = modelo_seleccionado
            resultado = set_modelo_local(modelo_seleccionado)
            st.toast(f"🔄 {resultado['mensaje']}")
            st.rerun()

        # Info del modelo seleccionado
        info_modelo = catalogo.get(modelo_seleccionado, {})
        if info_modelo:
            with st.expander("ℹ️ Info del modelo", expanded=False):
                st.markdown(f"""
**Arquitectura:** {info_modelo.get('arquitectura', 'N/A')}  
**Tamaño:** {info_modelo.get('tamano_gb', 0)} GB  
**RAM mínima:** {info_modelo.get('ram_min_gb', 0)} GB  
**VRAM mínima:** {info_modelo.get('vram_min_gb', 0)} GB  
**Calidad:** {'⭐' * info_modelo.get('calidad', 0)}  
**Uso recomendado:** {info_modelo.get('uso', 'N/A')}  
**Notas:** {info_modelo.get('notas', 'N/A')}
""")

        # Botón de gestión de modelos
        if st.button("📥 Gestionar Modelos", use_container_width=True):
            st.session_state.mostrar_gestion_modelos = not st.session_state.mostrar_gestion_modelos
            st.rerun()

        # Panel de gestión de modelos (MOSTRAR COMANDOS)
        if st.session_state.mostrar_gestion_modelos:
            with st.expander("📦 Gestión de Modelos", expanded=True):
                st.markdown("### 📥 Descargar modelos")
                st.info("💡 Abrí CMD o PowerShell y copiá los comandos:")
                
                # Mostrar comandos para modelos no descargados
                modelos_no_descargados = []
                for modelo_id in modelos_oficiales_ids:
                    if modelo_id in catalogo and not catalogo[modelo_id].get("descargado"):
                        modelos_no_descargados.append(modelo_id)
                
                if modelos_no_descargados:
                    for modelo_id in modelos_no_descargados:
                        info = catalogo[modelo_id]
                        st.code(f"ollama pull {modelo_id}", language="bash")
                        st.caption(f"{info['descripcion']} - {info.get('tamano_gb', 0)} GB")
                else:
                    st.success("✅ Todos los modelos del catálogo están descargados")
                
                st.markdown("---")
                st.markdown("### ✅ Modelos ya descargados")
                
                modelos_descargados = []
                for modelo_id in modelos_oficiales_ids:
                    if modelo_id in catalogo and catalogo[modelo_id].get("descargado"):
                        modelos_descargados.append(modelo_id)
                
                if modelos_descargados:
                    for modelo_id in modelos_descargados:
                        info = catalogo[modelo_id]
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            destacado = " ⭐" if info.get("destacado") else ""
                            st.markdown(f"**{info['descripcion']}**{destacado}")
                            st.caption(f"{info.get('tamano_gb', 0)} GB | {info.get('velocidad', '?')}")
                        with col2:
                            if modelo_id != st.session_state.modelo_local:
                                if st.button("🗑️", key=f"delete_{modelo_id}", help="Eliminar"):
                                    resultado = eliminar_modelo_local(modelo_id)
                                    if resultado["exito"]:
                                        st.success(resultado["mensaje"])
                                        st.rerun()
                                    else:
                                        st.error(resultado["mensaje"])
                else:
                    st.warning("No hay modelos descargados todavía")
                
                st.markdown("---")
                st.markdown("### 🖥️ Comandos útiles")
                st.code("ollama list", language="bash")
                st.caption("Ver modelos descargados")
                
                st.code("ollama rm nombre_modelo", language="bash")
                st.caption("Eliminar un modelo")
                
                # Info de hardware
                hardware = detectar_hardware()
                st.markdown("---")
                st.markdown(f"""
**Tu hardware:**  
🖥️ RAM: {hardware['ram_gb']} GB  
🎮 GPU: {hardware['gpu']}  
💾 VRAM: {hardware['vram_gb']} GB  
**Recomendación:** {hardware['recomendacion']}
""")

        st.caption(f"🔒 Consultas procesadas LOCALMENTE ({st.session_state.modelo_local})")

    # ========================================
    # ⚡ MODELO DE NUBE (solo si Prometeo está activo)
    # ========================================
    elif motor_activo == "prometeo":
        st.markdown("---")
        st.markdown("**⚡ Modelo de nube:**")

        modelos_nube = {
            "meta/llama-3.1-70b-instruct": "Llama 3.1 70B (Equilibrado)",
            "meta/llama-3.1-8b-instruct": "Llama 3.1 8B (Rápido)",
            "meta/llama-3.3-70b-instruct": "Llama 3.3 70B (Nuevo)",
            "deepseek-ai/deepseek-v4-flash": "DeepSeek V4 Flash",
            "deepseek-ai/deepseek-v4-pro": "DeepSeek V4 Pro (Top)",
            "google/gemma-3-12b-it": "Gemma 3 12B (Google)",
            "google/gemma-4-31b-it": "Gemma 4 31B (Google)",
            "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra 550B",
        }

        modelo_sel = st.selectbox(
            "Seleccioná un modelo:",
            options=list(modelos_nube.keys()),
            format_func=lambda x: modelos_nube[x],
            index=list(modelos_nube.keys()).index(st.session_state.modelo_nube) if st.session_state.modelo_nube in modelos_nube else 0,
            key="selector_modelo_nube"
        )

        if modelo_sel != st.session_state.modelo_nube:
            st.session_state.modelo_nube = modelo_sel
            st.info(f"Modelo: {modelos_nube[modelo_sel]}")

        st.caption(f"☁️ NVIDIA API ({st.session_state.modelo_nube.split('/')[-1]})")

    # ========================================
    # 🚀 MODELO GROQ (solo si Groq está activo)
    # ========================================
    elif motor_activo == "groq":
        st.markdown("---")
        st.markdown("**🚀 Modelos Groq Cloud:**")

        modelos_groq = {
            "llama-3.3-70b-versatile": "Llama 3.3 70B (Equilibrado - Top)",
            "meta-llama/llama-4-scout-17b-16e-instruct": "Llama 4 Scout 17B (Experimental)",
            "qwen/qwen3-32b": "Qwen 3 32B (Razonamiento)",
            "qwen/qwen3.6-27b": "Qwen 3.6 27B (Equilibrado)",
            "llama-3.1-8b-instant": "Llama 3.1 8B (Rápido)",
            "openai/gpt-oss-120b": "GPT-OSS 120B (Ultra Grande)",
        }

        modelo_groq_sel = st.selectbox(
            "Seleccioná un modelo:",
            options=list(modelos_groq.keys()),
            format_func=lambda x: modelos_groq[x],
            index=list(modelos_groq.keys()).index(st.session_state.modelo_groq) if st.session_state.modelo_groq in modelos_groq else 0,
            key="selector_modelo_groq"
        )

        if modelo_groq_sel != st.session_state.modelo_groq:
            st.session_state.modelo_groq = modelo_groq_sel
            st.info(f"🚀 Modelo: {modelos_groq[modelo_groq_sel]}")

        st.caption(f"⚡ Groq API ({st.session_state.modelo_groq.split('-')[0]})")

    # ========================================
    # SECCIÓN: Configuración de Digestión
    # ========================================
    st.markdown("---")
    st.subheader("🔄 Motor de Digestión")
    st.caption("Para ingesta web y archivos locales.")

    digestion_opciones = {
        "atlas": "🧠 Atlas Local (Ollama)",
        "prometeo": "⚡ Prometeo Nube (NVIDIA)",
        "groq": "🚀 Groq Cloud (Ultra rápido)",
    }
    motor_dig_sel = st.selectbox(
        "Motor para digerir PDFs/archivos:",
        options=list(digestion_opciones.keys()),
        format_func=lambda x: digestion_opciones[x],
        index=list(digestion_opciones.keys()).index(st.session_state.motor_ingestion),
        key="selector_motor_ingestion",
    )

    if motor_dig_sel != st.session_state.motor_ingestion:
        st.session_state.motor_ingestion = motor_dig_sel
        st.rerun()

    if st.session_state.motor_ingestion == "atlas":
        modelos_locales_opciones = {}
        catalogo_dig = obtener_catalogo_completo()
        for modelo_id in catalogo_dig:
            info = catalogo_dig[modelo_id]
            if info.get("descargado"):
                modelos_locales_opciones[modelo_id] = f"✅ {info['descripcion']} ({info.get('velocidad', '?')})"

        opciones_lista_dig = list(modelos_locales_opciones.keys())
        indice_actual_dig = opciones_lista_dig.index(st.session_state.modelo_ingestion_local) if st.session_state.modelo_ingestion_local in opciones_lista_dig else 0

        modelo_local_dig = st.selectbox(
            "Modelo local para digestión:",
            options=opciones_lista_dig,
            format_func=lambda x: modelos_locales_opciones[x],
            index=indice_actual_dig,
            key="selector_modelo_ingestion_local",
        )
        if modelo_local_dig != st.session_state.modelo_ingestion_local:
            st.session_state.modelo_ingestion_local = modelo_local_dig
            st.toast(f"Modelo de digestión: {modelo_local_dig}")

    elif st.session_state.motor_ingestion == "groq":
        modelos_groq_dig = {
            "llama-3.3-70b-versatile": "Llama 3.3 70B (Versátil - Top)",
            "llama-3.1-70b-versatile": "Llama 3.1 70B (Versátil)",
            "llama-3.1-8b-instant": "Llama 3.1 8B (Instant)",
        }
        modelo_groq_dig = st.selectbox(
            "Modelo Groq para digestión:",
            options=list(modelos_groq_dig.keys()),
            format_func=lambda x: modelos_groq_dig[x],
            index=list(modelos_groq_dig.keys()).index(st.session_state.modelo_ingestion_groq) if st.session_state.modelo_ingestion_groq in modelos_groq_dig else 0,
            key="selector_modelo_ingestion_groq",
        )
        if modelo_groq_dig != st.session_state.modelo_ingestion_groq:
            st.session_state.modelo_ingestion_groq = modelo_groq_dig
            st.toast(f"Modelo de digestión: {modelo_groq_dig}")

    else:
        # Usar modelos disponibles desde la configuración
        from core.config import MODELOS_NUBE_DISPONIBLES
        modelo_nube_dig = st.selectbox(
            "Modelo nube para digestión:",
            options=list(MODELOS_NUBE_DISPONIBLES.keys()),
            format_func=lambda x: MODELOS_NUBE_DISPONIBLES[x],
            index=list(MODELOS_NUBE_DISPONIBLES.keys()).index(st.session_state.modelo_ingestion_nube) if st.session_state.modelo_ingestion_nube in MODELOS_NUBE_DISPONIBLES else 0,
            key="selector_modelo_ingestion_nube",
        )
        if modelo_nube_dig != st.session_state.modelo_ingestion_nube:
            st.session_state.modelo_ingestion_nube = modelo_nube_dig
            st.toast(f"Modelo de digestión: {MODELOS_NUBE_DISPONIBLES[modelo_nube_dig]}")

    st.divider()

    # ========================================
    # SECCIÓN: Ingesta Web
    # ========================================
    st.subheader("🌐 Ingesta Web (URLs)")
    url_ingestion = st.text_input("URL del PDF:", placeholder="https://...", key="url_ingestion")
    categoria_ingestion = st.selectbox("Categoría:", ["Estudio", "Derecho", "Investigacion", "General"], key="categoria_ingestion")

    if st.button("🚀 Iniciar Ingesta Web", use_container_width=True, key="btn_ingestion"):
        if not url_ingestion:
            st.error("Ingresá una URL")
        else:
            from core.ingestion_manager import procesar_pipeline_ingestion
            motor_dig = st.session_state.get("motor_ingestion", "atlas")
            modelo_dig = None
            if motor_dig == "atlas":
                modelo_dig = st.session_state.get("modelo_ingestion_local", "qwen3:8b")
            elif motor_dig == "groq":
                modelo_dig = st.session_state.get("modelo_ingestion_groq", "llama-3.3-70b-versatile")
            else:
                modelo_dig = st.session_state.get("modelo_ingestion_nube", "meta/llama-3.1-70b-instruct")
            progreso_container = st.empty()
            try:
                for paso in procesar_pipeline_ingestion(url_ingestion, categoria_ingestion,
                                                        motor=motor_dig, modelo=modelo_dig):
                    if paso["estado"] == "error":
                        progreso_container.error(paso["mensaje"]); break
                    elif paso["estado"] == "completado":
                        progreso_container.success(paso["mensaje"])
                    else:
                        progreso_container.info(paso["mensaje"])
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

    st.divider()

    # ========================================
    # SECCIÓN: Drag & Drop Local (DINÁMICO)
    # ========================================
    st.subheader("📂 Archivos Locales (Drag & Drop)")
    st.caption("PDFs, audios, videos, imágenes. Seleccioná destino o creá subcarpeta nueva.")

    archivos_subidos = st.file_uploader(
        "Soltá tus archivos:",
        type=['pdf', 'txt', 'md', 'docx', 'epub', 'html', 'htm', 'png', 'jpg', 'jpeg', 
              'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac', 
              'mp4', 'mov', 'avi', 'mkv', 'webm'],
        accept_multiple_files=True,
        key="uploader_local"
    )

    # Obtener carpetas dinámicamente del backend
    from core.local_ingestion_manager import detectar_carpetas_atlas_memory, crear_subcarpeta
    carpetas_disponibles = detectar_carpetas_atlas_memory()

    categoria_local = st.selectbox(
        "📁 Carpeta destino:",
        options=carpetas_disponibles,
        key="categoria_local"
    )

    # Opción para crear subcarpeta nueva
    crear_sub = st.checkbox("📁 ¿Crear subcarpeta nueva dentro de esta ruta?", key="chk_crear_sub")
    if crear_sub:
        nombre_sub = st.text_input("Nombre de la subcarpeta:", placeholder="ej: balance_julio, facturas_2026", key="txt_nombre_sub")
        if st.button("✅ Crear y actualizar lista", use_container_width=True, key="btn_crear_subcarpeta"):
            if nombre_sub.strip():
                ruta_nueva = f"{categoria_local}/{nombre_sub.strip().replace(' ', '_')}"
                resultado = crear_subcarpeta(ruta_nueva)
                st.toast(resultado["mensaje"])
                if resultado["exito"]:
                    st.rerun()  # Recarga la lista de carpetas
            else:
                st.warning("Escribí un nombre válido para la subcarpeta.")

    # Botón de procesamiento
    if st.button("⚡ Procesar con Prometeo", use_container_width=True, key="btn_procesar_local"):
        if not archivos_subidos:
            st.warning("Soltá archivos primero")
        else:
            from core.local_ingestion_manager import procesar_archivo_local

            motor_dig = st.session_state.get("motor_ingestion", "atlas")
            modelo_dig = None
            if motor_dig == "atlas":
                modelo_dig = st.session_state.get("modelo_ingestion_local", "qwen3:8b")
            elif motor_dig == "groq":
                modelo_dig = st.session_state.get("modelo_ingestion_groq", "llama-3.3-70b-versatile")
            else:
                modelo_dig = st.session_state.get("modelo_ingestion_nube", "meta/llama-3.1-70b-instruct")

            # Determinar ruta final
            ruta_destino = st.session_state.get("categoria_local", categoria_local) or categoria_local

            for archivo in archivos_subidos:
                st.markdown(f"**Procesando:** `{archivo.name}` → `{ruta_destino}`")
                progreso_container = st.empty()
                try:
                    for paso in procesar_archivo_local(archivo, ruta_destino,
                                                       motor=motor_dig, modelo=modelo_dig):
                        if paso["estado"] == "error":
                            progreso_container.error(paso["mensaje"]); break
                        elif paso["estado"] == "completado":
                            progreso_container.success(paso["mensaje"])
                        else:
                            progreso_container.info(paso["mensaje"])
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                st.divider()

    st.divider()

    # ========================================
    # 🧪 PROMPT PLAYGROUND (Comparador de Modelos)
    # ========================================
    st.subheader("🧪 Prompt Playground")
    st.caption("Enviá un prompt y compará la respuesta de diferentes motores simultáneamente.")

    with st.expander("Abrir Laboratorio de Pruebas", expanded=False):
        col_play1, col_play2 = st.columns([3, 1])
        with col_play1:
            prompt_play = st.text_area("Prompt de prueba:", placeholder="Ej: Explícame la teoría de la relatividad en una frase...", key="play_prompt")
        with col_play2:
            st.markdown("**Modelos a probar:**")
            test_local = st.checkbox("Local (Atlas)", value=True, key="play_test_local")
            test_nube = st.checkbox("Nube (Prometeo)", value=True, key="play_test_nube")
            test_groq = st.checkbox("Groq Cloud", value=True, key="play_test_groq")

        if st.button("🚀 Comparar Respuestas", use_container_width=True):
            if not prompt_play:
                st.warning("Escribí un prompt primero")
            else:
                from core.brain import pensar_sin_streaming
                from core.config import MODELO_LOCAL, MODELO_NUBE_DEFAULT, MODELO_GROQ_DEFAULT
                
                with st.spinner("Consultando cerebros..."):
                    resultados = {}
                    
                    if test_local:
                        resultados["Local"] = pensar_sin_streaming(prompt_play, motor="atlas", modelo_local=MODELO_LOCAL)
                    if test_nube:
                        resultados["Prometeo"] = pensar_sin_streaming(prompt_play, motor="prometeo", modelo_nube=MODELO_NUBE_DEFAULT)
                    if test_groq:
                        resultados["Groq"] = pensar_sin_streaming(prompt_play, motor="groq", modelo_groq=MODELO_GROQ_DEFAULT)
                    
                    # Renderizado lado a lado
                    cols_res = st.columns(len(resultados))
                    for i, (motor, resp) in enumerate(resultados.items()):
                        with cols_res[i]:
                            st.markdown(f"**{motor}**")
                            st.info(resp)

    st.divider()

    # ========================================
    # SECCIÓN: Auto-conocimiento
    # ========================================
    st.subheader("🪞 Auto-conocimiento")

    if st.button("🔍 Auto-conocer", use_container_width=True):
        with st.spinner("Atlas analizando arquitectura..."):
            try:
                from core.self_awareness import generar_reporte_self_awareness
                reporte_base = generar_reporte_self_awareness()
            except (ImportError, Exception):
                reporte_base = "Módulo nativo no disponible."

            ahora_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            try:
                agentes_disponibles = list(listar_agentes().keys())
            except:
                agentes_disponibles = ["general", "estadistica", "researcher", "mentor", "arquitecto"]

             ficha_tecnica = f"""# 🧠 FICHA DE ARQUITECTURA - ATLAS v3.7
Generado: {ahora_str} | Creador: Charly

## Sistema Híbrido
- Atlas (local): {st.session_state.modelo_local} vía Ollama
- Prometeo (nube): NVIDIA API (Llama 3.1 70B, DeepSeek V4, etc.)

## RAG Semántico
- Vector DB: ChromaDB con embeddings multilingües
- Modelo: paraphrase-multilingual-MiniLM-L12-v2
- Chunks: {stats['total_chunks'] if 'stats' in locals() else '?'}

## Agentes: {", ".join(agentes_disponibles)}

## Reporte interno:
{reporte_base}
"""
            st.session_state.autoconocimiento_cache = ficha_tecnica
            st.success("✅ Ficha técnica generada")

    if st.session_state.autoconocimiento_cache:
        with st.expander("📊 Ver reporte técnico", expanded=True):
            st.code(st.session_state.autoconocimiento_cache, language="markdown")

    if st.button("🧘 Reflexionar", use_container_width=True):
        with st.spinner("Reflexionando..."):
            try:
                from core.reflection import reflexionar_sobre_conversaciones
                reflexion = reflexionar_sobre_conversaciones(HISTORIAL)
                with st.expander("💭 Reflexión", expanded=True):
                    st.markdown(reflexion)
            except Exception as e:
                st.error(f"❌ Error: {e}")

    if st.button("🚀 Buscar Mejoras", use_container_width=True):
        with st.spinner("Buscando..."):
            try:
                from core.self_improvement import buscar_mejores_practicas
                resultados = buscar_mejores_practicas("RAG local LLM")
                with st.expander("📚 Recursos", expanded=True):
                    for i, r in enumerate(resultados[:5], 1):
                        if "error" not in r:
                            st.markdown(f"**[{i}] {r.get('titulo', '')}**")
                            st.caption(f"🔗 {r.get('url', '')}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.divider()

    # ========================================
    # SECCIÓN: Perfiles
    # ========================================
    st.subheader("👤 Perfiles")
    nombre_export = st.text_input("Nombre:", value="charly", key="nombre_export")

    if st.button("💾 Exportar Perfil", use_container_width=True):
        try:
            from core.profile_manager import exportar_perfil_actual
            ok, resultado = exportar_perfil_actual(nombre_export)
            if ok: st.success(f"✅ {resultado}")
            else: st.error(f"❌ {resultado}")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    archivo_import = st.file_uploader("📥 Importar perfil", type=['zip'])
    if archivo_import is not None:
        if st.button("✅ Importar", use_container_width=True):
            try:
                from core.profile_manager import importar_perfil
                temp_path = f"temp_{archivo_import.name}"
                with open(temp_path, "wb") as f:
                    f.write(archivo_import.getbuffer())
                ok, resultado = importar_perfil(temp_path)
                os.remove(temp_path)
                if ok:
                    st.success(f"✅ {resultado}")
                    st.info("Reiniciá Atlas para aplicar")
                else:
                    st.error(f"❌ {resultado}")
            except Exception as e:
                st.error(f"❌ Error: {e}")

    st.divider()

    # ========================================
    # SECCIÓN: Comandos Rápidos
    # ========================================
    st.subheader("🛠️ Acciones Rápidas")

    if st.button("🗑️ Limpiar Chat", use_container_width=True):
        st.session_state.messages = []
        limpiar_historial()
        # Persistir vacío en el chat activo
        datos = chat_activo_datos()
        if datos:
            datos["messages"] = []
            guardar_chat()
        st.rerun()

    if st.button("🛡️ Reporte Seguridad", use_container_width=True):
        reporte = reporte_seguridad_completo()
        with st.expander("Reporte", expanded=True):
            st.json(reporte)

    st.divider()

    # ========================================
    # SECCIÓN: Info Sistema
    # ========================================
    st.subheader("ℹ️ Sistema")
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
    st.caption(f"🧠 Motor: {motor_activo.upper()}")
    if motor_activo == "atlas":
        st.caption(f"🏠 Modelo: {st.session_state.modelo_local}")
    else:
        st.caption(f"☁️ Modelo: {st.session_state.modelo_nube}")
        st.caption("📅 Versión: 3.7")

# ============================================
# HEADER PRINCIPAL
# ============================================
st.title("Atlas")
    st.caption(f"Asistente híbrido v3.8 | Motor: {st.session_state.get('motor_activo', 'atlas').upper()} | Escribí, hablá o usá comandos (!ayuda)")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(f"<div style='text-align: center'><span class='agent-badge'>🤖 Agente: {st.session_state.agente_actual}</span></div>", unsafe_allow_html=True)

st.divider()

# ============================================
# FUNCIONES AUXILIARES PARA EXAMEN
# ============================================
def _render_ayuda_modal():
    """Muestra el panel de comandos en un modal centrado y prolijo."""
    _ensure_state()
    @st.dialog("🧠 Atlas v3.7 — Comandos", width="large")
    def modal():
        _ensure_state()
        st.markdown(
            """
            <div style="font-size:16px; line-height:1.6">
            Selecciona un comando y copialo directo al chat cuando lo necesites.
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_rag, tab_reglas, tab_mem, tab_dia, tab_self, tab_ex = st.tabs(
            ["🔄 Sistema y RAG", "📏 Reglas", "🧠 Memoria", "📔 Diario",
             "🪞 Auto-conocimiento", "📝 Examen"]
        )

        with tab_rag:
            st.markdown("#### 🔄 Sistema y RAG Semántico")
            cmd_list = [
                ("`!indexar`", "Reconstruye el índice semántico desde `memory/Atlas_Memory/`."),
                ("`!limpiar` o `!limpiar_historial`", "Borra el historial de la sesión actual."),
                ("`!historial`", "Informa cantidad de mensajes acumulados."),
                ("`!categorias`", "Lista las categorías de memoria persistente."),
                ("`!agentes`", "Muestra los agentes disponibles (general, estadistica, researcher, mentor, arquitecto)."),
                ("`!seguridad`", "Auditoría de seguridad (ruta, ollama, permisos)."),
                ("`!stats`", "Cantidad total de chunks en ChromaDB."),
            ]
            for c, d in cmd_list:
                st.markdown(f"- {c}  \n  {d}")

        with tab_reglas:
            st.markdown("#### 📏 Reglas Temporales")
            for c, d in [
                ("`!reglas <texto>`", "Agrega una regla temporal de comportamiento."),
                ("`!reglas`", "Lista las reglas temporales activas."),
                ("`!limpiar_reglas`", "Elimina todas las reglas temporales."),
            ]:
                st.markdown(f"- {c}  \n  {d}")
            st.info(
                "Ej.: `!reglas respondé siempre en menos de 100 palabras`. "
                "Las reglas viven hasta que las limpies.",
                icon="💡",
            )

        with tab_mem:
            st.markdown("#### 🧠 Memoria Persistente")
            for c, d in [
                ("`!memoria`", "Revisa conquistas recientes y guarda recuerdos relevantes."),
                ("`!ver_memoria`", "Abre un panel con la memoria persistente por categoría."),
            ]:
                st.markdown(f"- {c}  \n  {d}")

        with tab_dia:
            st.markdown("#### 📔 Diario Personal")
            for c, d in [
                ("`!diario agregar [texto]`", "Crea una entrada con categorización automática."),
                ("`!diario leer`", "Abre el diario de hoy."),
                ("`!diario buscar [término]`", "Busca en todo el histórico del diario."),
            ]:
                st.markdown(f"- {c}  \n  {d}")
            st.caption(
                "Categorías: `general`, `logro`, `emocion`, `proyecto`, `reflexion` (autodetect)."
            )

        with tab_self:
            st.markdown("#### 🪞 Auto-conocimiento y Mejoras")
            for c, d in [
                ("`!autoconocer`", "Imprime el informe completo (con código)."),
                ("`!autoconocer_corto`", "Informe sin código embebido."),
                ("`!informe`", "Exporta el informe a `memory/Atlas_Memory/backups/`."),
                ("`!reflexionar`", "Atlas analiza la conversación actual y guarda aprendizajes."),
                ("`!mejorar`", "Busca mejoras recomendadas en la web (only URLs, no toca código)."),
            ]:
                st.markdown(f"- {c}  \n  {d}")

        with tab_ex:
            st.markdown("#### 📝 Modo Examen")
            st.markdown(
                "Comando: `!examen <material> capítulos X al Y [especs]`"
            )
            st.code(
                "!examen Compendio Bidart capítulos 7 al 9 "
                "3 conceptuales 4 desarrollo 3 V/F",
                language="bash",
            )
            st.caption(
                "Las especificaciones son opcionales. Tras iniciar, respondé las preguntas en el chat. "
                "Cuando termines, Atlas corrige y genera el informe final."
            )

        st.divider()
        if st.button("Cerrar", use_container_width=True, key="btn_cerrar_ayuda"):
            st.rerun()

    modal()

def renderizar_examen():
    _ensure_state()
    if not st.session_state.examen_activo:
        return

    examen = st.session_state.examen_activo
    preguntas = examen["preguntas"]
    respuestas = examen["respuestas"]
    total = len(preguntas)
    actual = len(respuestas)

    if actual >= total:
        st.markdown("## 🎉 Examen completado")

        resultados = []
        for r in respuestas:
            correccion = corregir_respuesta(
                r["pregunta"],
                r["respuesta_usuario"],
                motor=st.session_state.get("motor_activo", "atlas"),
                modelo_nube=st.session_state.get("modelo_nube", "meta/llama-3.1-70b-instruct") if st.session_state.get("motor_activo", "atlas") == "prometeo" else None
            )
            resultados.append({
                "pregunta": r["pregunta"],
                "respuesta_usuario": r["respuesta_usuario"],
                "correccion": correccion
            })

        informe = generar_informe_final(resultados)
        st.markdown(informe)

        if st.button("🔄 Iniciar nuevo examen"):
            st.session_state.examen_activo = None
            st.rerun()
        return

    st.markdown(f"### 📝 Examen en curso ({actual}/{total})")
    st.progress(actual / total)

    p = preguntas[actual]
    st.markdown(f"**Pregunta {actual+1}/{total}** [{p.get('tipo', 'general').upper()}]")
    st.markdown(p.get("enunciado", ""))
    st.info("Escribí tu respuesta en el chat y presioná Enter. No uses el signo ! al inicio.")

# ============================================
# HISTORIAL DE CHAT
# ============================================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============================================
# INPUT DEL USUARIO
# ============================================
if prompt := st.chat_input("Escribí tu mensaje o usá comandos (!ayuda)..."):
    # PRIORIDAD: si hay examen activo y NO es un comando, es una respuesta de examen
    if st.session_state.examen_activo and not prompt.strip().startswith("!"):
        examen = st.session_state.examen_activo
        preguntas = examen["preguntas"]
        respuestas = examen["respuestas"]
        actual = len(respuestas)

        if actual < len(preguntas):
            p = preguntas[actual]
            respuestas.append({
                "pregunta": p,
                "respuesta_usuario": prompt
            })
            st.session_state.examen_activo["respuestas"] = respuestas

            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": f"📝 Respuesta {actual+1}/{len(preguntas)} registrada."})
            st.rerun()
        else:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.messages.append({"role": "assistant", "content": "El examen ya fue completado."})
            st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    agregar_mensaje("user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    # ========================================
    # MANEJO DE COMANDOS (empiezan con !)
    # ========================================
    if prompt.strip().startswith("!"):
        parts = prompt.strip().split(maxsplit=2)
        comando = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        with st.chat_message("assistant"):
            # !AYUDA - El modal se invoca al final del flujo (post-ejecución)
            # para no perturbar el orden de 'with st.chat_message'.
            if comando in ["!ayuda", "!help"]:
                st.session_state["_mostrar_ayuda"] = True
                st.success("📚 Abro el panel de ayuda con todos los comandos.")

            # !REGLAS
            elif comando == "!reglas":
                if not args:
                    reglas = listar_reglas()
                    if reglas:
                        st.info(f"📏 **Reglas temporales activas ({len(reglas)}):**")
                        for i, regla in enumerate(reglas, 1):
                            st.markdown(f"{i}. {regla}")
                    else:
                        st.info("📏 No hay reglas temporales activas")
                else:
                    texto_regla = " ".join(args)
                    resultado = agregar_regla(texto_regla)
                    if resultado["exito"]:
                        st.success(resultado["mensaje"])
                    else:
                        st.error(resultado["mensaje"])

            # !LIMPIAR_REGLAS
            elif comando == "!limpiar_reglas":
                resultado = limpiar_reglas()
                if resultado["exito"]:
                    st.success(resultado["mensaje"])

            # !STATS
            elif comando == "!stats":
                try:
                    stats = obtener_estadisticas()
                    st.info(f"""
📊 Estadísticas de ChromaDB:
Total de chunks: {stats['total_chunks']}
Nombre de colección: {stats['nombre_coleccion']}
Ruta de DB: {stats['ruta_db']}""")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

            # !MEMORIA
            elif comando in ["!memoria", "!salir", "!revisar"]:
                with st.spinner("🧠 Atlas está revisando las conversaciones..."):
                    guardados, errores = procesar_historial_para_memoria(HISTORIAL)
                    if guardados > 0:
                        st.success(f"✅ Memoria actualizada: {guardados} nuevos recuerdos guardados.")
                    else:
                        st.info("ℹ️ No se encontró información nueva relevante.")
                    if errores > 0:
                        st.warning(f"⚠️ {errores} intentos fallidos.")

            # !VER_MEMORIA
            elif comando == "!ver_memoria":
                st.info("📂 Contenido actual de tu memoria persistente:")
                for cat, ruta in CATEGORIAS.items():
                    if os.path.exists(ruta):
                        with open(ruta, "r", encoding="utf-8") as f:
                            contenido = f.read().strip()
                        if contenido and not contenido.endswith("Registro automático de Atlas."):
                            with st.expander(f"**{cat}**", expanded=False):
                                st.text_area(f"Contenido de {cat}", contenido, height=150, key=f"mem_{cat}")

            # !DIARIO
            elif comando == "!diario":
                if not args:
                    st.warning("Usá: `!diario agregar [texto]`, `!diario leer` o `!diario buscar [término]`")
                else:
                    sub = args[0].lower()
                    if sub == "agregar":
                        texto = " ".join(args[1:]) if len(args) > 1 else ""
                        if texto:
                            t_low = texto.lower()
                            cat = "general"
                            if any(w in t_low for w in ["orgulloso", "aprobé", "logré", "bien", "éxito", "feliz", "terminé"]):
                                cat = "logro"
                            elif any(w in t_low for w in ["triste", "mal", "ansioso", "estresado", "cansado"]):
                                cat = "emocion"
                            elif any(w in t_low for w in ["atlas", "prometeo", "proyecto", "código"]):
                                cat = "proyecto"
                            elif any(w in t_low for w in ["pensé", "reflexion", "idea"]):
                                cat = "reflexion"
                            res = agregar_entrada(texto, cat)
                            if res["exito"]:
                                st.success(res["mensaje"])
                            else:
                                st.error(res["mensaje"])
                        else:
                            st.warning("Escribí el texto a guardar.")
                    elif sub == "leer":
                        st.markdown(leer_diario_hoy())
                    elif sub == "buscar":
                        termino = " ".join(args[1:])
                        if termino:
                            res = buscar_en_diario(termino)
                            if res:
                                for r in res:
                                    st.markdown(f"**📅 {r['archivo']}**: {r['fragmento']}")
                            else:
                                st.info("No encontré nada.")

            # !INDEXAR
            elif comando == "!indexar":
                with st.spinner("🔄 Reconstruyendo índice semántico..."):
                    try:
                        from core.indexer import construir_indice
                        indice = construir_indice()
                        st.success(f"✅ {len(indice)} archivos indexados en ChromaDB")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            # !LIMPIAR
            elif comando in ["!limpiar", "!limpiar_historial"]:
                n = ver_historial()['cantidad']
                if n == 0:
                    st.info("ℹ️ Ya está vacío")
                else:
                    limpiar_historial()
                    st.session_state.messages = []
                    st.success(f"🗑️ {n} interacciones eliminadas")

            # !HISTORIAL
            elif comando == "!historial":
                info = ver_historial()
                st.info(f"📜 Historial: {info['cantidad']} / {info['maximo']}")

            # !CATEGORIAS
            elif comando == "!categorias":
                try:
                    cats = listar_categorias()
                    st.info("📂 Categorías: " + ", ".join(cats) if cats else "Sin categorías")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

            # !AGENTES
            elif comando == "!agentes":
                try:
                    ags = listar_agentes()
                    for k, v in ags.items():
                        st.markdown(f"• **{k}**: {v}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

            # !SEGURIDAD
            elif comando == "!seguridad":
                with st.spinner("🛡️ Generando reporte..."):
                    st.json(reporte_seguridad_completo())

            # !AUTOCONOCER
            elif comando == "!autoconocer":
                with st.spinner("🪞 Analizando..."):
                    try:
                        from core.self_awareness import generar_reporte_self_awareness
                        st.code(generar_reporte_self_awareness(), language="markdown")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            # !AUTOCONOCER_CORTO
            elif comando == "!autoconocer_corto":
                with st.spinner("🪞 Resumen..."):
                    try:
                        from core.self_awareness import generar_reporte_sin_codigo
                        st.markdown(generar_reporte_sin_codigo())
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            # !INFORME
            elif comando in ["!informe", "!exportar_informe"]:
                with st.spinner("📄 Exportando..."):
                    try:
                        from core.self_awareness import exportar_reporte_a_archivo
                        ruta = exportar_reporte_a_archivo()
                        st.success(f"✅ Exportado: {ruta}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            # !EXAMEN
            elif comando == "!examen":
                if not args:
                    st.warning("Usá: `!examen [material] capítulos X al Y [especificaciones]`")
                else:
                    pregunta_examen = " ".join(args)
                    with st.spinner("🧠 Atlas está preparando tu examen..."):
                        try:
                            examen_data = ejecutar_examen_completo(
                                pregunta_examen,
                                motor=st.session_state.get("motor_activo", "atlas"),
                                modelo_nube=st.session_state.get("modelo_nube", "meta/llama-3.1-70b-instruct") if st.session_state.get("motor_activo", "atlas") == "prometeo" else None
                            )
                            if not examen_data.get("preguntas"):
                                st.error("❌ No se pudo generar el examen.")
                            else:
                                st.success(f"✅ Examen generado: {examen_data['total_preguntas']} preguntas")
                                st.session_state.examen_activo = {
                                    "preguntas": examen_data["preguntas"],
                                    "respuestas": [],
                                    "inicio": datetime.now()
                                }
                                st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

            # !REFLEXIONAR
            elif comando == "!reflexionar":
                with st.spinner("🧘 Reflexionando..."):
                    try:
                        from core.reflection import reflexionar_sobre_conversaciones
                        st.markdown(reflexionar_sobre_conversaciones(HISTORIAL))
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            # !MEJORAR
            elif comando == "!mejorar":
                with st.spinner("🔍 Buscando..."):
                    try:
                        from core.self_improvement import buscar_mejores_practicas
                        res = buscar_mejores_practicas("RAG local LLM")
                        st.info(f"📚 {len(res)} recursos:")
                        for i, r in enumerate(res[:5], 1):
                            if "error" not in r:
                                st.markdown(f"**[{i}] {r.get('titulo', '')}**")
                                st.caption(f"🔗 {r.get('url', '')}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

            else:
                st.warning(f"⚠️ Comando no reconocido: `{comando}`. Escribí `!ayuda`.")

        st.session_state.messages.append({"role": "assistant", "content": f"[Comando ejecutado: {comando}]"})
        agregar_mensaje("assistant", f"[Comando ejecutado: {comando}]")

    # ========================================
    # CHAT NORMAL (no es comando)
    # ========================================
    else:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            respuesta_completa = ""
            agente_detectado = None
            pensamiento = None
            error_msg = None

            # Setup thread communication
            q = Queue()

            # Capturar valores de sesión ANTES de lanzar el thread
            _motor_chat = st.session_state.get("motor_activo", "atlas")
            _modelo_nube_chat = st.session_state.get("modelo_nube", "meta/llama-3.1-70b-instruct")
            _modelo_local_chat = st.session_state.get("modelo_local", "qwen3:8b")
            _modelo_groq_chat = st.session_state.get("modelo_groq", "llama-3.3-70b-versatile")

            def worker():
                try:
                    for p, r in pensar_con_streaming(
                        prompt,
                        motor=_motor_chat,
                        modelo_nube=_modelo_nube_chat if _motor_chat == "prometeo" else None,
                        modelo_local=_modelo_local_chat if _motor_chat == "atlas" else None,
                        modelo_groq=_modelo_groq_chat if _motor_chat == "groq" else None
                    ):
                        q.put(("chunk", p, r))
                    q.put(("done", None, None))
                except Exception as e:
                    q.put(("error", None, str(e)))

            t = threading.Thread(target=worker, daemon=True)
            t.start()

            msg_id = len(st.session_state.messages)

            while True:
                try:
                    msg_type, p, r = q.get(timeout=0.1)
                    if msg_type == "chunk":
                        if p and p.startswith("[Agente:"):
                            agente_detectado = p
                        if p and not pensamiento:
                            pensamiento = p
                        if r:
                            respuesta_completa = r
                            message_placeholder.markdown(respuesta_completa + "▌")
                    elif msg_type == "done":
                        break
                    elif msg_type == "error":
                        error_msg = r
                        break
                except Empty:
                    pass

                time.sleep(0.05)

            if respuesta_completa:
                message_placeholder.markdown(respuesta_completa)
            elif not error_msg:
                message_placeholder.warning("No pude generar respuesta.")

            if error_msg:
                message_placeholder.error(f"❌ Error: {error_msg}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_msg}"})
                agregar_mensaje("assistant", f"Error: {error_msg}")
            elif respuesta_completa:
                if agente_detectado:
                    st.caption(agente_detectado)
                if pensamiento:
                    with st.expander("💭 Pensamiento de Atlas"):
                        st.markdown(pensamiento)
                message_placeholder.markdown(respuesta_completa)
                if st.session_state.voz_activa and respuesta_completa:
                    hablar(respuesta_completa)
                st.session_state.messages.append({"role": "assistant", "content": respuesta_completa})
                agregar_mensaje("assistant", respuesta_completa)

# ============================================
# SECCIÓN DE EXAMEN
# ============================================
if st.session_state.examen_activo:
    with st.container():
        st.divider()
        renderizar_examen()

# ============================================
# MODAL DE AYUDA (si se solicitó en este turno)
# ============================================
if st.session_state.pop("_mostrar_ayuda", False):
    _render_ayuda_modal()

# ============================================
# FOOTER
# ============================================
st.divider()
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.caption("Atlas v3.7 | RAG Semántico + Multi-Nube (NVIDIA/Groq) + Chats Múltiples | 09/07/2026")