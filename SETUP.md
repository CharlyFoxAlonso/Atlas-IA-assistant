# 🚀 SETUP — Atlas v4.1

> Pasos exactos para correr Atlas en una PC Windows nueva.

---

## 0. Diagnóstico (lo que ya sé)

- Python 3.14 está activo **pero NO es compatible** con tu requirements.
- Python 3.13.14 **sí está instalado** y se puede usar (es el que recomiendo).
- Vamos a usar un `venv` (entorno virtual) en `.venv/` para aislar las dependencias.

---

## 1. Lo que tenés que hacer (sólo una vez)

### 1.1. Abrir CMD

```cmd
cd <ruta-del-repo>
```

### 1.2. Crear el entorno virtual con Python 3.13

```cmd
py -3.13 -m venv .venv
```

> Si vos no tenés Python 3.13, instalalo desde:  
> https://www.python.org/ftp/python/3.13.7/python-3.13.7-amd64.exe  
> Marcar "Add Python 3.13 to PATH" durante el install.

### 1.3. Activar el entorno

```cmd
.venv\Scripts\activate
```

> Después de activarlo, vas a ver `(.venv)` al inicio de la línea en CMD.

### 1.4. Actualizar `pip` e instalar dependencias

```cmd
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

> Esto puede tardar varios minutos la primera vez (descarga ~500 MB en wheels).

### 1.5. (Opcional) Configurar las claves API

Creá el archivo `.env` en la raíz del proyecto si no lo tenés:

```ini
# LLM
NVIDIA_API_KEY=tu-clave-nvidia-aqui
ATLAS_OCR_LANG=spa

# Ollama
URL_OLLAMA=http://127.0.0.1:11434/api/chat
MODELO_LOCAL=qwen3:8b

# Whisper (Groq, opcional)
GROQ_API_KEY=tu-clave-groq-aqui
```

---

## 2. Cómo correr Atlas (cada vez)

Ya con todo instalado:

### Opción A — Doble click en el launcher

```cmd
:: UI web con Streamlit
.\run_ui.bat

:: CLI directa en terminal
.\run.bat
```

### Opción B — Manual con CMD

```cmd
cd <ruta-del-repo>
.venv\Scripts\activate

:: UI web
streamlit run atlas_ui.py

:: o CLI
python run.py
```

---

## 3. Verificación de que todo anda

```cmd
python -c "from openai import OpenAI; from core.brain import pensar_con_streaming; print('Atlas core OK')"
```

Debería imprimir: `Atlas core OK`.

---

## 4. Si algo se rompe

### Reinstalar todo desde cero (rápido)

```cmd
cd <ruta-del-repo>
deactivate
rmdir /s /q .venv
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Diagnóstico rápido

```cmd
python diagnostico_ocr.py
```

### Ver qué instaló

```cmd
.venv\Scripts\activate
pip list
```

---

## 5. Atajos

| Acción | Comando |
|--------|---------|
| **Activar venv** | `.venv\Scripts\activate` |
| **UI web** | `.\run_ui.bat` |
| **CLI** | `.\run.bat` |
| **Diagnosticar OCR** | `python diagnostico_ocr.py` |
| **Test NVIDIA** | `python test_nvidia.py` |
| **Actualizar deps** | `pip install --upgrade -r requirements.txt` |
| **Crear chat desde UI** | Sección "🗂️ Chats" → `➕ Nuevo` |

---

## 6. Versión de Python soportada

| Python | Soporte | Nota |
|--------|---------|------|
| **3.13.x** | ✅ Recomendado | Usá esto. |
| 3.12.x  | ✅ Compatible | Igual de bien. |
| 3.11.x  | ✅ Compatible | Igual de bien. |
| 3.10.x  | ⚠️ Funciona | Algunos paquetes pueden fallar. |
| 3.14.x  | ❌ NO usar | Pocos wheels. NO recomendado por ahora. |

---

Última actualización: **v4.1**
