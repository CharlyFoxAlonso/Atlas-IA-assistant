---
name: base-conocimiento
# domain: sistema RAG, ChromaDB, embeddings, indexación, digestión, ingesta
type: domain
description: |
  Sistema RAG y adquisición de conocimiento de Atlas: ChromaDB, embeddings, indexación,
  digestión, carga de documentos, búsqueda web y crawling.
  Usar al trabajar con documentos, búsqueda semántica, ingesta o recuperación de conocimiento.
  No usar para modificar la orquestación central, interfaces de usuario ni instalación del sistema.
---

# Base de Conocimiento

## Propósito

Mantener y mejorar el pipeline de conocimiento de Atlas: indexación semántica, digestión de documentos, búsqueda híbrida, crawling web e ingesta de contenido.

## Cuándo usarla

- El usuario menciona RAG, ChromaDB, embeddings, búsqueda semántica, indexar, ingesta, digestión
- El usuario pide agregar, modificar o depurar el pipeline de conocimiento
- El usuario reporta resultados de búsqueda incorrectos, vacíos o lentos
- El usuario solicita ingerir documentos (web, archivos locales, drag & drop)
- El usuario pregunta por el estado de la base de conocimiento

## Cuándo no usarla

- Respuestas incorrectas por orquestación o enrutamiento → `nucleo-atlas`
- Interfaz de ingesta en UI o comandos CLI → `interfaz-usuario`
- Instalación o dependencias de ChromaDB/sentence-transformers → `configuracion-sistema`

## Workflow

1. **Diagnosticar** — Si hay problemas de búsqueda, verificar: estado de ChromaDB (`!stats`), colecciones, chunks indexados
2. **Identificar** — Localizar el punto exacto del pipeline afectado: consulta (`vector_store`), indexación (`indexer`), digestión (`digestion_worker`), ingesta (`ingestion_manager`), carga de archivos (`universal_loader`)
3. **Leer** — Si no conoces la arquitectura del pipeline, lee `references/KNOWLEDGE.md` antes de modificar
4. **Modificar** — Aplicar el cambio en el archivo correspondiente
5. **Re-indexar** — Siempre ejecutar `!indexar` después de cambios en el pipeline de indexación
6. **Validar** — Probar con una consulta que active RAG (ej: "¿Qué dice el documento X?")

## Checklist rápido

- [ ] Los parámetros RAG (`CHUNK_SIZE`, `CHUNK_OVERLAP`, etc.) se modifican tanto en `config.py` como en `vector_store.py` si aplica
- [ ] `agregar_documento()` elimina chunks existentes con mismo `nombre` antes de insertar (evita duplicados)
- [ ] `construir_indice()` recorre TODO `Atlas_Memory/`, no solo archivos nuevos
- [ ] La digestión con motor `atlas` requiere que el modelo exista en Ollama
- [ ] La función `_get_collection()` maneja migraciones automáticas de ChromaDB
- [ ] No hay tests unitarios para estos módulos; validar manualmente después del cambio

## Gotchas / Riesgos

- **ChromaDB corrupta**: Forzar respaldo automático, pero si falla hay que borrar `vector_db/` y re-indexar
- **Carga lenta**: `sentence-transformers` carga ~500MB en RAM al primer uso de ChromaDB
- **Doble fuente de parámetros**: `CHUNK_SIZE` y similares están en `config.py` y `vector_store.py`; los efectivos son los de `vector_store.py`
- **Ingesta sin red**: La digestión requiere LLM — si es remoto, necesita internet; si es local, necesita Ollama

## Relaciones

- `nucleo-atlas` → Si el cambio afecta cómo brain.py consulta el RAG (`buscar_en_rag_semantico()`)
- `interfaz-usuario` → Si se exponen nuevos comandos o UI para ingesta/consulta
- `configuracion-sistema` → Si se requieren dependencias nuevas (ChromaDB, sentence-transformers, etc.)
- `multimodal` → Si la ingesta incluye archivos multimedia (transcripción vía Groq Whisper)

## Archivos relacionados

- `references/KNOWLEDGE.md` — Mapa de módulos, pipeline detallado, parámetros, invariantes, riesgos

## Validación

- **vector_store.py** → `!stats` confirma chunks y colección. Buscar un documento conocido
- **indexer.py** → `!indexar` ejecuta re-indexación. Verificar en logs que no haya errores
- **digestion_worker.py** → Probar digestión desde UI con URL o archivo pequeño
- **ingestion_manager.py** → Ingerir URL de prueba y verificar que aparece en `!stats` + búsqueda
- **universal_loader.py** → Cargar archivos de cada tipo soportado (PDF, DOCX, PPTX, TXT, imagen)
