# Atlas — Project Manifest

**Propósito:** Asistente AI híbrido (local/nube) con RAG semántico, búsqueda web, voz, visión y memoria persistente.

## Mission

Atlas es un asistente personal de inteligencia artificial diseñado para evolucionar durante años manteniendo una arquitectura modular, extensible y sostenible.

Toda modificación debe priorizar:
* simplicidad
* mantenibilidad
* bajo acoplamiento
* reutilización
* compatibilidad hacia atrás

## Technology Stack

Python 3.11–3.13 · Ollama / NVIDIA NIM / Groq · Streamlit · FastAPI
ChromaDB + sentence-transformers · pypdf / docx / pptx / Tesseract / Pillow
Groq Whisper / Vosk / Edge TTS / pyttsx3 · DuckDuckGo / Tavily / SearXNG

## Entry Points

`python run.py` — CLI interactivo
`streamlit run atlas_ui.py` — UI web
`uvicorn main_api:app --reload` — API REST
`python -m core.system` — CLI técnico (doctor/heal/launch)

## Key Directories

`core/` — Brain, router, models, config, RAG, memoria, seguridad, multimodal
`core/system/` — Doctor, healer, launcher, paths, logs, command runner
`agents/` — Stats researcher, export study
`tests/` — Tests unitarios (unittest)
`scripts/` — Backup, restore, distribución
`docs/` — Arquitectura, RFCs, guías de instalación
`memory/` — Datos de usuario, perfiles, diario (gitignored)
`vector_db/` — ChromaDB persistente (gitignored)

## Core Components

**Brain** (`core/brain.py`): Orquestador con streaming híbrido, historial deslizante, reglas temporales
**Router** (`core/router.py`): Clasificador LLM (general, estadistica, researcher, mentor, arquitecto)
**Models** (`core/models.py`): Gateway unificado Ollama / NVIDIA / Groq
**Config** (`core/config.py`): Catálogo de modelos, detección HW, rutas, parámetros RAG
**RAG** (`core/vector_store.py` + `core/indexer.py` + `core/digestion_worker.py`): ChromaDB, embeddings multilingües, chunking, búsqueda híbrida
**System** (`core/system/`): Diagnóstico read-only (doctor), reparaciones dry-run (healer), arranque (launcher)

## Conventions

- Type hints: obligatorios en `core/system/`, recomendados en el resto
- Docstrings: estilo Google
- Español en UI/mensajes · Inglés en APIs internas (mantener mezcla existente)
- Dry-run por defecto: healer y launcher requieren `--apply`

## Environment Variables (`.env`)

`NVIDIA_API_KEY` · `GROQ_API_KEY` · `TAVILY_API_KEY`
`MODELO_LOCAL` (default: qwen3:8b) · `MOTOR_POR_DEFECTO` (atlas/prometeo/groq)
`URL_OLLAMA` (default: http://127.0.0.1:11434) · `SEARXNG_URL`

## Design Principles

- Local-first
- Privacy-first
- Modular architecture
- Provider-agnostic
- Streaming by default
- Explicit over implicit
- Fail safely

## Architectural Invariants

- **Interfaces contain orchestration, not core domain logic.** UI, CLI, and API delegate to core/ for thinking, searching, classifying, and vector operations.
- **LLM provider access is NOT fully centralized.** Brain, digestion_worker, and exam_mode implement their own streaming or direct calls to Ollama, NVIDIA, and Groq alongside the models.py gateway. This is known architectural debt.
- **System repairs default to dry-run.** Healer and launcher require explicit `--apply` to modify the system.
- **Personal data and vector DB remain local.** Both `memory/` and `vector_db/` are gitignored with no sync mechanism.
