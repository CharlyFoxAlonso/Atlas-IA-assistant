"""
Módulo de visión de Atlas.
Captura pantalla y extrae texto con OCR.
Atlas v3.9
"""
import os
from datetime import datetime
from PIL import Image
import pyautogui

# Carpeta para guardar capturas temporales - ✅ CORREGIDO: agregado #
CAPTURAS_DIR = "memory/Atlas_Memory/temp/capturas"


def asegurar_directorio():
    """Crea el directorio de capturas si no existe."""
    if not os.path.exists(CAPTURAS_DIR):
        os.makedirs(CAPTURAS_DIR, exist_ok=True)


def capturar_pantalla():
    """
    Captura la pantalla actual y la guarda como imagen.
    Devuelve la ruta del archivo de captura.
    """
    asegurar_directorio()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta_captura = os.path.join(CAPTURAS_DIR, f"captura_{timestamp}.png")
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(ruta_captura)
        return ruta_captura
    except Exception as e:
        return None, f"Error capturando pantalla: {str(e)}"


def extraer_texto_ocr(ruta_imagen):
    """
    Extrae texto de una imagen usando Tesseract OCR.
    Devuelve el texto extraído.
    """
    try:
        # Importar aquí para evitar errores si no está instalado
        import pytesseract
        imagen = Image.open(ruta_imagen)
        texto = pytesseract.image_to_string(imagen, lang='spa+eng')
        return texto.strip()
    except Exception as e:
        return f"Error en OCR: {str(e)}"


def analizar_pantalla():
    """
    Captura la pantalla, extrae texto con OCR y devuelve ambos.
    Devuelve: (ruta_imagen, texto_extraido)
    """
    ruta = capturar_pantalla()
    if not ruta:
        return None, "Error capturando pantalla"
    texto = extraer_texto_ocr(ruta)
    return ruta, texto


def limpiar_capturas_antiguas(max_archivos=10):
    """
    Elimina capturas antiguas, manteniendo solo las más recientes.
    """
    if not os.path.exists(CAPTURAS_DIR):
        return
    archivos = []
    for f in os.listdir(CAPTURAS_DIR):
        ruta = os.path.join(CAPTURAS_DIR, f)
        if os.path.isfile(ruta):
            archivos.append((ruta, os.path.getmtime(ruta)))
    # Ordenar por fecha (más reciente primero)
    archivos.sort(key=lambda x: x[1], reverse=True)
    # Eliminar los más antiguos
    for ruta, _ in archivos[max_archivos:]:
        try:
            os.remove(ruta)
        except Exception:
            pass