"""
core/diary_manager.py
Gestiona el diario personal de Charly.
Agrega entradas con fecha, permite leer y buscar.
Atlas v3.2
"""
import os
from datetime import datetime
from core.security import log_seguridad

DIARIO_PATH = "memory/Atlas_Memory/06_Diario"


def _asegurar_carpeta_diario():
    """Crea la carpeta del diario si no existe."""
    if not os.path.exists(DIARIO_PATH):
        os.makedirs(DIARIO_PATH, exist_ok=True)
        log_seguridad("DIARIO_INIT", f"Carpeta de diario creada: {DIARIO_PATH}")


def obtener_archivo_hoy() -> str:
    """Devuelve la ruta del archivo del día actual."""
    fecha = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(DIARIO_PATH, f"diario_{fecha}.md")  # ✅ CORREGIDO: agrega _ para consistencia


def agregar_entrada(contenido: str, categoria: str = "general") -> dict:
    """
    Agrega una entrada al diario del día actual.
    
    Args:
        contenido: Texto de la entrada
        categoria: Categoría (general, logro, emocion, reflexion, proyecto)
    
    Returns:
        Diccionario con estado y mensaje
    """
    try:
        _asegurar_carpeta_diario()
        archivo = obtener_archivo_hoy()  # ✅ CORREGIDO: sin guión bajo
        hora = datetime.now().strftime("%H:%M:%S")
        fecha_legible = datetime.now().strftime("%d/%m/%Y")
        
        # Formato de la entrada
        entrada = f"\n## 🕐 {hora} - [{categoria.upper()}]\n\n{contenido}\n\n---\n"
        
        # Si el archivo no existe, agregar encabezado
        if not os.path.exists(archivo):
            encabezado = f"# 📔 Diario de Charly - {fecha_legible}\n\n"
            with open(archivo, "w", encoding="utf-8") as f:
                f.write(encabezado + entrada)
        else:
            # Agregar al final del archivo
            with open(archivo, "a", encoding="utf-8") as f:
                f.write(entrada)
        
        log_seguridad("DIARIO_ENTRY", f"Entrada agregada al diario: {categoria}")
        return {
            "exito": True,
            "mensaje": f"✅ Entrada agregada al diario ({categoria})",
            "archivo": os.path.basename(archivo)
        }
    except Exception as e:
        log_seguridad("DIARIO_ERROR", f"Error agregando entrada: {str(e)}")
        return {
            "exito": False,
            "mensaje": f"❌ Error: {str(e)}"
        }


def leer_diario_hoy() -> str:
    """Lee el diario del día actual."""
    _asegurar_carpeta_diario()
    archivo = obtener_archivo_hoy()  # ✅ CORREGIDO: sin guión bajo
    if not os.path.exists(archivo):
        return "No hay entradas en el diario de hoy."
    with open(archivo, "r", encoding="utf-8") as f:
        return f.read()


def leer_ultimas_entradas(n_entradas: int = 5) -> str:
    """Lee las últimas N entradas del diario."""
    _asegurar_carpeta_diario()
    archivo = obtener_archivo_hoy()  # ✅ CORREGIDO: sin guión bajo
    if not os.path.exists(archivo):
        return "No hay entradas en el diario."
    with open(archivo, "r", encoding="utf-8") as f:
        contenido = f.read()
    
    # Dividir por entradas (separadas por ---)
    entradas = contenido.split("---")
    
    # Tomar las últimas N entradas (excluyendo el encabezado)
    ultimas = entradas[-(n_entradas + 1):-1] if len(entradas) > n_entradas else entradas[1:]
    return "---".join(ultimas)


def buscar_en_diario(termino: str) -> list:
    """Busca un término en todos los archivos del diario."""
    _asegurar_carpeta_diario()
    resultados = []
    for archivo in os.listdir(DIARIO_PATH):
        if archivo.endswith(".md"):
            ruta = os.path.join(DIARIO_PATH, archivo)
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if termino.lower() in contenido.lower():
                    resultados.append({
                        "archivo": archivo,
                        "fecha": archivo.replace("diario_", "").replace(".md", ""),
                        "fragmento": _extraer_contexto(contenido, termino)
                    })
    return resultados


def _extraer_contexto(texto: str, termino: str, contexto_chars: int = 100) -> str:
    """Extrae un fragmento de texto alrededor del término buscado."""
    posicion = texto.lower().find(termino.lower())
    if posicion == -1:
        return ""
    inicio = max(0, posicion - contexto_chars)
    fin = min(len(texto), posicion + len(termino) + contexto_chars)
    fragmento = texto[inicio:fin]
    return f"...{fragmento}..."