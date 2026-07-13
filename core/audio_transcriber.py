"""
core/audio_transcriber.py
Transcripción ultra-rápida de Audio y Video usando Groq API (Whisper-v3).
Soporta: MP3, WAV, M4A, AAC, OGG, FLAC, MP4, MOV, AVI, MKV, WEBM
Si el formato no es compatible con Groq, lo convierte automáticamente con FFmpeg.
Atlas v4
"""
import os
import subprocess
import logging
import tempfile
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # ✅ CORREGIDO: __name__

# Formatos que Groq acepta directamente
FORMATOS_GROQ_NATIVOS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm'}

# Todos los formatos de audio que Atlas acepta
FORMATOS_AUDIO = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma', '.opus'}

# Formatos de video
FORMATOS_VIDEO = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}


def _convertir_a_mp3(ruta_origen: str, ruta_salida_mp3: str) -> bool:
    """
    Convierte cualquier audio/video a MP3 16kHz mono usando FFmpeg.
    Optimizado para Whisper (mejor calidad de transcripción).
    """
    try:
        cmd = [
            'ffmpeg', '-i', ruta_origen,
            '-vn',                   # Sin video
            '-acodec', 'libmp3lame', # Codec MP3
            '-ar', '16000',          # 16kHz (óptimo para Whisper)
            '-ac',  '1',              # Mono
            '-y',                    # Sobrescribir sin preguntar
            ruta_salida_mp3
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except FileNotFoundError:
        logger.error("❌ FFmpeg no está instalado o no está en el PATH.")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en FFmpeg: {e.stderr.decode('utf-8', errors='ignore')[:500]}")
        return False
    except Exception as e:
        logger.error(f"Error convirtiendo archivo: {e}")
        return False


def transcribir_archivo(ruta_archivo: str, progreso_callback=None) -> str:
    """
    Transcribe un archivo de audio o video.
    - Si es video, extrae el audio primero.
    - Si el formato no es nativo de Groq (ej: .aac), lo convierte a MP3 automáticamente.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "❌ Error: GROQ_API_KEY no configurada en .env"

    extension = os.path.splitext(ruta_archivo)[1].lower()
    ruta_procesar = ruta_archivo
    archivo_temporal = None
    ruta_temporal = None

    def _crear_temporal_mp3():
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        return tmp.name

    try:
        # PASO 1: Si es video, extraer audio
        if extension in FORMATOS_VIDEO:
            if progreso_callback:
                progreso_callback("🎬 Extrayendo audio del video...")
            logger.info(f"Video detectado ({extension}), extrayendo audio...")
            ruta_temporal = _crear_temporal_mp3()
            if not _convertir_a_mp3(ruta_archivo, ruta_temporal):
                return "❌ Error: FFmpeg no pudo extraer el audio del video."
            ruta_procesar = ruta_temporal

        # PASO 2: Si es audio pero NO es formato nativo de Groq
        elif extension not in FORMATOS_GROQ_NATIVOS:
            if progreso_callback:
                progreso_callback(f"🔄 Convirtiendo {extension.upper()} a MP3...")
            logger.info(f"Formato {extension} no nativo de Groq, convirtiendo a MP3...")
            ruta_temporal = _crear_temporal_mp3()
            if not _convertir_a_mp3(ruta_archivo, ruta_temporal):
                return f"❌ Error: FFmpeg no pudo convertir {extension} a MP3."
            ruta_procesar = ruta_temporal

        # PASO 3: Transcribir con Groq
        if progreso_callback:
            progreso_callback("⚡ Transcribiendo con Groq (Whisper-v3)...")
        logger.info(f"Transcribiendo: {os.path.basename(ruta_procesar)}")

        client = Groq(api_key=api_key)
        with open(ruta_procesar, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(ruta_procesar), file.read()),
                model="whisper-large-v3",
                language="es",
                response_format="text"
            )

        logger.info(f"✅ Transcripción completada ({len(transcription)} caracteres)")
        return transcription

    except Exception as e:
        logger.error(f"Error en transcripción Groq: {e}")
        return f"❌ Error en la transcripción: {str(e)}"
    finally:
        # Limpiar archivo temporal si se creó uno
        if ruta_temporal and os.path.exists(ruta_temporal):
            try:
                os.remove(ruta_temporal)
            except Exception:
                pass
