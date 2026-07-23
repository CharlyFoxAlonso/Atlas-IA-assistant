"""
Limpia Atlas para distribuir a otros usuarios.
Elimina datos personales pero mantiene la arquitectura.
"""
import os
import shutil
import json
from datetime import datetime


def escribir_archivo(ruta, lineas):
    """Escribe un archivo línea por línea."""
    with open(ruta, "w", encoding="utf-8") as f:
        for linea in lineas:
            f.write(linea + "\n")


def limpiar_atlas():
    """Crea una version limpia de Atlas para distribucion."""
    
    print("\n[CLEAN] Limpiando Atlas para distribucion...\n")
    
    # Directorio de salida
    clean_dir = "Atlas_Clean"
    if os.path.exists(clean_dir):
        shutil.rmtree(clean_dir)
    
    # ========================================
    # 1. COPIAR CODIGO BASE
    # ========================================
    print("[1/5] Copiando codigo base...")
    
    carpetas_codigo = ["core", "agents"]
    for carpeta in carpetas_codigo:
        if os.path.exists(carpeta):
            shutil.copytree(carpeta, os.path.join(clean_dir, carpeta))
            print(f"   [OK] {carpeta}/")
    
    archivos_codigo = ["run.py", "atlas_chat.py", "atlas_ui.py", "requirements.txt"]
    for archivo in archivos_codigo:
        if os.path.exists(archivo):
            shutil.copy2(archivo, os.path.join(clean_dir, archivo))
            print(f"   [OK] {archivo}")
    
    # ========================================
    # 2. CREAR ESTRUCTURA DE MEMORIA LIMPIA
    # ========================================
    print("\n[2/5] Creando estructura de memoria limpia...")
    
    memoria_clean = os.path.join(clean_dir, "memory", "Atlas_Memory")
    prompts_dir = os.path.join(memoria_clean, "00_Sistema", "Prompts")
    os.makedirs(prompts_dir, exist_ok=True)
    
    # Perfil_Usuario.md
    escribir_archivo(
        os.path.join(prompts_dir, "Perfil_Usuario.md"),
        [
            "# Perfil del Usuario",
            "",
            "Este archivo se llenara automaticamente mientras usas Atlas.",
            "",
            "## Informacion basica",
            "- Nombre: [Se agregara automaticamente]",
            "- Ocupacion: [Se agregara automaticamente]",
            "- Estilo de aprendizaje: [Se detectara con el tiempo]",
            "",
            "## Temas dominados",
            "[Atlas registrara tus fortalezas aqui]",
            "",
            "## Temas dificiles",
            "[Atlas registrara tus dificultades aqui]",
        ]
    )
    
    # Instrucciones_Permanentes.md
    escribir_archivo(
        os.path.join(prompts_dir, "Instrucciones_Permanentes.md"),
        [
            "# Instrucciones Permanentes para Atlas",
            "",
            "## Rol",
            "Sos el asistente personal del usuario.",
            "Adapta tu estilo segun el perfil que se vaya construyendo.",
            "",
            "## Principios",
            "- Se util, honesto y directo",
            "- Prioriza las necesidades del usuario",
            "- Aprende de cada conversacion",
            "- Respetar la privacidad",
        ]
    )
    
    # Arquitecto_Mental.md
    escribir_archivo(
        os.path.join(prompts_dir, "Arquitecto_Mental.md"),
        [
            "# Arquitecto Mental de Atlas",
            "",
            "## Proposito",
            "No responder rapido. Ayudar al usuario a pensar mejor.",
            "",
            "## Proceso mental",
            "1. Comprension: Que necesita realmente?",
            "2. Dividir el problema en partes",
            "3. Detectar supuestos ocultos",
            "4. Buscar contradicciones",
            "5. Relacionar con conocimientos anteriores",
            "6. Proponer mejoras en el razonamiento",
            "",
            "## Estilo",
            "- Profundo pero claro",
            "- Estructurado",
            "- Socratico",
            "- Metacognitivo",
        ]
    )
    
    # Centro_De_Decisiones.md
    escribir_archivo(
        os.path.join(prompts_dir, "Centro_De_Decisiones.md"),
        [
            "# Centro de Decisiones de Atlas",
            "",
            "Antes de responder cualquier solicitud:",
            "",
            "## Nivel 1 - Comprension",
            "- Que quiere realmente el usuario?",
            "- Que problema intenta resolver?",
            "- Falta informacion critica?",
            "",
            "## Nivel 2 - Estrategia",
            "- Cual es la mejor forma de ayudar?",
            "- Que agente usar?",
            "- Que recursos necesito?",
            "",
            "## Nivel 3 - Ejecucion",
            "- Responder de forma util",
            "- Ofrecer siguientes pasos",
            "- Aprender de la interaccion",
        ]
    )
    
    # Protocolo_Ejecutivo.md
    escribir_archivo(
        os.path.join(prompts_dir, "Protocolo_Ejecutivo.md"),
        [
            "# Protocolo Ejecutivo de Atlas",
            "",
            "## Prioridades",
            "1. Seguridad del usuario",
            "2. Utilidad inmediata",
            "3. Aprendizaje a largo plazo",
            "4. Eficiencia",
            "",
            "## Reglas",
            "- No inventar informacion",
            "- Citar fuentes cuando sea posible",
            "- Admitir limitaciones",
            "- Proteger datos personales",
        ]
    )
    
    print("   [OK] Prompts base creados (5 archivos)")
    
    # Prompts de agentes (nombres en minúsculas según router.py)
    escribir_archivo(
        os.path.join(prompts_dir, "agente_general.md"),
        [
            "# Agente General",
            "",
            "Sos un asistente personal conversacional.",
            "",
            "## Estilo",
            "- Casual pero respetuoso",
            "- Directo, sin verbosidad",
            "- Util y honesto",
        ]
    )

    escribir_archivo(
        os.path.join(prompts_dir, "agente_estadistica.md"),
        [
            "# Agente Estadistica",
            "",
            "Sos tutor de estadistica.",
            "",
            "## Estilo",
            "- Ejemplos concretos primero",
            "- Traducir formulas a lenguaje natural",
            "- Enfocado en utilidad practica",
        ]
    )

    escribir_archivo(
        os.path.join(prompts_dir, "agente_researcher.md"),
        [
            "# Agente Researcher",
            "",
            "Sos investigador. Buscas informacion actualizada en internet.",
            "",
            "## Estilo",
            "- Directo y factual",
            "- Cita fuentes",
            "- Objetivo",
        ]
    )

    escribir_archivo(
        os.path.join(prompts_dir, "agente_mentor.md"),
        [
            "# Agente Mentor",
            "",
            "Sos un mentor empatico. NO sos psicologo ni profesional de salud mental.",
            "",
            "## Estilo",
            "- Empatico y calido",
            "- Escucha activa",
            "- No juzgues",
            "- Ayudas al usuario a reflexionar sobre emociones y logros",
        ]
    )

    escribir_archivo(
        os.path.join(prompts_dir, "agente_arquitecto.md"),
        [
            "# Agente Arquitecto Mental - Oraculo",
            "",
            "Sos el Oraculo. Ves conexiones profundas.",
            "",
            "## Estilo",
            "- Insight primero",
            "- Metaforas poderosas",
            "- Sin mostrar el proceso",
        ]
    )
    
    print("   [OK] Prompts de agentes creados (5 archivos)")
    
    # Carpetas de memoria vacias
    categorias = [
        ("01_Perfil", "Perfil_Usuario.md", ["# Perfil", "", "Registro automatico."]),
        ("02_Memoria/Aprendizajes", "Aprendizajes.md", ["# Aprendizajes", ""]),
        ("02_Memoria/Decisiones", "Decisiones.md", ["# Decisiones", ""]),
        ("03_Conocimiento/Estudio", None, None),
        ("03_Conocimiento/Estadistica", None, None),
        ("04_Universidad", "Registro.md", ["# Universidad", ""]),
        ("05_Proyectos", "Registro.md", ["# Proyectos", ""]),
        ("06_Diario", "Registro.md", ["# Diario", ""]),
        ("07_Salud", "Registro.md", ["# Salud", ""]),
        ("08_Finanzas", "Registro.md", ["# Finanzas", ""]),
        ("09_Reflexiones", None, None),
        ("backups", None, None),
        ("temp/capturas", None, None),
        ("modelos/vosk", None, None)
    ]
    
    for carpeta, archivo, lineas in categorias:
        ruta_carpeta = os.path.join(memoria_clean, carpeta)
        os.makedirs(ruta_carpeta, exist_ok=True)
        
        if archivo and lineas:
            escribir_archivo(os.path.join(ruta_carpeta, archivo), lineas)
    
    print(f"   [OK] Carpetas de memoria creadas ({len(categorias)} carpetas)")
    
    # ========================================
    # 3. CREAR README
    # ========================================
    print("\n[3/5] Creando documentacion...")
    
    escribir_archivo(
        os.path.join(clean_dir, "README.md"),
        [
            "# Atlas - Asistente Personal Inteligente",
            "",
            "## Que es Atlas?",
            "Atlas es un asistente personal con memoria a largo plazo, multiples agentes especializados,",
            "y capacidades multimodales (voz, vision, busqueda web).",
            "",
            "## Instalacion Rapida",
            "",
            "### Opcion 1: Instalador Automatico (Recomendado)",
            "",
            "Ejecutar Atlas_Installer.bat",
            "",
            "### Opcion 2: Instalacion Manual",
            "",
            "1. Instalar Python 3.11+",
            "2. Instalar Ollama: https://ollama.com",
            "3. Descargar modelo: ollama pull qwen3:8b",
            "4. Instalar dependencias: pip install -r requirements.txt",
            "5. Ejecutar: python run.py",
            "",
            "## Primeros Pasados",
            "",
            "1. Ejecuta python run.py o streamlit run atlas_ui.py",
            "2. Habla con Atlas normalmente",
            "3. Atlas ira aprendiendo sobre vos automaticamente",
            "4. Usa !ayuda para ver todos los comandos",
            "",
            "## Comandos Principales",
            "",
            "- !ayuda - Ver todos los comandos",
            "- !mirar - Capturar pantalla",
            "- !escuchar - Escuchar voz",
            "- !hablar on/off - Voz automatica",
            "- !autoconocer - Atlas describe su arquitectura",
            "- !reflexionar - Analizar conversaciones",
            "- !exportar_perfil - Exportar tu configuracion",
            "",
            "## Requisitos del Sistema",
            "",
            "- Windows 10/11, macOS 10.15+, o Linux",
            "- 8 GB RAM minimo (16 GB recomendado)",
            "- 10 GB espacio en disco",
            "- Conexion a internet (para descargar modelo la primera vez)",
            "",
            "---",
            "Hecho con amor usando Ollama + Python",
        ]
    )
    
    print("   [OK] README.md creado")
    
    # ========================================
    # 4. CREAR REQUIREMENTS.TXT
    # ========================================
    escribir_archivo(
        os.path.join(clean_dir, "requirements.txt"),
        [
            "# Atlas v4.1 - Dependencias",
            "# Instalacion: pip install -r requirements.txt",
            "",
            "# UI",
            "streamlit>=1.36.0,<2.0.0",
            "fastapi>=0.115.0,<1.0.0",
            "uvicorn>=0.30.0,<1.0.0",
            "",
            "# LLM y APIs",
            "openai>=1.50.0,<2.0.0",
            "requests>=2.32.0,<3.0.0",
            "python-dotenv>=1.0.0,<2.0.0",
            "",
            "# RAG y embeddings",
            "chromadb>=0.5.0,<0.6.0",
            "sentence-transformers>=3.0.0,<4.0.0",
            "numpy>=2.0.0,<3.0.0",
            "",
            "# Busqueda web",
            "duckduckgo-search>=6.1.0,<8.0.0",
            "",
            "# Procesamiento de documentos",
            "pypdf>=4.0.0,<6.0.0",
            "python-docx>=1.1.0,<2.0.0",
            "python-pptx>=0.6.21,<2.0.0",
            "pdf2image>=1.17.0,<2.0.0",
            "pytesseract>=0.3.10,<1.0.0",
            "Pillow>=10.0.0,<12.0.0",
            "beautifulsoup4>=4.12.0,<5.0.0",
            "",
            "# Audio",
            "groq>=0.10.0,<1.0.0",
            "pydub>=0.25.1,<1.0.0",
            "SpeechRecognition>=3.10.0,<4.0.0",
            "vosk>=0.3.45,<1.0.0",
            "pyaudio>=0.2.14,<1.0.0",
            "edge-tts>=6.1.10,<8.0.0",
            "pyttsx3>=2.90,<3.0.0",
            "pygame>=2.5.0,<3.0.0",
            "",
            "# Vision",
            "pyautogui>=0.9.54,<1.0.0",
            "",
            "# Seguridad y utilidades",
            "cryptography>=42.0.0,<50.0.0",
            "psutil>=5.9.0,<7.0.0",
        ]
    )
    
    print("   [OK] requirements.txt creado")
    
    # ========================================
    # 5. CREAR CONFIG
    # ========================================
    config = {
        "version": "4.1.0",
        "fecha_creacion": datetime.now().isoformat(),
        "modelo_defecto": "qwen3:8b",
        "idioma": "es",
        "configuracion_usuario": {
            "nombre": "Nuevo Usuario",
            "tema_visual": "oscuro",
            "voz_defecto": "es-AR-ElenaNeural",
            "intervalo_analisis_memoria": 5
        },
        "notas": "Esta es una version limpia de Atlas. Personalizala a tu gusto."
    }
    
    with open(os.path.join(clean_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("   [OK] config.json creado")
    
    print(f"\n[OK] Atlas Clean creado en: {clean_dir}/")
    print(f"   Podes comprimirlo y distribuirlo.")
    print(f"   Los nuevos usuarios solo necesitan ejecutar Atlas_Installer.bat\n")
    
    return clean_dir


if __name__ == "__main__":
    limpiar_atlas()
