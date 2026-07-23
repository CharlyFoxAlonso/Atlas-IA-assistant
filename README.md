# 🧠 Atlas v4.1 - AI Assistant System

<div align="center">

**Hybrid local/cloud AI Assistant with semantic RAG, specialized agents, persistent memory, and a comprehensive Streamlit UI**

[![Python](https://img.shields.io/badge/Python-3.11_/_3.12_/_3.13-blue.svg)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLMs-green.svg)](https://ollama.ai/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-red.svg)](https://streamlit.io/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)

</div>

---

## 📋 Table of Contents

- [Description](#-description)
- [Architecture](#-architecture)
- [Key Features](#-key-features)
- [Technologies](#-technologies)
- [Installation & Setup](#-installation)
- [Usage](#-usage)
- [Streamlit Interface](#-streamlit-interface)
- [Use Cases](#-use-cases)
- [Project Structure](#-structure-of-the-project)
- [Roadmap (Sane & Realistic)](#-roadmap)
- [Licencia](#-licencia)

---

## 🎯 Description

Atlas is an **advanced AI assistant system** that seamlessly combines local models (100% privacy) with high-performance cloud APIs (maximum power). It implements:

Atlas v4.1 is currently a **release candidate**.

- **Semantic RAG (Retrieval-Augmented Generation)** powered by ChromaDB for contextual document search.
- **Intelligent multi-agent system** with dynamic intent routing based on user input.
- **Persistent cross-session memory** of conversations and user context.
- **Multimodal processing** including screenshot vision, OCR, and audio/video transcription.
- **Self-awareness metrics** and internal system reporting.
- **Advanced Streamlit UI** with multiple persistent chat tabs, real-time model hot-swapping, and an isolated document digestion engine.

### Why Atlas?

Most AI assistants are opaque black boxes. Atlas is engineered to be:
- **Transparent:** Always know which agent and model is responding, along with the reasoning (thought) process.
- **Hybrid:** Sensitive data remains local (using Ollama), while complex tasks can leverage high-performance cloud models.
- **Extensible:** Modulate behavior by placing markdown prompts (`.md`) directly in system folders.
- **Context-Aware:** Remembers conversations, notes preferences, and populates a personal diary over time.
- **User-Friendly:** Simple batch launching scripts and clean web interface.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       ATLAS v4.1 - CORE                     │
├─────────────────────────────────────────────────────────────┤
│  Router Model → Classifies intent & assigns specialized agent│
├─────────────────────────────────────────────────────────────┤
│  Dual-Engine Chat Execution                                 │
│  ├─ ATLAS (Local)  → Ollama (Qwen 3, Gemma 3, DeepSeek R1)  │
│  └─ CLOUD (Nube)   → NVIDIA NIM / Groq Cloud API            │
├─────────────────────────────────────────────────────────────┤
│  Semantic RAG (ChromaDB) with Lazy-Loading                  │
│  ├─ Embeddings: paraphrase-multilingual-MiniLM-L12-v2      │
│  └─ Hybrid search: semantic + token-matching fallbacks      │
├─────────────────────────────────────────────────────────────┤
│  Triple Digestion Engine (Isolated process)                   │
│  ├─ Local Digestion: Ollama-based parsing & summarization    │
│  ├─ Cloud (Prometeo): Parallel workers via NVIDIA NIM API    │
│  └─ Cloud (Groq): Ultra-fast processing via Groq Cloud       │
├─────────────────────────────────────────────────────────────┤
│  Multimodal Integration                                     │
│  ├─ Vision: Screen capture & layout-preserving Tesseract OCR │
│  ├─ Audio: Groq API (Whisper-large-v3) or local Vosk engine │
│  └─ Voice: Edge TTS synthesis or pyttsx3 offline fallback   │
├─────────────────────────────────────────────────────────────┤
│  Persistent Multi-Session UI (Streamlit)                    │
│  ├─ Persistent chats saved as isolated JSON sessions        │
│  └─ Automated background reflection logging to diary files   │
└─────────────────────────────────────────────────────────────┘
```

---

## ⭐ Key Features

### 🧠 Advanced Semantic RAG
- Automatically indexes PDFs, DOCX, PPTX, TXT, MD, and images.
- **Incremental indexing (v4.1):** ingesting a new file indexes only that file — it no longer rebuilds the whole library. A local manifest (`vector_db/index_manifest.json`) tracks each document's SHA-256, so unchanged files are never re-read or re-embedded, modified files are re-indexed individually, and deleted files are removed from the index.
- `!indexar` keeps its meaning: an explicit **full rebuild**. `!indexar sync` runs the **incremental synchronization** (new/modified/deleted only).
- Implements smart chunking with chapter and section boundary detection.
- Uses **lazy-loaded ChromaDB & SentenceTransformers** to keep memory footprint light and start times ultra-fast.
- Fallback text search using contextual score matching when vector DB is uninitialized.

### 🤖 Multi-Agent Routing
- **Classifier Model:** Evaluates prompts and assigns them to specialized agents:
  - `general`: Casual conversations and broad knowledge.
  - `estadistica`: Advanced mathematical analysis, covariance, variance, and formula explanations.
  - `researcher`: Academic search, legal/constitutional exploration, and web queries.
  - `mentor`: Relational coaching, achievements, and habit tracking.
  - `arquitecto`: Structural system design and code refactoring.
- Dynamic emotion and academic intent classification.

### 🔀 Hybrid Models & Triple-Digestion
- Chat and document ingestion are **decoupled**:
  - Chat via local Ollama models (`qwen3:8b`, `deepseek-r1:14b`) or high-performance cloud APIs: **NVIDIA NIM** (`deepseek-v4-pro`, `llama-3.3-70b-instruct`) and **Groq Cloud** (`llama-3.3-70b-versatile`).
  - Digestion (PDF ingestion) can run **locally** to keep sensitive files off the web, or in the cloud using either **NVIDIA NIM** (multi-threaded parallel workers) or **Groq Cloud** (ultra-fast processing), with a dynamic model selector in the UI.

### 💾 Multi-Session Chat & Persistent Memory
- **Persistent Chat Tabs:** Create and delete conversations in the sidebar. Chat histories are saved as JSON files in `memory/Atlas_Memory/chats/` and survive app restarts.
- **Automated Reflection:** At the end of chat sessions, Atlas evaluates key milestones, insights, or personal progress, storing them directly in a markdown personal diary under `memory/Atlas_Memory/06_Diario/`.
- Dynamic rule interception using customizable temporary rule sets.

### 🛡️ Security Controls
- Path traversal verification using strict `os.path.commonpath` comparison.
- Prompt injection mitigation with configurable pattern filters.
- Native logger that captures security events and logs them in real-time.

---

## 🔧 Changelog

### v4.1 — Release candidate
- **Incremental local indexing:** new and modified files are indexed individually; `!indexar sync` reconciles additions, updates, deletions, unchanged files, and failures through the SHA-256 manifest.
- **Incremental web ingestion:** crawler artifacts are indexed per saved document, without rebuilding the full library.
- **EPUB and HTML:** `core/universal_loader.py` supports both formats.
- **Prompt Playground:** the Streamlit UI can compare one prompt across available local models.
- **Basic dashboard:** the UI exposes current system and RAG metrics. Advanced observability remains partial.
- **Runtime foundation:** `core/system` provides Doctor, Healer, Launcher, typed results, dry-run defaults, and a technical CLI.
- **Version identity:** technical metadata uses `4.1.0`; visible product labels use `Atlas v4.1`.
- **Pending:** Chat Session Exporter, advanced dashboard completion, and v4.1.x crawler follow-ups listed in the roadmap.

---

## 🔧 Changelog v3.9 (historical)

### New Features
- **Web Crawler (`core/web_crawler.py`)**: Intelligent web crawling engine with theme-based filtering, automatic subfolder organization, and configurable page limits. Integrated into the Streamlit UI sidebar under "Rastreo Inteligente".
- **Timer display in UI**: All ingestion operations (web, local, crawler) now show elapsed time during processing.

### Bugfixes
- **`core/models.py`**: Fixed hardcoded local model (`qwen3:8b`) to use `MODELO_LOCAL` from `config.py`. The router now respects user model changes.
- **`main_api.py`**: Added missing `MODELO_GROQ_DEFAULT` import. Groq motor in API no longer throws `NameError`.
- **`core/self_awareness.py`**: Fixed internal version metadata (2.9 → 3.9), corrected invalid imports (`ddgs` → `duckduckgo_search`, `python-dotenv` → `dotenv`), removed phantom dependencies (`pdfplumber`, `sounddevice`).
- **`core/config.py`**: Updated hardware recommendation for 24GB+ VRAM to reference models actually available in the catalog.
- **`atlas_chat.py`**: `MODELO_NUBE_ACTIVO` now pulls from `config.py` instead of hardcoded value. Agent name in help text changed from obsolete "Psicólogo" to "Mentor".
- **`core/chat_manager.py`**: Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)`.
- **`core/self_improvement.py`**: Moved `urllib.parse.urlparse` import to module level.
- **`core/vector_store.py`**: Removed redundant `import os` inside `_get_collection()`.

### Version Sync
- All 30+ source files, launchers, and documentation now reference v3.9 consistently (previously had mixed v3.4/v3.7/v3.8 references).

---

## 🛠️ Technologies

### Core & Frameworks
- **Python 3.11 / 3.12 / 3.13** (Fully compatible and verified setup).
- **Streamlit 1.59+** for the web interface.
- **Ollama** for local inference.
- **NVIDIA NIM API** for cloud-accelerated inference.

### Data & Retrieval
- **ChromaDB 0.5.23+** (Vector database).
- **sentence-transformers** (Model: `paraphrase-multilingual-MiniLM-L12-v2`).
- **numpy** / **pandas** for structural indexing.

### Document Processing
- **pypdf** / **pdf2image** / **pytesseract** / **python-docx** / **python-pptx** / **Pillow**.

### Audio & Interface
- **Groq API** (Whisper-large-v3) & local **Vosk** engine for speech input.
- **Edge TTS** & **pyttsx3** for natural voice feedback.
- **Pygame** / **PyAudio** / **PyAutoGUI** for capture and audio routing.

---

## 📦 Installation

To ensure maximum package compatibility and avoid compilation issues, we recommend installing the project within a virtual environment using **Python 3.13**.

### Sane Steps (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/CharlyFoxAlonso/Atlas-IA-assistant.git
   cd Atlas-IA-assistant
   ```

2. **Create the environment and install dependencies:**
   Follow our detailed [SETUP.md](SETUP.md) guide:
   ```cmd
   py -3.13 -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

3. **Configure API Keys:**
   Create a `.env` file in the root directory:
   ```ini
   NVIDIA_API_KEY=your_nvidia_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ATLAS_OCR_LANG=spa
   POPPLER_PATH=C:\Program Files\poppler\bin
   ```

---

## 💡 Usage

### Launches (Batch Scripts)
No need to remember long terminal commands. Use the pre-configured launchers:

- **Web interface (Streamlit):**
  Simply double-click `run_ui.bat` or run:
  ```cmd
  .\run_ui.bat
  ```
- **CLI Chat (Terminal):**
  Simply double-click `run.bat` or run:
  ```cmd
  .\run.bat
  ```

### CLI System Commands
When using the terminal or chat input, you can type special commands starting with `!`:
- `!ayuda` or `!help` - Display available commands.
- `!indexar` - Rebuild the semantic RAG index from `memory/Atlas_Memory/`.
- `!analizar` - Force memory analysis on pending conversations.
- `!categorias` - List available memory categories.
- `!modelos` - View and manage downloaded Ollama models.
- `!autoconocer` - Generate a detailed system architecture report.

---

## 🎨 Streamlit Interface

The web UI is divided into intuitive sections:
1. **🗂️ Chats Sidebar:** Add, select, and remove independent conversation sessions.
2. **📊 System Metrics:** Live counters showing chat messages, long-term memory points, and vector database chunks.
3. **⚙️ Configuration Panels:** Independent selectors for Chat Engine (Local/Nube) and **Digestion Engine** (allowing you to process documents offline).
4. **👁️👂 Sentidos (Sensory Inputs):** Single-click screen capture, OCR processing, and voice recording.
5. **Drag-and-Drop Ingestion:** Effortlessly drop PDFs, audios, or videos, select a destination folder, and process them directly into your RAG pipeline.

---

## 📁 Structure of the Project

```
<ruta-del-repo>\
├── run.py                 # Core wrapper for launching the CLI
├── run.bat                # CLI launcher batch (auto-activates venv)
├── run_ui.bat             # UI launcher batch (auto-activates venv)
├── atlas_chat.py          # Main CLI chat loop and command parser
├── atlas_ui.py            # Streamlit UI dashboard
├── requirements.txt       # Unified project dependency file
├── SETUP.md               # Quick-setup guide for new machines
├── core/                  # Engine logic and utility modules
│   ├── brain.py           # Stream orchestrator and prompt synthesis
│   ├── chat_manager.py    # Multi-session JSON persistent manager
│   ├── digestion_worker.py# Unified Local & Cloud document digestor
│   ├── config.py          # Centralized configs and hardware detection
│   ├── models.py          # Remote & local API communication handlers
│   ├── vector_store.py    # Lazy-initialized ChromaDB vector engine
│   ├── security.py        # Log rotation, path traversal, injection filters
│   ├── universal_loader.py# Structural document extractor (PDF/Docx/Pptx/Img)
│   ├── audio_transcriber.py# FFmpeg audio conversion & Groq Whisper transcriptions
│   ├── pdf_reader.py      # PDF parser with direct and OCR-fallback modes
│   └── diary_manager.py   # Date-based personal diary compiler
└── memory/                # Persistent directories (Git ignored)
    └── Atlas_Memory/      
        ├── 00_Sistema/    # Global system prompts
        ├── 01_Perfil/     # User identity and profile parameters
        ├── 03_Conocimiento/# Files actively scanned by the RAG indexer
        └── chats/         # Saved JSON chat sessions
```

---

## 🗺️ Roadmap

We prioritize maintaining a secure, lightweight, and robust assistant over "feature creep". Here is our realistic development timeline:

### v4.1 (Release candidate)

Completed:
- [x] Incremental local indexing and synchronization.
- [x] Incremental web/crawler ingestion.
- [x] EPUB and HTML loading.
- [x] Prompt Playground.
- [x] Basic system and RAG dashboard.

Partial:
- [~] **Advanced dashboard:** basic metrics exist; expanded CPU, RAM, GPU, and operational views remain pending.

### v4.1.x technical follow-ups
- [ ] **L1 / ATLAS-TD-001:** make the ignored crawler `reindexer` compatibility parameter explicit.
- [ ] **L2 / ATLAS-TD-002:** define or reset crawler state when an instance is reused.
- [ ] **L3 / ATLAS-TD-003:** clarify the UI summary when saved artifacts remain pending indexing.

### v3.6 (Connectivity & Polish)
- [x] **FastAPI Integration:** Lightweight local REST API to interact with Atlas from external platforms.
- [x] **Edge TTS Fine-Tuning:** Dropdown selector to choose specific regional voices.
- [x] **Global Profiler:** Exporting/importing profiles bundled with saved chat sessions.

### v3.7 (Stability & Resilience)
- [x] **Groq Cloud Integration:** Full support for ultra-fast inference and document digestion.
- [x] **Dynamic Model Selection:** Unified selector for cloud models in both chat and ingestion engines.
- [x] **System-wide Consistency:** Centralized model defaults and synchronized versioning.
- [x] **RAG Stability:** Enhanced error handling and validation in the digestion worker.

### v4.2
- [ ] **Chat Session Exporter:** export the active chat to Markdown or structured PDF.
- [ ] Complete the advanced dashboard.
- [ ] Design a compatible migration from internal personal profile identifiers.
- [ ] Select and publish a project license.

### Long-Term Vision
- [ ] **Secure Tool-Calling (Function-Calling):** Safe local function-calling utilizing an explicit, user-confirmed whitelist of tasks (e.g. search specific local folders, run math calculations) with absolutely **no unsafe shell-execution allowed**.

---

## 📄 Licencia

La selección y publicación de una licencia continúan pendientes.

*Designed by Charly in Tandil, Argentina*
