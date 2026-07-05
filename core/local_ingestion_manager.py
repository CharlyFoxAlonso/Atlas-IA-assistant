"""
core/local_ingestion_manager.py
Orquesta la ingestión de archivos LOCALES (Drag & Drop) hacia el RAG.
Con PARALELISMO (4 workers) para máxima velocidad en la digestión.
Atlas v2.9
"""
import os
import hashlib
from datetime import datetime
from core.prometeo_worker import digerir_documento_con_progreso
from core.security import log_seguridad

RAG_BASE_PATH = "memory/Atlas_Memory/03_Conocimiento"
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
    fecha = datetime.now().strftime("%Y-%m-%d %H-%M")  # ✅ CORREGIDO: sin espacio
    hash_archivo = _generar_hash_archivo(nombre_original)  # ✅ CORREGIDO: agregar _
    base = os.path.splitext(nombre_original)[0].replace(" ", "_")[:30]
    return f"Local_{fecha}_{base}_{hash_archivo}.md"  # ✅ CORREGIDO: formato limpio


def procesar_archivo_local(archivo_streamlit, categoria: str = "Estudio", max_workers: int = 4):
    """
    Procesa un archivo subido desde la UI con PARALELISMO en la digestión.
    Es un GENERADOR que reporta progreso paso a paso.
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
        
        # PASO 3: Digerir con Prometeo (CON PARALELISMO)
        tipo_fuente = "Audio/Video Transcrito" if extension in FORMATOS_MULTIMEDIA else "Archivo Local"
        yield {"estado": "procesando", "mensaje": f"⚡ Prometeo está digiriendo el contenido con {max_workers} workers en paralelo..."}
        
        texto_procesado = ""
        for paso in digerir_documento_con_progreso(
            texto_crudo=texto_crudo,
            nombre_original=nombre_original,
            url_origen=f"{tipo_fuente} (Drag & Drop)",
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
        nombre_final = normalizar_nombre(nombre_original)  # ✅ CORREGIDO: quitar _
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
        
        # PASO 5: Re-indexar
        yield {"estado": "indexando", "mensaje": "🔄 Reconstruyendo índice..."}
        try:
            from core.indexer import construir_indice
            construir_indice()
        except Exception:
            pass
        
        yield {
            "estado": "completado", 
            "mensaje": f"✅ {nombre_original} procesado y listo para el RAG",
            "archivo": nombre_final
        }
        
    except Exception as e:
        log_seguridad("LOCAL_INGESTION_ERROR", str(e))
        yield {"estado": "error", "mensaje": f"❌ Error inesperado: {str(e)}"}