"""
scripts/backup_atlas.py
Genera un backup completo de Atlas listo para restaurar en otra PC.
"""
import os
import shutil
import zipfile
from datetime import datetime
import json

def crear_backup_atlas():
    """
    Crea un ZIP con todo lo necesario para restaurar Atlas.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"Atlas_Backup_{timestamp}.zip"
    
    # Carpetas a incluir
    carpetas_backup = [
        "core",                           # Código fuente
        "memory",                         # Memoria, prompts, conocimiento
        "vector_db",                      # Base de datos vectorial
        "atlas_ui.py",                    # UI
        "atlas_chat.py",                  # CLI
        ".env",                           # Variables de entorno
        "requirements.txt",               # Dependencias
        "README.md" if os.path.exists("README.md") else None
    ]
    
    # Archivos a excluir
    excluir = [
        "__pycache__",
        "*.pyc",
        ".git",
        "temp_*",
        "*.log"
    ]
    
    print(f"\n🔧 Creando backup: {nombre_backup}")
    print("=" * 60)
    
    with zipfile.ZipFile(nombre_backup, 'w', zipfile.ZIP_DEFLATED) as zipf:
        archivos_incluidos = 0
        
        for item in carpetas_backup:
            if not item or not os.path.exists(item):
                continue
            
            if os.path.isdir(item):
                for root, dirs, files in os.walk(item):
                    # Excluir carpetas
                    dirs[:] = [d for d in dirs if not any(exc in d for exc in excluir)]
                    
                    for file in files:
                        if any(file.endswith(exc.replace("*", "")) for exc in excluir if "*" in exc):
                            continue
                        
                        ruta_completa = os.path.join(root, file)
                        ruta_zip = os.path.relpath(ruta_completa, ".")
                        
                        try:
                            zipf.write(ruta_completa, ruta_zip)
                            archivos_incluidos += 1
                            print(f"  ✓ {ruta_zip}")
                        except Exception as e:
                            print(f"  ⚠️ Error con {ruta_zip}: {e}")
            else:
                # Es archivo individual
                try:
                    zipf.write(item)
                    archivos_incluidos += 1
                    print(f"  ✓ {item}")
                except Exception as e:
                    print(f"  ⚠️ Error con {item}: {e}")
    
    tamaño_mb = os.path.getsize(nombre_backup) / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print(f"✅ Backup creado: {nombre_backup}")
    print(f"   📊 Archivos incluidos: {archivos_incluidos}")
    print(f"   💾 Tamaño: {tamaño_mb:.2f} MB")
    print(f"   📁 Ubicación: {os.path.abspath(nombre_backup)}")
    print("\n💡 INSTRUCCIONES DE RESTAURACIÓN:")
    print("   1. Copiá este ZIP a la nueva PC")
    print("   2. Descomprimilo en la carpeta donde querés Atlas")
    print("   3. Ejecutá: python scripts/restaurar_atlas.py")
    print("=" * 60)
    
    return nombre_backup

if __name__ == "__main__":
    crear_backup_atlas()