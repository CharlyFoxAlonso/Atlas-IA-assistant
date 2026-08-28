# 📖 User Guide - Atlas v4.1

Welcome to Atlas, your hybrid AI assistant. This guide will help you get started and master the system.

## 🚀 Quick Start

### 1. Launching the System
You have two ways to interact with Atlas:
- **Web UI (Recommended):** Double-click `run_ui.bat`. Its normal local `.venv` route uses `http://localhost:8401`; if that interpreter is absent and the launcher follows its `py` or global Streamlit fallback route, use `http://localhost:8501`.
- **Terminal (CLI):** Double-click `run.bat` for a lightweight interactive experience.

### 2. Using the Interface

#### The Sidebar (UI)
- **Chat Management:** Create new sessions or switch between previous ones.
- **Model Selector:** Choose your "Brain".
  - **Atlas (Local):** Fast, private, runs on your GPU/RAM.
  - **Prometeo (NVIDIA):** Extremely powerful, best for complex reasoning.
  - **Groq:** Ultra-fast, nearly instant responses.
- **Ingestion:** Drag and drop files to add them to your knowledge base (RAG).

#### The Crawler (Web Ingestion)
Under the **🌐 Ingesta Web** section, you can:
- **Single Page:** Ingest a specific PDF or webpage URL.
- **Intelligent Crawl:** Provide a root URL and a "Theme". Atlas will navigate the site, extract relevant pages based on the theme, and organize them into subfolders.

## ⌨️ Command Reference (CLI & UI)

Type these commands directly into the chat:

| Command | Description |
| :--- | :--- |
| `!ayuda` | Displays the full command list. |
| `!indexar` | Re-scans `memory/Atlas_Memory` to rebuild the semantic index. |
| `!indexar sync` | Synchronizes only new, modified, and deleted source files. |
| `!indexar status` | Runs the read-only index diagnosis and shows layer/writer state. |
| `!analizar` | Forces Atlas to analyze the current conversation for important memories. |
| `!categorias` | Lists all memory categories (University, Projects, etc.). |
| `!historial` | Shows the current session's interaction count. |
| `!limpiar_historial` | Wipes the current session's short-term memory. |
| `!modelos` | Lists all available local models and their status. |
| `!modelo_local [name]` | Switches the active local model (e.g., `!modelo_local qwen3:14b`). |
| `!descargar_modelo [name]` | Downloads a model via Ollama. |
| `!hardware` | Displays current RAM/VRAM and suggests the best model for your PC. |
| `!mirar` | Captures the screen and analyzes the text. |
| `!escuchar [sec]` | Records voice input for the specified duration. |
| `!autoconocer` | Generates a full technical report of the system architecture. |

### Controlled index repair

Repair is deliberately separate from chat and UI commands. Run the technical CLI
from the repository root:

```powershell
.venv\Scripts\python.exe -m core.system heal index_consistency
.venv\Scripts\python.exe -m core.system heal index_consistency --apply
```

The first command is a read-only preview. The second is the explicit consent to run
conservative repair under the single-writer lock and confirm it with a final
post-check. No startup, Doctor, `!indexar status`, or UI render repairs the index.

The status can be `HEALTHY`, `HEALTHY_EMPTY`, `DEGRADED`, `INCONSISTENT`, or
`UNAVAILABLE`. A planned `INCONSISTENT` preview exits `0`; a blocked `DEGRADED` or
`UNAVAILABLE` preview exits `1`; invalid arguments exit `2`; and a requested repair
that remains busy, blocked, partial, failed, or inconsistent exits `3`. Orphan
vectors are reported but never purged. User-facing output uses anonymous item
ordinals and safe reason/type codes rather than document identities, absolute paths,
or raw exception text.

## 💡 Tips for Better Results

### 1. Using Agents
Atlas automatically switches agents, but you can guide it:
- **For Math/Stats:** Ask specifically about "covariance", "probability", or "formulas".
- **For Academic Research:** Use "Summarize", "Explain", or "Compare" regarding laws or books.
- **For Personal Growth:** Share your achievements or feelings ("I'm proud that...").

### 2. Improving RAG
- Organize your files in `memory/Atlas_Memory/03_Conocimiento` using folders.
- Use clear filenames.
- After adding many files, run `!indexar sync`; reserve `!indexar` for an explicit
  full rebuild of known sources.
- Use `!indexar status` when you want to inspect consistency without changing the
  index.
