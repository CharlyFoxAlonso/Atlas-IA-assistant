"""
diagnostico_ocr.py
Script de diagnóstico para verificar que Tesseract OCR funciona correctamente.
Atlas v2.9
"""
import os
import subprocess
import platform
from PIL import Image, ImageDraw
import pytesseract

# ============================================
# DETECCIÓN AUTOMÁTICA DE TESSERACT
# ============================================

def _detectar_tesseract_cmd():
    """Detecta la ruta de Tesseract según el sistema operativo."""
    # Windows (rutas comunes)
    if platform.system() == "Windows":
        rutas_posibles = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                return ruta
    # Linux / macOS
    else:
        try:
            result = subprocess.run(["which", "tesseract"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
    return "tesseract"  # Asumir que está en PATH


def _detectar_tessdata():
    """Detecta la carpeta tessdata."""
    if platform.system() == "Windows":
        rutas_posibles = [
            r"C:\Program Files\Tesseract-OCR\tessdata",
            r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        ]
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                return ruta
    else:
        rutas_posibles = [
            "/usr/share/tesseract-ocr/5/tessdata",
            "/usr/share/tesseract-ocr/4.00/tessdata",
            "/usr/local/share/tessdata",
            "/opt/homebrew/share/tessdata",
        ]
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                return ruta
    return None


# Variables globales detectadas automáticamente
TESSERACT_CMD = _detectar_tesseract_cmd()
TESSDATA_DIR = _detectar_tessdata()
OCR_LANGUAGE = "spa"

print("=" * 60)
print("🔍 DIAGNÓSTICO COMPLETO DE OCR")
print("=" * 60)

# 1. Verificar que Tesseract existe
print(f"\n1. Tesseract instalado en: {TESSERACT_CMD}")
print(f"   ¿Existe? {os.path.exists(TESSERACT_CMD)}")

# 2. Verificar tessdata
print(f"\n2. Carpeta tessdata: {TESSDATA_DIR}")
print(f"   ¿Existe? {os.path.exists(TESSDATA_DIR) if TESSDATA_DIR else False}")

# 3. Verificar idioma español
if TESSDATA_DIR:
    spa_path = os.path.join(TESSDATA_DIR, "spa.traineddata")
    print(f"\n3. Idioma español (spa.traineddata):")
    print(f"   Ruta: {spa_path}")
    print(f"   ¿Existe? {os.path.exists(spa_path)}")
    if not os.path.exists(spa_path):
        print("\n   ❌ FALTA EL IDIOMA ESPAÑOL")
        print("   Descárgalo desde: https://github.com/tesseract-ocr/tessdata/blob/main/spa.traineddata")
        print(f"   Guárdalo en: {TESSDATA_DIR}")
else:
    print("\n3. ❌ No se pudo detectar la carpeta tessdata")

# 4. Listar idiomas disponibles
print(f"\n4. Idiomas disponibles en Tesseract:")
try:
    result = subprocess.run(
        [TESSERACT_CMD, "--list-langs"],
        capture_output=True,
        text=True,
        timeout=5
    )
    print(result.stdout)
except Exception as e:
    print(f"   Error: {e}")

# 5. Crear imagen de prueba más grande y clara
print("\n5. Creando imagen de prueba...")
img = Image.new('RGB', (800, 200), color='white')
draw = ImageDraw.Draw(img)
draw.text((50, 80), "Hola mundo prueba OCR", fill='black', font=None)
img.save('test_ocr_claro.png')
print("   Imagen guardada: test_ocr_claro.png")

# 6. Probar Tesseract directamente desde línea de comandos
print("\n6. Probando Tesseract directamente...")
try:
    result = subprocess.run(
        [TESSERACT_CMD, 'test_ocr_claro.png', 'stdout', '-l', 'spa'],
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"   Salida: '{result.stdout}'")
    if result.stderr:
        print(f"   Errores: {result.stderr}")
except Exception as e:
    print(f"   Error: {e}")

# 7. Probar pytesseract SIN --tessdata-dir
print("\n7. Probando pytesseract SIN --tessdata-dir...")
try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    texto = pytesseract.image_to_string(img, lang='spa')
    print(f"   Texto extraído: '{texto}'")
    print(f"   Longitud: {len(texto)} caracteres")
except Exception as e:
    print(f"   Error: {e}")

# 8. Probar pytesseract CON --tessdata-dir (si está disponible)
print("\n8. Probando pytesseract CON --tessdata-dir...")
try:
    if TESSDATA_DIR:
        config = f'--tessdata-dir "{TESSDATA_DIR}" --oem 3 --psm 6'
        texto = pytesseract.image_to_string(img, lang='spa', config=config)
        print(f"   Texto extraído: '{texto}'")
        print(f"   Longitud: {len(texto)} caracteres")
    else:
        print("   ⚠️ No se pudo detectar TESSDATA_DIR, omitiendo")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)