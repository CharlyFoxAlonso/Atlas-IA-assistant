# 🧠 ATLAS v2.7 - GUÍA MAESTRA DE RESTAURACIÓN (POST-FORMATEO)
**Creador:** Charly | **Fecha:** 04/07/2026
**Arquitectura:** Híbrida (Ollama Local + NVIDIA API) + RAG Semántico (ChromaDB)

Esta guía asume que acabás de formatear tu PC con Windows y tenés el ZIP de backup (`Atlas_Backup_YYYYMMDD.zip`) a mano. Seguí estos pasos en orden para tener Atlas 100% operativo en menos de 20 minutos.

---

## 🛠️ FASE 1: INSTALACIONES BASE (WINDOWS)

Antes de tocar el código de Atlas, necesitás instalar los motores externos.

### 1. Python 3.10 o 3.11 (Obligatorio)
1. Descargá el instalador desde [python.org/downloads](https://www.python.org/downloads/).
2. ⚠️ **CRÍTICO:** En la primera pantalla del instalador, marcá la casilla **"Add Python.exe to PATH"**.
3. Instalá con "Install Now".
4. *Verificación:* Abrí la consola (CMD o PowerShell) y escribí `python --version`.

### 2. Ollama (Cerebro Local - Atlas)
1. Descargá e instalá desde [ollama.com/download](https://ollama.com/download).
2. Abrí la consola y descargá el modelo principal:
   ```bash
   ollama pull qwen3:8b