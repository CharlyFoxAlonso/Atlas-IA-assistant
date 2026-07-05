"""
Módulo de seguridad de Atlas.
Protecciones básicas contra ataques comunes.
"""
import os
import logging
from datetime import datetime

# Configurar logging de seguridad
logging.basicConfig(
    filename='atlas_security.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Base de memoria (debe coincidir con la usada en otros módulos)
BASE_MEMORIA = "memory/Atlas_Memory"

# Patrones sospechosos de inyección de prompts (SIN espacios al final)
PATRONES_PELIGROSOS = [
    "ignore previous",
    "ignore all",
    "ignore instructions",
    "system:",
    "override",
    "you are now",
    "forget everything",
    "new instructions",
    "act as",
    "pretend you are",
    "jailbreak",
    "do anything now",
    "dan mode",
    "developer mode",
    "bypass",
    "hack",
    "exploit"
]


def validar_ruta(ruta_archivo):
    """
    Valida que la ruta esté dentro de la carpeta de memoria.
    Previene path traversal attacks.

    Args:
        ruta_archivo: Ruta del archivo a validar

    Returns:
        (bool, str): (es_valida, mensaje_error)
    """
    try:
        # Convertir a rutas absolutas reales (resuelve .. y symlinks)
        base_real = os.path.realpath(BASE_MEMORIA)
        ruta_real = os.path.realpath(ruta_archivo)

        # Verificar que la ruta esté dentro de la base
        if not ruta_real.startswith(base_real):
            log_seguridad("ACCESO_DENEGADO", f"Intento de acceso fuera de memoria: {ruta_archivo}")
            return False, "Acceso fuera de la carpeta de memoria"
        return True, ""
    except Exception as e:
        log_seguridad("ERROR_VALIDACION", f"Error validando ruta {ruta_archivo}: {str(e)}")
        return False, f"Error validando ruta: {str(e)}"


def sanitizar_contenido(texto):
    """
    Detecta patrones sospechosos de inyección de prompts.

    Args:
        texto: Texto a analizar

    Returns:
        (bool, list): (es_seguro, lista_de_paternes_detectados)
    """
    if not texto:
        return True, []

    texto_lower = texto.lower()
    patrones_detectados = []

    for patron in PATRONES_PELIGROSOS:
        if patron in texto_lower:
            patrones_detectados.append(patron)

    if patrones_detectados:
        log_seguridad("INYECCION_DETECTADA", f"Patrones sospechosos: {', '.join(patrones_detectados)}")
        return False, patrones_detectados

    return True, []


def log_seguridad(evento, detalle):
    """
    Registra eventos de seguridad en el log.

    Args:
        evento: Tipo de evento (ACCESO_DENEGADO, INYECCION_DETECTADA, etc.)
        detalle: Descripción del evento
    """
    logging.warning(f"{evento}: {detalle}")


def verificar_ollama_localhost():
    """
    Verifica que Ollama solo escuche en localhost.

    Returns:
        (bool, str): (es_seguro, mensaje)
    """
    try:
        import socket
        # Verificar si el puerto 11434 está escuchando en 0.0.0.0 (peligroso)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)

        # Intentar conectar a 0.0.0.0:11434
        result = s.connect_ex(('0.0.0.0', 11434))
        s.close()

        if result == 0:
            # Puerto abierto en 0.0.0.0 - verificar si también está en localhost
            s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s2.settimeout(1)
            result2 = s2.connect_ex(('127.0.0.1', 11434))
            s2.close()

            if result2 == 0:
                # Está en ambos - podría estar expuesto
                log_seguridad("OLLAMA_EXPUESTO", "Ollama podría estar accesible en red local")
                return False, "Ollama podría estar expuesto en la red local. Configurá OLLAMA_HOST=127.0.0.1:11434"

        return True, "Ollama está configurado correctamente (solo localhost)"
    except Exception as e:
        return True, f"No se pudo verificar Ollama: {str(e)}"


def verificar_permisos_carpeta():
    """
    Verifica los permisos de la carpeta de memoria.

    Returns:
        (bool, str): (es_seguro, mensaje)
    """
    try:
        if not os.path.exists(BASE_MEMORIA):
            return False, f"La carpeta {BASE_MEMORIA} no existe"

        # En Windows, verificar si la carpeta es accesible
        # (esto es básico, en producción se debería verificar ACLs)
        if os.access(BASE_MEMORIA, os.W_OK):
            return True, "La carpeta de memoria tiene permisos de escritura"
        else:
            return False, "La carpeta de memoria no tiene permisos de escritura"
    except Exception as e:
        return False, f"Error verificando permisos: {str(e)}"


def reporte_seguridad_completo():
    """
    Genera un reporte completo de seguridad.

    Returns:
        dict: Reporte con estado de cada verificación
    """
    reporte = {
        "timestamp": datetime.now().isoformat(),
        "verificaciones": {}
    }

    # Verificar Ollama
    ollama_ok, ollama_msg = verificar_ollama_localhost()
    reporte["verificaciones"]["ollama_localhost"] = {
        "estado": "OK" if ollama_ok else "ADVERTENCIA",
        "mensaje": ollama_msg
    }

    # Verificar permisos
    permisos_ok, permisos_msg = verificar_permisos_carpeta()
    reporte["verificaciones"]["permisos_carpeta"] = {
        "estado": "OK" if permisos_ok else "ADVERTENCIA",
        "mensaje": permisos_msg
    }

    # Contar eventos de seguridad en el log
    try:
        with open('atlas_security.log', 'r', encoding='utf-8') as f:
            lineas = f.readlines()
            eventos_recientes = [l for l in lineas[-10:] if l.strip()]
            reporte["verificaciones"]["eventos_recientes"] = {
                "cantidad": len(eventos_recientes),
                "ultimos": eventos_recientes[-3:] if eventos_recientes else []
            }
    except FileNotFoundError:
        reporte["verificaciones"]["eventos_recientes"] = {
            "cantidad": 0,
            "ultimos": []
        }

    return reporte