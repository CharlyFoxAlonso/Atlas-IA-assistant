from core.pdf_reader import leer_pdf
from core.models import preguntar


def investigar_pdf(ruta_pdf):
    """
    Investiga un PDF individual y genera apuntes de estudio.
    
    Devuelve:
        Texto con resumen, conceptos clave, fórmulas, preguntas de examen, etc.
    """
    # 1. Leer el PDF
    data = leer_pdf(ruta_pdf)
    
    if not data["ok"]:
        return f"❌ Error leyendo PDF: {data.get('error', 'Error desconocido')}"
    
    texto = data["texto"]
    
    if not texto or len(texto.strip()) < 100:
        return f"⚠️ El PDF no tiene suficiente texto extraíble ({len(texto)} caracteres)"
    
    # 2. Construir el prompt (contexto reducido a 5000)
    prompt = f"""
Eres un investigador académico especializado en estadística.
Tu tarea es analizar material de estudio y convertirlo en contenido útil para un examen.

========================
TEXTO DEL PDF:
{texto[:5000]}

INSTRUCCIONES:
Devuelve:
1. RESUMEN GENERAL (simple y claro, máximo 100 palabras)
2. CONCEPTOS CLAVE (lista de 5-10 conceptos)
3. FÓRMULAS IMPORTANTES (si hay)
4. POSIBLES PREGUNTAS DE EXAMEN (3-5 preguntas)
5. EXPLICACIÓN SIMPLE (como para estudiar rápido)
6. ERRORES COMUNES DE ESTUDIANTES (qué suelen confundir)

Reglas:
- Usa principalmente el texto proporcionado
- Si falta información crítica, puedes complementar con conocimiento general de estadística
- Indica con [MATERIAL] lo que viene del PDF y con [COMPLEMENTO] lo que agregas tú
- Sé claro y directo
- Usa formato Markdown
"""
    
    # 3. Consultar al modelo
    try:
        respuesta = preguntar(prompt)
        return respuesta
    except Exception as e:
        return f"❌ Error al procesar el PDF: {str(e)}"