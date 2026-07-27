# Auditoría general del código — Atlas v4.1

| Campo | Valor |
|---|---|
| **Fecha** | 25 julio 2026 |
| **Commit** | `10812cb079c3ad5a632a6c38d07c142943fc27ce` |
| **Rama** | `atlas-v4.1-incremental-indexing` |
| **Working tree** | Limpio |
| **Tipo** | Auditoría general de código |
| **Auditor** | opencode (skll:auditoria) |

---

## Resumen ejecutivo

**ESTADO GENERAL: ACEPTABLE**

Atlas v4.1 está en release candidate sobre `atlas-v4.1-incremental-indexing`. Las funcionalidades del milestone (indexación incremental, ingestión web incremental, sistema Doctor/Healer/Launcher, limpieza de identidad) están implementadas y probadas con fixtures sintéticas.

**Fortalezas principales:**
- Arquitectura modular clara (Brain → Router → LLM → RAG)
- Test suite con fakes que no requieren ChromaDB real ni APIs externas
- Registro formal de deuda técnica
- Sistema de diagnóstico/reparación con dry-run por defecto
- Identidad pública limpiada de referencias personales

**Riesgos principales:**
- Acceso a LLMs no centralizado (Brain, digestion_worker y exam_mode tienen streams propios)
- Sin licencia (ATLAS-TD-018, bloqueante para distribución)
- Portabilidad no validada en entorno limpio
- Rutas personales residuales en fallbacks OCR/PDF (ATLAS-TD-021)

---

## Arquitectura detectada

| Capa | Componente |
|---|---|
| **Orquestación** | `core/brain.py` — streaming híbrido, historial deslizante, reglas temporales |
| **Clasificación** | `core/router.py` — clasificador LLM (5 agentes: general, estadistica, researcher, mentor, arquitecto) |
| **LLM Gateway** | `core/models.py` — gateway unificado (no totalmente adoptado) |
| **Config** | `core/config.py` — catálogo, detección HW, rutas, parámetros RAG |
| **RAG** | `core/vector_store.py` + `core/indexer.py` + `core/digestion_worker.py` |
| **Sistema** | `core/system/` — Doctor (diagnóstico), Healer (reparaciones dry-run), Launcher (arranque) |
| **Seguridad** | `core/security.py` — path traversal, prompt injection, log de eventos |
| **Chat sessions** | `core/chat_manager.py` — JSON persistente multi-sesión |
| **Interfaces** | CLI (`atlas_chat.py`), Streamlit (`atlas_ui.py`), FastAPI (`main_api.py`) |
| **Multimodal** | `core/vision.py`, `core/ocr.py`, `core/speech_input.py`, `core/speech_output.py` |

**Stack tecnológico:** Python 3.11–3.13, Ollama, NVIDIA NIM, Groq, ChromaDB, sentence-transformers, Streamlit, FastAPI.

---

## Problemas críticos

*Ninguno.*

---

## Problemas importantes

### P-I01 — Acceso a LLMs no centralizado

| Campo | Valor |
|---|---|
| **Severidad** | MEDIUM |
| **Archivos** | `core/brain.py`, `core/digestion_worker.py`, `core/exam_mode.py` |
| **Componente** | Arquitectura de LLM Gateway |
| **Descripción** | Tres módulos implementan sus propias llamadas directas a Ollama, NVIDIA y Groq, además del gateway en `core/models.py`. Cada uno tiene su propio timeout, temperatura y manejo de errores. |
| **Evidencia** | `brain.py:_stream_local`, `_stream_nube`, `_stream_groq`; `digestion_worker.py:_procesar_chunk_nvidia`, `_procesar_chunk_groq`, `_procesar_chunk_ollama`; `exam_mode.py:_preguntar_nvidia`. |
| **Impacto** | Un cambio en API de proveedor requiere parches en 3+ sitios; riesgo de divergencia. |
| **Recomendación** | Centralizar gradualmente en `core/models.py`; eliminar streams redundantes. |

### P-I02 — Licencia del proyecto pendiente

| Campo | Valor |
|---|---|
| **Severidad** | MEDIUM |
| **Archivo** | `README.md` (sección "Licencia") |
| **Componente** | Publicación / distribución |
| **Descripción** | README tiene badge de licencia y sección explícita que dice "pendiente". |
| **Evidencia** | README línea 334: *"La selección y publicación de una licencia continúan pendientes."* |
| **Impacto** | Impide distribución oficial. |
| **Recomendación** | Seleccionar licencia (MIT, Apache 2.0 o similar), crear LICENSE, actualizar README. |

---

## Problemas menores

### P-M01 — Rutas personales en fallbacks OCR/PDF

| Campo | Valor |
|---|---|
| **Severidad** | LOW |
| **Archivos** | `core/pdf_reader.py`, `diagnostico_ocr.py` |
| **Componente** | OCR / PDF |
| **Descripción** | Rutas con `C:\Users\delfa` en fallbacks para herramientas externas. |
| **Recomendación** | Usar variables de entorno o detección portable (shutil.which). |

### P-M02 — `reindexer` aceptado pero ignorado (ATLAS-TD-001)

| Campo | Valor |
|---|---|
| **Severidad** | LOW |
| **Archivo** | `core/web_crawler.py` — `WebCrawler.__init__` |
| **Descripción** | Parámetro `reindexer=` se acepta pero no se invoca. |
| **Recomendación** | Emitir deprecation warning cuando se provea `reindexer`. |

### P-M03 — Estado acumulado en WebCrawler (ATLAS-TD-002)

| Campo | Valor |
|---|---|
| **Severidad** | LOW |
| **Archivo** | `core/web_crawler.py` |
| **Descripción** | Contadores y colecciones se inicializan en constructor, no se reinician en segunda llamada a `crawl()`. |
| **Recomendación** | Documentar contrato de un solo uso o reiniciar estado por corrida. |

### P-M04 — Historial como variable global mutable

| Campo | Valor |
|---|---|
| **Severidad** | LOW |
| **Archivo** | `core/brain.py` — `HISTORIAL = []` (línea 41) |
| **Descripción** | El historial de conversación es una lista mutable a nivel de módulo. |
| **Recomendación** | Mover a clase con instancia o usar `contextvars`. |

### P-M05 — Identidad interna acoplada a `Perfil_Charly.md` (ATLAS-TD-014)

| Campo | Valor |
|---|---|
| **Severidad** | LOW |
| **Archivos** | `core/brain.py`, `core/memory_manager.py` |
| **Descripción** | `cargar_perfil_charly()` y ruta `Perfil_Charly.md` hardcodeadas. |
| **Recomendación** | Diseñar migración a perfil neutral en v4.2. |

---

## Fortalezas encontradas

### Atomicidad del manifiesto de indexación
`core/index_manifest.py` escribe `.tmp` → flush → fsync → `os.replace()`. Si el proceso falla a medio escribir, el archivo original nunca se corrompe.

### Contención de rutas con `Path.resolve()`
El indexador (`_resolver_contenida_en_base`) usa `pathlib.Path.resolve()` + `relative_to()` en vez de `startswith`. Esto previene bypass con symlinks, `..` maliciosos y prefijos tipo `Atlas_Memory_Evil`.

### Tests con fakes que no requieren infraestructura real
- `FakeCollection` reemplaza ChromaDB entera en memoria para tests de indexación.
- `FakeSession` reemplaza requests para tests del crawler.
- Los tests corren sin Ollama, sin APIs, sin ChromaDB, sin internet.

### Security module con defensas en profundidad
- Path traversal: `validar_ruta()` con `os.path.commonpath`
- Prompt injection: `sanitizar_contenido()` con 17 patrones bloqueados
- Log de seguridad dedicado con encoding robusto (`atlas_security.log`)
- Verificación de exposición de Ollama en red

### Type hints obligatorios en `core/system/`
Doctor, Healer, Launcher y result_types usan dataclasses tipadas y resultados `JSON-serializable`. Las reparaciones registran diagnóstico before/after.

### Registro de deuda técnica formal
`docs/TECHNICAL_DEBT.md` mantiene 21 entradas con ID, severidad, estado, componente, solución propuesta y prueba de aceptación. Cada resolución se vincula a un commit.

---

## Plan de acción

### Fase 1 — Bloqueantes (previo a publicación)

1. Resolver licencia (ATLAS-TD-018): crear LICENSE, actualizar README
2. Limpiar rutas personales residuales (ATLAS-TD-021): `core/pdf_reader.py`, `diagnostico_ocr.py`
3. Emitir deprecation warning para `reindexer` (ATLAS-TD-001)

### Fase 2 — Mantenimiento v4.1.x

4. WebCrawler: reiniciar estado por corrida o documentar single-use (ATLAS-TD-002)
5. WebCrawler/UI: mensaje claro cuando todas las indexaciones fallen (ATLAS-TD-003)
6. Tests de seguridad: cobertura para `security.py:validar_ruta`, `sanitizar_contenido`

### Fase 3 — Deuda arquitectónica

7. Centralizar acceso a LLMs (ARQ-DEBT-001): absorber streams de brain, digestion_worker y exam_mode en `core/models.py`
8. Migrar perfil de `Perfil_Charly.md` a nombre neutral (ATLAS-TD-014)

### Fase 4 — v4.2

9. Chat Session Exporter
10. Dashboard avanzado (CPU/RAM/GPU)
11. Validación de portabilidad en PC limpia

---

## Conclusión

Atlas v4.1 es un proyecto con **arquitectura sólida**, **implementación completa de sus funcionalidades core** y **test suite robusta**. El mayor activo técnico es la disciplina de cortes con evidencia en commits, tests y registro de deuda.

Los riesgos son manejables y están documentados. El proyecto puede continuar desarrollo hacia v4.2 sin necesidad de refactorización de base, siempre que se atienda la deuda arquitectónica del gateway LLM antes de que crezca.

**Estado: ACEPTABLE. No se detectaron blockers ni problemas HIGH.**
