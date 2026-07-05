import os
from core.indexer import cargar_indice
from core.file_loader import leer_archivo_estudio

BASE = "memory/Atlas_Memory"


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
    # Cargar el índice
    indice = cargar_indice()

    if not indice:
        return []

    resultados = []

    for entry in indice:
        # Buscar en nombre + keywords + preview
        texto_busqueda = (
            entry.get("nombre", "") + " " +
            " ".join(entry.get("keywords", [])) + " " +
            entry.get("preview", "")
        )
        
        score = score_match(query, texto_busqueda)
        
        if score > 0:
            # Leer el contenido completo solo si hay coincidencia
            ruta = entry.get("ruta")
            contenido = _leer_archivo(ruta)
            
            if contenido:
                resultados.append({
                    "path": ruta,
                    "content": contenido,
                    "score": score
                })

    # Ordenar por score (mayor primero)
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