"""
core/profile_manager.py
Gestiona perfiles de usuario: exportar, importar, crear nuevos.
Atlas v3.9
"""
import os
import json
import shutil
from datetime import datetime
from core.security import log_seguridad

# Estructura de directorios - ✅ CORREGIDO: agregado #
ESTRUCTURA_MEMORIA = {
    "00_Sistema": ["Prompts"],
    "01_Perfil": [],
    "02_Memoria": [],
    "03_Conocimiento": ["Estudio", "Derecho", "Investigacion", "General"],
    "04_Universidad": [],  # ✅ CORREGIDO: Univercidad → Universidad
    "05_Proyectos": [],
    "06_Diario": [],
    "07_Salud": [],
    "08_Finanzas": [],
    "backups": []
}


def crear_estructura_memoria(ruta_base="memory/Atlas_Memory"):
    """Crea la estructura completa de directorios de memoria."""
    try:
        for carpeta, subcarpetas in ESTRUCTURA_MEMORIA.items():
            ruta_carpeta = os.path.join(ruta_base, carpeta)
            os.makedirs(ruta_carpeta, exist_ok=True)
            for subcarpeta in subcarpetas:
                ruta_subcarpeta = os.path.join(ruta_carpeta, subcarpeta)
                os.makedirs(ruta_subcarpeta, exist_ok=True)
        return True, "Estructura de memoria creada correctamente"
    except Exception as e:
        return False, f"Error creando estructura: {str(e)}"


def exportar_perfil_actual(nombre_usuario="charly"):
    """
    Exporta el perfil actual (memoria + prompts + config) a un archivo ZIP.
    """
    try:
        import zipfile
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_zip = f"perfil_{nombre_usuario}_{timestamp}.zip"
        ruta_zip = os.path.join("memory/Atlas_Memory/backups", nombre_zip)
        
        os.makedirs(os.path.dirname(ruta_zip), exist_ok=True)
        
        with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Exportar memoria
            memoria_dir = "memory/Atlas_Memory"
            if os.path.exists(memoria_dir):
                for root, dirs, files in os.walk(memoria_dir):
                    # Excluir backups y vector_db
                    if "backups" in root or "vector_db" in root:
                        continue
                    for file in files:
                        ruta_archivo = os.path.join(root, file)
                        arcname = os.path.relpath(ruta_archivo, ".")
                        zipf.write(ruta_archivo, arcname)
            
            # Exportar prompts
            prompts_dir = "memory/Atlas_Memory/00_Sistema/Prompts"
            if os.path.exists(prompts_dir):
                for file in os.listdir(prompts_dir):
                    if file.endswith(".md"):
                        ruta_archivo = os.path.join(prompts_dir, file)
                        arcname = os.path.relpath(ruta_archivo, ".")
                        zipf.write(ruta_archivo, arcname)
        
        log_seguridad("PERFIL_EXPORTADO", f"Perfil exportado: {nombre_zip}")
        return True, ruta_zip
    except Exception as e:
        log_seguridad("PERFIL_EXPORT_ERROR", f"Error exportando perfil: {str(e)}")
        return False, str(e)


def importar_perfil(ruta_zip):
    """
    Importa un perfil desde un archivo ZIP.
    Hace backup del perfil actual antes de importar.
    """
    try:
        import zipfile
        if not os.path.exists(ruta_zip):
            return False, f"Archivo no encontrado: {ruta_zip}"
        
        # Backup del perfil actual
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = "memory/Atlas_Memory/backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_zip = os.path.join(backup_dir, f"backup_antes_importar_{timestamp}.zip")
        
        ok_backup, msg_backup = exportar_perfil_actual("backup")
        if not ok_backup:
            return False, f"Error haciendo backup: {msg_backup}"
        
        # Extraer perfil de forma segura (protección Zip Slip).
        with zipfile.ZipFile(ruta_zip, 'r') as zipf:
            destino = os.path.abspath(".")
            entrada_invalida = None
            for miembro in zipf.namelist():
                ruta_destino = os.path.abspath(os.path.join(destino, miembro))
                # commonpath detecta traversal tipo ../../Windows/...
                if os.path.commonpath([ruta_destino, destino]) != destino:
                    entrada_invalida = miembro
                    break
            if entrada_invalida:
                raise ValueError(f"Entrada Zip Slip detectada: {entrada_invalida}")
            zipf.extractall(destino)
        
        log_seguridad("PERFIL_IMPORTADO", f"Perfil importado desde: {ruta_zip}")
        return True, f"Perfil importado. Backup guardado en: {backup_zip}"
    except Exception as e:
        log_seguridad("PERFIL_IMPORT_ERROR", f"Error importando perfil: {str(e)}")
        return False, str(e)


def listar_perfiles_exportados():
    """Lista todos los perfiles exportados en la carpeta de backups."""
    try:
        backup_dir = "memory/Atlas_Memory/backups"
        if not os.path.exists(backup_dir):
            return []
        
        perfiles = []
        for archivo in os.listdir(backup_dir):
            if archivo.startswith("perfil_") and archivo.endswith(".zip"):
                ruta = os.path.join(backup_dir, archivo)
                stat = os.stat(ruta)
                perfiles.append({
                    "nombre": archivo,
                    "ruta": ruta,
                    "tamano_kb": round(stat.st_size / 1024, 2),
                    "fecha": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
        return sorted(perfiles, key=lambda x: x["fecha"], reverse=True)
    except Exception as e:
        return []


def crear_perfil_nuevo(nombre_usuario):
    """
    Crea un perfil nuevo con estructura de memoria vacía.
    """
    try:
        ruta_base = f"memory/Atlas_Memory_{nombre_usuario}"
        ok, msg = crear_estructura_memoria(ruta_base)
        if ok:
            log_seguridad("PERFIL_CREADO", f"Perfil nuevo creado: {nombre_usuario}")
            return True, nombre_usuario
        else:
            return False, msg
    except Exception as e:
        log_seguridad("PERFIL_CREATE_ERROR", f"Error creando perfil: {str(e)}")
        return False, str(e)