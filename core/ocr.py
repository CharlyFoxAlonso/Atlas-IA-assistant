import pytesseract
from PIL import Image
from config.tools import TESSERACT_CMD, OCR_LANGUAGE

# Configurar ruta de Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def imagen_a_texto(imagen):
    """
    Recibe: PIL.Image
    Devuelve: texto OCR
    """
    try:
        # Configuración simple sin --tessdata-dir
        config = '--oem 3 --psm 6'

        texto = pytesseract.image_to_string(
            imagen,
            lang=OCR_LANGUAGE,
            config=config
        )

        return texto.strip()
    except Exception as e:
        print(f"  ❌ Error en OCR: {e}")
        return ""


def archivo_imagen_a_texto(ruta):
    """
    Lee una imagen desde disco.
    Compatible con: jpg, jpeg, png, bmp, tif, tiff, webp
    """
    try:
        imagen = Image.open(ruta)
        return imagen_a_texto(imagen)
    except Exception as e:
        print(f"  ❌ Error abriendo imagen {ruta}: {e}")
        return ""