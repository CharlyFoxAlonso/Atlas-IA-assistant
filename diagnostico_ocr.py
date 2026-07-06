"""
diagnostico_ocr.py
Script de diagnóstico para verificar que Tesseract OCR funciona correctamente.
Atlas v3
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
    if platform.system() == "Windows":
        rutas_posibles = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]
        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                return ruta
    else:
        try:
            result = subprocess.run(["which", "tesseract"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
    return "tesseract"


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


def ejecutar_diagnostico():
    """Ejecuta todas las verificaciones de OCR y retorna un reporte."""
    tesseract_cmd = _detectar_tesseract_cmd()
    tessdata_dir = _detectar_tessdata()
    ocr_language = "spa"
    lineas = []

    linea = lambda s="": lineas.append(s)

    linea("=" * 60)
    linea("DIAGNÓSTICO COMPLETO DE OCR")
    linea("=" * 60)

    # 1. Verificar que Tesseract existe
    linea(f"\n1. Tesseract instalado en: {tesseract_cmd}")
    linea(f"   ¿Existe? {os.path.exists(tesseract_cmd)}")

    # 2. Verificar tessdata
    linea(f"\n2. Carpeta tessdata: {tessdata_dir}")
    linea(f"   ¿Existe? {os.path.exists(tessdata_dir) if tessdata_dir else False}")

    # 3. Verificar idioma español
    if tessdata_dir:
        spa_path = os.path.join(tessdata_dir, "spa.traineddata")
        linea(f"\n3. Idioma español (spa.traineddata):")
        linea(f"   Ruta: {spa_path}")
        linea(f"   ¿Existe? {os.path.exists(spa_path)}")
        if not os.path.exists(spa_path):
            linea("\n   FALTA EL IDIOMA ESPAÑOL")
            linea("   Descárgalo desde: https://github.com/tesseract-ocr/tessdata/blob/main/spa.traineddata")
            linea(f"   Guárdalo en: {tessdata_dir}")
    else:
        linea("\n3. No se pudo detectar la carpeta tessdata")

    # 4. Listar idiomas disponibles
    linea(f"\n4. Idiomas disponibles en Tesseract:")
    try:
        result = subprocess.run(
            [tesseract_cmd, "--list-langs"],
            capture_output=True,
            text=True,
            timeout=5
        )
        linea(result.stdout)
    except Exception as e:
        linea(f"   Error: {e}")

    # 5. Crear imagen de prueba más grande y clara
    import tempfile
    linea("\n5. Creando imagen de prueba...")
    img = Image.new('RGB', (800, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), "Hola mundo prueba OCR", fill='black', font=None)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img_path = tmp.name
    img.save(img_path)
    linea(f"   Imagen guardada: {img_path}")

    # 6. Probar Tesseract directamente desde línea de comandos
    linea("\n6. Probando Tesseract directamente...")
    try:
        result = subprocess.run(
            [tesseract_cmd, img_path, 'stdout', '-l', 'spa'],
            capture_output=True,
            text=True,
            timeout=10
        )
        linea(f"   Salida: '{result.stdout}'")
        if result.stderr:
            linea(f"   Errores: {result.stderr}")
    except Exception as e:
        linea(f"   Error: {e}")

    # 7. Probar pytesseract SIN --tessdata-dir
    linea("\n7. Probando pytesseract SIN --tessdata-dir...")
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        texto = pytesseract.image_to_string(img, lang='spa')
        linea(f"   Texto extraído: '{texto}'")
        linea(f"   Longitud: {len(texto)} caracteres")
    except Exception as e:
        linea(f"   Error: {e}")

    # 8. Probar pytesseract CON --tessdata-dir (si está disponible)
    linea("\n8. Probando pytesseract CON --tessdata-dir...")
    try:
        if tessdata_dir:
            config = f'--tessdata-dir "{tessdata_dir}" --oem 3 --psm 6'
            texto = pytesseract.image_to_string(img, lang='spa', config=config)
            linea(f"   Texto extraído: '{texto}'")
            linea(f"   Longitud: {len(texto)} caracteres")
        else:
            linea("   No se pudo detectar TESSDATA_DIR, omitiendo")
    except Exception as e:
        linea(f"   Error: {e}")

    linea("\n" + "=" * 60)

    # Limpiar imagen temporal
    try:
        os.remove(img_path)
    except Exception:
        pass

    reporte = "\n".join(lineas)
    return {
        "tesseract_cmd": tesseract_cmd,
        "tessdata_dir": tessdata_dir,
        "reporte": reporte,
    }


if __name__ == "__main__":
    diag = ejecutar_diagnostico()
    print(diag["reporte"])