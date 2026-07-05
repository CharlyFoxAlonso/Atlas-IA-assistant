import os
import platform

# ==========================================================
# CONFIGURACIÓN CENTRAL DE ATLAS
# ==========================================================

# Idioma OCR (español)
OCR_LANGUAGE = "spa"

# Resolución al convertir PDF → Imagen
OCR_DPI = 300

# Máximo de caracteres que Atlas leerá por archivo
MAX_TEXT = 120000

# ==========================================================
# RUTAS POSIBLES DE TESSERACT (se busca automáticamente)
# ==========================================================
POSIBLES_TESSERACT = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\tesseract\tesseract.exe",
    r"C:\teseract\tesseract.exe",  # por si alguien lo instaló con el typo
    os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
]

# ==========================================================
# RUTAS POSIBLES DE POPPLER (se busca automáticamente)
# ==========================================================
POSIBLES_POPPLER = [
    r"C:\Tools\poppler\poppler-26.02.0\Library\bin",
    r"C:\Tools\poppler\Library\bin",
    r"C:\poppler\Library\bin",
    r"C:\Program Files\poppler\Library\bin",
]


def _buscar_en_lista(rutas_posibles):
    """Devuelve la primera ruta que exista, o None si no encuentra nada."""
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return ruta
    return None


def _detectar_tesseract():
    """Busca Tesseract automáticamente."""
    return _buscar_en_lista(POSIBLES_TESSERACT)


def _detectar_poppler():
    """Busca Poppler automáticamente."""
    return _buscar_en_lista(POSIBLES_POPPLER)


# Detectar al importar el módulo
TESSERACT_CMD = _detectar_tesseract()
POPPLER_PATH = _detectar_poppler()

# La carpeta tessdata siempre está al lado de tesseract.exe
if TESSERACT_CMD:
    TESSDATA_DIR = os.path.join(os.path.dirname(TESSERACT_CMD), "tessdata")
else:
    TESSDATA_DIR = None


# ==========================================================
# VERIFICACIÓN COMPLETA DE HERRAMIENTAS
# ==========================================================
def verificar_herramientas():
    """
    Revisa qué herramientas están instaladas.
    Devuelve un diccionario con el estado de cada una.
    """
    resultado = {
        "tesseract": {
            "ok": TESSERACT_CMD is not None,
            "ruta": TESSERACT_CMD,
            "mensaje": ""
        },
        "poppler": {
            "ok": POPPLER_PATH is not None,
            "ruta": POPPLER_PATH,
            "mensaje": ""
        }
    }

    if not resultado["tesseract"]["ok"]:
        resultado["tesseract"]["mensaje"] = (
            "❌ Tesseract no encontrado.\n"
            "   Instálalo desde: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "   Luego reinicia Atlas."
        )
    else:
        resultado["tesseract"]["mensaje"] = f"✅ Tesseract OK: {TESSERACT_CMD}"

    if not resultado["poppler"]["ok"]:
        resultado["poppler"]["mensaje"] = (
            "❌ Poppler no encontrado.\n"
            "   Descárgalo desde: https://github.com/oschwartz10612/poppler-windows/releases\n"
            "   Descomprímelo en C:\\Tools\\poppler\\ y reinicia Atlas."
        )
    else:
        resultado["poppler"]["mensaje"] = f"✅ Poppler OK: {POPPLER_PATH}"

    return resultado


def mostrar_estado():
    """Imprime en pantalla el estado de todas las herramientas."""
    print("\n" + "=" * 50)
    print("🔧 ESTADO DE HERRAMIENTAS ATLAS")
    print("=" * 50)

    estado = verificar_herramientas()

    for nombre, info in estado.items():
        print(info["mensaje"])

    print("=" * 50 + "\n")

    # Devuelve True si TODO está OK
    return all(info["ok"] for info in estado.values())