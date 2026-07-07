"""Búsqueda web usando duckduckgo-search (paquete oficial)."""
import logging

logger = logging.getLogger(__name__)

try:
    # Nombre correcto del paquete (la librería se llamaba 'ddgs'
    # hasta v5.x, después se renombró a 'duckduckgo-search').
    from duckduckgo_search import DDGS
    _DDGS_AVAILABLE = True
except Exception:
    DDGS = None
    _DDGS_AVAILABLE = False


def buscar_web(query, max_resultados=5):
    """
    Busca en la web usando DuckDuckGo Search.
    Devuelve lista de resultados con título, URL y snippet.
    """
    if not _DDGS_AVAILABLE:
        return [{"error": "Instalá duckduckgo-search: pip install duckduckgo-search"}]

    resultados = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_resultados):
                # duckduckgo-search 6+/7+ usa 'title', 'href', 'body'
                # pero defensivamente aceptamos ambas convenciones.
                titulo = r.get("title") or r.get("Title") or ""
                url = r.get("href") or r.get("Href") or r.get("url") or ""
                snippet = r.get("body") or r.get("Body") or r.get("snippet") or ""
                if not url:
                    continue
                resultados.append({
                    "titulo": titulo,
                    "url": url,
                    "snippet": snippet[:400],
                })
        return resultados
    except Exception as e:
        logger.error(f"Error en búsqueda DuckDuckGo: {e}")
        return [{"error": f"Error en búsqueda: {str(e)}"}]


def formatear_resultados_web(resultados):
    """Formatea resultados web para el prompt."""
    if not resultados:
        return "No se encontraron resultados."
    
    if resultados and "error" in resultados[0]:
        return resultados[0]["error"]
    
    texto = ""
    for i, r in enumerate(resultados, 1):
        texto += f"\n[{i}] {r['titulo']}\n"
        texto += f"    URL: {r['url']}\n"
        texto += f"    {r['snippet']}\n"
    
    return texto