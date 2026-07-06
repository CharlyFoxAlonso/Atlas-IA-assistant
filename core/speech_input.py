"""
Módulo de reconocimiento de voz para Atlas.
Usa Google Speech (online) o Vosk (offline).
Atlas v2.9
"""
import os
import json
from core.utils import hay_internet

# Directorio para modelos de Vosk - ✅ CORREGIDO: agregado #
VOSK_MODEL_DIR = "memory/Atlas_Memory/modelos/vosk"
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"


def asegurar_modelo_vosk():
    """
    Descarga el modelo pequeño de Vosk para español si no existe.
    Devuelve la ruta al modelo.
    """
    if not os.path.exists(VOSK_MODEL_DIR):
        os.makedirs(VOSK_MODEL_DIR, exist_ok=True)
    modelo_path = os.path.join(VOSK_MODEL_DIR, "vosk-model-small-es-0.42")
    if not os.path.exists(modelo_path):
        print("\n📥 Descargando modelo de voz Vosk (español, ~50MB)...")
        print("   Esto puede tardar unos minutos la primera vez.\n")
        try:
            import urllib.request
            import zipfile
            zip_path = os.path.join(VOSK_MODEL_DIR, "modelo.zip")
            # Descargar con progreso
            def mostrar_progreso(bloque, tam_bloque, tam_total):
                descargado = bloque * tam_bloque
                if tam_total > 0:
                    porcentaje = min(100, int(descargado * 100 / tam_total))
                    print(f"\r   Descargando: {porcentaje}%", end="", flush=True)
            urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path, reporthook=mostrar_progreso)
            print()  # Salto de línea
            # Extraer
            print("   Extrayendo modelo...")
            destino = os.path.abspath(VOSK_MODEL_DIR)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                entrada_invalida = None
                for miembro in zip_ref.namelist():
                    ruta_destino = os.path.abspath(os.path.join(destino, miembro))
                    if os.path.commonpath([ruta_destino, destino]) != destino:
                        entrada_invalida = miembro
                        break
                if entrada_invalida:
                    raise ValueError(f"Entrada Zip Slip detectada: {entrada_invalida}")
                zip_ref.extractall(destino)
            # Eliminar zip
            os.remove(zip_path)
            print("✅ Modelo descargado correctamente\n")
            return modelo_path
        except Exception as e:
            print(f"❌ Error descargando modelo: {e}\n")
            return None
    return modelo_path


def escuchar_con_google(duracion=5):
    """
    Escucha audio del micrófono usando Google Speech API (online).
    Muy preciso en español.
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print(f"\n🎤 Escuchando... (máx {duracion} segundos)")
            print("   Hablá ahora...\n")
            # Ajustar para ruido ambiente
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            # Escuchar
            audio = recognizer.listen(source, timeout=duracion, phrase_time_limit=duracion)
            print("✅ Audio capturado, reconociendo...")
            # Reconocer con Google
            texto = recognizer.recognize_google(audio, language="es-AR")
            return texto.strip()
    except sr.WaitTimeoutError:
        return "No escuché nada. Intentá de nuevo."
    except sr.UnknownValueError:
        return "No pude entender lo que dijiste."
    except sr.RequestError as e:
        return f"Error con Google Speech (sin internet?): {e}"
    except ImportError:
        return "Error: Instalá SpeechRecognition y pyaudio"
    except Exception as e:
        return f"Error en reconocimiento: {str(e)}"


def escuchar_con_vosk(duracion=5):
    """
    Escucha audio del micrófono usando Vosk (offline).
    """
    try:
        from vosk import Model, KaldiRecognizer
        import pyaudio
        # Asegurar modelo
        modelo_path = asegurar_modelo_vosk()
        if not modelo_path:
            return "Error: No se pudo cargar el modelo Vosk"
        # Cargar modelo
        model = Model(modelo_path)
        recognizer = KaldiRecognizer(model, 16000)
        # Configurar micrófono
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=8000
        )
        print(f"\n🎤 Escuchando (offline)... (máx {duracion} segundos)")
        print("   Hablá ahora...\n")
        stream.start_stream()
        # Grabar audio
        import time
        texto_final = ""
        inicio = time.time()
        while time.time() - inicio < duracion:
            data = stream.read(4000, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                resultado = json.loads(recognizer.Result())
                texto = resultado.get("text", "")
                if texto:
                    texto_final = texto
                    break
        # Obtener resultado final
        if not texto_final:
            resultado = json.loads(recognizer.FinalResult())
            texto_final = resultado.get("text", "")
        # Limpiar
        stream.stop_stream()
        stream.close()
        p.terminate()
        if texto_final:
            return texto_final.strip()
        else:
            return "No escuché nada. Intentá de nuevo."
    except ImportError:
        return "Error: Instalá vosk y pyaudio"
    except Exception as e:
        return f"Error en reconocimiento offline: {str(e)}"


def escuchar(duracion=5):
    """
    Función principal: escucha del micrófono.
    - Con internet: usa Google Speech (preciso)
    - Sin internet: usa Vosk (offline)
    """
    if hay_internet():
        print("🌐 Modo online (Google Speech)")
        return escuchar_con_google(duracion)
    else:
        print("📴 Modo offline (Vosk)")
        return escuchar_con_vosk(duracion)


def probar_microfono():
    """
    Prueba que el micrófono funcione correctamente.
    """
    try:
        import speech_recognition as sr
        print("\n🎤 Probando micrófono...\n")
        # Listar micrófonos disponibles
        mics = sr.Microphone.list_microphone_names()
        print(f"Micrófonos detectados: {len(mics)}")
        for i, mic in enumerate(mics):
            print(f"  [{i}] {mic}")
        # Probar micrófono por defecto
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("\n🔊 Voy a escuchar 3 segundos. Hablá algo...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
        print("✅ Micrófono funciona correctamente")
        # Intentar reconocer
        try:
            texto = recognizer.recognize_google(audio, language="es-AR")
            print(f"🎤 Escuché: '{texto}'")
        except:
            print("⚠️ Micrófono captura audio pero no se pudo reconocer (verificá conexión a internet)")
        return True
    except Exception as e:
        print(f"❌ Error probando micrófono: {e}")
        return False