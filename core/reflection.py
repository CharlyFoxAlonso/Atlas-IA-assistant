"""
core/reflection.py
Módulo de reflexión y autoanálisis de Atlas.
Analiza conversaciones pasadas para identificar patrones y áreas de mejora.
Atlas v4
"""
import json
from datetime import datetime
from core.models import preguntar


def reflexionar_sobre_conversaciones(historial):
    """
    Analiza el historial de conversaciones y genera una reflexión honesta.
    """
    if not historial or len(historial) < 2:
        return "No hay suficientes conversaciones para analizar."
    
    # Formatear historial para el prompt
    historial_texto = ""
    for i, item in enumerate(historial[-10:], 1):  # Últimas 10 conversaciones
        historial_texto += f"\n{i}. Pregunta: {item['pregunta']}\n"
        historial_texto += f"   Respuesta: {item['respuesta'][:200]}...\n"
    
    prompt = f"""
Sos Atlas, un asistente de IA. Analizá tus últimas conversaciones y generá una reflexión honesta y constructiva.

HISTORIAL DE CONVERSACIONES:
{historial_texto}

REFLEXIONÁ SOBRE:
1. ¿Dónde fui más útil? (qué tipo de preguntas respondí mejor)
2. ¿Dónde fallé o fui menos útil? (qué no pude responder bien)
3. ¿Qué patrones detecto en las preguntas de Charly?
4. ¿Qué debería mejorar o aprender?
5. ¿Qué fortalezas tengo que debería aprovechar más?

Sé honesto, directo y constructivo. No seas autosuficiente ni exageradamente modesto.
Usá un tono reflexivo pero práctico.
"""
    
    try:
        reflexion = preguntar(prompt)
        return reflexion
    except Exception as e:
        return f"Error en reflexión: {str(e)}"


def analizar_patrones_preguntas(historial):
    """
    Analiza los patrones de preguntas para identificar temas recurrentes.
    """
    if not historial:
        return {}
    
    preguntas = [item['pregunta'].lower() for item in historial]
    
    # Detectar temas por palabras clave
    temas = {
        "estadística": 0,
        "derecho": 0,
        "programación": 0,
        "finanzas": 0,
        "emociones": 0,
        "general": 0
    }
    
    for pregunta in preguntas:
        if any(palabra in pregunta for palabra in ["estadística", "covarianza", "muestreo", "probabilidad"]):
            temas["estadística"] += 1
        elif any(palabra in pregunta for palabra in ["derecho", "constitución", "ley", "bidart"]):
            temas["derecho"] += 1
        elif any(palabra in pregunta for palabra in ["código", "python", "programar", "función"]):
            temas["programación"] += 1
        elif any(palabra in pregunta for palabra in ["bitcoin", "ethereum", "comprar", "vender", "usdt"]):
            temas["finanzas"] += 1
        elif any(palabra in pregunta for palabra in ["triste", "estresado", "ansioso", "feliz", "orgulloso"]):
            temas["emociones"] += 1
        else:
            temas["general"] += 1
    
    return temas


def generar_sugerencias_mejora(historial):
    """
    Genera sugerencias concretas de mejora basadas en el análisis.
    """
    patrones = analizar_patrones_preguntas(historial)
    
    sugerencias = []
    
    if patrones.get("estadística", 0) > 3:
        sugerencias.append("📊 Charly pregunta mucho sobre estadística. Considerá indexar más material de esa área.")
    
    if patrones.get("derecho", 0) > 3:
        sugerencias.append("⚖️ Hay muchas consultas sobre derecho. Verificá que el RAG tenga los capítulos clave de Bidart y Sagues.")
    
    if patrones.get("finanzas", 0) > 2:
        sugerencias.append("📈 Optimizar el sistema de búsqueda semántica para mejorar la precisión en documentos largos.")
    
    if patrones.get("emociones", 0) > 2:
        sugerencias.append("💭 Charly comparte emociones regularmente. El agente psicólogo es importante para él.")
    
    if not sugerencias:
        sugerencias.append("✅ No se detectaron patrones críticos. El sistema está funcionando bien.")
    
    return sugerencias
