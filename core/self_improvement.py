"""
core/self_improvement.py
Rastreador de mejoras para Atlas v3.
Busca en la web (foros, noticias, documentación) recomendaciones de
actualización o mejora, **sin modificar código**.
Las URLs encontradas se persisten para revisión manual en la UI.
"""

import os
import json
from datetime import datetime
from urllib.parse import urlparse as _urlparse
from core.web_search import buscar_web

RUTA_RECOMENDACIONES = "memory/Atlas_Memory/sandbox/recomendaciones.json"

CATEGORIAS_BUSQUEDA = {
    "rag":  [
        "RAG retrieval augmented generation best practices 2026",
        "ChromaDB performance tuning tips site:github.com OR site:docs.trychroma.com",
        "local vector database optimization techniques",
    ],
    "llm_local": [
        "Ollama deployment optimization production 2026",
        "best small LLM models 2026 local GPU inference",
        "Ollama new features releases site:ollama.com OR site:github.com/ollama",
    ],
    "prompt_engineering": [
        "prompt engineering latest techniques 2026 site:arxiv.org",
        "system prompt design improvements open source",
        "multi-agent routing optimization LLM",
    ],
    "seguridad": [
        "LLM security prompt injection mitigation 2026",
        "local AI assistant security best practices",
        "Ollama authentication access control updates",
    ],
    "modelos_nvidia": [
        "NVIDIA NIM new models catalog 2026",
        "free NVIDIA API models updates site:nvidia.com OR site:build.nvidia.com",
        "deepseek llama new versions NVIDIA API",
    ],
}


def _asegurar_sandbox():
    """Crea la carpeta sandbox si no existe."""
    sandbox_dir = os.path.dirname(RUTA_RECOMENDACIONES)
    os.makedirs(sandbox_dir, exist_ok=True)


def _cargar_recomendaciones() -> list:
    """Carga las recomendaciones persistidas desde disco."""
    _asegurar_sandbox()
    if not os.path.exists(RUTA_RECOMENDACIONES):
        return []
    try:
        with open(RUTA_RECOMENDACIONES, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _guardar_recomendaciones(recomendaciones: list):
    """Persiste la lista de recomendaciones en disco."""
    _asegurar_sandbox()
    with open(RUTA_RECOMENDACIONES, "w", encoding="utf-8") as f:
        json.dump(recomendaciones, f, indent=2, ensure_ascii=False)


def _deduplicar_por_url(resultados: list) -> list:
    """Elimina URLs duplicadas manteniendo la primera ocurrencia."""
    vistas = set()
    unicos = []
    for r in resultados:
        url = r.get("url", "").strip().lower()
        if url and url not in vistas:
            vistas.add(url)
            unicos.append(r)
    return unicos


def _extraer_dominio(url: str) -> str:
    """Extrae el nombre del dominio para etiquetar la fuente."""
    try:
        netloc = _urlparse(url).netloc.replace("www.", "")
        return netloc.split(".")[0] if netloc else "desconocido"
    except Exception:
        return "desconocido"


def _buscar_por_categoria(categoria: str, max_por_query: int = 4) -> list:
    """
    Ejecuta las queries de una categoría y devuelve resultados
    con metadata enriquecida (titulo, url, snippet, dominio, categoria).
    """
    queries = CATEGORIAS_BUSQUEDA.get(categoria, [])
    resultados = []
    for query in queries:
        try:
            raw = buscar_web(query, max_resultados=max_por_query)
            for item in raw:
                url = item.get("url", "") or item.get("href", "")
                titulo = item.get("titulo", "") or item.get("title", "")
                snippet = item.get("snippet", "") or item.get("body", "")
                if not url:
                    continue
                resultados.append({
                    "titulo": titulo,
                    "url": url,
                    "snippet": snippet[:300],
                    "dominio": _extraer_dominio(url),
                    "categoria": categoria,
                })
        except Exception:
            continue
    return _deduplicar_por_url(resultados)


def buscar_mejores_practicas(tema: str = None, categorias: list = None) -> list:
    """
    Busca en la web mejores prácticas para mejorar Atlas.

    Si se especifica ``tema``, busca con queries genéricas centradas en ese tema
    (compatibilidad con llamadas antiguas desde atlas_chat.py y atlas_ui.py).

    Si se especifican ``categorias``, busca sólo en esas categorías.
    Por defecto busca en TODAS las categorías definidas en CATEGORIAS_BUSQUEDA.

    Retorna:
      Lista de dicts con {titulo, url, snippet, dominio, categoria, timestamp}.
      Ideal para mostrar en la barra lateral de Streamlit.
    """
    if tema:
        queries = [
            f"mejores practicas {tema} 2026",
            f"latest updates {tema} site:github.com OR site:stackoverflow.com",
            f"optimization {tema} local LLM",
        ]
        resultados = []
        for q in queries:
            try:
                raw = buscar_web(q, max_resultados=4)
                for item in raw:
                    url = item.get("url", "") or item.get("href", "")
                    titulo = item.get("titulo", "") or item.get("title", "")
                    snippet = item.get("snippet", "") or item.get("body", "")
                    if not url:
                        continue
                    resultados.append({
                        "titulo": titulo,
                        "url": url,
                        "snippet": snippet[:300],
                        "dominio": _extraer_dominio(url),
                        "categoria": tema,
                    })
            except Exception:
                continue
        return _deduplicar_por_url(resultados)

    cats = categorias if categorias else list(CATEGORIAS_BUSQUEDA.keys())
    resultados = []
    for cat in cats:
        resultados.extend(_buscar_por_categoria(cat))
    return _deduplicar_por_url(resultados)


def rastrear_y_persistir(categorias: list = None) -> dict:
    """
    Busca recomendaciones en la web y las persiste en disco.
    Devuelve un resumen {nuevas, total, timestamp} para la UI.

    Este es el entry-point para el botón "Rastrear mejoras" en Streamlit.
    """
    ahora = datetime.now().isoformat()
    anteriores = _cargar_recomendaciones()
    urls_anteriores = {r["url"].strip().lower() for r in anteriores if r.get("url")}

    nuevas_raw = buscar_mejores_practicas(categorias=categorias)
    nuevas_filtradas = []

    for r in nuevas_raw:
        url_key = r.get("url", "").strip().lower()
        if url_key and url_key not in urls_anteriores:
            r["timestamp"] = ahora
            r["revisada"] = False
            nuevas_filtradas.append(r)

    total = anteriores + nuevas_filtradas
    _guardar_recomendaciones(total)

    return {
        "nuevas": len(nuevas_filtradas),
        "total": len(total),
        "timestamp": ahora,
    }


def obtener_recomendaciones_pendientes() -> list:
    """
    Devuelve todas las recomendaciones persistidas, ordenadas por
    fecha descendente (más recientes primero). Para la sidebar de Streamlit.
    """
    recs = _cargar_recomendaciones()
    recs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return recs


def marcar_recomendacion_revisada(indice: int) -> bool:
    """
    Marca una recomendación como revisada por índice.
    Retorna True si se pudo marcar.
    """
    recs = _cargar_recomendaciones()
    if 0 <= indice < len(recs):
        recs[indice]["revisada"] = True
        _guardar_recomendaciones(recs)
        return True
    return False


def limpiar_recomendaciones() -> int:
    """Elimina todas las recomendaciones persistidas. Retorna cantidad eliminada."""
    recs = _cargar_recomendaciones()
    _guardar_recomendaciones([])
    return len(recs)


# ============================================================
# Funciones de análisis — compatibles con self_awareness,
# sólo ANALIZAN, no modifican código.
# ============================================================

def analizar_debilidades(historial_conversaciones):
    """
    Analiza el historial para detectar patrones de error o mejora.
    NO modifica código — sólo devuelve un dict con análisis.
    """
    from core.models import preguntar
    if not historial_conversaciones:
        return {"debilidades": [], "fortalezas": []}

    prompt = f"""
Sos un analista de sistemas de IA. Analizá estas conversaciones de Atlas
y detectá patrones de error o áreas de mejora.

HISTORIAL (ultimas conversaciones):
{json.dumps(historial_conversaciones[-10:], indent=2, ensure_ascii=False)}

IDENTIFICA:
- Errores repetidos (ej: clasificar mal el agente)
- Respuestas muy largas o verbosas
- Informacion incorrecta o inventada
- Casos donde no pudo ayudar
- Patrones de preguntas que podrian optimizarse

Devolve un JSON con:
{{
  "debilidades": [
    {{"tipo": "...", "ejemplo": "...", "sugerencia": "..."}}
  ],
  "fortalezas": ["..."]
}}
"""
    try:
        resultado = preguntar(prompt)
        return json.loads(resultado)
    except Exception:
        return {"debilidades": [], "fortalezas": []}


def generar_propuesta_mejora(area, contexto_actual):
    """
    Genera una propuesta concreta de mejora para un área específica.
    NO modifica código — sólo devuelve un dict descriptivo.
    """
    from core.models import preguntar
    prompt = f"""
Sos un arquitecto de sistemas de IA. Genera una propuesta concreta de mejora
para el area: {area}

CONTEXTO ACTUAL DE ATLAS:
{contexto_actual}

REQUISITOS:
- La propuesta debe ser ESPECIFICA y APLICABLE
- Incluir codigo Python de ejemplo
- Explicar beneficios y riesgos
- Estimar esfuerzo de implementacion (bajo/medio/alto)

Formato de respuesta:
{{
  "area": "{area}",
  "propuesta": "Descripcion clara",
  "codigo_ejemplo": "Codigo Python",
  "beneficios": ["..."],
  "riesgos": ["..."],
  "esfuerzo": "bajo/medio/alto",
  "prioridad": "alta/media/baja"
}}
"""
    try:
        resultado = preguntar(prompt)
        return json.loads(resultado)
    except Exception:
        return None


if __name__ == "__main__":
    print("🔍 Rastreando mejoras en todas las categorías...")
    resumen = rastrear_y_persistir()
    print(f"✅ {resumen['nuevas']} nuevas recomendaciones encontradas")
    print(f"📊 Total acumulado: {resumen['total']}")
    recs = obtener_recomendaciones_pendientes()
    for i, r in enumerate(recs[:10]):
        estado = "✅" if r.get("revisada") else "🆕"
        print(f"  {i+1}. {estado} [{r.get('categoria','?')}] {r.get('titulo','sin titulo')[:80]}")
        print(f"     {r.get('url','')}")