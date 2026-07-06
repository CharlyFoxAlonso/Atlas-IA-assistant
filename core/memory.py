import os
from core.file_loader import leer_archivo_estudio

BASE = "memory/Atlas_Memory"

EXTENSIONES_INDEX = {'.md', '.txt', '.pdf', '.docx', '.pptx'}
PREVIEW_CHARS = 300


def _construir_indice_en_memoria():
    """
    Construye un índice liviano en memoria a partir de los archivos
    de la carpeta BASE. Devuelve una lista de entradas con campos:
      - nombre
      - ruta
      - ruta_relativa
      - keywords (palabras relevantes)
      - preview (primeros N caracteres del contenido)
    Esta función sustituye a la antigua ``cargar_indice`` del
    ``indexer.py``, que no existe en el código actual.
    """
    entradas = []

    if not os.path.exists(BASE):
        return entradas

    skip_dirs = {'__pycache__', 'temp_ingestion', 'temp_local_ingestion'}

    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in skip_dirs]

        for f in files:
            extension = os.path.splitext(f)[1].lower()
            if extension not in EXTENSIONES_INDEX:
                continue

            ruta_completa = os.path.join(root, f)
            try:
                contenido = _leer_archivo(ruta_completa) or ""
            except Exception:
                continue

            ruta_relativa = os.path.relpath(ruta_completa, BASE)
            preview = contenido[:PREVIEW_CHARS].replace("\n", " ").strip()
            keywords = _extraer_keywords(preview)

            entradas.append({
                "nombre": f,
                "ruta": ruta_completa,
                "ruta_relativa": ruta_relativa,
                "keywords": keywords,
                "preview": preview,
            })

    entradas.sort(key=lambda e: e["ruta"])
    return entradas


def _extraer_keywords(texto, max_keywords=12):
    """Extrae palabras relevantes (>=4 chars, no stopwords simples) para indexar."""
    if not texto:
        return []
    stopwords = {
        "este", "esta", "esto", "esos", "esas", "aquel", "aquella", "para",
        "pero", "como", "más", "menos", "todo", "todos", "todas", "sin",
        "con", "por", "del", "los", "las", "una", "uno", "unos", "unas",
        "que", "qué", "cual", "cuál", "the", "and", "for", "with", "from",
    }
    palabras = []
    for p in texto.lower().split():
        limpio = "".join(c for c in p if c.isalnum())
        if len(limpio) < 4 or limpio in stopwords:
            continue
        if limpio not in palabras:
            palabras.append(limpio)
        if len(palabras) >= max_keywords:
            break
    return palabras


def normalizar(texto):
    """Convierte texto a minúsculas sin espacios extra."""
    if not texto:
        return ""
    return texto.lower().strip()


def score_match(query, text):
    """
    Calcula qué tan bien coincide la búsqueda con el texto.
    Devuelve: Número entero (mayor = mejor coincidencia)
    """
    q = normalizar(query)
    t = normalizar(text)

    if not q or not t:
        return 0

    score = 0

    # Coincidencia exacta de la frase completa
    if q in t:
        score += 15

    # Coincidencia de palabras individuales
    palabras_query = q.split()
    palabras_texto = set(t.split())

    for word in palabras_query:
        if len(word) < 3:
            continue
        
        if word in palabras_texto:
            score += 5
        
        # Coincidencia parcial (primeros 4 caracteres)
        for token in palabras_texto:
            if len(token) >= 4 and word[:4] == token[:4]:
                score += 2

    return score


def buscar_memoria(query, max_resultados=5):
    """
    Busca información relevante en la memoria usando el índice.
    """
    indice = _construir_indice_en_memoria()

    if not indice:
        return []

    resultados = []

    for entry in indice:
        texto_busqueda = (
            entry.get("nombre", "") + " " +
            " ".join(entry.get("keywords", [])) + " " +
            entry.get("preview", "")
        )

        score = score_match(query, texto_busqueda)

        if score > 0:
            ruta = entry.get("ruta")
            contenido = _leer_archivo(ruta)

            if contenido:
                resultados.append({
                    "path": ruta,
                    "content": contenido,
                    "score": score
                })

    resultados.sort(key=lambda x: x["score"], reverse=True)

    return resultados[:max_resultados]


def _leer_archivo(ruta):
    """Lee el contenido de un archivo."""
    try:
        # Usar el loader universal para soportar PDFs, Word, etc.
        from core.universal_loader import leer_archivo_con_info
        data = leer_archivo_con_info(ruta)
        if data["ok"]:
            return data["texto"]
        return None
    except Exception:
        # Fallback: leer como texto plano
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                return archivo.read()
        except Exception:
            return None


def listar_archivos():
    """Lista todos los archivos de la memoria."""
    archivos = []
    for root, _, files in os.walk(BASE):
        for f in files:
            ruta = os.path.join(root, f)
            
            archivos.append({
                "nombre": f,
                "ruta": ruta,
                "extension": os.path.splitext(f)[1].lower()
            })

    archivos.sort(key=lambda x: x["ruta"])

    return archivos