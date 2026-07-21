"""
core/local_ingestion_manager.py
Orquesta la ingestión de archivos LOCALES (Drag & Drop) hacia el RAG.
Con PARALELISMO (4 workers) para máxima velocidad en la digestión.
Atlas v4
"""
import os
import hashlib
from datetime import datetime
from core.digestion_worker import digerir_documento_con_progreso
from core.security import log_seguridad

RAG_BASE_PATH = "memory/Atlas_Memory"
TEMP_DIR = "temp_local_ingestion"

FORMATOS_MULTIMEDIA = {
    '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma', '.opus',
    '.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'
}


def _generar_hash_archivo(nombre: str) -> str:
    """Genera un hash corto basado en el nombre del archivo."""
    return hashlib.md5(nombre.encode()).hexdigest()[:8]


def normalizar_nombre(nombre_original: str) -> str:
    """Genera un nombre normalizado para el archivo final en el RAG."""
    fecha = datetime.now().strftime("%Y-%m-%d %H-%M")
    hash_archivo = _generar_hash_archivo(nombre_original)
    base = os.path.splitext(nombre_original)[0].replace(" ", "_")[:30]
    return f"Local_{fecha}_{base}_{hash_archivo}.md"


def detectar_carpetas_atlas_memory() -> list:
    """
    Detecta automáticamente todas las carpetas disponibles en Atlas_Memory.
    Devuelve lista de rutas relativas (ej: ["03_Conocimiento/Estudio", "05_Proyectos"])
    """
    carpetas = []
    
    if not os.path.exists(RAG_BASE_PATH):
        return ["03_Conocimiento/General"]  # Default si no existe
    
    # Recorrer todas las carpetas de Atlas_Memory
    for item in os.listdir(RAG_BASE_PATH):
        ruta_completa = os.path.join(RAG_BASE_PATH, item)
        
        if os.path.isdir(ruta_completa) and not item.startswith('.'):
            # Agregar la carpeta principal
            carpetas.append(item)
            
            # Agregar subcarpetas (un nivel de profundidad)
            for subitem in os.listdir(ruta_completa):
                ruta_subcarpeta = os.path.join(ruta_completa, subitem)
                if os.path.isdir(ruta_subcarpeta) and not subitem.startswith('.'):
                    carpetas.append(f"{item}/{subitem}")
    
    # Ordenar alfabéticamente
    carpetas.sort()
    
    # Si está vacío, agregar default
    if not carpetas:
        carpetas = ["03_Conocimiento/General"]
    
    return carpetas


def crear_subcarpeta(ruta_relativa: str) -> dict:
    """
    Crea una subcarpeta en Atlas_Memory si no existe.
    Args:
        ruta_relativa: Ruta relativa desde Atlas_Memory (ej: "05_Proyectos/balance_julio")
    Returns:
        Dict con estado y mensaje
    """
    try:
        ruta_completa = os.path.join(RAG_BASE_PATH, ruta_relativa)
        
        if os.path.exists(ruta_completa):
            return {
                "exito": True,
                "mensaje": f"✅ La carpeta '{ruta_relativa}' ya existe"
            }
        
        os.makedirs(ruta_completa, exist_ok=True)
        log_seguridad("SUBCARPETA_CREADA", f"Subcarpeta creada: {ruta_relativa}")
        
        return {
            "exito": True,
            "mensaje": f"✅ Subcarpeta creada: {ruta_relativa}"
        }
    except Exception as e:
        log_seguridad("SUBCARPETA_ERROR", f"Error creando subcarpeta: {str(e)}")
        return {
            "exito": False,
            "mensaje": f"❌ Error: {str(e)}"
        }


def procesar_archivo_local(archivo_streamlit, categoria: str = "03_Conocimiento/General",
                            motor: str = "atlas", modelo: str = None,
                            max_workers: int = 4):
    """
    Procesa un archivo subido desde la UI con PARALELISMO en la digestión.
    Es un GENERADOR que reporta progreso paso a paso.
    
    Args:
        archivo_streamlit: Archivo subido desde Streamlit
        categoria: Ruta relativa de la carpeta destino (ej: "05_Proyectos/balance_julio")
        motor: "atlas" (Ollama local) o "prometeo" (NVIDIA API)
        modelo: Modelo específico (None = usar default del motor)
        max_workers: Número de workers paralelos (default: 4)
    """
    try:
        nombre_original = archivo_streamlit.name
        extension = os.path.splitext(nombre_original)[1].lower()
        
        yield {"estado": "leyendo", "mensaje": f"📂 Leyendo {nombre_original}..."}
        
        # PASO 1: Guardar temporalmente
        os.makedirs(TEMP_DIR, exist_ok=True)
        ruta_temp = os.path.join(TEMP_DIR, nombre_original)
        with open(ruta_temp, "wb") as f:
            f.write(archivo_streamlit.getbuffer())
        
        texto_crudo = ""
        
        # PASO 2: Detectar tipo y extraer texto
        if extension in FORMATOS_MULTIMEDIA:
            yield {"estado": "transcribiendo", "mensaje": "🎙️ Iniciando transcripción de audio/video..."}
            from core.audio_transcriber import transcribir_archivo
            texto_crudo = transcribir_archivo(ruta_temp, progreso_callback=None)
            if texto_crudo.startswith("❌"):
                yield {"estado": "error", "mensaje": texto_crudo}
                return
        else:
            yield {"estado": "extrayendo", "mensaje": "🔍 Extrayendo texto..."}
            try:
                from core.universal_loader import leer_archivo
                texto_crudo = leer_archivo(ruta_temp)
            except Exception as e:
                yield {"estado": "error", "mensaje": f"❌ No se pudo leer: {str(e)}"}
                return
        
        if not texto_crudo or len(texto_crudo.strip()) < 50:
            yield {"estado": "error", "mensaje": "⚠️ El archivo está vacío o no se pudo extraer texto."}
            return
        
        # Limpiar archivo temporal
        try:
            os.remove(ruta_temp)
        except Exception:
            pass
        
        # PASO 3: Digerir con el motor elegido (CON PARALELISMO)
        tipo_fuente = "Audio/Video Transcrito" if extension in FORMATOS_MULTIMEDIA else "Archivo Local"
        yield {"estado": "procesando", "mensaje": f"⚡ Procesando el contenido con {max_workers} workers en paralelo..."}
        
        texto_procesado = ""
        for paso in digerir_documento_con_progreso(
            texto_crudo=texto_crudo,
            nombre_original=nombre_original,
            url_origen=f"{tipo_fuente} (Drag & Drop)",
            motor=motor,
            modelo=modelo,
            max_workers=max_workers
        ):
            if paso["estado"] in ["chunking", "procesando_chunk", "procesando"]:
                yield paso
            elif paso["estado"] == "completado":
                texto_procesado = paso["texto"]
            elif paso["estado"] == "error":
                yield paso
                return
        
        if not texto_procesado:
            yield {"estado": "error", "mensaje": "❌ No se pudo procesar el documento"}
            return
        
        # PASO 4: Archivar en el RAG
        yield {"estado": "archivando", "mensaje": "💾 Guardando en tu base de conocimiento..."}
        nombre_final = normalizar_nombre(nombre_original)
        
        # Crear ruta completa con la categoría
        ruta_final = os.path.join(RAG_BASE_PATH, categoria, nombre_final)
        os.makedirs(os.path.dirname(ruta_final), exist_ok=True)
        
        metadata = f"""---
titulo: "{nombre_original}"
fuente: "{tipo_fuente}"
fecha_ingestion: "{datetime.now().isoformat()}"
categoria: "{categoria}"
---

"""
        with open(ruta_final, "w", encoding="utf-8") as f:
            f.write(metadata + texto_procesado)
        
        # PASO 5: Indexar SOLO el documento recién creado (Atlas v4.1)
        yield {"estado": "indexando", "mensaje": "🔍 Indexando documento nuevo..."}
        error_indexacion = None
        try:
            from core.indexer import indexar_archivo
            resultado_idx = indexar_archivo(ruta_final)
            if resultado_idx.status == "indexed":
                log_seguridad(
                    "LOCAL_INGESTION_INDEXED",
                    f"{nombre_final}: {resultado_idx.chunk_count} chunks"
                )
            else:
                error_indexacion = resultado_idx.error
        except Exception as e:
            # indexar_archivo no debería lanzar, pero el límite queda protegido.
            error_indexacion = f"{type(e).__name__}: {e}"

        if error_indexacion is not None:
            # El Markdown YA está guardado: NO se borra. Queda pendiente de
            # indexación y una sincronización posterior lo recuperará.
            log_seguridad(
                "LOCAL_INGESTION_INDEX_FAILED",
                f"{nombre_final}: {error_indexacion}"
            )
            yield {
                "estado": "advertencia",
                "mensaje": (f"⚠️ Guardado, pero la indexación falló: {error_indexacion}. "
                            f"Queda pendiente; se reintentará con !indexar sync.")
            }

        mensaje_final = f"✅ {nombre_original} procesado y guardado en {categoria}"
        if error_indexacion is not None:
            mensaje_final += " (pendiente de indexación)"

        yield {
            "estado": "completado",
            "mensaje": mensaje_final,
            "archivo": nombre_final,
            "ruta": ruta_final
        }
        
    except Exception as e:
        log_seguridad("LOCAL_INGESTION_ERROR", str(e))
        yield {"estado": "error", "mensaje": f"❌ Error inesperado: {str(e)}"}
