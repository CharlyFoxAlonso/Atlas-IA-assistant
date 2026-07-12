# 🏗️ Architecture Guide - Atlas v3.9

Atlas is a hybrid AI orchestration system designed to balance high-performance cloud inference with absolute local privacy.

## 1. High-Level Overview

The system follows a **Modular Orchestration Pattern**. Instead of a simple prompt-response loop, Atlas uses a "Brain" (`core/brain.py`) that manages context, intent, and retrieval before interacting with an LLM.

### System Flow
`User Input` $\rightarrow$ `Interface (UI/CLI/API)` $\rightarrow$ `Brain` $\rightarrow$ `Router` $\rightarrow$ `Context Assembly` $\rightarrow$ `LLM Engine` $\rightarrow$ `Response`

## 2. Core Components

### 🧠 The Brain (`core/brain.py`)
The orchestrator. It manages:
- **History:** Maintains a sliding window of the last $N$ interactions.
- **Rule Interception:** Applies temporary user-defined rules before the prompt reaches the model.
- **Contextualization:** Integrates User Profile, Agent Identity, and RAG results.
- **Streaming:** Handles real-time token delivery across different backends.

### 🚦 Intelligent Router (`core/router.py`)
The router uses a lightweight LLM call to classify the user's intent into one of five specialized agents:
- **General:** Broad knowledge and casual chat.
- **Estadística:** Mathematical and statistical analysis.
- **Researcher:** Deep academic search, legal/constitutional analysis.
- **Mentor:** Emotional support, habit tracking, and personal growth.
- **Arquitecto:** Meta-cognitive reasoning and structural design.

### 📚 Semantic RAG Pipeline (`core/vector_store.py`, `core/indexer.py`)
Atlas implements a **Retrieval-Augmented Generation** pipeline:
1. **Universal Loading:** Extracts text from PDF, DOCX, PPTX, HTML, and Images (via OCR).
2. **Smart Chunking:** Splits text into overlapping segments, detecting chapter boundaries.
3. **Vectorization:** Uses `paraphrase-multilingual-MiniLM-L12-v2` for dense embeddings.
4. **Storage:** Persists vectors in **ChromaDB**.
5. **Hybrid Retrieval:** Combines semantic cosine similarity with metadata filtering (e.g., specific chapters).

## 3. Inference Engines

Atlas supports three distinct backends for flexibility:
- **Atlas Local:** Powered by **Ollama**. 100% private, runs on local hardware.
- **Prometeo Cloud:** Powered by **NVIDIA NIM**. High-performance, industrial-grade models.
- **Groq Cloud:** Powered by **Groq LPU**. Ultra-low latency for real-time applications.

## 4. Data Persistence
- **Chats:** Saved as isolated JSON files per session.
- **Long-term Memory:** Markdown files organized by category (Profile, University, Projects, etc.).
- **Vector DB:** Persistent ChromaDB storage in `/vector_db`.
