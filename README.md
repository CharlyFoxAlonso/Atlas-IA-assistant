# 🧠 Atlas v3.4 - AI Assistant System

<div align="center">

**Hybrid local/cloud AI Assistant with semantic RAG, specialized agents, persistent memory, and a comprehensive Streamlit UI**

[![Python](https://img.shields.io/badge/Python-3.11_/_3.12_/_3.13-blue.svg)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLMs-green.svg)](https://ollama.ai/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-red.svg)](https://streamlit.io/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
- [License](#-licence)

---

## 🎯 Description

Atlas is an **advanced AI assistant system** that seamlessly combines local models (100% privacy) with high-performance cloud APIs (maximum power). It implements:

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
│                       ATLAS v3.4 - CORE                     │
├─────────────────────────────────────────────────────────────┤
│  Router Model → Classifies intent & assigns specialized agent│
├─────────────────────────────────────────────────────────────┤
│  Dual-Engine Chat Execution                                 │
│  ├─ ATLAS (Local)  → Ollama (Qwen 3, Gemma 3, DeepSeek R1)  │
│  └─ PROMETEO (Nube) → NVIDIA NIM (Llama 3.3, DeepSeek V4)   │
├─────────────────────────────────────────────────────────────┤
│  Semantic RAG (ChromaDB) with Lazy-Loading                  │
│  ├─ Embeddings: paraphrase-multilingual-MiniLM-L12-v2       │
│  └─ Hybrid search: semantic + token-matching fallbacks      │
├─────────────────────────────────────────────────────────────┤
│  Dual Digestion Engine (Isolated process)                   │
│  ├─ Local Digestion: Ollama-based parsing & summarization    │
│  └─ Cloud Digestion: Parallel workers via NVIDIA NIM API    │
├─────────────────────────────────────────────────────────────┤
│  Multimodal Integration                                     │
│  ├─ Vision: Screen capture & layout-preserving Tesseract OCR │
│  ├─ Audio: Groq API (Whisper-large-v3) or local Vosk engine │
│  └─ Voice: Edge TTS synthesis or pyttsx3 offline fallback   │
├─────────────────────────────────────────────────────────────┤
│  Persistent Multi-Session UI (Streamlit v1.59)              │
│  ├─ Persistent chats saved as isolated JSON sessions        │
│  └─ Automated background reflection logging to diary files   │
└─────────────────────────────────────────────────────────────┘
```

---

## ⭐ Key Features

### 🧠 Advanced Semantic RAG
- Automatically indexes PDFs, DOCX, PPTX, TXT, MD, and images.
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

### 🔀 Hybrid Models & Dual-Digestion
- Chat and document ingestion are **decoupled**:
  - Chat via local Ollama models (`qwen3:8b`, `deepseek-r1:14b`) or cloud NVIDIA NIM APIs (`deepseek-v4-pro`, `llama-3.3-70b-instruct`).
  - Digestion (PDF ingestion) can run **locally** to keep sensitive files off the web, using your choice of downloaded Ollama models, or **in the cloud** using multi-threaded parallel workers for speed.

### 💾 Multi-Session Chat & Persistent Memory
- **Persistent Chat Tabs:** Create and delete conversations in the sidebar. Chat histories are saved as JSON files in `memory/Atlas_Memory/chats/` and survive app restarts.
- **Automated Reflection:** At the end of chat sessions, Atlas evaluates key milestones, insights, or personal progress, storing them directly in a markdown personal diary under `memory/Atlas_Memory/06_Diario/`.
- Dynamic rule interception using customizable temporary rule sets.

### 🛡️ Audited Security
- Path traversal verification using strict `os.path.commonpath` comparison.
- Prompt injection mitigation with configurable pattern filters.
- Native logger that captures security events and logs them in real-time.

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
   git clone https://github.com/CharlyFoxAlonso/Atlas-AI-assistant.git
   cd Atlas-AI-assistant
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
- `!memoria` - Force memory analysis on the active thread.
- `!ver_memoria` - Review saved markdown memory files.
- `!reglas` - View or add temporary behavior rules.
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
C:\Users\delfa\Documents\Atlas\
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

### v3.5 (Upcoming Minor Release)
- [ ] **EPUB & HTML support** inside `core/universal_loader.py`.
- [ ] **Chat Session Exporter:** Export the active chat to Markdown (`.md`) or structured PDF directly from the UI.
- [ ] **Prompt Playground:** Sandbox in the UI to test a single prompt against all downloaded local models simultaneously to evaluate responses.
- [ ] **Enhanced Dashboard:** Display real-time CPU, RAM, and GPU usage in the sidebar.

### v3.6 (Connectivity & Polish)
- [ ] **FastAPI Integration:** Introduce a lightweight local REST API to interact with Atlas from external platforms (e.g. custom Discord/Telegram clients).
- [ ] **Edge TTS Fine-Tuning:** Dropdown selector to choose specific regional voices and customize synthesis speech speed.
- [ ] **Global Profiler:** Exporting/importing profiles will bundle your saved chat sessions together with your documents.

### v3.7 (Stability & Resilience)
- [ ] Comprehensive unit test suites for the `digestion_worker.py` and JSON schema validators for saved chat sessions.
- [ ] Self-documenting commands index that automatically registers new `!` commands.

### v4.0+ (Long-Term Vision)
- [ ] **Secure Tool-Calling (Function-Calling):** Safe local function-calling utilizing an explicit, user-confirmed whitelist of tasks (e.g. search specific local folders, run math calculations) with absolutely **no unsafe shell-execution allowed**.

---

## 📄 Licence

This project is licensed under the MIT License. See [LICENSE](LICENSE) for more details.

*Designed by Charly in Tandil, Argentina*
