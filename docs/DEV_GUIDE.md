# 🛠️ Developer Guide - Atlas v3.9

This guide provides the technical details necessary to extend and maintain Atlas.

## 1. Project Structure
- `core/`: The engine. All logic resides here.
- `agents/`: Specialized logic for complex task agents.
- `memory/`: User data and system prompts.
- `atlas_ui.py`: The Streamlit frontend.
- `atlas_chat.py`: The CLI frontend.

## 2. Extending the System

### Adding a New Agent
1. **Create a Prompt:** Add a new `.md` file in `memory/Atlas_Memory/00_Sistema/Prompts/` (e.g., `agente_analista.md`).
2. **Update the Router:** In `core/router.py`:
   - Add the agent name to the `AGENTES` list.
   - Update the `detectar_agente_con_modelo` prompt to describe when this agent should be used.
   - Update `cargar_prompt_agente` to map the name to your `.md` file.
3. **Update UI:** Add the agent to the help descriptions in `atlas_chat.py` or `atlas_ui.py`.

### Adding a New Document Loader
1. **Implement Reader:** In `core/universal_loader.py`, create a function `leer_[format](ruta_archivo)`.
2. **Register Extension:** Add the extension (e.g., `.odt`) to the `leer_archivo` detection logic.
3. **Update Requirements:** Add any necessary Python libraries to `requirements.txt`.

### Tuning the RAG
Adjust the following constants in `core/config.py`:
- `CHUNK_SIZE`: Number of characters per segment (Default: 500).
- `CHUNK_OVERLAP`: Overlap between segments to maintain context (Default: 100).
- `UMBRAL_SEMANTICO`: Threshold for hybrid search fallback.

## 3. Deployment & Maintenance
- **Updating Models:** Use `ollama pull <model>` and then update `MODELOS_LOCALES_DISPONIBLES` in `config.py` with the new metadata.
- **Security:** Any new file access must be passed through `core.security.validar_ruta()` to prevent path traversal attacks.
- **Performance:** For large-scale ingestion, use the `prometeo_worker.py` parallel processing logic.
