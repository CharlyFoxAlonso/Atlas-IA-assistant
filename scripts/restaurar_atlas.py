"""
scripts/restaurar_atlas.py
Restaura Atlas desde un backup en una PC nueva.
"""
import os
import sys
import subprocess
import zipfile

def restaurar_backup():
    """
    Restaura Atlas desde un backup ZIP.
    """
    print("\n🔧 Restaurando Atlas desde backup...")
    print("=" * 60)
    
    # Buscar el backup más reciente
    backups = [f for f in os.listdir(".") if f.startswith("Atlas_Backup_") and f.endswith(".zip")]
    
    if not backups:
        print("❌ No se encontró ningún backup (Atlas_Backup_*.zip)")
        return False
    
    backup_mas_reciente = sorted(backups)[-1]
    print(f"📦 Backup detectado: {backup_mas_reciente}")
    
    # Descomprimir
    print("📂 Descomprimiendo...")
    with zipfile.ZipFile(backup_mas_reciente, 'r') as zipf:
        zipf.extractall(".")
    
    print("✅ Archivos extraídos")
    
    # Instalar dependencias
    print("\n📦 Instalando dependencias...")
    if os.path.exists("requirements.txt"):
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            print("✅ Dependencias instaladas")
        except Exception as e:
            print(f"⚠️ Error instalando dependencias: {e}")
            print("   Instalá manualmente: pip install -r requirements.txt")
    else:
        print("⚠️ No se encontró requirements.txt")
    
    # Verificar .env
    if not os.path.exists(".env"):
        print("\n⚠️ No se encontró archivo .env")
        print("   Creá uno con estas variables:")
        print("   MOTOR_POR_DEFECTO=atlas")
        print("   NVIDIA_API_KEY=tu_api_key")
        print("   GROQ_API_KEY=tu_api_key")
        print("   BINANCE_API_KEY=tu_api_key")
        print("   BINANCE_API_SECRET=tu_api_secret")
    
    print("\n" + "=" * 60)
    print("✅ RESTAURACIÓN COMPLETADA")
    print("\n🚀 Próximos pasos:")
    print("   1. Instalá Ollama: https://ollama.com/download")
    print("   2. Descargá el modelo: ollama pull qwen3:8b")
    print("   3. Instalá Tesseract OCR (para PDFs escaneados)")
    print("   4. Instalá Poppler (para PDFs escaneados)")
    print("   5. Ejecutá: streamlit run atlas_ui.py")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    restaurar_backup()