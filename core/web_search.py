"""
core/web_search.py
Búsqueda web en cadena con fallback.
Atlas v3.4 — intento automático entre varios backends.

Jerarquía (intentamos en orden):
  1. Tavily (gratis con TAVILY_API_KEY)      — primera opción, optimizado para IA
  2. SearXNG (auto-hospedado, SEARXNG_URL)   — fallback privado self-hosted
  3. DuckDuckGo (gratis, sin API key)        — fallback universal

Cada backend expone:
    _disponible() -> bool
    _buscar(query, max_resultados) -> list[dict]
        Devuelve [{"titulo", "url", "snippet"}]
"""
import os
import logging
from typing import List, Dict, Optional

import requests as _requests

logger = logging.getLogger(__name__)


# ============================================
# Backend DuckDuckGo (gratis, sin API key)
# ============================================

_DUCKDUCK_BACKEND_AVAILABLE = False
try:
    from duckduckgo_search import DDGS as _DDGS
    _DUCKDUCK_BACKEND_AVAILABLE = True
except Exception:
    _DDGS = None


def _ddgs_disponible() -> bool:
    return _DUCKDUCK_BACKEND_AVAILABLE


def _ddgs_buscar(query: str, max_resultados: int = 5) -> List[Dict[str, str]]:
    resultados = []
    if not _DUCKDUCK_BACKEND_AVAILABLE:
        return [{"error": "duckduckgo-search no instalado"}]
    try:
        with _DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_resultados):
                titulo = r.get("title") or r.get("Title") or ""
                url = r.get("href") or r.get("Href") or r.get("url") or ""
                snippet = r.get("body") or r.get("Body") or r.get("snippet") or ""
                if not url:
                    continue
                resultados.append({
                    "titulo": titulo,
                    "url": url,
                    "snippet": snippet[:400],
                    "fuente": "duckduckgo",
                })
    except Exception as e:
        return [{"error": f"duckduckgo: {str(e)}"}]
    return resultados


# ============================================
# Backend Tavily (API key TAVILY_API_KEY)
# ============================================

_TAVILY_AVAILABLE = False
try:
    from tavily import TavilyClient as _TavilyClient
    _TAVILY_AVAILABLE = True
except Exception:
    _TavilyClient = None


def _tavily_disponible() -> bool:
    return _TAVILY_AVAILABLE and bool(os.getenv("TAVILY_API_KEY"))


def _tavily_buscar(query: str, max_resultados: int = 5) -> List[Dict[str, str]]:
    if not _TAVILY_AVAILABLE:
        return [{"error": "tavily-python no instalado"}]
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return [{"error": "TAVILY_API_KEY no configurada"}]
    try:
        client = _TavilyClient(api_key=api_key)
        res = client.search(
            query=query,
            max_results=max_resultados,
        )
        resultados = []
        for r in res.get("results", []):
            resultados.append({
                "titulo": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:400],
                "fuente": "tavily",
            })
        return resultados
    except Exception as e:
        return [{"error": f"tavily: {str(e)}"}]


# ============================================
# Backend SearXNG (URL en SEARXNG_URL)
# ============================================

def _searxng_disponible() -> bool:
    return bool(os.getenv("SEARXNG_URL"))


def _searxng_buscar(query: str, max_resultados: int = 5) -> List[Dict[str, str]]:
    url = os.getenv("SEARXNG_URL")
    if not url:
        return [{"error": "SEARXNG_URL no configurada"}]
    try:
        resp = _requests.get(
            f"{url.rstrip('/')}/search",
            params={
                "q": query,
                "format": "json",
                "language": "auto",
                "safesearch": 0,
            },
            headers={"User-Agent": "Atlas/3.4 (compatible)"},
            timeout=20,
        )
        if resp.status_code != 200:
            return [{"error": f"searxng HTTP {resp.status_code}"}]
        data = resp.json()
        resultados = []
        for r in data.get("results", [])[:max_resultados]:
            resultados.append({
                "titulo": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:400],
                "fuente": "searxng",
            })
        return resultados
    except Exception as e:
        return [{"error": f"searxng: {str(e)}"}]


# ============================================
# Orquestador en cadena
# ============================================

_BACKENDS = [
    ("tavily",     _tavily_disponible, _tavily_buscar),
    ("searxng",    _searxng_disponible, _searxng_buscar),
    ("duckduckgo", _ddgs_disponible, _ddgs_buscar),
]


def _es_error(lista):
    if not lista:
        return False
    if not isinstance(lista, list):
        return False
    if len(lista) > 0 and isinstance(lista[0], dict) and "error" in lista[0]:
        return True
    return False


def _es_vacia_por_rate_limit(lista):
    """Heurística: detectar 202 Ratelimit en el error string."""
    if not _es_error(lista):
        return False
    return "202" in str(lista[0].get("error", "")) or "rate" in str(lista[0].get("error", "")).lower()


def buscar_web(query: str, max_resultados: int = 5) -> List[Dict[str, str]]:
    """
    Busca en la web intentando cada backend en orden.
    Devuelve lista de resultados con {titulo, url, snippet, fuente}.
    Si todos fallan, devuelve el último error con un prefijo.
    """
    if not query or not query.strip():
        return [{"error": "Query vacía"}]

    ultimo_error = [{"error": "No hay backends disponibles"}]
    backends_usados = []

    for nombre, disponible, fn in _BACKENDS:
        if not disponible():
            continue
        try:
            resultados = fn(query, max_resultados)
        except Exception as e:
            logger.error(f"Backend {nombre} lanzó excepción: {e}")
            ultimo_error = [{"error": f"{nombre} excepción: {str(e)}"}]
            continue

        backends_usados.append(nombre)

        if _es_error(resultados):
            logger.warning(f"Backend {nombre} reportó error: {resultados[0].get('error','')}")
            ultimo_error = resultados
            continue

        if not resultados:
            ultimo_error = [{"error": f"{nombre}: 0 resultados"}]
            continue

        return resultados

    # Si ningún backend funcionó, devolver un error con metadata completa
    if not backends_usados:
        return [{
            "error": (
                "Ningún backend de búsqueda disponible. "
                "Instalá duckduckgo-search (pip install duckduckgo-search) "
                "o configurá TAVILY_API_KEY / SEARXNG_URL en tu .env."
            )
        }]

    # Devolvemos el último error + nota de fallback agotado
    ultimo = ultimo_error[0] if ultimo_error else {"error": "fallo sin detalles"}
    return [{
        "error": ultimo.get("error", "fallo sin detalles"),
        "backends_usados": backends_usados,
    }]


def formatear_resultados_web(resultados):
    """
    Formatea resultados web para meterlos en un prompt.
    Devuelve string listo para inyectar.
    """
    if not resultados:
        return "No se encontraron resultados."

    if isinstance(resultados, list) and resultados and "error" in resultados[0]:
        msg = resultados[0].get("error", "búsqueda fallida")
        return f"[Búsqueda web no disponible: {msg}]"

    lines = []
    for i, r in enumerate(resultados, 1):
        lines.append(f"[{i}] {r.get('titulo', '')}")
        lines.append(f"    URL: {r.get('url', '')}")
        snippet = r.get('snippet', '').replace("\n", " ")
        lines.append(f"    {snippet}")
        if r.get("fuente"):
            lines.append(f"    Fuente: {r['fuente']}")

    return "\n".join(lines)
