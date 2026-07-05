"""
Módulo de auto-mejora de Atlas.
Busca mejores prácticas y PROPONE mejoras (no las aplica automáticamente).
Atlas v2.9
"""
import os
import json
from datetime import datetime
from core.web_search import buscar_web
from core.models import preguntar


def analizar_debilidades(historial_conversaciones):
    """
    Analiza el historial para detectar patrones de error o mejora.
    """
    if not historial_conversaciones:
        return []
    
    prompt = f"""
Sos un analista de sistemas de IA. Analizá estas conversaciones de Atlas
y detectá patrones de error o áreas de mejora.

HISTORIAL (últimas conversaciones):
{json.dumps(historial_conversaciones[-10:], indent=2, ensure_ascii=False)}

IDENTIFICÁ:
- Errores repetidos (ej: clasificar mal el agente)
- Respuestas muy largas o verbosas
- Información incorrecta o inventada
- Casos donde no pudo ayudar
- Patrones de preguntas que podrían optimizarse

Devuelve un JSON con:
{{
  "debilidades": [
    {{"tipo": "...", "ejemplo": "...", "sugerencia": "..."}}
  ],
  "fortalezas": ["..."]
}}
"""
    try:
        resultado = preguntar(prompt)
        return json.loads(resultado)
    except:
        return {"debilidades": [], "fortalezas": []}


def buscar_mejores_practicas(tema):
    """
    Busca en la web mejores prácticas para mejorar Atlas.
    """
    queries = [
        f"mejores prácticas RAG 2026 {tema}",
        f"prompt engineering techniques {tema}",
        f"local LLM optimization {tema}"
    ]
    
    resultados_completos = []
    for query in queries:
        resultados = buscar_web(query, max_resultados=3)
        resultados_completos.extend(resultados)
    
    return resultados_completos


def generar_propuesta_mejora(area, contexto_actual):
    """
    Genera una propuesta concreta de mejora para un área específica.
    """
    prompt = f"""
Sos un arquitecto de sistemas de IA. Generá una propuesta concreta de mejora
para el área: {area}

CONTEXTO ACTUAL DE ATLAS:
{contexto_actual}

REQUISITOS:
- La propuesta debe ser ESPECÍFICA y APLICABLE
- Incluir código Python de ejemplo
- Explicar beneficios y riesgos
- Estimar esfuerzo de implementación (bajo/medio/alto)

Formato de respuesta:
{{
  "area": "{area}",
  "propuesta": "Descripción clara",
  "codigo_ejemplo": "Código Python",
  "beneficios": ["..."],
  "riesgos": ["..."],
  "esfuerzo": "bajo/medio/alto",
  "prioridad": "alta/media/baja"
}}
"""
    try:
        resultado = preguntar(prompt)
        return json.loads(resultado)
    except:
        return None


def aplicar_mejora_con_backup(ruta_archivo, nuevo_contenido, razon):
    """
    Aplica una mejora haciendo backup primero.
    SIEMPRE hace backup antes de modificar.
    """
    backup_dir = "memory/Atlas_Memory/backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Crear backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_backup = f"{os.path.basename(ruta_archivo)}_{timestamp}.bak"
    ruta_backup = os.path.join(backup_dir, nombre_backup)
    
    try:
        # Backup
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                contenido_original = f.read()
            with open(ruta_backup, "w", encoding="utf-8") as f:
                f.write(contenido_original)
        
        # Aplicar mejora
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write(nuevo_contenido)
        
        # Registrar en log
        log_path = os.path.join(backup_dir, "mejoras_log.json")
        log_entry = {
            "timestamp": timestamp,
            "archivo": ruta_archivo,
            "backup": ruta_backup,
            "razon": razon
        }
        
        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        
        logs.append(log_entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
        
        return True, ruta_backup
    except Exception as e:
        return False, str(e)


def rollback_mejora(ruta_backup):
    """Restaura un backup si algo salió mal."""
    try:
        # Extraer ruta original del nombre del backup
        # Formato: nombre_archivo_TIMESTAMP.bak
        nombre = os.path.basename(ruta_backup)
        partes = nombre.rsplit("_", 1)
        
        if len(partes) != 2:
            return False, "Nombre de backup inválido"
        
        nombre_original = partes[0]
        
        # Buscar el archivo original
        for root, _, files in os.walk("."):
            if nombre_original in files:
                ruta_original = os.path.join(root, nombre_original)
                with open(ruta_backup, "r", encoding="utf-8") as f:
                    contenido_backup = f.read()
                with open(ruta_original, "w", encoding="utf-8") as f:
                    f.write(contenido_backup)
                return True, ruta_original
        
        return False, "No se encontró el archivo original"
    except Exception as e:
        return False, str(e)