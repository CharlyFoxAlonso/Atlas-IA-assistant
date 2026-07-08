"""
core/indexer.py
Construye el índice semántico de ChromaDB desde los archivos de Atlas_Memory.
Atlas v3 - Indexa TODAS las carpetas de Atlas_Memory (no solo 03_Conocimiento)
"""
import os
import sys

# Agregar la carpeta raíz al path para que funcione como script directo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vector_store import agregar_documento
from core.universal_loader import leer_archivo_con_info
from core.security import log_seguridad

# Ruta base de Atlas_Memory (indexa TODO, no solo 03_Conocimiento)
MEMORIA_BASE = "memory/Atlas_Memory"

# Extensiones soportadas
EXTENSIONES_PERMITIDAS = {'.md', '.pdf', '.txt', '.docx', '.pptx'}


def construir_indice():
    """
    Recorre TODAS las carpetas de Atlas_Memory y las indexa en ChromaDB.
    Devuelve la lista de archivos indexados.
    """
    archivos_indexados = []
    
    if not os.path.exists(MEMORIA_BASE):
        print(f"❌ No existe la carpeta {MEMORIA_BASE}")
        return archivos_indexados
    
    print(f"🔍 Escaneando todas las carpetas de {MEMORIA_BASE}...")
    
    # Recorrer recursivamente TODAS las carpetas
    for root, dirs, files in os.walk(MEMORIA_BASE):
        # Ignorar carpetas temporales o de sistema
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'temp_ingestion', 'temp_local_ingestion']]
        
        for archivo in files:
            extension = os.path.splitext(archivo)[1].lower()
            
            if extension in EXTENSIONES_PERMITIDAS:
                ruta_completa = os.path.join(root, archivo)
                
                # Calcular categoría relativa (ej: "05_Proyectos/balance_julio")
                ruta_relativa = os.path.relpath(ruta_completa, MEMORIA_BASE)
                categoria = os.path.dirname(ruta_relativa)
                
                print(f"📄 Procesando: {ruta_relativa}")
                
                try:
                    # Leer archivo
                    resultado = leer_archivo_con_info(ruta_completa)
                    
                    if resultado.get("ok") and resultado.get("contenido"):
                        contenido = resultado["contenido"]
                        
                        # Agregar metadata
                        metadata = {
                            "nombre": archivo,
                            "ruta": ruta_relativa,
                            "categoria": categoria,
                            "tamano_kb": resultado.get("tamano_kb", 0)
                        }
                        
                        # Indexar en ChromaDB
                        chunks_agregados = agregar_documento(
                            doc_id=ruta_relativa,
                            texto=contenido,
                            metadata=metadata
                        )
                        
                        if chunks_agregados > 0:
                            archivos_indexados.append(ruta_relativa)
                            print(f"   ✅ Indexado: {chunks_agregados} chunks")
                        else:
                            print(f"   ⚠️ No se pudo indexar (contenido vacío o muy corto)")
                    else:
                        error = resultado.get("error", "Error desconocido")
                        print(f"   ❌ Error: {error}")
                
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    print(f"   ❌ Error procesando {archivo}: {str(e)}")
                    log_seguridad("INDEXER_ERROR", f"Error indexando {ruta_relativa}: {str(e)}\n{error_detail}")
    
    print(f"\n✅ Indexación completa: {len(archivos_indexados)} archivos procesados")
    return archivos_indexados


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 ATLAS INDEXER - Construyendo índice semántico")
    print("=" * 60)
    archivos = construir_indice()
    print(f"\n📊 Total archivos indexados: {len(archivos)}")
    print("=" * 60)