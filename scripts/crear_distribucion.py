"""
Atlas - Generador de Distribucion.
Genera un ZIP con Atlas limpio (sin datos personales de Charly)
listo para instalar en otra PC.

USO:
    cd C:/Users/delfa/Documents/Atlas/scripts
    python crear_distribucion.py
"""
import os
import sys
import shutil
import zipfile
from datetime import datetime


def crear_distribucion():
    """Crea el paquete distribuible de Atlas."""
    
    print("\n" + "=" * 60)
    print("CREANDO DISTRIBUCION DE ATLAS")
    print("=" * 60 + "\n")
    
    # Guardar directorio raiz (Atlas/)
    raiz_atlas = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(raiz_atlas)
    
    print(f"[DIR] Directorio raiz: {raiz_atlas}\n")
    
    # Agregar scripts al path para importar
    scripts_dir = os.path.join(raiz_atlas, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    
    # ========================================
    # PASO 1: Limpiar datos personales
    # ========================================
    print("[1/5] Limpiando datos personales...")
    try:
        from limpiar_para_distribuir import limpiar_atlas
        clean_dir = limpiar_atlas()
        print(f"[OK] Atlas Clean creado en: {clean_dir}/\n")
    except ImportError as e:
        print(f"[ERROR] Importando limpiar_para_distribuir: {e}")
        print("   Asegurate de tener scripts/limpiar_para_distribuir.py")
        return None
    except Exception as e:
        print(f"[ERROR] En limpieza: {e}")
        return None
    
    # ========================================
    # PASO 2: Copiar instalador
    # ========================================
    print("[2/5] Copiando instalador...")
    installer_path = os.path.join(raiz_atlas, "Atlas_Installer.bat")
    
    if os.path.exists(installer_path):
        destino_installer = os.path.join(clean_dir, "Atlas_Installer.bat")
        shutil.copy2(installer_path, destino_installer)
        print(f"[OK] Instalador copiado\n")
    else:
        print("[WARN] Atlas_Installer.bat no encontrado en la raiz\n")
    
    # ========================================
    # PASO 3: Copiar scripts utiles
    # ========================================
    print("[3/5] Copiando scripts de utilidad...")
    scripts_destino = os.path.join(clean_dir, "scripts")
    os.makedirs(scripts_destino, exist_ok=True)
    
    scripts_a_copiar = ["limpiar_para_distribuir.py", "crear_distribucion.py"]
    for script in scripts_a_copiar:
        origen = os.path.join(scripts_dir, script)
        if os.path.exists(origen):
            shutil.copy2(origen, os.path.join(scripts_destino, script))
            print(f"   [OK] {script}")
        else:
            print(f"   [WARN] {script} no encontrado")
    print()
    
    # ========================================
    # PASO 4: Crear ZIP
    # ========================================
    print("[4/5] Comprimiendo...")
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_name = f"Atlas_v2.0_{timestamp}.zip"
    zip_path = os.path.join(raiz_atlas, zip_name)
    
    # Eliminar ZIP anterior si existe
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            archivos_comprimidos = 0
            for root, dirs, files in os.walk(clean_dir):
                # Excluir __pycache__
                if "__pycache__" in root:
                    continue
                
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, clean_dir)
                    zipf.write(file_path, arcname)
                    archivos_comprimidos += 1
        
        print(f"[OK] ZIP creado: {zip_name}")
        print(f"   Archivos comprimidos: {archivos_comprimidos}\n")
    
    except Exception as e:
        print(f"[ERROR] Creando ZIP: {e}")
        shutil.rmtree(clean_dir, ignore_errors=True)
        return None
    
    # ========================================
    # PASO 5: Limpiar directorio temporal
    # ========================================
    print("[5/5] Limpiando archivos temporales...")
    try:
        shutil.rmtree(clean_dir)
        print(f"[OK] Directorio temporal eliminado\n")
    except Exception as e:
        print(f"[WARN] No se pudo eliminar: {e}\n")
    
    # ========================================
    # RESULTADO FINAL
    # ========================================
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print("DISTRIBUCION CREADA EXITOSAMENTE")
    print("=" * 60)
    
    print(f"\n[ARCHIVO] {zip_name}")
    print(f"[UBICACION] {zip_path}")
    print(f"[TAMANIO] {size_mb:.2f} MB")
    
    print(f"\n[CONTENIDO]")
    print(f"   - Codigo completo de Atlas (core/, config/)")
    print(f"   - Estructura de memoria limpia (sin datos personales)")
    print(f"   - Prompts genericos (sin personalizacion)")
    print(f"   - Instalador automatico (Atlas_Installer.bat)")
    print(f"   - Documentacion (README.md)")
    print(f"   - requirements.txt")
    print(f"   - Scripts de utilidad (scripts/)")
    
    print(f"\n[INSTALACION EN OTRA PC]")
    print(f"   1. Copiar {zip_name} a la PC destino")
    print(f"   2. Descomprimir el ZIP")
    print(f"   3. Ejecutar Atlas_Installer.bat (como administrador)")
    print(f"   4. Esperar descarga de Ollama + modelo (~5GB)")
    print(f"   5. Listo!")
    
    print("\n" + "=" * 60 + "\n")
    
    return zip_path


def verificar_requisitos():
    """Verifica que todos los archivos necesarios existan."""
    print("\n[CHECK] Verificando requisitos...\n")
    
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    archivos_requeridos = [
        "run.py",
        "atlas_chat.py",
        "atlas_ui.py",
        "requirements.txt",
        "core/brain.py",
        "core/router.py",
        "core/models.py",
        "core/memory_manager.py",
        "scripts/limpiar_para_distribuir.py"
    ]
    
    todos_ok = True
    for archivo in archivos_requeridos:
        ruta = os.path.join(raiz, archivo)
        if os.path.exists(ruta):
            print(f"   [OK] {archivo}")
        else:
            print(f"   [FALTA] {archivo}")
            todos_ok = False
    
    print()
    
    if todos_ok:
        print("[OK] Todos los archivos requeridos estan presentes\n")
        return True
    else:
        print("[WARN] Faltan archivos. Completalos antes de continuar.\n")
        return True  # Permitir continuar igual


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ATLAS - GENERADOR DE DISTRIBUCION")
    print("=" * 60)
    
    # Verificar requisitos
    verificar_requisitos()
    
    # Confirmar
    print("\n[INFO] Este script creara un paquete distribuible de Atlas.")
    print("[INFO] Los datos personales NO se incluiran.")
    print("[INFO] Se generara un ZIP en la raiz de Atlas.\n")
    
    confirmar = input("Continuar? (s/n): ").strip().lower()
    
    if confirmar not in ["s", "si", "si"]:
        print("\n[CANCELADO]\n")
        sys.exit(0)
    
    # Crear distribucion
    resultado = crear_distribucion()
    
    if resultado:
        print(f"\n[EXITO] Distribucion creada: {resultado}\n")
    else:
        print(f"\n[ERROR] No se pudo crear la distribucion.\n")
        sys.exit(1)