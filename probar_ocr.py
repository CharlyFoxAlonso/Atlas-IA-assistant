"""
probar_ocr.py
Smoke test para verificar OCR con Tesseract.
Atlas v4
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw
from core.ocr import imagen_a_texto
from core.config import TESSERACT_CMD

TESSDATA_DIR = os.environ.get(
    "TESSDATA_PREFIX",
    os.path.dirname(TESSERACT_CMD) if TESSERACT_CMD else None
)
OCR_LANGUAGE = "spa"

print(f"Tesseract: {TESSERACT_CMD}")
print(f"tessdata: {TESSDATA_DIR}")


def _probar():
    img = Image.new('RGB', (400, 100), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Hola mundo", fill='black')

    print("\nProbando OCR en imagen de prueba...")
    texto = imagen_a_texto(img)
    print(f"Texto extraído: '{texto}'")
    print(f"Longitud: {len(texto)} caracteres")

    if len(texto.strip()) < 3:
        print("\nOCR NO FUNCIONA")
        print("Posibles causas:")
        print("1. Tesseract no está instalado")
        print("2. Falta el idioma español (spa.traineddata)")
        print("3. La ruta de Tesseract es incorrecta")
    else:
        print("\nOCR FUNCIONA")


if __name__ == "__main__":
    _probar()
