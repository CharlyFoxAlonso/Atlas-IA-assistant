"""
core/memory_manager.py
Gestión de memoria persistente y análisis de conversaciones.
Atlas v3.4
"""
import os
from datetime import datetime
from core.models import preguntar
from core.security import validar_ruta, sanitizar_contenido, log_seguridad

# Categorías de memoria disponibles (SIN espacios)
CATEGORIAS = {
    "Perfil": "memory/Atlas_Memory/01_Perfil/Perfil_Charly.md",
    "Aprendizajes": "memory/Atlas_Memory/02_Memoria/Aprendizajes.md",
    "Decisiones": "memory/Atlas_Memory/02_Memoria/Decisiones.md",
    "Universidad": "memory/Atlas_Memory/04_Universidad/Registro.md",  # ✅ CORREGIDO: Univercidad → Universidad
    "Proyectos": "memory/Atlas_Memory/05_Proyectos/Registro.md",
    "Diario": "memory/Atlas_Memory/06_Diario/Registro.md",
    "Salud": "memory/Atlas_Memory/07_Salud/Registro.md",
    "Finanzas": "memory/Atlas_Memory/08_Finanzas/Registro.md"
}


def analizar_conversacion(pregunta, respuesta):
    """Analiza una conversación para detectar información importante sobre el USUARIO."""
    prompt_analisis = f"""
Sos un analista de conversaciones. Tu tarea es detectar información sobre CHARLY (el usuario), NO sobre el tema de la conversación.

PREGUNTA DE CHARLY:
{pregunta}

RESPUESTA DE ATLAS:
{respuesta[:300]}

═══════════════════════════════════════════════════════════
REGLA CRÍTICA:
═══════════════════════════════════════════════════════════
SOLO debés guardar información si Charly dice algo sobre SÍ MISMO.

❌ NO GUARDES: Explicaciones de conceptos, fórmulas, ejemplos educativos.
✅ SÍ GUARDA: "Me cuesta...", "No entiendo...", "Prefiero...", "Aprobé...", "Tengo examen...", "Estoy estresado...", "Trabajo en..."

Si NO hay info sobre Charly → respondé SOLO: "NADA"
Si SÍ hay info → respondé en este formato:

CATEGORIA: [Perfil/Aprendizajes/Decisiones/Universidad/Proyectos/Diario/Salud/Finanzas]
RESUMEN: [máximo 50 palabras sobre Charly]
RAZON: [por qué es importante recordar esto sobre Charly]

Tu análisis:
"""
    try:
        resultado = preguntar(prompt_analisis)
        
        if "NADA" in resultado.upper()[:30]:
            return []
        
        propuestas = []
        if "CATEGORIA:" in resultado and "RESUMEN:" in resultado:
            categoria = _extraer_campo(resultado, "CATEGORIA:")
            resumen = _extraer_campo(resultado, "RESUMEN:")
            razon = _extraer_campo(resultado, "RAZON:")
            
            if categoria and resumen:
                propuestas.append({
                    "categoria": categoria.strip(),
                    "resumen": resumen.strip(),
                    "razon": razon.strip() if razon else "Información relevante sobre Charly"
                })
        
        return propuestas
    except Exception as e:
        print(f"   ⚠️ Error en análisis de memoria: {e}")
        return []


def _extraer_campo(texto, campo):
    """Extrae el valor de un campo del formato CATEGORIA: valor"""
    try:
        inicio = texto.find(campo) + len(campo)
        resto = texto[inicio:]
        siguiente_campo = resto.find("\n")
        if siguiente_campo == -1:
            return resto.strip()
        return resto[:siguiente_campo].strip()
    except:
        return None


def guardar_en_memoria(categoria, resumen):
    """Guarda información en el archivo de memoria correspondiente."""
    if categoria not in CATEGORIAS:
        return False, f"Categoría '{categoria}' no existe"
    
    # Validar contenido
    es_seguro, patrones = sanitizar_contenido(resumen)
    if not es_seguro:
        log_seguridad("GUARDADO_BLOQUEADO", f"Contenido sospechoso en categoría {categoria}: {', '.join(patrones)}")
        return False, f"Contenido bloqueado por seguridad. Patrones detectados: {', '.join(patrones)}"
    
    ruta_archivo = CATEGORIAS[categoria]
    
    # Validar ruta
    es_valida, error_ruta = validar_ruta(ruta_archivo)
    if not es_valida:
        return False, error_ruta
    
    # Crear directorio si no existe
    directorio = os.path.dirname(ruta_archivo)
    os.makedirs(directorio, exist_ok=True)
    
    # Formatear entrada
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entrada = f"\n\n### {timestamp}\n{resumen}\n"
    
    try:
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, "a", encoding="utf-8") as f:
                f.write(entrada)
        else:
            with open(ruta_archivo, "w", encoding="utf-8") as f:
                f.write(f"# {categoria}\n\nRegistro automático de Atlas.\n")
                f.write(entrada)
        
        log_seguridad("GUARDADO_EXITOSO", f"Guardado en {ruta_archivo}")
        return True, ruta_archivo
    except Exception as e:
        log_seguridad("ERROR_GUARDADO", f"Error guardando en {ruta_archivo}: {str(e)}")
        return False, str(e)


def listar_categorias():
    """Devuelve la lista de categorías disponibles."""
    return list(CATEGORIAS.keys())


# ============================================
# NUEVA FUNCIÓN: Revisar Historial y Actualizar Memoria
# ============================================

def procesar_historial_para_memoria(historial):
    """
    Recorre el historial de conversaciones, analiza cada interacción
    y guarda la información relevante sobre Charly en la memoria persistente.
    (Equivalente al comando 'salir' de la versión CMD).
    """
    guardados = 0
    errores = 0
    
    for interaccion in historial:
        pregunta = interaccion.get("pregunta", "")
        respuesta = interaccion.get("respuesta", "")
        
        if not pregunta or not respuesta:
            continue
        
        # Usar el LLM para analizar si hay info sobre Charly
        propuestas = analizar_conversacion(pregunta, respuesta)
        
        for p in propuestas:
            ok, msg = guardar_en_memoria(p["categoria"], p["resumen"])
            if ok:
                guardados += 1
            else:
                errores += 1
    
    return guardados, errores