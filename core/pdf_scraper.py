"""
core/pdf_scraper.py
Descarga, valida y extrae texto de recursos web.
Atlas v4
"""
import os
import requests
from urllib.parse import urlparse
from core.security import log_seguridad

# Dominios de alta confianza (expandible) - SIN espacios
DOMINIOS_CONFIABLES = [
    ".gob.ar", ".edu.ar", ".gov", ".edu", ".org",
    "infojus.gob.ar", "diputados.gob.ar", "senado.gob.ar",
    "boletinoficial.gob.ar", "unlp.edu.ar", "uba.ar"
]


def validar_fuente(url: str) -> dict:
    """Valida si la fuente es confiable y el archivo es seguro."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme in ["http", "https"]:  # ✅ CORREGIDO: sin espacios
            return {"valido": False, "razon": "Protocolo no soportado"}

        dominio = parsed.netloc.lower()
        es_confiable = any(dominio.endswith(ext) for ext in DOMINIOS_CONFIABLES)

        # Validar con HEAD request
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AtlasBot/4.0)",
            "Accept": "text/html,application/pdf,*/*"
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=15)
        content_type = response.headers.get("Content-Type", "").lower()
        content_length = int(response.headers.get("Content-Length", 0))

        # Validaciones de seguridad
        if content_length > 50 * 1024 * 1024:
            return {"valido": False, "razon": "Archivo demasiado pesado (>50MB)"}

        tipos_soportados = ["application/pdf", "text/html", "text/plain", "application/octet-stream"]
        if not any(tipo in content_type for tipo in tipos_soportados):
            return {"valido": False, "razon": f"Tipo no soportado: {content_type}"}

        return {
            "valido": True,
            "es_confiable": es_confiable,
            "tipo": "pdf" if "application/pdf" in content_type else "html",
            "peso_mb": round(content_length / (1024 * 1024), 2) if content_length > 0 else 0
        }
    except requests.exceptions.Timeout:
        return {"valido": False, "razon": "Timeout al conectar con el servidor"}
    except Exception as e:
        return {"valido": False, "razon": f"Error de conexión: {str(e)}"}


def descargar_y_extraer(url: str, carpeta_destino: str = "temp_ingestion") -> dict:
    """Descarga el archivo y extrae el texto crudo."""
    os.makedirs(carpeta_destino, exist_ok=True)

    # Nombre del archivo desde la URL
    path = urlparse(url).path
    nombre_archivo = os.path.basename(path) or f"documento_{hash(url) % 10000}.pdf"
    ruta_local = os.path.join(carpeta_destino, nombre_archivo)

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; AtlasBot/4.0)"}
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        # Descargar con chunks para no saturar memoria
        with open(ruta_local, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extraer texto usando el loader universal de Atlas
        texto_crudo = ""
        try:
            from core.universal_loader import leer_archivo
            texto_crudo = leer_archivo(ruta_local)
        except ImportError:
            # Fallback básico si no hay universal_loader
            if nombre_archivo.endswith(".txt"):
                with open(ruta_local, "r", encoding="utf-8", errors="ignore") as f:
                    texto_crudo = f.read()
            else:
                texto_crudo = f"[Archivo descargado: {nombre_archivo} - {os.path.getsize(ruta_local)} bytes]"

        return {
            "exito": True,
            "ruta": ruta_local,
            "texto": texto_crudo,
            "nombre": nombre_archivo
        }
    except Exception as e:
        log_seguridad("SCRAPER_ERROR", f"Fallo al descargar {url}: {str(e)}")
        return {"exito": False, "razon": str(e)}
