"""
scripts/backup_atlas.py
Genera un backup completo de Atlas listo para restaurar en otra PC.
"""
import os
import shutil
import zipfile
from datetime import datetime
import json


def _authoritative_vector_source():
    from core.config import CHROMA_PATH
    from core.system.paths import validate_vector_store_path

    return validate_vector_store_path(CHROMA_PATH)


def crear_backup_atlas():
    """
    Crea un ZIP con todo lo necesario para restaurar Atlas.
    """
    vector_source = os.fspath(_authoritative_vector_source())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"Atlas_Backup_{timestamp}.zip"
    
    # Cada entrada separa la fuente real de su ruta estable dentro del ZIP.
    carpetas_backup = [
        ("core", "core"),                         # Código fuente
        ("memory", "memory"),                     # Memoria, prompts, conocimiento
        (vector_source, "vector_db"),             # Base de datos vectorial
        ("atlas_ui.py", "atlas_ui.py"),           # UI
        ("atlas_chat.py", "atlas_chat.py"),       # CLI
        (".env", ".env"),                         # Variables de entorno
        ("requirements.txt", "requirements.txt"), # Dependencias
        ("README.md", "README.md"),
    ]
    
    # Archivos a excluir
    excluir = [
        "__pycache__",
        "*.pyc",
        ".git",
        "temp_*",
        "*.log"
    ]
    
    print(f"\n[BACKUP] Creando backup: {nombre_backup}")
    print("=" * 60)
    
    with zipfile.ZipFile(nombre_backup, 'w', zipfile.ZIP_DEFLATED) as zipf:
        archivos_incluidos = 0
        
        for source, archive_root in carpetas_backup:
            if not os.path.exists(source):
                continue
            
            if os.path.isdir(source):
                source_root = os.path.abspath(source)
                for root, dirs, files in os.walk(source_root):
                    # Excluir carpetas
                    dirs[:] = [d for d in dirs if not any(exc in d for exc in excluir)]
                    
                    for file in files:
                        if any(file.endswith(exc.replace("*", "")) for exc in excluir if "*" in exc):
                            continue
                        
                        ruta_completa = os.path.join(root, file)
                        relative_file = os.path.relpath(ruta_completa, source_root)
                        ruta_zip = os.path.join(archive_root, relative_file).replace("\\", "/")
                        
                        try:
                            zipf.write(ruta_completa, ruta_zip)
                            archivos_incluidos += 1
                            print(f"  [OK] {ruta_zip}")
                        except Exception as e:
                            print(f"  [WARNING] Error con {ruta_zip}: {e}")
            else:
                # Es archivo individual
                try:
                    zipf.write(source, archive_root)
                    archivos_incluidos += 1
                    print(f"  [OK] {archive_root}")
                except Exception as e:
                    print(f"  [WARNING] Error con {archive_root}: {e}")
    
    tamaño_mb = os.path.getsize(nombre_backup) / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print(f"[OK] Backup creado: {nombre_backup}")
    print(f"   [INFO] Archivos incluidos: {archivos_incluidos}")
    print(f"   [INFO] Tamaño: {tamaño_mb:.2f} MB")
    print(f"   [INFO] Ubicación: {os.path.abspath(nombre_backup)}")
    print("\n[INFO] INSTRUCCIONES DE RESTAURACIÓN:")
    print("   1. Copiá este ZIP a la nueva PC")
    print("   2. Descomprimilo en la carpeta donde querés Atlas")
    print("   3. Ejecutá: python scripts/restaurar_atlas.py")
    print("=" * 60)
    
    return nombre_backup

if __name__ == "__main__":
    crear_backup_atlas()
