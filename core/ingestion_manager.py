"""
core/ingestion_manager.py
Orquesta el flujo de Ingesta Web -> RAG.
Con PARALELISMO (4 workers) para máxima velocidad en la digestión.
Atlas v3.4
"""
import os
import hashlib
from datetime import datetime
from urllib.parse import urlparse
from core.pdf_scraper import validar_fuente, descargar_y_extraer
from core.digestion_worker import digerir_documento_con_progreso
from core.security import log_seguridad

RAG_BASE_PATH = "memory/Atlas_Memory/03_Conocimiento"
TEMP_DIR = "temp_ingestion"


def _generar_hash_url(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:8]


def normalizar_nombre(url: str, nombre_original: str) -> str:  # ✅ SIN _ al inicio
    fecha = datetime.now().strftime("%Y-%m-%d %H-%M")  # ✅ CORREGIDO: sin espacio
    hash_url = _generar_hash_url(url)  # ✅ CORREGIDO: agregar _
    base = os.path.splitext(nombre_original)[0] if nombre_original else "documento"  # ✅ CORREGIDO: sin espacio
    base = base.replace(" ", "_")[:40]
    return f"Ingestion_{fecha}_{base}_{hash_url}.md"  # ✅ CORREGIDO: sin espacios


def procesar_pipeline_ingestion(url: str, categoria: str = "Estudio",
                                motor: str = "atlas", modelo: str = None,
                                max_workers: int = 4):
    """
    Ejecuta el pipeline completo con PARALELISMO en la digestión.
    Es un GENERADOR que va yielding el estado para que la UI muestre el progreso.
    
    Args:
        url: URL del recurso a descargar
        categoria: Subcarpeta dentro de 03_Conocimiento
        motor: "atlas" (Ollama local) o "prometeo" (NVIDIA API)
        modelo: Modelo específico (None = usar default del motor)
        max_workers: Número de workers paralelos (default: 4)
    """
    try:
        # PASO 1: Validar fuente
        yield {"estado": "validando", "mensaje": "🔍 Validando fuente y seguridad..."}
        validacion = validar_fuente(url)
        
        if not validacion["valido"]:
            yield {"estado": "error", "mensaje": f"❌ Validación fallida: {validacion['razon']}"}
            return
        
        advertencia = ""
        if not validacion["es_confiable"]:
            advertencia = "⚠️ Fuente no oficial, proceder con cautela"
        
        # PASO 2: Descargar y extraer texto
        yield {"estado": "descargando", "mensaje": f"📥 Descargando documento{advertencia}..."}
        resultado_download = descargar_y_extraer(url, carpeta_destino=TEMP_DIR)
        
        if not resultado_download["exito"]:
            yield {"estado": "error", "mensaje": f"❌ Error de descarga: {resultado_download['razon']}"}
            return
        
        try:
            if os.path.exists(resultado_download["ruta"]):
                os.remove(resultado_download["ruta"])
        except Exception:
            pass
        
        # PASO 3: Digerir con el motor elegido (CON PARALELISMO)
        yield {"estado": "procesando", "mensaje": f"⚡ Procesando el documento con {max_workers} workers en paralelo..."}
        texto_procesado = ""
        
        for paso in digerir_documento_con_progreso(
            texto_crudo=resultado_download["texto"],
            nombre_original=resultado_download["nombre"],
            url_origen=url,
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
        yield {"estado": "archivando", "mensaje": "💾 Archivando en tu base de conocimiento..."}
        nombre_final = normalizar_nombre(url, resultado_download["nombre"])  # ✅ CORREGIDO: quitar _
        ruta_final = os.path.join(RAG_BASE_PATH, categoria, nombre_final)
        os.makedirs(os.path.dirname(ruta_final), exist_ok=True)
        
        metadata = f"""---
titulo: "{resultado_download['nombre']}"
fuente: "{url}"
fecha_ingestion: "{datetime.now().isoformat()}"
categoria: "{categoria}"
hash_url: "{_generar_hash_url(url)}"
"""
        contenido_final = metadata + texto_procesado
        
        with open(ruta_final, "w", encoding="utf-8") as f:
            f.write(contenido_final)
        
        # PASO 5: Re-indexar
        yield {"estado": "indexando", "mensaje": "🔄 Reconstruyendo índice de búsqueda..."}
        try:
            from core.indexer import construir_indice
            construir_indice()
            log_seguridad("INGESTION_EXITOSA", f"Documento archivado y re-indexado: {nombre_final}")
        except Exception:
            log_seguridad("INGESTION_EXITOSA", f"Documento archivado (sin re-indexado): {nombre_final}")
        
        yield {
            "estado": "completado", 
            "mensaje": "✅ Documento procesado y archivado exitosamente",
            "archivo": nombre_final,
            "ruta": ruta_final,
            "categoria": categoria
        }
        
    except Exception as e:
        log_seguridad("INGESTION_ERROR", f"Error en pipeline: {str(e)}")
        yield {"estado": "error", "mensaje": f"❌ Error inesperado: {str(e)}"}


def buscar_documentos_ingestionados(categoria: str = None) -> list:
    """Lista los documentos previamente ingeridos en el RAG."""
    documentos = []
    carpeta = os.path.join(RAG_BASE_PATH, categoria) if categoria else RAG_BASE_PATH
    
    if not os.path.exists(carpeta):
        return documentos
    
    for root, _, files in os.walk(carpeta):  # ✅ CORREGIDO: doble coma → _
        for f in files:
            if f.endswith(".md") and f.startswith("Ingestion_"):  # ✅ CORREGIDO: sin espacios
                ruta = os.path.join(root, f)
                stat = os.stat(ruta)
                documentos.append({
                    "nombre": f,  # ✅ CORREGIDO: sin espacio
                    "ruta": ruta,  # ✅ CORREGIDO: sin espacio
                    "categoria": os.path.basename(root),  # ✅ CORREGIDO: sin espacio
                    "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),  # ✅ CORREGIDO: sin espacio
                    "tamano_kb": round(stat.st_size / 1024, 2)  # ✅ CORREGIDO: sin espacio
                })
    
    return sorted(documentos, key=lambda x: x["fecha"], reverse=True)  # ✅ CORREGIDO: sin espacio