"""
core/digestion_worker.py
Worker de digestión unificado para Atlas v3.9.
Soporta motores: "atlas" (Ollama local) y "prometeo" (NVIDIA API).
Procesa texto crudo → documento Markdown estructurado para indexación RAG.
"""
import os
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv
from core.security import log_seguridad

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROMPT_DIGESTION = """
Sos un experto en sistematización de conocimiento jurídico y académico.
Tu tarea es procesar el texto crudo adjunto y convertirlo en un documento Markdown estructurado, optimizado para ser indexado en un sistema RAG.

REGLAS DE PROCESAMIENTO:
Título: Generá un título claro y descriptivo al inicio (como encabezado H1).
Resumen Ejecutivo: 3 a 5 oraciones con la idea central del documento.
Conceptos Clave: Extraé los términos técnicos, artículos de ley, doctrinas o fórmulas mencionadas. Usá una lista con viñetas.
Desarrollo Estructurado: Usá encabezados (##, ###) para organizar el contenido por temas. Mantené la lógica original del texto.
Citas Textuales: Si hay definiciones legales o citas importantes, usá blockquotes (>).
Limpieza: Eliminá ruido (números de página sueltos, headers/footers de PDF, enlaces rotos, caracteres raros).
Fidelidad: NO inventes información. Si algo no está claro en el texto original, marcá con [texto ilegible] o [sección incompleta].

FORMATO DE SALIDA:
Devuelve SOLO el Markdown estructurado. No incluyas preámbulos como "Aquí está el resumen" ni cierres como "Espero que te sirva".
"""

MODELOS_NUBE_DIGESTION = [
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.3-70b-instruct",
    "deepseek-ai/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-pro",
    "google/gemma-3-12b-it",
    "google/gemma-4-31b-it",
    "nvidia/nemotron-3-ultra-550b-a55b",
]

MODELOS_GROQ_DIGESTION = [
    "llama-3.3-70b-versatile",
    "llama-3.3-8b-instant",
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
]

URL_OLLAMA = os.getenv("URL_OLLAMA", "http://127.0.0.1:11434/api/chat")


def _get_client_nvidia() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("API Key de NVIDIA no configurada en .env")
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )


def _chunk_text(texto: str, max_chars: int = 80000) -> list:
    """Divide el texto en chunks de máximo max_chars caracteres."""
    if len(texto) <= max_chars:
        return [texto]

    chunks = []
    inicio = 0
    while inicio < len(texto):
        fin = inicio + max_chars
        if fin < len(texto):
            ultimo_salto = texto.rfind("\n\n", inicio, fin)
            if ultimo_salto > inicio + (max_chars // 2):
                fin = ultimo_salto
        chunks.append(texto[inicio:fin])
        inicio = fin
    return chunks


def _procesar_chunk_nvidia(client: OpenAI, chunk: str, modelo: str, numero: int, total: int) -> str:
    """Procesa un chunk via NVIDIA API (thread-safe)."""
    prompt_usuario = f"""
Nombre original del archivo: (documento en proceso)
Parte {numero} de {total}

TEXTO CRUDO A PROCESAR:
{chunk}
"""
    try:
        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": PROMPT_DIGESTION},
                {"role": "user", "content": prompt_usuario},
            ],
            temperature=0.2,
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error NVIDIA chunk {numero}/{total}: {e}")
        return f"\n\n⚠️ Error procesando parte {numero}: {str(e)}\n"


def _procesar_chunk_ollama(chunk: str, modelo: str, numero: int, total: int) -> str:
    """Procesa un chunk via Ollama local HTTP."""
    prompt_usuario = f"""
Nombre original del archivo: (documento en proceso)
Parte {numero} de {total}

TEXTO CRUDO A PROCESAR:
{chunk}
"""
    try:
        resp = requests.post(
            URL_OLLAMA,
            json={
                "model": modelo,
                "messages": [
                    {"role": "system", "content": PROMPT_DIGESTION},
                    {"role": "user", "content": prompt_usuario},
                ],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=300,
        )
        if resp.status_code != 200:
            return f"\n\n⚠️ Error Ollama chunk {numero}: HTTP {resp.status_code}\n"
        data = resp.json()
        return data.get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"Error Ollama chunk {numero}/{total}: {e}")
        return f"\n\n⚠️ Error procesando parte {numero}: {str(e)}\n"


def _verificar_modelo_ollama(modelo: str) -> bool:
    """Verifica que el modelo exista localmente en Ollama."""
    try:
        resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if resp.status_code != 200:
            return False
        modelos = [m.get("name", "") for m in resp.json().get("models", [])]
        return modelo in modelos or any(m.startswith(modelo + ":") for m in modelos)
    except Exception:
        return False


def digerir_documento_con_progreso(
    texto_crudo: str,
    nombre_original: str,
    url_origen: str,
    motor: str = "atlas",
    modelo: str = None,
    max_workers: int = 4,
):
    """
    Worker de digestión unificado. Generador que reporta progreso.

    Args:
        texto_crudo:     Texto a procesar.
        nombre_original: Nombre del archivo original.
        url_origen:      URL o fuente del documento.
        motor:           "atlas" (Ollama local) o "prometeo" (NVIDIA API).
        modelo:          Modelo específico. Si es None se usa el default.
        max_workers:     Número de chunks en paralelo.
    """
    if not texto_crudo or len(texto_crudo.strip()) < 100:
        yield {"estado": "error", "mensaje": "⚠️ El documento no tiene contenido suficiente"}
        return

    motor = motor.lower()
    if motor not in ("atlas", "prometeo", "groq"):
        yield {"estado": "error", "mensaje": f"❌ Motor de digestión no válido: {motor}"}
        return

    if modelo is None:
        if motor == "prometeo":
            from core.config import MODELO_NUBE_DEFAULT
            modelo = MODELO_NUBE_DEFAULT
        elif motor == "groq":
            from core.config import MODELO_GROQ_DEFAULT
            modelo = MODELO_GROQ_DEFAULT
        else:
            from core.config import MODELO_LOCAL
            modelo = MODELO_LOCAL

    if motor == "atlas":
        if not _verificar_modelo_ollama(modelo):
            log_seguridad("DIGESTION_MODELO_INVALIDO", f"Modelo Ollama no descargado: {modelo}")
            yield {
                "estado": "error",
                "mensaje": f"❌ Modelo local '{modelo}' no está descargado en Ollama. Descargalo con `ollama pull {modelo}` desde la terminal.",
            }
            return

    log_seguridad("DIGESTION_INICIADA", f"motor={motor} modelo={modelo} archivo={nombre_original}")

    if motor == "atlas":
        nombre_motor = "Atlas Local"
    elif motor == "groq":
        nombre_motor = "Groq Cloud"
    else:
        nombre_motor = "Prometeo Nube"

    if len(texto_crudo) > 80000:
        chunks = _chunk_text(texto_crudo)
        total_chunks = len(chunks)
        yield {
            "estado": "chunking",
            "mensaje": f"📄 Documento grande. Dividido en {total_chunks} partes. Procesando con {nombre_motor} ({modelo})..."
        }

        resultados = [None] * total_chunks

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            if motor == "prometeo":
                client = _get_client_nvidia()
                futures = {
                    executor.submit(_procesar_chunk_nvidia, client, c, modelo, i + 1, total_chunks): i
                    for i, c in enumerate(chunks)
                }
            else:
                futures = {
                    executor.submit(_procesar_chunk_ollama, c, modelo, i + 1, total_chunks): i
                    for i, c in enumerate(chunks)
                }

            completados = 0
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    resultados[idx] = future.result()
                except Exception as e:
                    resultados[idx] = f"\n\n⚠️ Error procesando parte {idx+1}: {str(e)}\n"
                completados += 1
                yield {
                    "estado": "procesando_chunk",
                    "mensaje": f"⚡ {nombre_motor} → parte {completados}/{total_chunks} ({completados/total_chunks*100:.0f}%)",
                    "progreso": (completados / total_chunks) * 100,
                }

        texto_final = "\n\n---\n\n".join([r for r in resultados if r])
        metadata = f"# {nombre_original}\n\n> Fuente: {url_origen}\n> Procesado con {nombre_motor} ({modelo})\n\n"

        log_seguridad("DIGESTION_OK", f"motor={motor} modelo={modelo} chunks={total_chunks} archivo={nombre_original}")
        yield {
            "estado": "completado",
            "mensaje": f"✅ Documento procesado ({total_chunks} partes con {nombre_motor})",
            "texto": metadata + texto_final,
        }
    else:
        yield {
            "estado": "procesando",
            "mensaje": f"⚡ {nombre_motor} digiriendo el documento ({modelo})...",
            "progreso": 50,
        }
        try:
            if motor == "prometeo":
                client = _get_client_nvidia()
                texto_final = _procesar_chunk_nvidia(client, texto_crudo, modelo, 1, 1)
            else:
                texto_final = _procesar_chunk_ollama(texto_crudo, modelo, 1, 1)

            log_seguridad("DIGESTION_OK", f"motor={motor} modelo={modelo} archivo={nombre_original}")
            yield {
                "estado": "completado",
                "mensaje": "✅ Documento procesado",
                "texto": texto_final,
            }
        except Exception as e:
            log_seguridad("DIGESTION_ERROR", f"motor={motor} modelo={modelo} error={e}")
            yield {
                "estado": "error",
                "mensaje": f"❌ Error en digestión: {str(e)}",
            }


def digerir_documento(texto_crudo: str, nombre_original: str, url_origen: str,
                      motor: str = "atlas", modelo: str = None) -> str:
    """Versión simple que devuelve solo el texto final."""
    resultado_final = ""
    for paso in digerir_documento_con_progreso(texto_crudo, nombre_original, url_origen, motor=motor, modelo=modelo):
        if paso["estado"] == "completado":
            resultado_final = paso["texto"]
        elif paso["estado"] == "error":
            raise Exception(paso["mensaje"])
    return resultado_final


if __name__ == "__main__":
    print("Probando Digestion Worker...")
    motor_test = os.getenv("ATLAS_TEST_MOTOR", "atlas")
    modelo_test = os.getenv("ATLAS_TEST_MODELO", None)
    texto = "Este es un texto de prueba para verificar que el worker de digestión funciona correctamente."
    for paso in digerir_documento_con_progreso(
        texto, "test.txt", "test", motor=motor_test, modelo=modelo_test, max_workers=1
    ):
        print(paso)