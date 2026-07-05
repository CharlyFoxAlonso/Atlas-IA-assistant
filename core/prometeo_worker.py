"""
core/prometeo_worker.py
Procesa texto crudo usando Prometeo (NVIDIA API) para ingestión en RAG.
Soporta chunking automático con PARALELISMO (4 workers) para máxima velocidad.
Atlas v2.9
"""
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # ✅ CORREGIDO: __name__

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

MODELOS_DIGESTION = [
    "meta/llama-3.1-70b-instruct",
    "deepseek-ai/deepseek-v4-pro",
    "nvidia/nemotron-3-ultra-550b-a55b"
]


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("API Key de Prometeo no configurada en .env")
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
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


def _procesar_chunk(client: OpenAI, chunk: str, modelo: str, numero: int, total: int) -> str:
    """Procesa un chunk individual (thread-safe)."""
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
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.2,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error procesando chunk {numero}/{total}: {str(e)}")
        return f"\n\n⚠️ Error procesando parte {numero}: {str(e)}\n"


def digerir_documento_con_progreso(texto_crudo: str, nombre_original: str, url_origen: str, modelo: str = None, max_workers: int = 4):
    """
    Versión generadora con PARALELISMO que reporta progreso entre chunks.
    Procesa múltiples chunks simultáneamente para máxima velocidad.

    Args:
        texto_crudo: Texto a procesar
        nombre_original: Nombre del archivo original
        url_origen: URL o fuente del documento
        modelo: Modelo de NVIDIA a usar
        max_workers: Número de chunks a procesar en paralelo (default: 4)
    """
    if not texto_crudo or len(texto_crudo.strip()) < 100:
        yield {"estado": "error", "mensaje": "⚠️ El documento no tiene contenido suficiente"}
        return

    client = _get_client()
    modelo = modelo or MODELOS_DIGESTION[0]

    # Si es muy largo, usar chunking con PARALELISMO
    if len(texto_crudo) > 80000:
        chunks = _chunk_text(texto_crudo)
        total_chunks = len(chunks)
        yield {
            "estado": "chunking",
            "mensaje": f"📄 Documento grande detectado. Dividido en {total_chunks} partes. Procesando con {max_workers} workers en paralelo..."
        }

        # Pre-allocar lista de resultados
        resultados = [None] * total_chunks

        # Procesar chunks en PARALELO
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Crear futures para cada chunk
            futures = {
                executor.submit(_procesar_chunk, client, chunk, modelo, i+1, total_chunks): i
                for i, chunk in enumerate(chunks)
            }

            # Procesar resultados a medida que se completan
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
                    "mensaje": f"⚡ Procesando parte {completados}/{total_chunks} ({completados/total_chunks*100:.0f}%)",
                    "progreso": (completados / total_chunks) * 100
                }

        # Unir resultados en orden
        texto_final = "\n\n---\n\n".join([r for r in resultados if r])
        metadata = f"# {nombre_original}\n\n> Fuente: {url_origen}\n> Procesado en {total_chunks} partes por Prometeo (paralelo con {max_workers} workers)\n\n"

        yield {
            "estado": "completado",
            "mensaje": f"✅ Documento procesado ({total_chunks} partes en paralelo)",
            "texto": metadata + texto_final
        }

    else:
        # Procesamiento directo (un solo chunk, sin paralelismo)
        yield {
            "estado": "procesando",
            "mensaje": "⚡ Prometeo está digiriendo el documento...",
            "progreso": 50
        }
        try:
            texto_final = _procesar_chunk(client, texto_crudo, modelo, 1, 1)
            yield {
                "estado": "completado",
                "mensaje": "✅ Documento procesado",
                "texto": texto_final
            }
        except Exception as e:
            yield {
                "estado": "error",
                "mensaje": f"❌ Error en Prometeo: {str(e)}"
            }


# Mantener la función original para compatibilidad
def digerir_documento(texto_crudo: str, nombre_original: str, url_origen: str, modelo: str = None) -> str:
    """Versión simple que devuelve solo el texto final."""
    resultado_final = ""
    for paso in digerir_documento_con_progreso(texto_crudo, nombre_original, url_origen, modelo):
        if paso["estado"] == "completado":
            resultado_final = paso["texto"]
        elif paso["estado"] == "error":
            raise Exception(paso["mensaje"])
    return resultado_final


if __name__ == "__main__":  # ✅ CORREGIDO: __name__ == "__main__"
    # Test simple
    texto_prueba = "Este es un texto de prueba para verificar que el worker funciona correctamente."
    print("Probando Prometeo Worker...")
    for paso in digerir_documento_con_progreso(texto_prueba, "test.txt", "test"):
        print(paso)