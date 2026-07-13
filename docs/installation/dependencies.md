# Dependencias operativas de Atlas

## Objetivo

Este documento clasifica dependencias según su impacto real. No todas son obligatorias y su ausencia no debe convertir automáticamente a Atlas en un sistema inutilizable.

## Runtime base

| Dependencia | Clasificación | Función |
|---|---|---|
| Python 3.11–3.13 | Crítica durante desarrollo | Ejecutar Atlas y sus herramientas |
| Runtime Python privado | Recomendado en desarrollo, crítico para distribución | Evitar conflictos con Python global |
| Streamlit | Crítica para la UI actual | Interfaz principal |
| `requests` y `python-dotenv` | Críticas para el flujo actual | Servicios HTTP y configuración |

Python 3.14 no se considera soportado actualmente porque varias dependencias pesadas pueden no disponer de wheels compatibles. Healer rechaza la instalación de paquetes en el Python global.

## Backends de IA

Atlas necesita al menos uno de los siguientes caminos funcionales:

| Backend | Requisitos | Clasificación |
|---|---|---|
| Ollama local | Ejecutable, servicio y modelo configurado | Crítico si se selecciona modo local |
| NVIDIA NIM | paquete `openai` y `NVIDIA_API_KEY` | Opcional |
| Groq | paquete `groq` y `GROQ_API_KEY` | Opcional |
| OpenAI | paquete `openai` y `OPENAI_API_KEY` | Opcional |

La ausencia de una clave concreta no reduce por sí sola la preparación si existe otro backend funcional.

## RAG semántico

El RAG requiere conjuntamente:

- `chromadb`;
- `sentence-transformers`;
- `torch`.

Se clasifica como recomendado para el arranque general y necesario para consultas semánticas sobre la biblioteca.

## Documentos y OCR

| Capacidad | Dependencias |
|---|---|
| Texto de PDF | `pypdf` |
| Imágenes | `Pillow` |
| OCR de imágenes | `pytesseract`, Pillow y Tesseract |
| OCR de PDF | `pdf2image`, Poppler, Tesseract y paquetes anteriores |
| Word | `python-docx` |
| PowerPoint | `python-pptx` |

Tesseract y Poppler son ejecutables externos. Tener instalado `pytesseract` no implica que OCR sea funcional.

## Audio y voz

| Capacidad | Dependencias principales |
|---|---|
| Transcripción Groq | `groq`, FFmpeg y clave Groq |
| Reconocimiento en línea | `SpeechRecognition` |
| Reconocimiento fuera de línea | `vosk` y un modelo local |
| Voz en línea | `edge-tts` |
| Voz fuera de línea | `pyttsx3` |
| Reproducción | `pygame`, según el flujo |

Estas capacidades son opcionales y deben degradarse de forma explícita.

## Visión y web

- Visión de pantalla: `pyautogui` y Pillow.
- Búsqueda web predeterminada: `duckduckgo-search`.
- Proveedores alternativos: `tavily-python` o configuración externa, según el código activo.
- Crawling: `requests` y `beautifulsoup4`.

## Herramientas externas

| Herramienta | Clasificación | Observación |
|---|---|---|
| Ollama | Condicionalmente crítica | Solo si no existe backend de nube funcional |
| Tesseract | Opcional | Habilita OCR |
| Poppler | Opcional | Habilita conversión de PDF para OCR |
| FFmpeg | Opcional | Habilita conversiones y transcripción de audio |
| GPU NVIDIA | Opcional | Mejora rendimiento local |
| Git | Solo desarrollo | No debe exigirse al usuario final |

## Instalación automática

La CLI puede instalar el archivo curado únicamente con doble consentimiento:

```powershell
python -m core.system heal python_packages --apply --allow-heavy
```

Esta operación:

- usa el intérprete activo;
- exige runtime privado o aplicación empaquetada;
- ejecuta `pip install -r requirements.txt`;
- comprueba el código de retorno;
- no tiene un timeout corto para paquetes pesados;
- vuelve a diagnosticar al finalizar.

Por el momento Atlas no instala automáticamente Tesseract, Poppler, FFmpeg ni Ollama. Antes se debe implementar una capa de descargas con HTTPS, fuentes permitidas y verificación SHA-256.

