import os
from core.security import validar_ruta, log_seguridad

BASE = "memory/Atlas_Memory"


def listar_archivos():
    """Lista todos los archivos de la memoria."""
    archivos = []
    
    for root, _, files in os.walk(BASE):
        for f in files:
            ruta = os.path.join(root, f)
            
            archivos.append({
                "nombre": f,
                "ruta": ruta,
                "extension": os.path.splitext(f)[1].lower()
            })
    
    archivos.sort(key=lambda x: x["ruta"])
    
    return archivos


def listar_carpetas():
    """Lista todas las carpetas de la memoria."""
    carpetas = []
    
    for root, dirs, _ in os.walk(BASE):
        for d in dirs:
            ruta = os.path.join(root, d)
            
            carpetas.append({
                "nombre": d,
                "ruta": ruta
            })
    
    carpetas.sort(key=lambda x: x["ruta"])
    
    return carpetas


def leer_archivo(nombre_archivo):
    """
    Lee un archivo de la memoria con validación de seguridad.
    
    Args:
        nombre_archivo: Nombre o ruta parcial del archivo
    
    Returns:
        dict con: {"encontrado": bool, "ruta": str, "contenido": str}
    """
    # Buscar el archivo
    archivos = listar_archivos()
    
    archivo_encontrado = None
    for a in archivos:
        if nombre_archivo.lower() in a["nombre"].lower():
            archivo_encontrado = a
            break
    
    if not archivo_encontrado:
        return {"encontrado": False, "ruta": "", "contenido": ""}
    
    ruta = archivo_encontrado["ruta"]
    
    # VALIDACIÓN DE SEGURIDAD: Prevenir path traversal
    es_valida, error_ruta = validar_ruta(ruta)
    if not es_valida:
        log_seguridad("LECTURA_BLOQUEADA", f"Intento de leer archivo fuera de memoria: {ruta}")
        return {"encontrado": False, "ruta": ruta, "contenido": f"Error de seguridad: {error_ruta}"}
    
    # Leer el contenido
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        
        log_seguridad("LECTURA_EXITOSA", f"Archivo leído: {ruta}")
        return {"encontrado": True, "ruta": ruta, "contenido": contenido}
    
    except Exception as e:
        log_seguridad("ERROR_LECTURA", f"Error leyendo {ruta}: {str(e)}")
        return {"encontrado": False, "ruta": ruta, "contenido": f"Error leyendo archivo: {str(e)}"}