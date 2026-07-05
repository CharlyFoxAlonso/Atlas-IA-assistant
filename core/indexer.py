"""
core/indexer.py v2.7
Construye y gestiona el índice de búsqueda semántica de Atlas.
Usa ChromaDB + embeddings multilingües para búsqueda por significado.
"""
import os
import json
from core.universal_loader import leer_archivo_con_info
from core.vector_store import agregar_documento, collection, obtener_estadisticas

BASE = "memory/Atlas_Memory"
INDEX = "memory/index.json"  # Mantenemos el JSON para metadata rápida


def construir_indice():
    """
    Construye un índice semántico de todos los archivos de memoria.
    1. Lee cada archivo
    2. Genera embeddings de chunks
    3. Los guarda en ChromaDB
    4. Mantiene un JSON liviano con metadata
    """
    indice_metadata = []  # Solo metadata para consultas rápidas
    
    # Contar archivos primero
    total_archivos = 0
    for root, _, files in os.walk(BASE):
        total_archivos += len(files)
    
    print(f"\n🔍 Indexando {total_archivos} archivos con embeddings semánticos...\n")
    
    archivos_procesados = 0
    archivos_omitidos = 0
    chunks_totales = 0
    
    for root, _, files in os.walk(BASE):
        for f in files:
            ruta = os.path.join(root, f)
            
            try:
                data = leer_archivo_con_info(ruta)
                
                if not data.get("ok", False):
                    archivos_omitidos += 1
                    continue
                
                contenido = data.get("contenido", "")
                
                if not contenido or len(contenido.strip()) < 50:
                    archivos_omitidos += 1
                    continue
                
                # Agregar a ChromaDB (genera embeddings automáticamente)
                chunks_agregados = agregar_documento(
                    doc_id=f,
                    texto=contenido,
                    metadata={
                        "nombre": f,
                        "ruta": ruta,
                        "categoria": os.path.basename(root),
                        "extension": os.path.splitext(f)[1].lower()
                    }
                )
                
                chunks_totales += chunks_agregados
                
                # Guardar metadata en JSON (para consultas rápidas)
                indice_metadata.append({
                    "nombre": f,
                    "ruta": ruta,
                    "carpeta": os.path.basename(root),
                    "extension": os.path.splitext(f)[1].lower(),
                    "tamano": os.path.getsize(ruta),
                    "chunks": chunks_agregados,
                    "preview": contenido[:300]
                })
                
                archivos_procesados += 1
                
                # Mostrar progreso cada 5 archivos
                if archivos_procesados % 5 == 0:
                    print(f"  ✓ {archivos_procesados}/{total_archivos} archivos ({chunks_totales} chunks)")
                    
            except Exception as e:
                print(f"  ⚠️ Error procesando {f}: {e}")
                archivos_omitidos += 1
    
    # Guardar metadata en JSON (liviano, solo para referencia)
    os.makedirs("memory", exist_ok=True)
    with open(INDEX, "w", encoding="utf-8") as archivo:
        json.dump(
            indice_metadata,
            archivo,
            indent=2,
            ensure_ascii=False
        )
    
    # Estadísticas finales
    stats = obtener_estadisticas()
    
    print(f"\n✅ Índice semántico construido:")
    print(f"   📄 Archivos indexados: {archivos_procesados}")
    print(f"   🧩 Chunks generados: {chunks_totales}")
    print(f"   💾 Total en ChromaDB: {stats['total_chunks']} chunks")
    print(f"   📁 Metadata en: {INDEX}\n")
    
    return indice_metadata


def cargar_indice():
    """
    Carga el índice desde disco.
    Si no existe, lo construye automáticamente.
    """
    if not os.path.exists(INDEX):
        return construir_indice()
    
    try:
        with open(INDEX, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception as e:
        print(f"⚠️ Error cargando índice: {e}")
        print("   Reconstruyendo índice...")
        return construir_indice()