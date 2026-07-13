"""
core/vector_store.py
Motor de búsqueda semántica para Atlas v4.
Usa ChromaDB y embeddings multilingües para entender el significado, no solo keywords.
Inicialización perezosa: ChromaDB y el modelo de embeddings se cargan sólo cuando
se necesita una búsqueda, no al importar este módulo.
"""
import os
import re
from datetime import datetime

# ============================================
# CONFIGURACIÓN
# ============================================
CHROMA_PATH = "./vector_db"
COLLECTION_NAME = "atlas_rag"

_cliente = None
_coleccion = None
_embedding_fn = None


def _get_collection():
    """
    Inicializa perezosamente el cliente de ChromaDB y la colección.
    Sólo se carga al primer uso (primera búsqueda o indexación).
    Si la DB existente tiene un formato incompatible (DB persistida
    con una versión vieja de ChromaDB), la migra automáticamente
    respaldando el archivo y restaurando desde cero (se reconstruye
    con `!indexar`).
    """
    global _cliente, _coleccion, _embedding_fn
    if _coleccion is not None:
        return _coleccion

    import chromadb
    import os as _os
    _os.environ["ANONYMIZED_TELEMETRY"] = "False"
    from chromadb.utils import embedding_functions

    try:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        _cliente = chromadb.PersistentClient(path=CHROMA_PATH)
        _coleccion = _cliente.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        return _coleccion
    except (KeyError, RuntimeError, ValueError) as e:
        # DB incompat (formato viejo). Respaldo y reintento limpio.
        from core.security import log_seguridad
        log_seguridad("VECTOR_DB_INCOMPAT", f"Reformateando {CHROMA_PATH}: {type(e).__name__}: {e}")
        import shutil
        if os.path.exists(CHROMA_PATH):
            backup = CHROMA_PATH + ".incompat." + datetime.now().strftime("%Y%m%d_%H%M%S")
            try:
                shutil.move(CHROMA_PATH, backup)
            except Exception:
                # Si no se puede mover (archivo bloqueado), abortar
                raise RuntimeError(
                    f"No se pudo migrar {CHROMA_PATH}. Cerrá Atlas (y Ollama si lo usás) "
                    f"y borrá manualmente la carpeta vector_db."
                ) from e
        _coleccion = None
        _cliente = None
        # Reintentar una vez con carpeta limpia
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        _cliente = chromadb.PersistentClient(path=CHROMA_PATH)
        _coleccion = _cliente.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        return _coleccion


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

    if chunk_size <= overlap:
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

    chunks_finales = []
    for chunk_data in chunks:
        chunk = chunk_data["texto"]
        cap = chunk_data["capitulo"]
        step = chunk_size - overlap
        if step <= 0:
            step = chunk_size

        if len(chunk) > chunk_size * 1.5:
            for i in range(0, len(chunk), step):
                recorte = chunk[i:i + chunk_size]
                if recorte.strip():
                    chunks_finales.append({
                        "texto": recorte.strip(),
                        "capitulo": cap
                    })
        else:
            chunks_finales.append(chunk_data)

    return [c for c in chunks_finales if len(c.get("texto", "")) > 20]


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

    col = _get_collection()

    chunks = [c["texto"] for c in chunks_data]
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

    metadatas = []
    base_metadata = metadata or {"nombre": doc_id}

    for chunk_data in chunks_data:
        chunk_metadata = base_metadata.copy()
        if chunk_data["capitulo"]:
            chunk_metadata["capitulo"] = chunk_data["capitulo"]
        metadatas.append(chunk_metadata)

    try:
        existing = col.get(where={"nombre": doc_id})
        if existing and 'ids' in existing and existing['ids']:
            col.delete(ids=existing['ids'])
    except Exception:
        pass

    col.add(
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
    col = _get_collection()

    where_filter = {}

    if filtro_categoria:
        where_filter["categoria"] = filtro_categoria
    if filtro_capitulo:
        where_filter["capitulo"] = filtro_capitulo

    if not where_filter:
        where_filter = None

    try:
        resultados = col.query(
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
    """
    if not palabras_clave:
        return buscar_relevante(pregunta, n_results=n_results)

    col = _get_collection()
    docs_relevantes = []
    vistas = set()

    for kw in palabras_clave:
        if len(kw) < 3:
            continue

        try:
            resultados = col.query(
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
    col = _get_collection()
    return {
        "total_chunks": col.count(),
        "nombre_coleccion": COLLECTION_NAME,
        "ruta_db": CHROMA_PATH
    }
