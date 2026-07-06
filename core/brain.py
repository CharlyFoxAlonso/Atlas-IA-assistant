"""
Cerebro principal de Atlas & Prometeo v3.2
Con RAG semántico (ChromaDB), detección de capítulos, reglas temporales inteligentes,
y streaming híbrido (Ollama local / NVIDIA API).
"""
import os
import io
import re
import json
import requests
from contextlib import redirect_stdout
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

from core.file_loader import leer_archivo_estudio
from core.memory_manager import analizar_conversacion
from core.router import detectar_agente_con_modelo, cargar_prompt_agente
from core.web_search import buscar_web, formatear_resultados_web
from core.security import log_seguridad
from core.vector_store import buscar_relevante, busqueda_hibrida
from core.temp_rules import (
    obtener_contexto_reglas,
    verificar_reglas_y_forzar_respuesta,
    obtener_reglas_de_formato
)

# ============================================
# CONFIGURACIÓN
# ============================================
try:
    from core.config import BASE_ESTUDIO as _CFG_BASE_ESTUDIO, BASE_PROMPTS as _CFG_BASE_PROMPTS, MAX_HISTORIAL as _CFG_MAX_HISTORIAL
    BASE_ESTUDIO = _CFG_BASE_ESTUDIO
    BASE_PROMPTS = _CFG_BASE_PROMPTS
    MAX_HISTORIAL = _CFG_MAX_HISTORIAL
except Exception:
    BASE_ESTUDIO = "memory/Atlas_Memory/03_Conocimiento"
    BASE_PROMPTS = "memory/Atlas_Memory/00_Sistema/Prompts"
    MAX_HISTORIAL = 5

HISTORIAL = []


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def cargar_perfil_charly():
    """Carga el perfil de Charly."""
    ruta = os.path.join(BASE_PROMPTS, "Perfil_Charly.md")
    if os.path.exists(ruta):
        f = io.StringIO()
        with redirect_stdout(f):
            contenido = leer_archivo_estudio(ruta)
        return contenido if contenido else ""
    return ""


def cargar_material_estudio():
    """Carga TODO el material de estudio (SOLO para casos especiales)."""
    contenido_total = ""
    if not os.path.exists(BASE_ESTUDIO):
        return contenido_total
    for root, _, files in os.walk(BASE_ESTUDIO):
        for f in files:
            if f.endswith((".md", ".pdf", ".txt")):
                path = os.path.join(root, f)
                f_io = io.StringIO()
                with redirect_stdout(f_io):
                    data = leer_archivo_estudio(path)
                if data:
                    contenido_total += f"\n\n===== {f} =====\n{data}"
    return contenido_total


def buscar_en_rag_semantico(pregunta, n_results=5, filtro_capitulo=None, palabras_clave=None, modo_hibrido=False):
    """
    Busca chunks relevantes en ChromaDB usando embeddings semánticos.
    """
    try:
        if modo_hibrido:
            resultados = busqueda_hibrida(
                pregunta,
                n_results=max(n_results, 15),
                palabras_clave=palabras_clave,
                umbral_semantico=200
            )
        else:
            resultados = buscar_relevante(
                pregunta,
                n_results=n_results,
                filtro_capitulo=filtro_capitulo
            )

        if not resultados:
            return "", []

        chunks_texto = []
        archivos_usados = []
        for i, r in enumerate(resultados, 1):
            metadata = r.get("metadata", {})
            nombre_archivo = metadata.get("nombre", "Desconocido")
            capitulo = metadata.get("capitulo", "")
            texto = r.get("texto", "")
            cap_info = f", {capitulo}" if capitulo else ""
            chunks_texto.append(f"\n--- Chunk {i} (de: {nombre_archivo}{cap_info}) ---\n{texto}")
            if nombre_archivo not in archivos_usados:
                archivos_usados.append(nombre_archivo)
        return "\n".join(chunks_texto), archivos_usados
    except Exception as e:
        log_seguridad("RAG_SEARCH_ERROR", str(e))
        return "", []


def reescribir_query(pregunta):
    """Detecta si la pregunta menciona capítulos específicos."""
    match = re.search(r'cap[íi]tulos?\s+(\d+)\s+(?:al|a|y)\s+(\d+)', pregunta, re.IGNORECASE)
    if match:
        cap_inicio = int(match.group(1))
        cap_fin = int(match.group(2))
        return [f"capitulo_{i}" for i in range(cap_inicio, cap_fin + 1)]

    match_single = re.search(r'cap[íi]tulo\s+(\d+)', pregunta, re.IGNORECASE)
    if match_single:
        return [f"capitulo_{match_single.group(1)}"]

    return None


def agregar_al_historial(pregunta, respuesta):
    """Agrega interacción al historial."""
    HISTORIAL.append({"pregunta": pregunta, "respuesta": respuesta})
    if len(HISTORIAL) > MAX_HISTORIAL:
        HISTORIAL.pop(0)


def formatear_historial():
    """Formatea historial para el prompt."""
    if not HISTORIAL:
        return ""
    texto = "\n========================\nHISTORIAL DE CONVERSACIÓN:\n"
    for i, item in enumerate(HISTORIAL, 1):
        texto += f"\n{i}. Charly: {item['pregunta']}\n"
        texto += f"   Atlas: {item['respuesta'][:300]}...\n"
    return texto


def limpiar_historial():
    """Limpia el historial."""
    HISTORIAL.clear()
    return True


def set_historial(nuevo: list):
    """
    Reemplaza el historial global con una lista externa.
    Usado por chat_manager al cambiar de pestaña de chat.
    """
    HISTORIAL.clear()
    HISTORIAL.extend(nuevo)


def get_historial() -> list:
    """
    Devuelve una copia del historial global.
    Usado por chat_manager para persistir el historial al guardar.
    """
    return list(HISTORIAL)


def ver_historial():
    """Devuelve info del historial."""
    return {
        "cantidad": len(HISTORIAL),
        "maximo": MAX_HISTORIAL,
        "items": HISTORIAL.copy()
    }


def verificar_fuentes(resultados_web):
    """Verifica que los resultados web tengan URLs válidas."""
    resultados_validos = []
    for r in resultados_web:
        url = r.get("url", "") or r.get("href", "")
        if url and (url.startswith("http://") or url.startswith("https://")):
            resultados_validos.append(r)
    return resultados_validos


# ============================================
# STREAMING HÍBRIDO
# ============================================

def _stream_local(prompt_completo, modelo="qwen3:8b"):
    """Streaming desde Ollama local (Atlas)."""
    try:
        url = "http://127.0.0.1:11434/api/chat"
        data = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt_completo}],
            "stream": True
        }
        with requests.post(url, json=data, stream=True, timeout=120) as r:
            r.raise_for_status()
            for linea in r.iter_lines():
                if linea:
                    try:
                        chunk = json.loads(linea)
                        if "message" in chunk and "content" in chunk["message"]:
                            yield chunk["message"]["content"]
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        log_seguridad("STREAM_LOCAL_ERROR", str(e))
        yield f"❌ Error en Atlas local: {e}"


def _stream_nube(prompt_completo, modelo_nube="meta/llama-3.1-70b-instruct"):
    """Streaming desde NVIDIA API (Prometeo)."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        yield "❌ Error: No se encontró API Key en .env"
        return

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        stream = client.chat.completions.create(
            model=modelo_nube,
            messages=[{"role": "user", "content": prompt_completo}],
            temperature=0.3,
            max_tokens=2048,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        log_seguridad("STREAM_NUBE_ERROR", str(e))
        yield f"❌ Error en Prometeo: {e}"


# ============================================
# FUNCIÓN PRINCIPAL CON INTERCEPTACIÓN DE REGLAS
# ============================================

def pensar_con_streaming(pregunta, motor=None, modelo_nube=None, modelo_local=None):
    """Generador principal con interceptación de reglas ANTES de enviar al modelo."""
    if motor is None:
        motor = os.getenv("MOTOR_POR_DEFECTO", "atlas").lower()
    if modelo_nube is None:
        modelo_nube = "meta/llama-3.1-70b-instruct"
    if modelo_local is None:
        modelo_local = os.getenv("MODELO_LOCAL", "qwen3:8b")

    # ⚠️ INTERCEPTACIÓN DE REGLAS: Verificar ANTES de procesar
    debe_forzar, respuesta_forzada = verificar_reglas_y_forzar_respuesta(pregunta)
    if debe_forzar:
        yield f"[Agente: interceptado] [Motor: reglas]", None
        yield None, respuesta_forzada
        agregar_al_historial(pregunta, respuesta_forzada)
        return

    # --------------------------------------------------------
    # FLUJO NORMAL (sin interceptor financiero)
    # --------------------------------------------------------
    perfil = cargar_perfil_charly()
    historial_contexto = formatear_historial()

    reglas_contexto = obtener_contexto_reglas()
    reglas_formato = obtener_reglas_de_formato()

    try:
        agente = detectar_agente_con_modelo(pregunta)
    except Exception as e:
        agente = "general"
        log_seguridad("ERROR_ROUTER", str(e))

    yield f"[Agente: {agente}] [Motor: {motor}]", None

    prompt_agente = cargar_prompt_agente(agente)

    # ============================
    # RESEARCHER (BÚSQUEDA SEMÁNTICA + WEB)
    # ============================
    if agente == "researcher":
        yield None, "📚 Buscando en tu base de conocimiento..."
        capitulos_buscar = reescribir_query(pregunta)
        material_local = ""
        archivos_usados = []

        if capitulos_buscar:
            yield None, f"📖 Buscando en capítulos: {', '.join(capitulos_buscar)}"
            for cap in capitulos_buscar[:3]:
                chunks_cap, archivos_cap = buscar_en_rag_semantico(
                    pregunta,
                    n_results=3,
                    filtro_capitulo=cap
                )
                material_local += chunks_cap
                archivos_usados.extend(archivos_cap)
            archivos_usados = list(set(archivos_usados))
        else:
            material_local, archivos_usados = buscar_en_rag_semantico(pregunta, n_results=7)

        if archivos_usados:
            yield None, f"📖 Encontré {len(archivos_usados)} archivos relevantes: {', '.join(archivos_usados[:3])}"
        else:
            yield None, "⚠️ No encontré material local relevante"

        yield None, "🔍 Buscando en fuentes web..."
        resultados_web = buscar_web(pregunta, max_resultados=5)
        resultados_web = verificar_fuentes(resultados_web)

        if len(resultados_web) < 3:
            palabras_clave = " ".join([p for p in pregunta.split() if len(p) > 4][:5])
            resultados_alt = buscar_web(palabras_clave, max_resultados=5)
            resultados_web.extend(verificar_fuentes(resultados_alt))

        urls_vistas = set()
        resultados_unicos = []
        for r in resultados_web:
            url = r.get("url", "") or r.get("href", "")
            if url and url not in urls_vistas:
                urls_vistas.add(url)
                resultados_unicos.append(r)

        contenido_web = formatear_resultados_web(resultados_unicos)

        contexto = f"""
{prompt_agente}
{perfil}
{historial_contexto}
{reglas_contexto}

MATERIAL DE ESTUDIO LOCAL (Chunks semánticos relevantes - PRIORIDAD ALTA):
{material_local if material_local else "No hay material local relevante."}

RESULTADOS DE BÚSQUEDA WEB (Complemento):
{contenido_web}

PREGUNTA: {pregunta}

INSTRUCCIONES CRÍTICAS:
PRIMERO usá el MATERIAL DE ESTUDIO LOCAL (tus archivos del RAG) como fuente principal.
Si el material local tiene la información, citá el archivo específico: "Según [nombre del archivo]..."
Si el material local no tiene suficiente información, complementá con las fuentes web.
Citá las fuentes: "Según [nombre del archivo PDF/MD]..." o "Según [URL web]..."
Si NO hay información en el RAG ni en la web, decí EXPLÍCITAMENTE: "No encontré información verificable sobre esto."
NO inventes datos. Si no estás seguro, aclaralo.
Si la pregunta menciona capítulos específicos, enfocá tu respuesta SOLO en esos capítulos.
"""

    # ============================
    # ESTADISTICA (BÚSQUEDA SEMÁNTICA)
    # ============================
    elif agente == "estadistica":
        yield None, "📚 Buscando en tus apuntes de estadística..."
        material_local, archivos_usados = buscar_en_rag_semantico(pregunta, n_results=5)
        if archivos_usados:
            yield None, f"📖 Encontré {len(archivos_usados)} archivos relevantes: {', '.join(archivos_usados[:3])}"

        contexto = f"""
{prompt_agente}
{perfil}
{historial_contexto}
{reglas_contexto}

MATERIAL DE ESTUDIO LOCAL (Chunks semánticos relevantes):
{material_local if material_local else "No hay material local relevante."}

PREGUNTA: {pregunta}

INSTRUCCIONES CRÍTICAS:
PRIMERO buscá la respuesta en el material de estudio local (tus apuntes).
Si está en tus apuntes, citá el PDF específico: "Según la Clase X de Estadística..."
Si NO está en tus apuntes, aclará: "Este concepto no está en tus apuntes, pero según fuentes generales..."
Usá SIEMPRE ejemplos concretos de la vida real.
"""

    # ============================
    # MENTOR, ARQUITECTO, GENERAL
    # ============================
    else:
        contexto = f"""
{prompt_agente}
{perfil}
{historial_contexto}
{reglas_contexto}

PREGUNTA DE CHARLY:
{pregunta}
"""

    # --------------------------------------------------------
    # PROMPT FINAL
    # --------------------------------------------------------
    prompt_final = f"""
{contexto}

INSTRUCCIONES FINALES:
Seguí tu estilo definido en el prompt del agente.
Devolvé SOLO la respuesta final sin preámbulos.
{reglas_formato}
"""

    if motor == "prometeo":
        stream_generator = _stream_nube(prompt_final, modelo_nube)
    else:
        stream_generator = _stream_local(prompt_final, modelo_local)

    respuesta_completa = ""
    error_final = None
    try:
        for chunk in stream_generator:
            if not chunk:
                continue
            respuesta_completa += chunk
            yield None, respuesta_completa
    except Exception as e:
        error_final = e
        log_seguridad("ERROR_RESPUESTA", str(e))

    if respuesta_completa:
        try:
            agregar_al_historial(pregunta, respuesta_completa)
        except Exception as e:
            log_seguridad("ERROR_HISTORIAL", str(e))

    if error_final is not None:
        yield None, f"Error: {str(error_final)}"


def analizar_para_memoria(pregunta, respuesta):
    """Delega el análisis al memory_manager."""
    return analizar_conversacion(pregunta, respuesta)