# Configuración del Sistema — Conocimiento técnico

## Mapa de módulos

| Archivo | Rol |
|---|---|
| `core/system/__init__.py` | API pública: exporta `diagnosticar_sistema`, `Healer`, `Launcher`, `launch_atlas` |
| `core/system/__main__.py` | CLI técnico: `python -m core.system {doctor, heal, launch}` |
| `core/system/doctor.py` | Diagnóstico read-only. Nunca modifica el sistema |
| `core/system/healer.py` | Reparaciones. Dry-run por defecto (requiere `--apply`) |
| `core/system/launcher.py` | Coordinador de arranque: diagnostica → repara (opcional) → lanza |
| `core/system/paths.py` | Resolución de rutas (dev vs packaged). Sin I/O |
| `core/system/command_runner.py` | Ejecución segura de subprocesos con redacción de secretos |
| `core/system/result_types.py` | Dataclasses serializables: `CheckResult`, `DiagnosisResult`, `RepairResult`, etc. |
| `core/system/operational_log.py` | Auditoría JSON rotativa con sanitización de secretos |
| `core/config.py` | Catálogo de modelos, parámetros RAG, detección HW |
| `scripts/backup_atlas.py` | Backup ZIP de código, memoria, vectores y configuración |
| `scripts/restaurar_atlas.py` | Restauración desde backup ZIP |
| `scripts/limpiar_para_distribuir.py` | Crea copia limpia sin datos personales |
| `scripts/crear_distribucion.py` | Orquesta limpieza + empaquetado para distribución |

## Resolución de rutas (AtlasPaths)

**Modo development** (default, `sys.frozen = False`):
- `project_root` = raíz del repositorio
- `data_dir` = `$ATLAS_DATA_DIR` o `project_root`
- `memory_dir` = `$ATLAS_MEMORY_DIR` o `data_dir/memory/Atlas_Memory`
- `config_dir` = `project_root`
- `chroma_dir` = `data_dir/vector_db`

**Modo packaged** (`sys.frozen = True`):
- `project_root` = directorio del ejecutable
- `data_dir` = `$ATLAS_DATA_DIR` o `%LOCALAPPDATA%/Atlas`
- `memory_dir` = `$ATLAS_MEMORY_DIR` o `data_dir/memory`
- `config_dir` = `%APPDATA%/Atlas`

**12 directorios gestionados:** `program_dir`, `project_root`, `data_dir`, `private_memory_dir`, `chroma_dir`, `config_dir`, `cache_dir`, `logs_dir`, `downloads_dir`, `temp_dir`, `managed_bin_dir`, `models_dir`

## Composición de doctor.py

- `diagnosticar_sistema()` devuelve dict con: `health_score`, `ready_to_start`, `critical_issues`, `warnings`, `recommendations`, `capabilities`, `system`, `python`, `cpu`, `ram`, `disk`, `gpu`, `ollama`, `python_packages`, `dependencies`, `environment`, `folders`
- Detecta 21 paquetes Python vía `importlib.find_spec`
- Detecta 4 herramientas externas: `tesseract`, `pdftoppm`, `ffmpeg`, `git`
- Derivates 15 capabilities booleanas (ej: `local_llm`, `ocr`, `rag`, `web_search`)
- Health score 0-100: critical=15pts, recommended=5pts, optional=1pt

## Composición de healer.py

**Componentes clasificados por riesgo:**

| Componente | Riesgo | Acción |
|---|---|---|
| `folders` | safe | Crear directorios faltantes |
| `config` | safe | Crear `.env` mínimo (sin API keys) |
| `venv` | safe | Verificar runtime privado |
| `ollama_service` | moderate | Iniciar `ollama serve` |
| `python_packages` | heavy | `pip install -r requirements.txt` |
| `ollama_model` | heavy | `ollama pull <modelo>` |

- Dry-run por defecto. `--apply` requiere consentimiento explícito
- Heavy requiere `--apply` + `--allow-heavy`
- `Launcher` solo auto-delega componentes safe

## Variables de entorno (.env)

| Variable | Default | Propósito |
|---|---|---|
| `MOTOR_POR_DEFECTO` | `atlas` | Motor por defecto |
| `MODELO_LOCAL` | `qwen3:8b` | Modelo Ollama local |
| `URL_OLLAMA` | `http://127.0.0.1:11434/api/chat` | Endpoint Ollama |
| `MODELO_NUBE` | `meta/llama-3.1-70b-instruct` | Modelo NVIDIA NIM |
| `MODELO_GROQ` | `llama-3.3-70b-versatile` | Modelo Groq |
| `NVIDIA_API_KEY` | — | API key NVIDIA |
| `GROQ_API_KEY` | — | API key Groq |
| `TAVILY_API_KEY` | — | API key Tavily |
| `SEARXNG_URL` | — | URL SearXNG |
| `POPPLER_PATH` | — | Ruta a Poppler (PDF OCR) |

## Invariantes del sistema

- **Doctor nunca repara** — Es read-only. Devuelve JSON serializable
- **Healer requiere consentimiento** — `--apply` para cambios reales; `--allow-heavy` adicional para instalaciones
- **Launcher no auto-repara heavy** — Solo componentes safe pueden auto-delegarse
- **Paths es puro** — `paths.py` nunca toca el filesystem
- **Secretos redactados en logs** — Tanto `command_runner` como `operational_log` sanitizan datos sensibles
- **Resultados JSON-serializables** — Todas las dataclasses heredan de `SerializableResult.to_dict()`
- **Dependencias inyectables** — Doctor, Healer y Launcher aceptan dependencias para testing
- **CLI separado de lógica** — `__main__.py` solo maneja argumentos y formato de salida
