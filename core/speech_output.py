"""
Módulo de síntesis de voz para Atlas.
Usa Edge TTS (online) o pyttsx3 (offline).
"""
import asyncio
import tempfile
import os
from core.utils import hay_internet


async def hablar_con_edge_tts(texto, voz="es-AR-ElenaNeural"):
    """
    Convierte texto a voz usando Edge TTS (Microsoft, alta calidad).
    Args:
        texto: Texto a convertir
        voz: Voz a usar (default: Elena, español Argentina)
    """
    try:
        import edge_tts
        import pygame
        
        # Inicializar pygame mixer
        pygame.mixer.init()
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
            temp_path = temp_audio.name
        
        # Generar audio
        communicate = edge_tts.Communicate(texto, voz)
        await communicate.save(temp_path)
        
        # Reproducir con pygame
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        
        # Esperar a que termine
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Limpiar
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        os.remove(temp_path)
        
    except ImportError:
        print("Error: Instalá edge-tts y pygame (pip install edge-tts pygame)")
    except Exception as e:
        print(f"Error en síntesis de voz: {str(e)}")


def hablar_con_pyttsx3(texto):
    """
    Convierte texto a voz usando pyttsx3 (offline, calidad básica).
    """
    try:
        import pyttsx3
        
        engine = pyttsx3.init()
        
        # Configurar voz en español si está disponible
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'spanish' in voice.name.lower() or 'español' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        engine.say(texto)
        engine.runAndWait()
        
    except ImportError:
        print("Error: Instalá pyttsx3 (pip install pyttsx3)")
    except Exception as e:
        print(f"Error en síntesis de voz: {str(e)}")


def hablar(texto):
    """
    Convierte texto a voz.
    Usa Edge TTS si hay internet, pyttsx3 si no.
    """
    if not texto:
        return
    
    # Limitar longitud para no saturar
    if len(texto) > 500:
        texto = texto[:500] + "..."
    
    if hay_internet():
        asyncio.run(hablar_con_edge_tts(texto))
    else:
        hablar_con_pyttsx3(texto)


def listar_voces_disponibles():
    """Lista las voces disponibles en Edge TTS."""
    try:
        import edge_tts
        
        async def obtener_voces():
            voices = await edge_tts.list_voices()
            return [v for v in voices if v["Locale"].startswith("es")]
        
        voces = asyncio.run(obtener_voces())
        
        print("\n🗣️ Voces disponibles (español):")
        for v in voces[:10]:  # Mostrar solo las primeras 10
            print(f"  • {v['ShortName']} - {v['Gender']}")
        
    except Exception as e:
        print(f"Error listando voces: {e}")