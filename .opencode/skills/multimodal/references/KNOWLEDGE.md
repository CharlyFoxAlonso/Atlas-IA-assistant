# Multimodal — Conocimiento técnico

## Mapa de módulos

| Archivo | Rol |
|---|---|
| `core/speech_input.py` | Reconocimiento de voz: Google Speech (online) / Vosk (offline) |
| `core/audio_transcriber.py` | Transcripción de archivos multimedia vía Groq Whisper API |
| `core/speech_output.py` | Síntesis de voz: Edge TTS (online) / pyttsx3 (offline) |
| `core/vision.py` | Captura de pantalla (pyautogui) + OCR (pytesseract) |
| `core/ocr.py` | Wrapper Tesseract para imágenes PIL |
| `core/pdf_reader.py` | OCR para PDFs escaneados (pdf2image + pytesseract) |

## Patrones de diseño

- **Online/offline fallback**: Cada módulo detecta internet y elige proveedor. Ej: `escuchar()` usa Google si hay internet, Vosk si no.
- **Imports perezosos**: Las librerías pesadas (`pytesseract`, `vosk`, `edge_tts`, `pygame`) se importan dentro de funciones, no al inicio del módulo.
- **Limpieza de temporales**: Capturas y audio TTS se limpian en bloques `finally`.
- **Dependencias opcionales**: Si falta una librería, el módulo no falla al importar, solo al usar.

## Riesgos

- **Vosk descarga modelo ~50MB** en primera ejecución sin internet → falla.
- **Edge TTS requiere internet**; sin conexión cae a pyttsx3 (voz robótica).
- **Tesseract sin idioma `spa`** produce texto vacío o basura.
- **FFmpeg necesario** para que `audio_transcriber` convierta formatos no MP3.
- **pyautogui.screenshot()** captura monitor principal; en headless/server falla.
