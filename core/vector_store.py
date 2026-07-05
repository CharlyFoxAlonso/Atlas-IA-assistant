"""
core/vector_store.py
Motor de búsqueda semántica para Atlas v2.9.
Usa ChromaDB y embeddings multilingües para entender el significado, no solo keywords.
"""
import chromadb
from chromadb.utils import embedding_functions
import os
import re

# ============================================
# CONFIGURACIÓN
# ============================================
CHROMA_PATH = "./vector_db"
COLLECTION_NAME = "atlas_rag"

# Usamos un modelo multilingüe optimizado para español
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

# Inicializar cliente persistente
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Crear o cargar la colección
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_fn,
    metadata={"hnsw:space": "cosine"}
)

# ============================================
# DETECCIÓN DE CAPÍTULOS
# ============================================

def detectar_capitulo(texto):
    """
    Intenta detectar si el texto pertenece a un capítulo específico.
    Busca patrones como "Capítulo 7", "CAPÍTULO VII", etc.
    """
    patrones = [
        r'cap[íi]tulo\s+(\d+|[IVX]+)',
        r't[íi]tulo\s+(\d+|[IVX]+)',
        r'secci[óo]n\s+(\d+|[IVX]+)',
    ]
    for patron in patrones:
        match = re.search(patron, texto[:500], re.IGNORECASE)
        if match:
            cap = match.group(1)
            if re.match(r'[IVX]+', cap):
                cap = str(convertir_romano(cap))
            return f"capitulo_{cap}"
    return None


def convertir_romano(romano):
    """Convierte número romano a arábigo."""
    valores = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    resultado = 0
    for i in range(len(romano)):
        if i > 0 and valores[romano[i]] > valores[romano[i-1]]:
            resultado += valores[romano[i]] - 2 * valores[romano[i-1]]
        else:
            resultado += valores[romano[i]]
    return resultado


# ============================================
# CHUNKING INTELIGENTE
# ============================================

def chunk_text(texto, chunk_size=500, overlap=100):
    """Divide un texto en chunks con detección de capítulos."""
    if not texto:
        return []
    
    parrafos = texto.split('\n\n')
    chunks = []
    chunk_actual = ""
    capitulo_actual = None
    
    for parrafo in parrafos:
        cap_detectado = detectar_capitulo(parrafo)
        if cap_detectado:
            capitulo_actual = cap_detectado
        
        if len(chunk_actual) + len(parrafo) > chunk_size and chunk_actual:
            chunks.append({
                "texto": chunk_actual.strip(),
                "capitulo": capitulo_actual
            })
            chunk_actual = chunk_actual[-overlap:] + parrafo
        else:
            chunk_actual += "\n\n" + parrafo
    
    if chunk_actual.strip():
        chunks.append({
            "texto": chunk_actual.strip(),
            "capitulo": capitulo_actual
        })
    
    # Dividir chunks muy grandes
    chunks_finales = []
    for chunk_data in chunks:
        chunk = chunk_data["texto"]
        cap = chunk_data["capitulo"]
        
        if len(chunk) > chunk_size * 1.5:
            for i in range(0, len(chunk), chunk_size - overlap):
                chunks_finales.append({
                    "texto": chunk[i:i + chunk_size],
                    "capitulo": cap
                })
        else:
            chunks_finales.append(chunk_data)
    
    return [c for c in chunks_finales if len(c["texto"]) > 20]


# ============================================
# AGREGAR DOCUMENTO
# ============================================

def agregar_documento(doc_id, texto, metadata=None):
    """
    Agrega un documento a la base de datos vectorial.
    Usa SIEMPRE 'nombre' como clave de metadata (compatible con indexer.py).
    """
    if not texto or len(texto.strip()) < 50:
        return 0
    
    chunks_data = chunk_text(texto)
    if not chunks_data:
        return 0
    
    chunks = [c["texto"] for c in chunks_data]
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    
    metadatas = []
    # SIEMPRE usar "nombre" (no "source")
    base_metadata = metadata or {"nombre": doc_id}
    
    for chunk_data in chunks_data:
        chunk_metadata = base_metadata.copy()
        if chunk_data["capitulo"]:
            chunk_metadata["capitulo"] = chunk_data["capitulo"]
        metadatas.append(chunk_metadata)
    
    # Eliminar chunks anteriores del mismo documento (si existen)
    try:
        existing = collection.get(where={"nombre": doc_id})
        if existing['ids']:
            collection.delete(ids=existing['ids'])
    except Exception:
        pass
    
    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )
    
    return len(chunks)


# ============================================
# BÚSQUEDA SEMÁNTICA
# ============================================

def buscar_relevante(pregunta, n_results=5, filtro_categoria=None, filtro_capitulo=None):
    """Busca chunks relevantes para una pregunta usando similitud semántica."""
    where_filter = {}
    
    if filtro_categoria:
        where_filter["categoria"] = filtro_categoria
    if filtro_capitulo:
        where_filter["capitulo"] = filtro_capitulo
    
    if not where_filter:
        where_filter = None
    
    try:
        resultados = collection.query(
            query_texts=[pregunta],
            n_results=n_results,
            where=where_filter
        )
        
        docs_relevantes = []
        if resultados and resultados['documents'][0]:
            for i in range(len(resultados['documents'][0])):
                docs_relevantes.append({
                    "texto": resultados['documents'][0][i],
                    "metadata": resultados['metadatas'][0][i],
                    "distancia": resultados['distances'][0][i]
                })
        
        return docs_relevantes
    except Exception as e:
        print(f"Error en búsqueda semántica: {e}")
        return []


# ============================================
# BÚSQUEDA POR NOMBRE
# ============================================

def buscar_por_nombre(pregunta, palabras_clave, n_results=10):
    """
    Búsqueda por METADATA: busca chunks cuyo nombre de archivo contenga
    alguna de las palabras_clave, combinado con similitud semántica.
    Usa SIEMPRE filtro por "nombre" (compatible con indexer.py).
    """
    if not palabras_clave:
        return buscar_relevante(pregunta, n_results=n_results)
    
    docs_relevantes = []
    vistas = set()
    
    for kw in palabras_clave:
        if len(kw) < 3:
            continue
        
        try:
            resultados = collection.query(
                query_texts=[pregunta],
                n_results=n_results,
                where={"nombre": {"$contains": kw}}
            )
            
            if resultados and resultados['documents'][0]:
                for i in range(len(resultados['documents'][0])):
                    doc_id = resultados['ids'][0][i]
                    if doc_id not in vistas:
                        vistas.add(doc_id)
                        docs_relevantes.append({
                            "texto": resultados['documents'][0][i],
                            "metadata": resultados['metadatas'][0][i],
                            "distancia": resultados['distances'][0][i]
                        })
        except Exception:
            continue
    
    if not docs_relevantes:
        return buscar_relevante(pregunta, n_results=n_results)
    
    return docs_relevantes


# ============================================
# BÚSQUEDA HÍBRIDA
# ============================================

def busqueda_hibrida(pregunta, n_results=15, palabras_clave=None, umbral_semantico=200):
    """
    Estrategia en 2 pasos:
    1. Busca semánticamente (sin filtro)
    2. Si el texto total es menor al umbral, reintenta con búsqueda por nombre de archivo
    """
    resultados_semanticos = buscar_relevante(pregunta, n_results=n_results)
    texto_total = sum(len(r["texto"]) for r in resultados_semanticos)
    
    if texto_total >= umbral_semantico or not palabras_clave:
        return resultados_semanticos
    
    return buscar_por_nombre(pregunta, palabras_clave, n_results=n_results)


# ============================================
# ESTADÍSTICAS
# ============================================

def obtener_estadisticas():
    """Devuelve info sobre la base de datos."""
    return {
        "total_chunks": collection.count(),
        "nombre_coleccion": COLLECTION_NAME,
        "ruta_db": CHROMA_PATH
    }