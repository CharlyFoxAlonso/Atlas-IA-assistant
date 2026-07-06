import os
import json
import hashlib

CACHE_FILE = "memory/cache.json"

_CACHE_ERRORES_JSON = (json.JSONDecodeError, UnicodeDecodeError)


def _cargar_cache():
    """Carga el cache desde disco."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, *_CACHE_ERRORES_JSON):
        return {}

def _guardar_cache(cache):
    """Guarda el cache en disco."""
    os.makedirs("memory", exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def hash_archivo(ruta):
    """Calcula un hash del archivo para detectar cambios."""
    try:
        stat = os.stat(ruta)
        return f"{stat.st_size}{stat.st_mtime}"
    except OSError:
        return None

def esta_en_cache(ruta):
    """
    Verifica si un archivo ya está en el cache y no cambió.
    Devuelve:
        True si está en cache y no cambió
        False si no está o cambió
    """
    cache = _cargar_cache()
    huella_actual = hash_archivo(ruta)  # ✅ CORREGIDO: sin guión bajo
    if ruta not in cache:
        return False
    if cache[ruta]["huella"] != huella_actual:
        return False
    return True

def guardar_en_cache(ruta, resultado):
    """
    Guarda el resultado de procesar un archivo en el cache.
    Args:
        ruta: Ruta del archivo procesado
        resultado: Texto generado por el researcher
    """
    cache = _cargar_cache()
    huella = hash_archivo(ruta)  # ✅ CORREGIDO: sin guión bajo
    cache[ruta] = {
        "huella": huella,
        "resultado": resultado
    }
    _guardar_cache(cache)

def obtener_del_cache(ruta):
    """
    Obtiene el resultado cacheado de un archivo.
    Devuelve:
        El texto cacheado, o None si no está
    """
    cache = _cargar_cache()
    if ruta in cache:
        return cache[ruta]["resultado"]
    return None

def limpiar_cache():
    """Borra todo el cache."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
        print("✅ Cache limpiado")