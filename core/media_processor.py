"""
Atlas v2.2 - Módulo de Procesamiento de Medios (media_processor.py)
Extrae pistas de audio y segmenta archivos largos para evitar desbordes de contexto.
"""
import os
import subprocess

def extraer_audio(ruta_video, ruta_salida_audio="memory/cache/audio_extraido.wav"):
    """
    Extrae el audio de un video usando ffmpeg (vía consola) para no sobrecargar Python.
    """
    os.makedirs(os.path.dirname(ruta_salida_audio), exist_ok=True)
    
    # Comando ffmpeg optimizado para extraer audio mono a 16kHz (ideal para transcripción local)
    comando = [
        "ffmpeg", "-y", "-i", ruta_video,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        ruta_salida_audio
    ]
    
    try:
        # Ejecución silenciosa
        subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return ruta_salida_audio
    except Exception as e:
        print(f"❌ Error al extraer audio con ffmpeg: {e}")
        return None

def segmentar_audio(ruta_audio, duracion_bloque_seg=300, carpeta_salida="memory/cache/chunks"):
    """
    Corta un audio largo en fragmentos (chunks) de N segundos (por defecto 5 minutos).
    Esto permite un procesamiento batch secuencial y evita cuelgues.
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    
    # Limpiar chunks anteriores
    for f in os.listdir(carpeta_salida):
        if f.endswith(".wav"):
            os.remove(os.path.join(carpeta_salida, f))
            
    comando = [
        "ffmpeg", "-y", "-i", ruta_audio,
        "-f", "segment", "-segment_time", str(duracion_bloque_seg),
        "-c", "copy", os.path.join(carpeta_salida, "chunk_%03d.wav")
    ]
    
    try:
        subprocess.run(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        chunks = [os.path.join(carpeta_salida, f) for f in os.listdir(carpeta_salida) if f.endswith(".wav")]
        chunks.sort()
        return chunks
    except Exception as e:
        print(f"❌ Error al segmentar audio: {e}")
        return []