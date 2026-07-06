"""
Router inteligente: el MODELO decide qué agente usar.
Atlas v3.2 - Detección mejorada de emociones, logros y derecho.
"""
import os
import re as _re
from core.models import preguntar

AGENTES = ["general", "estadistica", "researcher", "mentor", "arquitecto"]

_AGENTES_PATTERN = _re.compile(
    r"\b(" + "|".join(_re.escape(a) for a in AGENTES) + r")\b",
    flags=_re.IGNORECASE,
)


def _clasificar_agente_desde_texto(respuesta: str) -> str:
    """
    Clasificación estricta por palabra completa.
    Reglas:
      1. Si la respuesta coincide EXACTAMENTE con un agente (después de strip),
         se devuelve ese.
      2. Si no, se busca la PRIMERA coincidencia como palabra completa
         (evita falsos positivos tipo "comenta" → "menta").
      3. Si no se encuentra nada, se devuelve 'general'.
    """
    if not respuesta:
        return "general"

    texto = respuesta.strip().lower()
    if texto in AGENTES:
        return texto

    match = _AGENTES_PATTERN.search(texto)
    if match:
        return match.group(1).lower()

    return "general"


def detectar_agente_con_modelo(pregunta):
    """
    Usa el modelo local para decidir qué agente usar.
    Detecta emociones, logros, derecho y consultas académicas.
    """
    prompt = f"""
Sos un clasificador de intenciones ULTRA PRECISO. Analizá esta pregunta y decidí qué AGENTE debe responder.

PREGUNTA:
{pregunta}

AGENTES DISPONIBLES:
general: Conversación casual, conocimiento general del mundo, filosofía, historia antigua, cultura general.
estadistica: Preguntas ESPECÍFICAS sobre estadística, probabilidad, muestreo, fórmulas, ejercicios numéricos, covarianza, varianza, media, desviación.
researcher: Información ESPECÍFICA y ACTUALIZADA, resúmenes de temas académicos, leyes, constituciones, conceptos jurídicos, exámenes sobre libros específicos.
"Haceme un resumen de...", "Explicame...", "Qué es..." sobre temas académicos.
"Generame un examen sobre [libro/autor]", "Capítulos X al Y de [libro]"
Consultas sobre derecho constitucional, Bidart Campos, Sagues, leyes, constituciones.
mentor: Emociones, logros personales, estados de ánimo, consejos prácticos de vida, motivación, hábitos, relaciones, decisiones personales, bienestar general.
arquitecto: Razonamiento profundo, análisis metacognitivo, filosofía profunda.

REGLAS CRÍTICAS DE CLASIFICACIÓN:
Si pregunta sobre una PERSONA/EVENTO específico o noticias recientes → researcher
Si es sobre estadística, exámenes o matemáticas → estadistica
Si expresa EMOCIONES, LOGROS ("aprobé", "me fue bien", "orgulloso"), o pide consejo personal, motivación, hábitos, bienestar → mentor
Si pide "resumen", "explicación", "examen" sobre temas académicos (derecho, leyes, constituciones, Bidart, Sagues) → researcher
Solo si es conocimiento general abstracto o atemporal → general

EJEMPLOS:
"¿Qué es la covarianza?" → estadistica
"Explicame el muestreo estratificado" → estadistica
"¿Quién es el presidente de Francia hoy?" → researcher
"¿Qué es el estoicismo?" → general
"Haceme un resumen de los primeros 10 artículos de la Constitución Argentina" → researcher
"Explicame el artículo 14 de la Constitución" → researcher
"¿Qué dice la ley sobre...?" → researcher
"Generame un examen sobre los capítulos 7 al 9 del Compendio de Bidart Campos" → researcher
"estoy muy orgulloso, aprobé todo el cuatrimestre" → mentor
"me fue bien en estadística" → mentor
"me siento estresado por los exámenes" → mentor
"¿cómo puedo ser más productivo?" → mentor
"no sé qué hacer con mi vida" → mentor

Respondé SOLO con el nombre del agente (una sola palabra en minúsculas):
"""
    try:
        respuesta = preguntar(prompt).strip().lower()
        return _clasificar_agente_desde_texto(respuesta)
    except Exception:
        return "general"


def cargar_prompt_agente(agente):
    """Carga el archivo prompt de identidad correspondiente al agente."""
    archivos = {
        "general": "agente_general.md",
        "estadistica": "agente_estadistica.md",
        "researcher": "agente_researcher.md",
        "mentor": "agente_mentor.md",
        "arquitecto": "agente_arquitecto.md"
    }
    nombre_archivo = archivos.get(agente, "agente_general.md")
    ruta = os.path.join("memory/Atlas_Memory/00_Sistema/Prompts", nombre_archivo)
    if os.path.exists(ruta):
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    return "Sos un asistente útil y directo."


def listar_agentes():
    """Devuelve un diccionario con los agentes y sus descripciones."""
    return {
        "general": "Conversación casual, conocimiento general",
        "estadistica": "Estadística, probabilidad, exámenes, fórmulas",
        "researcher": "Información actualizada, resúmenes académicos, derecho, leyes, constituciones",
        "mentor": "Consejos prácticos de vida, emociones, logros, hábitos, bienestar, motivación",
        "arquitecto": "Razonamiento profundo, metacognición"
    }