"""
core/temp_rules.py
Gestiona reglas temporales con interceptación inteligente.
Diferencia entre reglas de contenido (forzar respuesta) y reglas de formato (inyectar en prompt).
Atlas v2.9
"""
import re

# Lista global de reglas temporales - ✅ CORREGIDO: agregado #
REGLAS_TEMPORALES = []


def agregar_regla(regla: str) -> dict:
    """Agrega una regla temporal."""
    if not regla or len(regla.strip()) < 3:
        return {
            "exito": False,
            "mensaje": "❌ La regla debe tener al menos 3 caracteres"
        }
    REGLAS_TEMPORALES.append(regla.strip())
    return {
        "exito": True,
        "mensaje": f"✅ Regla agregada: '{regla.strip()}'",
        "total_reglas": len(REGLAS_TEMPORALES)
    }


def listar_reglas() -> list:
    """Devuelve la lista de reglas temporales."""
    return REGLAS_TEMPORALES.copy()


def limpiar_reglas() -> dict:
    """Elimina todas las reglas temporales."""
    cantidad = len(REGLAS_TEMPORALES)
    REGLAS_TEMPORALES.clear()
    return {
        "exito": True,
        "mensaje": f"🗑️ {cantidad} reglas eliminadas" if cantidad > 0 else "ℹ️ No había reglas para eliminar"
    }


def _es_regla_de_contenido(regla: str) -> bool:
    """
    Determina si una regla es de CONTENIDO (se intercepta, no va al prompt).
    Reglas de contenido:
    - "si te pregunto por [tema], responde [respuesta]"
    - "responde siempre [respuesta]"
    - "siempre responde [respuesta]"
    """
    regla_lower = regla.lower()
    if "si te pregunto por" in regla_lower and ("responde" in regla_lower or "respondé" in regla_lower):
        return True
    if regla_lower.startswith("responde siempre") or regla_lower.startswith("siempre responde"):
        return True
    return False


def _es_regla_de_formato(regla: str) -> bool:
    """
    Determina si una regla es de FORMATO (se inyecta en el prompt).
    Reglas de formato:
    - "responde con [N] palabras"
    - "responde en [idioma]"
    - "máximo/minimo [N] caracteres/oraciones/párrafos"
    """
    regla_lower = regla.lower()
    if any(patron in regla_lower for patron in [
        "responde con", "responde en", "máximo", "minimo",
        "palabras", "caracteres", "oraciones", "párrafos"
    ]):
        return True
    return False


def obtener_contexto_reglas() -> str:
    """
    Genera el texto de contexto con las reglas para inyectar en el prompt.
    SOLO incluye reglas que NO son de contenido (las de contenido ya fueron interceptadas).
    Esto evita que reglas ya forzadas por Python lleguen al modelo y lo confundan.
    """
    if not REGLAS_TEMPORALES:
        return ""
    # Filtrar: solo reglas que NO son de contenido
    reglas_a_inyectar = [r for r in REGLAS_TEMPORALES if not _es_regla_de_contenido(r)]
    if not reglas_a_inyectar:
        return ""
    contexto = "\n========================\nREGLAS TEMPORALES DEL USUARIO (OBLIGATORIAS):\n"
    for i, regla in enumerate(reglas_a_inyectar, 1):
        contexto += f"{i}. {regla}\n"
    contexto += "========================\n"
    return contexto


def verificar_reglas_y_forzar_respuesta(pregunta: str) -> tuple:
    """
    Verifica si hay reglas de CONTENIDO que apliquen y fuerza una respuesta específica.
    NO aplica reglas de formato (como "3 palabras"), esas van al prompt.
    Returns:
         (debe_forzar: bool, respuesta_forzada: str)
    """
    if not REGLAS_TEMPORALES:
        return False, ""
    pregunta_lower = pregunta.lower()
    for regla in REGLAS_TEMPORALES:
        regla_lower = regla.lower()
        # REGLA DE CONTENIDO: "si te pregunto por [tema], responde [respuesta]"
        if "si te pregunto por" in regla_lower and ("responde" in regla_lower or "respondé" in regla_lower):
            try:
                partes = regla_lower.split("responde") if "responde" in regla_lower else regla_lower.split("respondé")
                if len(partes) == 2:
                    tema_parte = partes[0].replace("si te pregunto por", "").strip()
                    respuesta_forzada = partes[1].strip().strip('"').strip("'").strip()
                    palabras_tema = tema_parte.split()
                    coincidencias = sum(1 for palabra in palabras_tema if palabra in pregunta_lower)
                    if coincidencias > 0:
                        return True, respuesta_forzada
            except Exception:
                pass
        # REGLA DE CONTENIDO: Respuesta literal para cualquier pregunta
        if regla_lower.startswith("responde siempre") or regla_lower.startswith("siempre responde"):
            try:
                respuesta_forzada = regla_lower.replace("responde siempre", "").replace("siempre responde", "").strip()
                return True, respuesta_forzada
            except:
                pass
    return False, ""


def obtener_reglas_de_formato() -> str:
    """
    Extrae SOLO reglas de formato (como "responde con 3 palabras") para inyectar en el prompt.
    Estas reglas NO fuerzan la respuesta, solo dan instrucciones al modelo.
    Returns:
        String con las reglas de formato formateadas
    """
    if not REGLAS_TEMPORALES:
        return ""
    reglas_formato = [r for r in REGLAS_TEMPORALES if _es_regla_de_formato(r)]
    if not reglas_formato:
        return ""
    contexto = "\n========================\nREGLAS DE FORMATO (INSTRUCCIONES PARA EL MODELO):\n"
    for i, regla in enumerate(reglas_formato, 1):
        contexto += f"{i}. {regla}\n"
    contexto += "========================\n"
    return contexto