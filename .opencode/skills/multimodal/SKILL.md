---
name: multimodal
# domain: capacidades de audio, voz, visión, OCR, transcripción
type: domain
description: |
  Capacidades de audio, voz, transcripción, síntesis, visión, captura de pantalla
  y OCR de Atlas. Usar al trabajar con micrófono, Whisper, Vosk, TTS, imágenes,
  pantalla o reconocimiento óptico. No usar para interfaces de usuario,
  lógica del núcleo o configuración del sistema.
---

# Multimodal

## Propósito

Desarrollar o depurar las capacidades de audio (entrada/salida), visión (captura/OCR) y transcripción de Atlas, incluyendo los proveedores online (Google Speech, Edge TTS, Groq Whisper) y offline (Vosk, pyttsx3, Tesseract OCR).

## Cuándo usarla

- El usuario menciona voz, audio, micrófono, hablar, escuchar, transcripción, Whisper, Vosk, TTS
- El usuario menciona pantalla, captura, visión, OCR, Tesseract, imagen
- El usuario reporta errores en entrada/salida de audio, reconocimiento de voz, OCR o captura de pantalla
- El usuario pide cambiar voces TTS, idioma de OCR, o probar micrófono

## Cuándo no usarla

- La interfaz de comandos de voz en UI/CLI → `interfaz-usuario` (esta skill cubre los módulos internos)
- La instalación de Tesseract, Poppler, FFmpeg → `configuracion-sistema`
- La lógica de transcripción para ingesta de documentos → `base-conocimiento`

## Workflow

1. **Identificar la modalidad** — Audio input (`speech_input.py`), transcripción de archivos (`audio_transcriber.py`), síntesis de voz (`speech_output.py`), captura de pantalla (`vision.py`), OCR (`ocr.py`)
2. **Entender el fallback online/offline** — Cada módulo tiene modo online y offline. Verificar cuál está fallando
3. **Verificar dependencias** — Los módulos multimodales tienen dependencias opcionales; verificar que estén instaladas
4. **Modificar** — Aplicar el cambio en el archivo correspondiente
5. **Probar modo online y offline** — Si el cambio afecta a un proveedor, verificar el fallback
6. **Validar limpieza de archivos temporales** — Capturas de pantalla y audio TTS deben limpiarse después de usar

## Checklist rápido

- [ ] Los imports de librerías pesadas (`pytesseract`, `vosk`, `edge_tts`, `pygame`) son perezosos (dentro de funciones)
- [ ] `speech_input.escuchar()` detecta internet y elige Google Speech (online) o Vosk (offline)
- [ ] `speech_output.hablar()` selecciona Edge TTS (online) o pyttsx3 (offline) automáticamente
- [ ] `vision.analizar_pantalla()` guarda captura en `memory/Atlas_Memory/temp/capturas/` y la limpia después
- [ ] `audio_transcriber.transcribir_archivo()` requiere FFmpeg para formatos no nativos
- [ ] Tesseract requiere idioma instalado (`spa` por defecto); si no está, OCR falla silenciosamente

## Gotchas / Riesgos

- **Dependencias opcionales**: Si falta `vosk`, `speech_input` no falla — intenta Google Speech; si no hay internet, retorna error amigable
- **FFmpeg necesario para Groq Whisper**: Los formatos de video/audio no MP3 requieren conversión; sin FFmpeg, falla
- **Tesseract sin idioma español**: Si `spa` no está instalado, `imagen_a_texto()` produce basura o texto vacío
- **Edge TTS requiere internet**: Sin conexión, `hablar()` cae a pyttsx3 (voz robótica de baja calidad)
- **Captura de pantalla en segundo plano**: `pyautogui.screenshot()` captura el monitor principal; en headless/server falla
- **Vosk descarga modelo ~50MB**: La primera vez que se usa `escuchar_con_vosk()`, descarga el modelo desde Alphacephei; puede fallar sin internet

## Relaciones

- `interfaz-usuario` → Los comandos `!mirar`, `!escuchar`, `!hablar`, `!probar_mic`, `!voces` están en UI/CLI
- `base-conocimiento` → `audio_transcriber` se usa en `local_ingestion_manager` para ingesta multimedia
- `configuracion-sistema` → Para instalar Tesseract, Poppler, FFmpeg o dependencias Python
- `nucleo-atlas` → No suele interactuar directamente; los módulos multimodales se llaman desde UI/CLI

## Archivos relacionados

- `references/KNOWLEDGE.md` — Mapa de módulos multimodales, patrones de diseño y riesgos

## Validación

- **speech_input**: `python -c "from core.speech_input import probar_microfono; probar_microfono()"` lista micrófonos
- **speech_output**: `python -c "from core.speech_output import listar_voces_disponibles; print(listar_voces_disponibles())"` lista voces
- **vision**: `python -c "from core.vision import analizar_pantalla; print(analizar_pantalla())"` captura y OCR
- **ocr**: `python probar_ocr.py` o `python diagnostico_ocr.py` para diagnóstico completo de Tesseract
- **audio_transcriber**: Usar `!indexar` con un archivo multimedia desde la UI (requiere ingesta local)
