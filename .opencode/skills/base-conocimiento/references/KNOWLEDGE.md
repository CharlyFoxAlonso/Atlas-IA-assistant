# Base de Conocimiento — Conocimiento técnico

## Mapa de módulos

| Archivo | Rol |
|---|---|
| `core/vector_store.py` | Abstracción sobre ChromaDB: chunking, inserción, búsqueda semántica, búsqueda híbrida |
| `core/indexer.py` | Construye el índice semántico desde `memory/Atlas_Memory/` |
| `core/digestion_worker.py` | Procesa texto crudo → Markdown estructurado vía LLM (Ollama / NVIDIA / Groq) |
| `core/ingestion_manager.py` | Pipeline de ingesta web: descarga → digiere → archiva → re-indexa |
| `core/local_ingestion_manager.py` | Pipeline de ingesta local: archivo → detecta tipo → digiere → archiva → re-indexa |
| `core/universal_loader.py` | Lector universal: PDF, DOCX, PPTX, TXT, MD, imágenes (OCR), EPUB, HTML |
| `core/brain.py` | Orquestador: llama a `buscar_en_rag_semantico()` para agentes researcher y estadistica |
| `core/pdf_scraper.py` | Descarga y extrae texto de URLs (PDF, HTML, texto plano) |

## Pipeline de ingesta (web)

1. Usuario ingresa URL en UI (o API)
2. `ingestion_manager.procesar_pipeline_ingestion()` inicia
3. `pdf_scraper.validar_fuente()` + `descargar_y_extraer()` validan y extraen texto
4. `digestion_worker.digerir_documento_con_progreso()` envía raw text a LLM con `PROMPT_DIGESTION`
5. El LLM devuelve Markdown estructurado (título, resumen, conceptos, desarrollo, citas)
6. El resultado se archiva como `.md` en `memory/Atlas_Memory/` con frontmatter YAML
7. `indexer.construir_indice()` re-escanea toda la memoria y repuebla ChromaDB

## Pipeline de ingesta (local)

1. Usuario arrastra archivo en UI (o lo envía por API)
2. `local_ingestion_manager.procesar_archivo_local()` detecta tipo:
   - Multimedia (audio/video) → `audio_transcriber.transcribir_archivo()` vía Groq Whisper
   - Otros → `universal_loader.leer_archivo_con_info()`
3. Misma digestión, archivado y re-indexación que ingesta web

## Pipeline de consulta

1. `brain.buscar_en_rag_semantico(pregunta, ...)` es llamado desde `pensar_con_streaming()`
2. Para agente `researcher`: búsqueda híbrida (semántica + palabras clave) + búsqueda web
3. Para agente `estadistica`: solo búsqueda semántica
4. `vector_store.busqueda_hibrida()` ejecuta: búsqueda semántica → si resultados < umbral, reintenta con `buscar_por_nombre()`
5. Resultados formateados como texto con metadatos de origen

## Parámetros RAG

| Parámetro | Default | Descripción |
|---|---|---|
| `CHUNK_SIZE` | 500 | Tamaño de fragmento para chunking |
| `CHUNK_OVERLAP` | 100 | Solapamiento entre fragmentos |
| `N_RESULTS_DEFAULT` | 5 | Resultados por búsqueda |
| `UMBRAL_SEMANTICO` | 200 | Mínimo de caracteres para considerar resultados suficientes |
| `CHROMA_PATH` | `./vector_db` | Ruta de persistencia de ChromaDB |
| `COLLECTION_NAME` | `atlas_rag` | Nombre de la colección |

Nota: Estos valores están definidos tanto en `core/config.py` como en `core/vector_store.py`. Los efectivos son los de `vector_store.py`.

## Invariantes

- ChromaDB se inicializa perezosamente (no al importar, sí al primer uso)
- `_get_collection()` maneja migraciones automáticas: si el formato de DB es incompatible, respalda y crea DB fresca
- La ingestión es asíncrona desde la perspectiva del chat; el usuario puede seguir preguntando mientras se digiere
- `construir_indice()` falla silenciosamente (log + continue) sin detener el pipeline
- El embedding usa `paraphrase-multilingual-MiniLM-L12-v2` (multilingüe, 384 dimensiones)

## Riesgos conocidos

- **ChromaDB corrupta**: Si la base se corrompe, hay que borrar `vector_db/` y re-indexar con `!indexar`
- **Embedding lento en primera llamada**: `sentence-transformers` carga el modelo (~500MB) al primer `_get_collection()`
- **Documentos sin chunks**: Si un documento tiene solo texto corto (< 50 chars) o chunks < 20 chars, no se indexa
- **Límite de documentos grandes**: Textos > 80K chars se parten en chunks de 80K para digestión paralela
- **Modelo de digestión no disponible**: Para motor `atlas`, se verifica que el modelo exista en Ollama antes de empezar; si no, se notifica al usuario
- **Re-indexación costosa**: `construir_indice()` recorre TODO `Atlas_Memory/`, no solo archivos nuevos
- **Sin tests**: No existen tests unitarios para `vector_store.py`, `indexer.py` ni `digestion_worker.py`
