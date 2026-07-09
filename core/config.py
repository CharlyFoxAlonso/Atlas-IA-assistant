"""
core/config.py
========================================
CONFIGURACIÓN CENTRALIZADA DE ATLAS v3
========================================

Este archivo es el ÚNICO lugar donde se definen:
- Modelos de IA (local y nube)
- URLs de servicios
- Rutas base del sistema
- Parámetros de RAG
- Detección de hardware

PARA UPGRADE DE HARDWARE:
    1. Descargá el nuevo modelo:  ollama pull <modelo>
    2. Cambiá MODELO_LOCAL abajo (o en .env)
    3. Reiniciá Atlas
"""
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

# ============================================
# VERSIÓN E IDENTIDAD
# ============================================
VERSION = "3.6"
NOMBRE = "Atlas"
CODENAME = "Multi-Nube"

# ============================================
# 🧠 MODELO LOCAL (Ollama)
# ============================================
MODELO_LOCAL = os.getenv("MODELO_LOCAL", "qwen3:8b")
URL_OLLAMA = os.getenv("URL_OLLAMA", "http://127.0.0.1:11434/api/chat")

# ============================================
# ⚡ MODELO NUBE (NVIDIA API - Prometeo)
# ============================================
MODELO_NUBE_DEFAULT = os.getenv("MODELO_NUBE", "meta/llama-3.1-70b-instruct")
URL_NVIDIA = "https://integrate.api.nvidia.com/v1"

MODELOS_NUBE_DISPONIBLES = {
    "meta/llama-3.1-70b-instruct": "Llama 3.1 70B (Equilibrado)",
    "meta/llama-3.1-8b-instruct": "Llama 3.1 8B (Rápido)",
    "meta/llama-3.3-70b-instruct": "Llama 3.3 70B (Nuevo)",
    "deepseek-ai/deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-ai/deepseek-v4-pro": "DeepSeek V4 Pro (Top)",
    "google/gemma-3-12b-it": "Gemma 3 12B (Google)",
    "google/gemma-4-31b-it": "Gemma 4 31B (Google)",
    "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra 550B",
}

MODELOS_DIGESTION = [
    "meta/llama-3.1-70b-instruct",
    "deepseek-ai/deepseek-v4-pro",
    "nvidia/nemotron-3-ultra-550b-a55b",
]

# ============================================
# 🏠 CATÁLOGO DE MODELOS LOCALES (Ollama)
# ============================================
MODELOS_LOCALES_DISPONIBLES = {
    "qwen3:8b": {
        "nombre": "qwen3:8b",
        "descripcion": "Qwen3 8B (Actual - Rápido)",
        "tamano_gb": 4.7,
        "ram_min_gb": 8,
        "vram_min_gb": 6,
        "velocidad": "~30 tok/s",
        "calidad": 3,
        "uso": "Conversación rápida, tareas simples",
        "arquitectura": "Dense",
        "destacado": False,
        "notas": "Modelo actual. Excelente para tareas cotidianas."
    },
    "qwen3:14b": {
        "nombre": "qwen3:14b",
        "descripcion": "Qwen3 14B (Balance)",
        "tamano_gb": 9.0,
        "ram_min_gb": 16,
        "vram_min_gb": 8,
        "velocidad": "~18 tok/s",
        "calidad": 4,
        "uso": "Exámenes, análisis jurídico, razonamiento medio",
        "arquitectura": "Dense",
        "destacado": False,
        "notas": "Salto de calidad notable vs 8b."
    },
    "qwen3:30b-a3b": {
        "nombre": "qwen3:30b-a3b",
        "descripcion": "Qwen3 30B-A3B MoE (⭐ MEJOR OPCIÓN)",
        "tamano_gb": 18.0,
        "ram_min_gb": 32,
        "vram_min_gb": 10,
        "velocidad": "~25 tok/s",
        "calidad": 5,
        "uso": "TODO: exámenes, derecho, código, razonamiento",
        "arquitectura": "MoE (Mixture of Experts)",
        "destacado": True,
        "notas": "Solo activa 3B params por token. Piensa como 30B, corre como 8B."
    },
    "gemma3:12b": {
        "nombre": "gemma3:12b",
        "descripcion": "Gemma 3 12B (Google)",
        "tamano_gb": 8.0,
        "ram_min_gb": 16,
        "vram_min_gb": 6,
        "velocidad": "~20 tok/s",
        "calidad": 4,
        "uso": "Alternativa a Qwen, mejor en español",
        "arquitectura": "Dense",
        "destacado": False,
        "notas": "Modelo de Google. Muy bueno en español."
    },
    "deepseek-r1:14b": {
        "nombre": "deepseek-r1:14b",
        "descripcion": "DeepSeek R1 14B (Razonamiento)",
        "tamano_gb": 9.0,
        "ram_min_gb": 16,
        "vram_min_gb": 8,
        "velocidad": "~15 tok/s",
        "calidad": 5,
        "uso": "Problemas complejos, estadística, lógica",
        "arquitectura": "Dense (Chain-of-Thought)",
        "destacado": False,
        "notas": "Muestra cadena de pensamiento. Ideal para exámenes difíciles."
    },
    "mistral-small:22b": {
        "nombre": "mistral-small:22b",
        "descripcion": "Mistral Small 22B (Máxima calidad)",
        "tamano_gb": 13.0,
        "ram_min_gb": 32,
        "vram_min_gb": 0,
        "velocidad": "~8 tok/s",
        "calidad": 5,
        "uso": "Tareas donde la calidad importa más que velocidad",
        "arquitectura": "Dense",
        "destacado": False,
        "notas": "Lento pero muy capaz. Corre en RAM."
    },
    "llama3.1:8b": {
        "nombre": "llama3.1:8b",
        "descripcion": "Llama 3.1 8B (Meta)",
        "tamano_gb": 4.7,
        "ram_min_gb": 8,
        "vram_min_gb": 6,
        "velocidad": "~28 tok/s",
        "calidad": 3,
        "uso": "Alternativa a Qwen3 8B",
        "arquitectura": "Dense",
        "destacado": False,
        "notas": "Modelo de Meta. Mejor en inglés."
    },
    "phi4:14b": {
        "nombre": "phi4:14b",
        "descripcion": "Phi-4 14B (Microsoft)",
        "tamano_gb": 8.5,
        "ram_min_gb": 16,
        "vram_min_gb": 8,
        "velocidad": "~17 tok/s",
        "calidad": 4,
        "uso": "Razonamiento, matemáticas, código",
        "arquitectura": "Dense",
        "destacado": False,
        "notas": "Modelo pequeño pero muy capaz de Microsoft."
    },
}

# ============================================
# 📂 RUTAS BASE
# ============================================
BASE_MEMORIA = "memory/Atlas_Memory"
BASE_ESTUDIO = "memory/Atlas_Memory/03_Conocimiento"
BASE_PROMPTS = "memory/Atlas_Memory/00_Sistema/Prompts"
CHROMA_PATH = "./vector_db"
COLLECTION_NAME = "atlas_rag"

# ============================================
# 🔍 PARÁMETROS DE RAG
# ============================================
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
N_RESULTS_DEFAULT = 5
UMBRAL_SEMANTICO = 200

# ============================================
# 💬 HISTORIAL Y ANÁLISIS
# ============================================
MAX_HISTORIAL = 5
INTERVALO_ANALISIS = 5

# ============================================
# 🔧 FUNCIONES AUXILIARES
# ============================================

def get_modelo_local() -> str:
    return MODELO_LOCAL


def set_modelo_local(nuevo_modelo: str) -> dict:
    global MODELO_LOCAL
    modelo_anterior = MODELO_LOCAL
    MODELO_LOCAL = nuevo_modelo
    return {
        "exito": True,
        "modelo_anterior": modelo_anterior,
        "modelo_nuevo": nuevo_modelo,
        "mensaje": f"Modelo cambiado: {modelo_anterior} → {nuevo_modelo}"
    }


def get_modelo_nube() -> str:
    return MODELO_NUBE_DEFAULT


def obtener_info_modelo(modelo_id: str) -> dict:
    if modelo_id in MODELOS_LOCALES_DISPONIBLES:
        return MODELOS_LOCALES_DISPONIBLES[modelo_id].copy()
    return {
        "nombre": modelo_id,
        "descripcion": modelo_id,
        "tamano_gb": 0,
        "ram_min_gb": 0,
        "vram_min_gb": 0,
        "velocidad": "Desconocida",
        "calidad": 0,
        "uso": "Desconocido",
        "arquitectura": "Desconocida",
        "destacado": False,
        "notas": "Modelo no catalogado."
    }


def listar_modelos_locales_descargados() -> list:
    """Lista modelos descargados en Ollama (compatible con Windows UTF-8)."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            return []
        modelos = []
        lineas = result.stdout.strip().split("\n")
        for linea in lineas[1:]:
            if linea.strip():
                partes = linea.split()
                if partes:
                    modelos.append(partes[0])
        return modelos
    except FileNotFoundError:
        return []
    except Exception:
        return []


def verificar_modelo_local(modelo_id: str) -> bool:
    descargados = listar_modelos_locales_descargados()
    return modelo_id in descargados


def descargar_modelo_local(modelo_id: str, callback_progreso=None) -> dict:
    """Descarga un modelo desde Ollama (compatible con Windows UTF-8)."""
    if verificar_modelo_local(modelo_id):
        return {"exito": True, "mensaje": f"✅ {modelo_id} ya está descargado"}
    try:
        if callback_progreso:
            callback_progreso(f"📥 Descargando {modelo_id}...")
        
        # Forzar UTF-8 y entorno limpio para Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        proceso = subprocess.Popen(
            ["ollama", "pull", modelo_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            encoding='utf-8',
            errors='replace',
            env=env
        )
        
        ultima_linea = ""
        for linea in proceso.stdout:
            ultima_linea = linea.strip()
            if callback_progreso and ultima_linea:
                callback_progreso(ultima_linea)
        
        proceso.wait()
        
        if proceso.returncode == 0:
            return {"exito": True, "mensaje": f"✅ {modelo_id} descargado correctamente"}
        else:
            return {"exito": False, "mensaje": f"❌ Error descargando {modelo_id}: {ultima_linea}"}
    
    except FileNotFoundError:
        return {"exito": False, "mensaje": "❌ Ollama no está instalado o no está en el PATH"}
    except Exception as e:
        return {"exito": False, "mensaje": f"❌ Error: {str(e)}"}


def eliminar_modelo_local(modelo_id: str) -> dict:
    """Elimina un modelo descargado (compatible con Windows UTF-8)."""
    try:
        result = subprocess.run(
            ["ollama", "rm", modelo_id],
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            return {"exito": True, "mensaje": f"🗑️ {modelo_id} eliminado"}
        else:
            return {"exito": False, "mensaje": f"❌ Error: {result.stderr}"}
    except Exception as e:
        return {"exito": False, "mensaje": f"❌ Error: {str(e)}"}


def obtener_catalogo_completo() -> dict:
    descargados = listar_modelos_locales_descargados()
    catalogo = {}
    for modelo_id, metadata in MODELOS_LOCALES_DISPONIBLES.items():
        info = metadata.copy()
        info["descargado"] = modelo_id in descargados
        info["activo"] = (modelo_id == MODELO_LOCAL)
        catalogo[modelo_id] = info
    for modelo_id in descargados:
        if modelo_id not in catalogo:
            catalogo[modelo_id] = {
                "nombre": modelo_id,
                "descripcion": modelo_id,
                "tamano_gb": 0,
                "ram_min_gb": 0,
                "vram_min_gb": 0,
                "velocidad": "Desconocida",
                "calidad": 0,
                "uso": "Desconocido",
                "arquitectura": "Desconocida",
                "destacado": False,
                "notas": "Modelo descargado pero no catalogado",
                "descargado": True,
                "activo": (modelo_id == MODELO_LOCAL)
            }
    return catalogo


def detectar_hardware() -> dict:
    ram_gb = _detectar_ram()
    gpu_info = _detectar_gpu()
    vram_gb = _detectar_vram()
    return {
        "ram_gb": ram_gb,
        "gpu": gpu_info,
        "vram_gb": vram_gb,
        "modelo_actual": MODELO_LOCAL,
        "recomendacion": _recomendar_modelo(ram_gb, vram_gb),
        "upgrade_sugerido": _sugerir_upgrade(ram_gb, vram_gb)
    }


def _detectar_ram() -> float:
    try:
        import psutil
        return round(psutil.virtual_memory().total / (1024**3), 1)
    except ImportError:
        pass
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    kb = int(line.split()[1])
                    return round(kb / (1024**2), 1)
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["wmic", "os", "get", "TotalVisibleMemorySize", "/Value"],
            capture_output=True, text=True, timeout=5,
            encoding='utf-8', errors='replace'
        )
        for line in result.stdout.split("\n"):
            if "=" in line:
                kb = int(line.split("=")[1].strip())
                return round(kb / (1024**2), 1)
    except Exception:
        pass
    return 0.0


def _detectar_gpu() -> str:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
            encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "No detectada o no NVIDIA"


def _detectar_vram() -> float:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
            encoding='utf-8', errors='replace'
        )
        if result.returncode == 0 and result.stdout.strip():
            mb = float(result.stdout.strip().split("\n")[0])
            return round(mb / 1024, 1)
    except Exception:
        pass
    return 0.0


def _recomendar_modelo(ram_gb: float, vram_gb: float) -> str:
    if ram_gb == 0:
        return "No se pudo detectar RAM"
    if vram_gb >= 24:
        return "llama3.1:70b (Q4) - aprovecha tu GPU"
    if vram_gb >= 16:
        return "qwen3:14b o gemma3:12b"
    if vram_gb >= 8:
        return "qwen3:8b (actual) o mistral:7b"
    if ram_gb >= 64:
        return "llama3.1:70b (Q4) en CPU"
    if ram_gb >= 32:
        return "qwen3:30b-a3b (MoE) - IDEAL para tu hardware"
    if ram_gb >= 16:
        return "qwen3:14b (ajustado) o gemma3:12b"
    if ram_gb >= 8:
        return "qwen3:8b (actual, óptimo para tu RAM)"
    return "RAM limitada → usar Prometeo (nube) para tareas pesadas"


def _sugerir_upgrade(ram_gb: float, vram_gb: float) -> str:
    if ram_gb < 8:
        return "🔴 Upgrade recomendado: 16 GB RAM mínimo"
    if ram_gb < 16:
        return "🟡 Upgrade útil: 32 GB RAM permitiría modelos más grandes"
    if vram_gb == 0 and ram_gb >= 16:
        return "💡 Upgrade recomendado: GPU NVIDIA con 8+ GB VRAM aceleraría todo"
    if vram_gb > 0 and vram_gb < 12:
        return "💡 Upgrade útil: GPU con 16+ GB VRAM permitiría modelos 70B cuantizados"
    return "✅ Hardware adecuado para el modelo actual"


def obtener_config_completa() -> dict:
    return {
        "version": VERSION,
        "nombre": NOMBRE,
        "modelo_local": MODELO_LOCAL,
        "url_ollama": URL_OLLAMA,
        "modelo_nube_default": MODELO_NUBE_DEFAULT,
        "url_nvidia": URL_NVIDIA,
        "modelos_nube_disponibles": list(MODELOS_NUBE_DISPONIBLES.keys()),
        "modelos_locales_catalogo": list(MODELOS_LOCALES_DISPONIBLES.keys()),
        "modelos_locales_descargados": listar_modelos_locales_descargados(),
        "base_memoria": BASE_MEMORIA,
        "chroma_path": CHROMA_PATH,
        "collection_name": COLLECTION_NAME,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "max_historial": MAX_HISTORIAL,
        "hardware": detectar_hardware()
    }


# ============================================
# OCR (Tesseract)
# ============================================
import sys as _sys


def _detectar_tesseract_cmd():
    """Detecta la ruta del ejecutable de Tesseract según la plataforma."""
    candidatos = []
    if _sys.platform.startswith("win"):
        candidatos.append(os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"))
        candidatos.append(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        candidatos.append(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe")
    elif _sys.platform == "darwin":
        candidatos += [
            "/opt/homebrew/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/local/bin/tesseract",
        ]
    else:
        candidatos += [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/snap/bin/tesseract",
        ]

    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta

    from shutil import which as _which
    encontrado = _which("tesseract")
    if encontrado:
        return encontrado

    return "tesseract"


TESSERACT_CMD = _detectar_tesseract_cmd()
OCR_LANGUAGE = os.getenv("ATLAS_OCR_LANG", "spa")


if __name__ == "__main__":
    print("=" * 60)
    print(f"  {NOMBRE} v{VERSION} - Configuración")
    print("=" * 60)
    config = obtener_config_completa()
    for k, v in config.items():
        if isinstance(v, dict):
            print(f"\n{k}:")
            for kk, vv in v.items():
                print(f"  {kk}: {vv}")
        elif isinstance(v, list):
            print(f"\n{k}:")
            for item in v:
                print(f"  - {item}")
        else:
            print(f"{k}: {v}")
    print("=" * 60)
    print("\n📚 Catálogo de modelos locales:")
    for modelo_id, info in MODELOS_LOCALES_DISPONIBLES.items():
        descargado = "✅" if verificar_modelo_local(modelo_id) else "❌"
        destacado = "⭐" if info.get("destacado") else "  "
        print(f"  {destacado} {descargado} {info['descripcion']:45s} | {info['tamano_gb']:5.1f} GB | {info['velocidad']}")