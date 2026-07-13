"""
core/exam_mode.py - Atlas v4 (búsqueda híbrida + parsing robusto)
Modo Examen Interactivo Completo con RAG Semántico + fallback por nombre de archivo.
Soporta motor local (Ollama) y Prometeo (NVIDIA API).
"""
import os
import re
from openai import OpenAI
from dotenv import load_dotenv
from core.brain import buscar_en_rag_semantico
from core.models import preguntar
load_dotenv()

# ============================================
# NVIDIA API (con max_tokens ajustable)
# ============================================

def _preguntar_nvidia(prompt: str, modelo_nube: str = "meta/llama-3.1-70b-instruct", max_tokens=2048) -> str:  # ✅ CORREGIDO: sin espacio
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")  # ✅ CORREGIDO: sin espacios
    if not api_key:
        raise Exception("No se encontró API Key de NVIDIA en .env")
    
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)  # ✅ CORREGIDO: sin espacio
    response = client.chat.completions.create(
        model=modelo_nube,
        messages=[{"role": "user", "content": prompt}],  # ✅ CORREGIDO: sin espacios
        temperature=0.3,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content


def _preguntar_adaptable(prompt: str, motor: str = "atlas", modelo_nube: str = "meta/llama-3.1-70b-instruct", max_tokens=2048) -> str:  # ✅ CORREGIDO: sin espacio
    if motor == "prometeo":
        return _preguntar_nvidia(prompt, modelo_nube, max_tokens=max_tokens)
    else:
        return preguntar(prompt)


# ============================================
# LIMPIEZA DE LA CONSULTA
# ============================================

def _limpiar_material(query: str) -> str:
    """
    Elimina SOLO especificaciones numéricas de examen, NO palabras del material.
    Ej: "clase de muestreo, 10 preguntas" -> "clase de muestreo"
        "muestreo aleatorio simple" -> "muestreo aleatorio simple" (se conserva)
    """
    query = re.sub(r',?\s*\d+\s*preguntas?\s*(?:aleatori[ao]s?)?\s*', '', query, flags=re.IGNORECASE)
    query = re.sub(r',?\s*\d+\s*(?:conceptuales|desarrollo|verdadero\s*y?\s*falso|v/?f)\s*.*', '', query, flags=re.IGNORECASE)
    query = query.strip().strip(',').strip()
    return query


# ============================================
# DETECCIÓN MEJORADA
# ============================================

def detectar_material_y_capitulos(pregunta: str) -> dict:
    texto = pregunta.lower()
    resultado = {"material": None, "capitulos": [], "especificaciones": {}}

    match_rango = re.search(r'cap[íi]tulos?\s+(\d+)\s+(?:al|a|y|hasta)\s+(\d+)', texto, re.IGNORECASE)
    if match_rango:
        inicio, fin = int(match_rango.group(1)), int(match_rango.group(2))
        resultado["capitulos"] = [f"capitulo_{i}" for i in range(inicio, fin + 1)]
    else:
        match_single = re.search(r'cap[íi]tulo\s+(\d+)', texto, re.IGNORECASE)
        if match_single:
            resultado["capitulos"] = [f"capitulo_{match_single.group(1)}"]

    # Extraer specs numéricas primero
    especs = {"conceptuales": None, "desarrollo": None, "vf": None, "total": 10}
    m = re.search(r'(\d+)\s*(?:preguntas?\s*(?:de\s*)?)?conceptuales?', texto)
    if m: especs["conceptuales"] = int(m.group(1))
    m = re.search(r'(\d+)\s*(?:preguntas?\s*(?:de\s*)?)?desarrollo', texto)
    if m: especs["desarrollo"] = int(m.group(1))
    m = re.search(r'(\d+)\s*(?:preguntas?\s*(?:de\s*)?)?(?:verdadero\s*(?:y|o)\s*falso|v\s*(?:y|o)?\s*f)', texto)
    if m: especs["vf"] = int(m.group(1))
    m = re.search(r'(\d+)\s*preguntas?', texto)
    total_detectado = int(m.group(1)) if m else None

    if especs["conceptuales"] or especs["desarrollo"] or especs["vf"]:
        especs["total"] = (especs["conceptuales"] or 0) + (especs["desarrollo"] or 0) + (especs["vf"] or 0)
    elif total_detectado:
        especs["total"] = total_detectado

    resultado["especificaciones"] = especs

    # Extraer material: remover patrones de especificación, NO cortar con aleatorio
    material_raw = texto.strip()
    material_raw = re.sub(r'^(hazme|dame|quiero|necesito|genera|crea|hacé|da)\s*\d*\s*preguntas?\s*(de|sobre|del)?\s*', '', material_raw, flags=re.IGNORECASE)
    material_raw = re.sub(r',?\s*\d+\s*preguntas?\s*(?:aleatori[ao]s?)?\s*,?\s*', '', material_raw, flags=re.IGNORECASE)
    material_raw = re.sub(r',?\s*\d+\s*(?:conceptuales|desarrollo|verdadero\s*y?\s*falso|v/?f).*', '', material_raw, flags=re.IGNORECASE)
    material_raw = re.sub(r'\b(cap[íi]tulo\s*\d+(\s*(al|a|y|hasta)\s*\d+)?)\b', '', material_raw, flags=re.IGNORECASE)
    material_raw = re.sub(r'\s*,\s*$', '', material_raw)

    posible_material = _limpiar_material(material_raw)
    if posible_material:
        resultado["material"] = posible_material

    return resultado


# ============================================
# EXTRACCIÓN DE PALABRAS CLAVE PARA BÚSQUEDA HÍBRIDA
# ============================================

STOP_WORDS = {'de', 'la', 'el', 'en', 'un', 'una', 'del', 'los', 'las', 'con', 'por', 'para', 'y', 'e', 'o', 'a', 'al', 'que', 'es', 'se', 'su', 'lo', 'como', 'más', 'entre', 'según', 'todo', 'este', 'esta', 'esto', 'clase', 'tema', 'capítulo', 'material'}


def _extraer_keywords(texto: str) -> list:
    """Extrae palabras clave significativas del nombre del material para búsqueda por metadata."""
    palabras = re.findall(r'\b[a-záéíóúñ]{3,}\b', texto.lower())
    return list(set(p for p in palabras if p not in STOP_WORDS))


# ============================================
# EXTRACCIÓN RAG (con búsqueda híbrida)
# ============================================

def extraer_material_rag(material: str, capitulos: list) -> tuple:
    if not material:
        return "", []

    texto_total = ""
    archivos_usados = []
    keywords = _extraer_keywords(material)

    if capitulos:
        for cap in capitulos[:5]:
            chunks_texto, archivos_chunk = buscar_en_rag_semantico(
                f"{material} {cap}", n_results=4, filtro_capitulo=cap)
            texto_total += chunks_texto
            archivos_usados.extend(archivos_chunk)
        archivos_usados = list(set(archivos_usados))
    else:
        texto_total, archivos_usados = buscar_en_rag_semantico(
            material,
            n_results=15,
            palabras_clave=keywords,
            modo_hibrido=True
        )

    return texto_total, archivos_usados


# ============================================
# GENERACIÓN DEL EXAMEN (con fallback si no hay contexto)
# ============================================

def generar_examen(texto_contexto: str, especificaciones: dict, material: str, capitulos: list,
                   motor: str = "atlas", modelo_nube: str = "meta/llama-3.1-70b-instruct") -> list:  # ✅ CORREGIDO: sin espacio
    caps_str = f"capítulos {', '.join(capitulos)}" if capitulos else "todo el material"
    n_conceptuales = especificaciones.get("conceptuales", 0)
    n_desarrollo = especificaciones.get("desarrollo", 0)
    n_vf = especificaciones.get("vf", 0)
    total = especificaciones.get("total", 10)

    if not n_conceptuales and not n_desarrollo and not n_vf:
        n_conceptuales = round(total * 0.4)
        n_desarrollo = round(total * 0.4)
        n_vf = total - n_conceptuales - n_desarrollo

    usar_conocimiento_general = (len(texto_contexto) < 200)
    if usar_conocimiento_general:
        nota_contexto = "⚠️ No encontré suficiente material local en el RAG. Usaré mi conocimiento general sobre el tema."
    else:
        nota_contexto = ""

    prompt = f"""
Sos un profesor universitario experto en la materia correspondiente. Generá un examen sobre: "{material}".
{nota_contexto}

MATERIAL DE ESTUDIO LOCAL:
{texto_contexto[:18000] if not usar_conocimiento_general else 'No disponible.'}

FORMATO DEL EXAMEN:
{n_conceptuales} preguntas CONCEPTUALES (definiciones, explicaciones de conceptos clave)
{n_desarrollo} preguntas de DESARROLLO (análisis, relación entre conceptos, aplicación práctica)
{n_vf} preguntas de VERDADERO/FALSO (justificar las falsas)

REGLAS CRÍTICAS:
Cada pregunta debe estar NUMERADA: P1, P2, P3, etc.
Cada pregunta debe indicar su TIPO: [CONCEPTUAL], [DESARROLLO] o [V/F]
Para V/F: incluir la justificación si es FALSO.
Incluir RESPUESTA CORRECTA y CRITERIOS DE CORRECCIÓN.
Priorizar el material local si existe; si no, generar preguntas precisas con tu conocimiento.

IMPORTANTE - Usá EXACTAMENTE este formato para CADA pregunta (separá cada pregunta con exactamente 3 guiones ---):

PREGUNTA 1: [CONCEPTUAL]
ENUNCIADO: ¿Qué es el muestreo aleatorio simple?
RESPUESTA CORRECTA: Es un método donde cada elemento tiene la misma probabilidad de ser seleccionado.
CRITERIOS: Debe mencionar equiprobabilidad y selección al azar.
PUNTAJE: 10

PREGUNTA 2: [DESARROLLO]
ENUNCIADO: Explique la diferencia entre muestreo probabilístico y no probabilístico.
RESPUESTA CORRECTA: ...
CRITERIOS: ...
PUNTAJE: 10

No uses ningún otro formato. No agregues introducciones ni despedidas. Solo las preguntas separadas por ---.
Generá exactamente {total} preguntas.
"""
    try:
        respuesta = _preguntar_adaptable(prompt, motor, modelo_nube, max_tokens=4096)
        preguntas = _parsear_preguntas(respuesta, total)
        return preguntas
    except Exception as e:
        return [{"error": str(e)}]


# ============================================
# PARSEO (robusto: tolera formato sin ---)
# ============================================

def _parsear_preguntas(texto: str, total_esperado: int) -> list:
    preguntas = []

    # Intento 1: separar por --- (formato estricto)
    bloques = [b.strip() for b in texto.split("---") if b.strip()]

    # Intento 2: si no encontró bloques con ---, buscar preguntas numeradas
    if not any("PREGUNTA" in b.upper() for b in bloques):
        bloques = _dividir_por_preguntas(texto)

    for bloque in bloques:
        bloque = bloque.strip()
        if not bloque:
            continue

        pregunta = {"tipo": "general", "numero": len(preguntas) + 1}

        m_num = re.search(r'PREGUNTA\s*(?:N[°º:]?\s*)?(\d+)', bloque, re.IGNORECASE)
        if m_num:
            pregunta["numero"] = int(m_num.group(1))

        m_tipo = re.search(r'\[(CONCEPTUAL|DESARROLLO|V/F|VF|VERDADERO/FALSO)\]', bloque, re.IGNORECASE)
        if m_tipo:
            tipo_raw = m_tipo.group(1).upper()
            if tipo_raw in ["V/F", "VF", "VERDADERO/FALSO"]:
                pregunta["tipo"] = "vf"
            else:
                pregunta["tipo"] = tipo_raw.lower()

        m_enunciado = re.search(r'ENUNCIADO\s*:\s*(.+?)(?=\n(?:OPCIONES|RESPUESTA|JUSTIFICACION|CRITERIOS|PUNTAJE|\Z))', bloque, re.IGNORECASE | re.DOTALL)
        if m_enunciado:
            pregunta["enunciado"] = m_enunciado.group(1).strip()
        else:
            _extraer_enunciado_flexible(bloque, pregunta)

        if "enunciado" not in pregunta or not pregunta["enunciado"]:
            continue

        m_respuesta = re.search(r'RESPUESTA\s*(?:CORRECTA)?\s*:\s*(.+?)(?=\n(?:JUSTIFICACION|CRITERIOS|PUNTAJE|\Z))', bloque, re.IGNORECASE | re.DOTALL)
        if m_respuesta:
            pregunta["respuesta_correcta"] = m_respuesta.group(1).strip()

        m_just = re.search(r'JUSTIFICACION\s*:\s*(.+?)(?=\n(?:CRITERIOS|PUNTAJE|\Z))', bloque, re.IGNORECASE | re.DOTALL)
        if m_just:
            pregunta["justificacion"] = m_just.group(1).strip()

        m_criterios = re.search(r'CRITERIOS\s*:\s*(.+?)(?=\n(?:PUNTAJE|\Z))', bloque, re.IGNORECASE | re.DOTALL)
        if m_criterios:
            pregunta["criterios"] = m_criterios.group(1).strip()

        m_puntaje = re.search(r'PUNTAJE\s*:\s*(\d+)', bloque, re.IGNORECASE)
        pregunta["puntaje"] = int(m_puntaje.group(1)) if m_puntaje else 10

        pregunta.setdefault("respuesta_correcta", "No especificada")
        pregunta.setdefault("criterios", "Evaluar precisión conceptual y completitud")

        preguntas.append(pregunta)

    if not preguntas:
        preguntas = [{"numero": 1, "tipo": "general", "enunciado": "El modelo no pudo generar preguntas estructuradas.", "puntaje": 0, "respuesta_correcta": "N/A", "criterios": "N/A"}]

    return preguntas


def _dividir_por_preguntas(texto: str) -> list:
    """Si el modelo no usó ---, intenta dividir por "PREGUNTA N:" o "Pregunta N:"."""
    bloques = re.split(r'(?=PREGUNTA\s+\d+\s*:)', texto, flags=re.IGNORECASE)
    bloques = [b.strip() for b in bloques if b.strip()]
    if len(bloques) <= 1:
        bloques = re.split(r'(?=[Pp]regunta\s*\d+)', texto)
        bloques = [b.strip() for b in bloques if b.strip()]
    return bloques


def _extraer_enunciado_flexible(bloque: str, pregunta: dict):
    """
    Si el modelo no puso ENUNCIADO:, intenta inferir el enunciado
    de la primera línea significativa después del encabezado.
    """
    lineas = bloque.strip().split('\n')
    for linea in lineas:
        limpia = linea.strip()
        if not limpia:
            continue
        if re.search(r'PREGUNTA', limpia, re.IGNORECASE):
            continue
        if re.search(r'^(RESPUESTA|JUSTIFICACION|CRITERIOS|PUNTAJE|OPCIONES)', limpia, re.IGNORECASE):
            break
        pregunta["enunciado"] = limpia
        return


# ============================================
# CORRECCIÓN
# ============================================

def corregir_respuesta(pregunta: dict, respuesta_usuario: str,
                       motor: str = "atlas", modelo_nube: str = "meta/llama-3.1-70b-instruct") -> dict:  # ✅ CORREGIDO: sin espacio
    tipo = pregunta.get("tipo", "general")
    enunciado = pregunta.get("enunciado", "")
    respuesta_correcta = pregunta.get("respuesta_correcta", "")
    criterios = pregunta.get("criterios", "")
    puntaje_max = pregunta.get("puntaje", 10)
    justificacion = pregunta.get("justificacion", "")

    if tipo == "vf":
        prompt = f"""
Sos un corrector de examen. Evaluá esta respuesta de Verdadero/Falso.

PREGUNTA: {enunciado}
RESPUESTA CORRECTA: {respuesta_correcta}
JUSTIFICACION (si es FALSO): {justificacion}
RESPUESTA DEL ALUMNO: {respuesta_usuario}
PUNTAJE MÁXIMO: {puntaje_max}

CRITERIOS:
Si la respuesta del alumno indica correctamente V o F: {puntaje_max * 0.4:.0f} puntos
Si es FALSO y el alumno justifica correctamente: {puntaje_max * 0.6:.0f} puntos adicionales

Devolvé EXACTAMENTE en este formato:
PUNTAJE: [número]
FEEDBACK: [explicación breve, máximo 3 líneas]
"""
    else:
        prompt = f"""
Sos un corrector de examen universitario. Evaluá esta respuesta.

PREGUNTA: {enunciado}
RESPUESTA ESPERADA: {respuesta_correcta}
CRITERIOS DE CORRECCIÓN: {criterios}
RESPUESTA DEL ALUMNO: {respuesta_usuario}
PUNTAJE MÁXIMO: {puntaje_max}

EVALUÁ:
Precisión conceptual (60%)
Completitud (30%)
Claridad (10%)

Devolvé EXACTAMENTE:
PUNTAJE: [número entero]
FEEDBACK: [explicación clara, máximo 4 líneas]
"""

    try:
        resultado = _preguntar_adaptable(prompt, motor, modelo_nube, max_tokens=512)
        m_puntaje = re.search(r'PUNTAJE\s*:\s*(\d+)', resultado, re.IGNORECASE)
        puntaje = int(m_puntaje.group(1)) if m_puntaje else 0
        puntaje = max(0, min(puntaje, puntaje_max))

        m_feedback = re.search(r'FEEDBACK\s*:\s*(.+)', resultado, re.IGNORECASE | re.DOTALL)
        feedback = m_feedback.group(1).strip() if m_feedback else "Sin feedback."

        return {"puntaje_obtenido": puntaje, "puntaje_max": puntaje_max, "feedback": feedback, "correcta": puntaje >= puntaje_max * 0.7}
    except Exception as e:
        return {"puntaje_obtenido": 0, "puntaje_max": puntaje_max, "feedback": f"Error: {e}", "correcta": False}


# ============================================
# INFORME FINAL
# ============================================

def generar_informe_final(resultados: list) -> str:
    total_puntaje_max = sum(r["correccion"]["puntaje_max"] for r in resultados)
    total_puntaje_obtenido = sum(r["correccion"]["puntaje_obtenido"] for r in resultados)
    porcentaje = (total_puntaje_obtenido / total_puntaje_max * 100) if total_puntaje_max > 0 else 0
    correctas = [r for r in resultados if r["correccion"]["correcta"]]
    incorrectas = [r for r in resultados if not r["correccion"]["correcta"]]
    nota = round(porcentaje / 10, 1)

    informe = f"""
{'='*60}
📊 INFORME FINAL DEL EXAMEN
{'='*60}

🎯 PUNTUACIÓN TOTAL: {total_puntaje_obtenido}/{total_puntaje_max} ({porcentaje:.1f}%)
📝 NOTA: {nota}/10
✅ CORRECTAS: {len(correctas)}/{len(resultados)}
❌ INCORRECTAS: {len(incorrectas)}/{len(resultados)}

{'─'*60}
📋 DETALLE:
"""
    for r in resultados:
        p = r["pregunta"]
        c = r["correccion"]
        icono = "✅" if c["correcta"] else "❌"
        informe += f"""
{icono} P{p['numero']} [{p.get('tipo','general').upper()}] — {c['puntaje_obtenido']}/{c['puntaje_max']}
📝 Tu respuesta: {r['respuesta_usuario'][:150]}{'...' if len(r['respuesta_usuario']) > 150 else ''}
💬 Feedback: {c['feedback']}
"""

    informe += f"""
{'─'*60}
🔍 ANÁLISIS DE ERRORES:
"""
    if incorrectas:
        for r in incorrectas:
            p = r["pregunta"]
            c = r["correccion"]
            informe += f"""
❌ P{p['numero']}: {p.get('enunciado','')[:120]}...
➤ Esperado: {p.get('respuesta_correcta','N/A')[:200]}
➤ Problema: {c['feedback']}
"""
    else:
        informe += "\n🎉 ¡Sin errores!\n"

    informe += f"""
{'─'*60}
💡 RECOMENDACIONES:
"""
    if porcentaje >= 80:
        informe += "✅ Excelente desempeño.\n"
    elif porcentaje >= 60:
        informe += "⚠️ Buen nivel, repasá los puntos débiles.\n"
    else:
        informe += "🔴 Repaso intensivo necesario.\n"

    informe += f"{'='*60}\n"
    return informe


# ============================================
# ORQUESTADOR
# ============================================

def ejecutar_examen_completo(pregunta_usuario: str, motor: str = "atlas",
                             modelo_nube: str = "meta/llama-3.1-70b-instruct") -> dict:  # ✅ CORREGIDO: sin espacio
    info = detectar_material_y_capitulos(pregunta_usuario)
    material = info["material"] or pregunta_usuario
    capitulos = info["capitulos"]
    especs = info["especificaciones"]

    texto_contexto, archivos = extraer_material_rag(material, capitulos)
    preguntas = generar_examen(texto_contexto, especs, material, capitulos, motor, modelo_nube)

    return {
        "material": material,
        "capitulos": capitulos,
        "archivos_encontrados": archivos,
        "total_preguntas": len(preguntas),
        "preguntas": preguntas,
        "texto_contexto": texto_contexto,
        "especificaciones": especs
    }
