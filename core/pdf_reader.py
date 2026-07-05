"""
core/pdf_reader.py
Lector de PDFs inteligente con soporte OCR (Tesseract + Poppler).
Configurado para procesar libros completos (hasta 600 páginas).

v2.7.1 - Poppler externalizado a .env con detección automática
"""
import os
import logging
from pypdf import PdfReader
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# DETECCIÓN INTELIGENTE DE POPPLER (3 NIVELES DE FALLBACK)
# ============================================================
def _detectar_poppler() -> str:
    """
    Detecta la ruta de Poppler usando 3 niveles de fallback:
    1. Variable POPPLER_PATH en .env (preferido)
    2. Detección automática en rutas comunes de Windows
    3. Ruta hardcodeada de emergencia (compatibilidad hacia atrás)
    """
    # NIVEL 1: Variable de entorno (.env)
    poppler_env = os.getenv("POPPLER_PATH", "").strip()
    if poppler_env and os.path.exists(poppler_env):
        logger.info(f"✅ Poppler encontrado vía .env: {poppler_env}")
        return poppler_env
    
    # NIVEL 2: Detección automática en rutas comunes de Windows
    rutas_comunes = [
        r"C:\Tools\poppler\poppler-26.02.0\Library\bin",
        r"C:\Tools\poppler\poppler-24.08.0\Library\bin",
        r"C:\Tools\poppler\Library\bin",
        r"C:\Tools\poppler\bin",
        r"C:\ProgramData\chocolatey\lib\poppler\tools\poppler-24.08.0\Library\bin",
        r"C:\ProgramData\chocolatey\bin",
        os.path.expanduser(r"~\scoop\apps\poppler\current\Library\bin"),
        r"C:\Program Files\poppler\bin",
        r"C:\Program Files (x86)\poppler\bin",
    ]
    
    for ruta in rutas_comunes:
        if os.path.exists(ruta):
            logger.info(f"✅ Poppler detectado automáticamente: {ruta}")
            return ruta
    
    # NIVEL 3: Fallback hardcodeado (tu ruta original, para no romper nada)
    ruta_emergencia = r"C:\Tools\poppler\poppler-26.02.0\Library\bin"
    if os.path.exists(ruta_emergencia):
        logger.warning(f"⚠️ Poppler usando ruta de emergencia: {ruta_emergencia}")
        logger.warning(f"   💡 Agregá POPPLER_PATH={ruta_emergencia} a tu .env")
        return ruta_emergencia
    
    # No se encontró en ningún lado
    logger.error("❌ Poppler no encontrado en ninguna ubicación")
    return ""

# Ruta global de Poppler (se detecta una sola vez al importar el módulo)
POPPLER_PATH = _detectar_poppler()

# ============================================================
# LECTOR DE PDF (LÓGICA ORIGINAL INTACTA)
# ============================================================
def leer_pdf(ruta_archivo: str, max_paginas_ocr: int = 600) -> str:
    """
    Lee un PDF de forma inteligente:
    1. Intenta extraer texto con pypdf (rápido, para PDFs de texto).
    2. Si es escaneado, usa OCR con Tesseract y Poppler (lento).
    """
    try:
        logger.info(f"Leyendo PDF: {ruta_archivo}")
        reader = PdfReader(ruta_archivo)
        total_paginas = len(reader.pages)
        logger.info(f"Total de páginas: {total_paginas}")
        
        # ============================================
        # ESTRATEGIA 1: Extracción directa con pypdf (RÁPIDO)
        # ============================================
        texto_completo = []
        paginas_con_texto = 0
        
        for i, pagina in enumerate(reader.pages, 1):
            try:
                texto = pagina.extract_text()
                if texto and len(texto.strip()) > 50:
                    texto_completo.append(f"\n--- Página {i} ---\n{texto}")
                    paginas_con_texto += 1
            except Exception as e:
                logger.warning(f"Error extrayendo página {i}: {e}")
                continue
        
        # Si al menos el 30% de las páginas tienen texto, usamos eso
        if paginas_con_texto > total_paginas * 0.3:
            logger.info(f"✅ Texto extraído directamente de {paginas_con_texto}/{total_paginas} páginas")
            return "\n".join(texto_completo)
        
        # ============================================
        # ESTRATEGIA 2: OCR (LENTO - Solo si es escaneado)
        # ============================================
        logger.info(f"⚠️ PDF escaneado detectado ({paginas_con_texto} páginas con texto). Iniciando OCR...")
        
        try:
            from pdf2image import convert_from_path
            import pytesseract
        except ImportError as e:
            logger.error(f"Dependencias OCR no instaladas: {e}")
            return "[Error: Instalá pdf2image y pytesseract]"
        
        # Verificar que Poppler exista en la ruta detectada
        if not POPPLER_PATH or not os.path.exists(POPPLER_PATH):
            logger.error(f"❌ Poppler no encontrado. Ruta detectada: '{POPPLER_PATH}'")
            return f"[Error: Poppler no encontrado. Configurá POPPLER_PATH en tu .env]"
        
        logger.info(f"✅ Poppler encontrado en: {POPPLER_PATH}")
        
        # Limitar páginas para no saturar RAM
        paginas_a_procesar = min(total_paginas, max_paginas_ocr)
        if total_paginas > max_paginas_ocr:
            logger.warning(f"⚠️ PDF tiene {total_paginas} páginas, procesando solo las primeras {max_paginas_ocr}")
        
        texto_ocr = []
        chunk_size = 10  # Procesar de 10 en 10 páginas
        
        for inicio in range(0, paginas_a_procesar, chunk_size):
            fin = min(inicio + chunk_size, paginas_a_procesar)
            logger.info(f"Procesando páginas {inicio+1} a {fin}...")
            
            try:
                # Convertir PDF a imágenes usando Poppler
                imagenes = convert_from_path(
                    ruta_archivo,
                    first_page=inicio + 1,
                    last_page=fin,
                    dpi=200,
                    poppler_path=POPPLER_PATH
                )
                
                # Aplicar OCR a cada imagen con Tesseract
                for i, img in enumerate(imagenes, inicio + 1):
                    try:
                        texto = pytesseract.image_to_string(img, lang='spa')
                        if texto.strip():
                            texto_ocr.append(f"\n--- Página {i} (OCR) ---\n{texto}")
                    except Exception as e:
                        logger.warning(f"Error en OCR página {i}: {e}")
                        continue
                
                del imagenes  # Liberar memoria
                
            except Exception as e:
                logger.error(f"Error procesando chunk {inicio+1}-{fin}: {e}")
                continue
        
        if texto_ocr:
            logger.info(f"✅ OCR completado: {len(texto_ocr)} páginas procesadas")
            return "\n".join(texto_ocr)
        else:
            return "[Error: No se pudo extraer texto del PDF con OCR]"
    
    except Exception as e:
        logger.error(f"Error general leyendo PDF {ruta_archivo}: {e}")
        return f"[Error al leer PDF: {str(e)}]"