"""
core/self_awareness.py
Módulo de auto-conocimiento de Atlas v3.9.
Genera informes técnicos completos con código real de los archivos.
Incluye sistema de modelos locales y detección de hardware.
"""
import os
import json
from datetime import datetime

# Archivos core y su descripción (SIN espacios en keys ni values)
ARCHIVOS_CORE = {
    "brain.py": "Cerebro principal - genera respuestas con streaming híbrido",
    "router.py": "Router inteligente - detecta qué agente usar",
    "models.py": "Conexión con Ollama y NVIDIA - envía prompts",
    "config.py": "Configuración centralizada - modelos, URLs, hardware",
    "memory_manager.py": "Gestor de memoria - analiza y guarda conversaciones",
    "web_search.py": "Búsqueda web - DuckDuckGo",
    "vision.py": "Visión - captura pantalla y OCR",
    "speech_input.py": "Oídos - reconocimiento de voz (Google/Vosk)",
    "speech_output.py": "Voz - síntesis de voz (Edge TTS/pyttsx3)",
    "security.py": "Seguridad - validación de rutas y contenido",
    "file_loader.py": "Cargador de archivos - wrapper de universal_loader",
    "universal_loader.py": "Cargador universal - PDF, DOCX, PPTX, imágenes",
    "pdf_reader.py": "Lector de PDFs - pypdf + OCR con Poppler",
    "audio_transcriber.py": "Transcriptor de audio/video - Groq Whisper",
    "media_processor.py": "Procesador de medios - FFmpeg",
    "indexer.py": "Indexador - construye índice semántico ChromaDB",
    "vector_store.py": "Motor de búsqueda semántica - ChromaDB",
    "pdf_scraper.py": "Descargador web - validación y extracción",
    "ingestion_manager.py": "Ingesta web - pipeline URL → RAG",
    "local_ingestion_manager.py": "Ingesta local - pipeline Drag&Drop → RAG",
    "prometeo_worker.py": "Worker de digestión - paralelismo NVIDIA",
    "exam_mode.py": "Modo examen - RAG + generación de preguntas",
    "diary_manager.py": "Diario personal - entradas con fecha",
    "temp_rules.py": "Reglas temporales - interceptación inteligente",
    "cache.py": "Sistema de caché - evita reprocesamiento",
    "self_awareness.py": "Auto-conocimiento - este archivo",
    "self_improvement.py": "Auto-mejora - busca mejores prácticas",
    "profile_manager.py": "Perfiles - exportar/importar configuración",
    "reflection.py": "Reflexión - analiza conversaciones pasadas",
    "utils.py": "Utilidades - verificar internet, etc.",
    "files.py": "Gestión de archivos - listar, leer",
    "memory.py": "Búsqueda en memoria - score matching",
    "ocr.py": "OCR - Tesseract wrapper"
}


def leer_archivo_fragmento(ruta, max_lineas=80):
    """
    Lee un archivo y devuelve sus primeras N líneas como fragmento.
    Si el archivo es más largo, indica cuántas líneas se omitieron.
    """
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        total_lineas = len(lineas)
        fragmento = "".join(lineas[:max_lineas])

        if total_lineas > max_lineas:
            fragmento += f"\n... ({total_lineas - max_lineas} líneas más omitidas) ...\n"

        return fragmento, total_lineas
    except Exception as e:
        return f"Error leyendo archivo: {e}", 0


def obtener_funciones_de_archivo(ruta):
    """Extrae los nombres de las funciones definidas en un archivo Python."""
    funciones = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            for linea in f:
                linea_stripped = linea.strip()
                if linea_stripped.startswith("def "):
                    nombre = linea_stripped.split("(")[0].replace("def ", "")
                    funciones.append(nombre)
    except Exception:
        pass
    return funciones


def obtener_imports_de_archivo(ruta):
    """Extrae los imports de un archivo Python."""
    imports = []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            for linea in f:
                linea_stripped = linea.strip()
                if linea_stripped.startswith("import ") or linea_stripped.startswith("from "):
                    imports.append(linea_stripped)
                elif linea_stripped and not linea_stripped.startswith("#") and not linea_stripped.startswith('"""'):
                    if not linea_stripped.startswith("import ") and not linea_stripped.startswith("from "):
                        break
    except Exception:
        pass
    return imports


def contar_lineas_archivo(ruta):
    """Cuenta las líneas de un archivo."""
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return len(f.readlines())
    except Exception:
        return 0


def obtener_arquitectura_detallada():
    """
    Devuelve un diccionario con la arquitectura completa y detallada de Atlas.
    """
    # Importar config para obtener info de modelos
    try:
        from core.config import (
            obtener_config_completa,
            detectar_hardware,
            MODELO_LOCAL,
            MODELO_NUBE_DEFAULT
        )
        config_disponible = True
    except ImportError:
        config_disponible = False

    arquitectura = {
        "metadata": {
            "version": "3.8",
            "timestamp": datetime.now().isoformat(),
            "directorio_actual": os.getcwd(),
        },
        "modelos": {},
        "archivos_core": {},
        "prompts_sistema": {},
        "estructura_memoria": {},
        "capacidades": {},
        "dependencias": {},
        "estado": {},
    }

    # ========================================
    # 0. INFORMACIÓN DE MODELOS (NUEVO)
    # ========================================
    if config_disponible:
        try:
            config = obtener_config_completa()
            hardware = detectar_hardware()

            arquitectura["modelos"] = {
                "modelo_local_actual": MODELO_LOCAL,
                "modelo_nube_default": MODELO_NUBE_DEFAULT,
                "modelos_locales_disponibles": config.get("modelos_locales_catalogo", []),
                "modelos_locales_descargados": config.get("modelos_locales_descargados", []),
                "hardware": hardware
            }
        except Exception as e:
            arquitectura["modelos"] = {"error": str(e)}

    # ========================================
    # 1. ANALIZAR ARCHIVOS CORE
    # ========================================
    core_dir = "core"
    if os.path.exists(core_dir):
        for archivo in os.listdir(core_dir):
            if archivo.endswith(".py") and archivo != "__init__.py":
                ruta = os.path.join(core_dir, archivo)
                lineas = contar_lineas_archivo(ruta)
                funciones = obtener_funciones_de_archivo(ruta)
                imports = obtener_imports_de_archivo(ruta)
                tamano_kb = os.path.getsize(ruta) / 1024
                descripcion = ARCHIVOS_CORE.get(archivo, "Sin descripción")

                arquitectura["archivos_core"][archivo] = {
                    "descripcion": descripcion,
                    "lineas": lineas,
                    "tamano_kb": round(tamano_kb, 2),
                    "funciones": funciones,
                    "imports": imports,
                    "existe": True,
                }

    # Archivos que deberían existir pero no están
    for archivo, descripcion in ARCHIVOS_CORE.items():
        if archivo not in arquitectura["archivos_core"]:
            arquitectura["archivos_core"][archivo] = {
                "descripcion": descripcion,
                "existe": False,
                "lineas": 0,
                "funciones": [],
            }

    # ========================================
    # 2. ANALIZAR PROMPTS DEL SISTEMA
    # ========================================
    prompts_dir = "memory/Atlas_Memory/00_Sistema/Prompts"
    if os.path.exists(prompts_dir):
        for archivo in os.listdir(prompts_dir):
            if archivo.endswith(".md"):
                ruta = os.path.join(prompts_dir, archivo)
                lineas = contar_lineas_archivo(ruta)
                tamano_kb = os.path.getsize(ruta) / 1024

                arquitectura["prompts_sistema"][archivo] = {
                    "lineas": lineas,
                    "tamano_kb": round(tamano_kb, 2),
                }

    # ========================================
    # 3. ANALIZAR ESTRUCTURA DE MEMORIA
    # ========================================
    memoria_dir = "memory/Atlas_Memory"
    if os.path.exists(memoria_dir):
        for root, dirs, files in os.walk(memoria_dir):
            if "__pycache__" in root:
                continue

            ruta_relativa = os.path.relpath(root, memoria_dir)
            if ruta_relativa == ".":
                ruta_relativa = "raiz"

            archivos_md = [f for f in files if f.endswith(".md")]
            archivos_pdf = [f for f in files if f.endswith(".pdf")]
            otros = [f for f in files if not f.endswith((".md", ".pdf", ".pyc"))]

            if archivos_md or archivos_pdf or otros:
                arquitectura["estructura_memoria"][ruta_relativa] = {
                    "archivos_md": archivos_md,
                    "archivos_pdf": archivos_pdf,
                    "otros": otros,
                }

    # ========================================
    # 4. VERIFICAR CAPACIDADES
    # ========================================
    capacidades = {
        "agentes": ["general", "estadistica", "researcher", "mentor", "arquitecto"],
        "sentidos": {
            "ojos": os.path.exists("core/vision.py"),
            "oidos": os.path.exists("core/speech_input.py"),
            "voz": os.path.exists("core/speech_output.py"),
        },
        "memoria_larga": os.path.exists("core/memory_manager.py"),
        "seguridad": os.path.exists("core/security.py"),
        "web_search": os.path.exists("core/web_search.py"),
        "autoconocimiento": os.path.exists("core/self_awareness.py"),
        "perfiles": os.path.exists("core/profile_manager.py"),
        "reflexion": os.path.exists("core/reflection.py"),
        "modelos_locales": config_disponible,
        "rag_semantico": os.path.exists("core/vector_store.py"),
        "modo_examen": os.path.exists("core/exam_mode.py"),
        "diario": os.path.exists("core/diary_manager.py"),
        "reglas_temporales": os.path.exists("core/temp_rules.py"),
    }
    arquitectura["capacidades"] = capacidades

    # ========================================
    # 5. VERIFICAR DEPENDENCIAS
    # ========================================
    paquetes = [
        "requests", "duckduckgo_search", "PIL", "pyautogui", "pytesseract",
        "SpeechRecognition", "vosk", "edge_tts", "pyttsx3",
        "pygame", "pypdf", "streamlit",
        "chromadb", "sentence_transformers",
        "openai", "dotenv", "groq", "pdf2image"
    ]

    for paquete in paquetes:
        try:
            __import__(paquete)
            arquitectura["dependencias"][paquete] = "instalado"
        except ImportError:
            arquitectura["dependencias"][paquete] = "NO instalado"

    # ========================================
    # 6. ESTADO DEL SISTEMA
    # ========================================
    estado = {
        "saludable": True,
        "advertencias": [],
        "metricas": {},
    }

    archivos_criticos = [
        "core/brain.py", "core/router.py", "core/models.py",
        "core/config.py", "atlas_chat.py", "atlas_ui.py"
    ]

    for archivo in archivos_criticos:
        if not os.path.exists(archivo):
            estado["saludable"] = False
            estado["advertencias"].append(f"Falta archivo crítico: {archivo}")

    # Contar archivos de memoria
    total_md = 0
    total_pdf = 0
    for info in arquitectura["estructura_memoria"].values():
        total_md += len(info.get("archivos_md", []))
        total_pdf += len(info.get("archivos_pdf", []))

    estado["metricas"]["archivos_md"] = total_md
    estado["metricas"]["archivos_pdf"] = total_pdf
    estado["metricas"]["archivos_core"] = len([
        a for a in arquitectura["archivos_core"].values() if a.get("existe", False)
    ])

    if config_disponible:
        estado["metricas"]["modelos_locales_descargados"] = len(
            arquitectura["modelos"].get("modelos_locales_descargados", [])
        )

    arquitectura["estado"] = estado

    return arquitectura


def generar_reporte_completo(incluir_codigo=True, max_lineas_codigo=50):
    """
    Genera un informe técnico completo de Atlas.
    Si incluir_codigo es True, incluye fragmentos de los archivos .py principales.
    """
    arq = obtener_arquitectura_detallada()
    lineas = []

    # ========================================
    # ENCABEZADO
    # ========================================
    lineas.append("=" * 70)
    lineas.append("  ATLAS v3.9 - INFORME TÉCNICO DE AUTO-CONOCIMIENTO")
    lineas.append("=" * 70)
    lineas.append(f"  Fecha: {arq['metadata']['timestamp']}")
    lineas.append(f"  Directorio: {arq['metadata']['directorio_actual']}")
    lineas.append("=" * 70)
    lineas.append("")

    # ========================================
    # 1. ESTADO GENERAL
    # ========================================
    lineas.append("1. ESTADO GENERAL")
    lineas.append("-" * 40)
    estado = arq["estado"]
    lineas.append(f"   Saludable: {'SI' if estado['saludable'] else 'NO'}")
    lineas.append(f"   Archivos core: {estado['metricas'].get('archivos_core', 0)}")
    lineas.append(f"   Archivos MD en memoria: {estado['metricas'].get('archivos_md', 0)}")
    lineas.append(f"   Archivos PDF en memoria: {estado['metricas'].get('archivos_pdf', 0)}")

    if "modelos_locales_descargados" in estado['metricas']:
        lineas.append(f"   Modelos locales descargados: {estado['metricas']['modelos_locales_descargados']}")

    if estado["advertencias"]:
        lineas.append("")
        lineas.append("   ADVERTENCIAS:")
        for adv in estado["advertencias"]:
            lineas.append(f"   - {adv}")

    lineas.append("")

    # ========================================
    # 2. MODELOS DE IA (NUEVO)
    # ========================================
    if arq.get("modelos"):
        lineas.append("2. MODELOS DE IA")
        lineas.append("-" * 40)
        modelos = arq["modelos"]

        if "error" not in modelos:
            lineas.append(f"   Modelo local actual: {modelos.get('modelo_local_actual', 'N/A')}")
            lineas.append(f"   Modelo nube default: {modelos.get('modelo_nube_default', 'N/A')}")

            descargados = modelos.get("modelos_locales_descargados", [])
            if descargados:
                lineas.append(f"   Modelos locales descargados:")
                for m in descargados:
                    lineas.append(f"      - {m}")

            hardware = modelos.get("hardware", {})
            if hardware:
                lineas.append(f"   Hardware detectado:")
                lineas.append(f"      RAM: {hardware.get('ram_gb', 'N/A')} GB")
                lineas.append(f"      GPU: {hardware.get('gpu', 'N/A')}")
                lineas.append(f"      VRAM: {hardware.get('vram_gb', 'N/A')} GB")
                lineas.append(f"      Recomendación: {hardware.get('recomendacion', 'N/A')}")
        else:
            lineas.append(f"   Error: {modelos['error']}")

        lineas.append("")

    # ========================================
    # 3. CAPACIDADES
    # ========================================
    lineas.append("3. CAPACIDADES")
    lineas.append("-" * 40)
    caps = arq["capacidades"]
    lineas.append(f"   Agentes: {', '.join(caps['agentes'])}")
    lineas.append(f"   Ojos (visión):     {'SI' if caps['sentidos']['ojos'] else 'NO'}")
    lineas.append(f"   Oídos (voz input): {'SI' if caps['sentidos']['oidos'] else 'NO'}")
    lineas.append(f"   Voz (voz output):  {'SI' if caps['sentidos']['voz'] else 'NO'}")
    lineas.append(f"   Memoria larga:     {'SI' if caps['memoria_larga'] else 'NO'}")
    lineas.append(f"   Seguridad:         {'SI' if caps['seguridad'] else 'NO'}")
    lineas.append(f"   Web search:        {'SI' if caps['web_search'] else 'NO'}")
    lineas.append(f"   Autoconocimiento:  {'SI' if caps['autoconocimiento'] else 'NO'}")
    lineas.append(f"   Perfiles:          {'SI' if caps['perfiles'] else 'NO'}")
    lineas.append(f"   Reflexión:         {'SI' if caps['reflexion'] else 'NO'}")
    lineas.append(f"   Modelos locales:   {'SI' if caps.get('modelos_locales') else 'NO'}")
    lineas.append(f"   RAG semántico:     {'SI' if caps.get('rag_semantico') else 'NO'}")
    lineas.append(f"   Modo examen:       {'SI' if caps.get('modo_examen') else 'NO'}")
    lineas.append(f"   Diario:            {'SI' if caps.get('diario') else 'NO'}")
    lineas.append(f"   Reglas temporales: {'SI' if caps.get('reglas_temporales') else 'NO'}")
    lineas.append("")

    # ========================================
    # 4. ARCHIVOS CORE (DETALLADO)
    # ========================================
    lineas.append("4. ARCHIVOS CORE (DETALLADO)")
    lineas.append("-" * 40)
    for nombre, info in sorted(arq["archivos_core"].items()):
        if info.get("existe", False):
            lineas.append(f"   [OK] {nombre}")
            lineas.append(f"        Descripción: {info['descripcion']}")
            lineas.append(f"        Líneas: {info['lineas']} | Tamaño: {info['tamano_kb']} KB")
            if info.get("funciones"):
                lineas.append(f"        Funciones: {', '.join(info['funciones'][:10])}")
                if len(info.get("funciones", [])) > 10:
                    lineas.append(f"                 ... y {len(info['funciones']) - 10} más")
            if info.get("imports"):
                lineas.append(f"        Imports: {', '.join(info['imports'][:5])}")
                if len(info.get("imports", [])) > 5:
                    lineas.append(f"                 ... y {len(info['imports']) - 5} más")
        else:
            lineas.append(f"   [FALTA] {nombre}")
            lineas.append(f"           Descripción: {info['descripcion']}")
        lineas.append("")

    # ========================================
    # 5. PROMPTS DEL SISTEMA
    # ========================================
    lineas.append("5. PROMPTS DEL SISTEMA")
    lineas.append("-" * 40)
    if arq["prompts_sistema"]:
        for nombre, info in sorted(arq["prompts_sistema"].items()):
            lineas.append(f"   {nombre} ({info['lineas']} líneas, {info['tamano_kb']} KB)")
    else:
        lineas.append("   (no se encontraron prompts)")
    lineas.append("")

    # ========================================
    # 6. ESTRUCTURA DE MEMORIA
    # ========================================
    lineas.append("6. ESTRUCTURA DE MEMORIA")
    lineas.append("-" * 40)
    if arq["estructura_memoria"]:
        for carpeta, info in sorted(arq["estructura_memoria"].items()):
            md = info.get("archivos_md", [])
            pdf = info.get("archivos_pdf", [])
            otros = info.get("otros", [])
            total = len(md) + len(pdf) + len(otros)

            if total > 0:
                lineas.append(f"   {carpeta}/ ({total} archivos)")
                for f in md[:5]:
                    lineas.append(f"      [MD] {f}")
                if len(md) > 5:
                    lineas.append(f"      ... y {len(md) - 5} MD más")
                for f in pdf[:3]:
                    lineas.append(f"      [PDF] {f}")
                if len(pdf) > 3:
                    lineas.append(f"      ... y {len(pdf) - 3} PDF más")
    else:
        lineas.append("   (estructura de memoria vacía)")
    lineas.append("")

    # ========================================
    # 7. DEPENDENCIAS
    # ========================================
    lineas.append("7. DEPENDENCIAS")
    lineas.append("-" * 40)
    for dep, estado_dep in sorted(arq["dependencias"].items()):
        icono = "[OK]" if estado_dep == "instalado" else "[FALTA]"
        lineas.append(f"   {icono} {dep}")
    lineas.append("")

    # ========================================
    # 8. CÓDIGO FUENTE (FRAGMENTOS)
    # ========================================
    if incluir_codigo:
        lineas.append("8. CÓDIGO FUENTE (FRAGMENTOS DE ARCHIVOS PRINCIPALES)")
        lineas.append("-" * 40)
        lineas.append("   Estos son los primeros fragmentos de los archivos principales.")
        lineas.append("   Útiles para dar contexto a otro modelo o desarrollador.")
        lineas.append("")

        archivos_a_mostrar = [
            "brain.py", "router.py", "models.py",
            "config.py", "self_awareness.py"
        ]

        for nombre in archivos_a_mostrar:
            ruta = os.path.join("core", nombre)
            if os.path.exists(ruta):
                fragmento, total_lineas = leer_archivo_fragmento(ruta, max_lineas=max_lineas_codigo)
                lineas.append(f"   --- core/{nombre} ({total_lineas} líneas total) ---")
                lineas.append("")

                # Indentar cada línea del fragmento
                for linea_fragmento in fragmento.split("\n"):
                    lineas.append(f"   {linea_fragmento}")

                lineas.append("")
                lineas.append(f"   --- fin de fragmento de {nombre} ---")
                lineas.append("")

    # ========================================
    # PIE
    # ========================================
    lineas.append("=" * 70)
    lineas.append("  FIN DEL INFORME")
    lineas.append("=" * 70)
    lineas.append("")
    lineas.append("  Este informe fue generado automáticamente por Atlas v3.9.")
    lineas.append("  Puede ser compartido con otro modelo de IA para obtener")
    lineas.append("  asistencia técnica, revisión de código o sugerencias.")
    lineas.append("")

    return "\n".join(lineas)


def generar_reporte_self_awareness():
    """
    Función de compatibilidad con el comando !autoconocer.
    Llama a generar_reporte_completo con código incluido.
    """
    return generar_reporte_completo(incluir_codigo=True, max_lineas_codigo=50)


def generar_reporte_sin_codigo():
    """Genera reporte sin fragmentos de código (más corto)."""
    return generar_reporte_completo(incluir_codigo=False)


def exportar_reporte_a_archivo(nombre_archivo=None):
    """
    Exporta el informe completo a un archivo .txt en la carpeta de backups.
    """
    if nombre_archivo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"informe_atlas_{timestamp}.txt"

    backup_dir = "memory/Atlas_Memory/backups"
    os.makedirs(backup_dir, exist_ok=True)
    ruta = os.path.join(backup_dir, nombre_archivo)

    reporte = generar_reporte_completo(incluir_codigo=True, max_lineas_codigo=80)

    with open(ruta, "w", encoding="utf-8") as f:
        f.write(reporte)

    return ruta


if __name__ == "__main__":
    print(generar_reporte_completo())