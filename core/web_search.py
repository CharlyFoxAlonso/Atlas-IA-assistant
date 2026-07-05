"""Búsqueda web usando DDGS (paquete actualizado de DuckDuckGo)."""

def buscar_web(query, max_resultados=5):
    """
    Busca en la web usando DDGS (DuckDuckGo Search).
    Devuelve lista de resultados con título, URL y snippet.
    """
    try:
        from ddgs import DDGS
        
        with DDGS() as ddgs:
            resultados = []
            for r in ddgs.text(query, max_results=max_resultados):
                resultados.append({
                    "titulo": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
            return resultados
    
    except ImportError:
        return [{"error": "Instalá ddgs: pip install ddgs"}]
    except Exception as e:
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