"""
Módulo de síntesis de voz para Atlas.
Usa Edge TTS (online) o pyttsx3 (offline).
"""
import asyncio
import tempfile
import os
import logging
from core.utils import hay_internet

logger = logging.getLogger(__name__)


def _run_async(coro):
    """
    Ejecuta una corrutina de forma segura.
    Si ya hay un event loop corriendo (Streamlit, Jupyter), usa
    nest_asyncio o crea un loop nuevo en un thread aparte.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import threading

            result = [None]

            def _run():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                result[0] = new_loop.run_until_complete(coro)
                new_loop.close()

            t = threading.Thread(target=_run)
            t.start()
            t.join()
            return result[0]
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def hablar_con_edge_tts(texto, voz="es-AR-ElenaNeural"):
    """
    Convierte texto a voz usando Edge TTS (Microsoft, alta calidad).
    Args:
        texto: Texto a convertir
        voz: Voz a usar (default: Elena, español Argentina)
    """
    temp_path = None
    try:
        import edge_tts
        import pygame

        pygame.mixer.init()

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            temp_path = temp_audio.name

        communicate = edge_tts.Communicate(texto, voz)
        await communicate.save(temp_path)

        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except ImportError:
        logger.warning("Instalá edge-tts y pygame (pip install edge-tts pygame)")
    except Exception as e:
        logger.error(f"Error en síntesis de voz: {e}")
    finally:
        try:
            import pygame
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def hablar_con_pyttsx3(texto):
    """
    Convierte texto a voz usando pyttsx3 (offline, calidad básica).
    """
    try:
        import pyttsx3

        engine = pyttsx3.init()

        voices = engine.getProperty('voices')
        for voice in voices:
            if 'spanish' in voice.name.lower() or 'español' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break

        engine.say(texto)
        engine.runAndWait()

    except ImportError:
        logger.warning("Instalá pyttsx3 (pip install pyttsx3)")
    except Exception as e:
        logger.error(f"Error en síntesis de voz: {e}")


def hablar(texto):
    """
    Convierte texto a voz.
    Usa Edge TTS si hay internet, pyttsx3 si no.
    """
    if not texto:
        return

    if len(texto) > 500:
        texto = texto[:500] + "..."

    if hay_internet():
        _run_async(hablar_con_edge_tts(texto))
    else:
        hablar_con_pyttsx3(texto)


def listar_voces_disponibles():
    """
    Lista las voces disponibles en Edge TTS.
    Devuelve una lista de dicts con 'ShortName' y 'Gender'.
    """
    try:
        import edge_tts

        async def obtener_voces():
            voices = await edge_tts.list_voices()
            return [v for v in voices if v["Locale"].startswith("es")]

        voces = _run_async(obtener_voces())

        resultado = []
        for v in voces[:10]:
            resultado.append({
                "short_name": v.get("ShortName", "?"),
                "gender": v.get("Gender", "?"),
            })
        return resultado

    except Exception as e:
        logger.error(f"Error listando voces: {e}")
        return []
