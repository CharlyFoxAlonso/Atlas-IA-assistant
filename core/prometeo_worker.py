"""
core/prometeo_worker.py
Shim de compatibilidad. Delega al digestion_worker unificado (v3.4).
Mantenido para no romper imports de código anterior.
Atlas v3.4
"""
from core.digestion_worker import (
    digerir_documento_con_progreso,
    digerir_documento,
    PROMPT_DIGESTION,
    MODELOS_NUBE_DIGESTION as MODELOS_DIGESTION,
    _chunk_text,
    _procesar_chunk_nvidia as _procesar_chunk,
)
from core.digestion_worker import _get_client_nvidia as _get_client


if __name__ == "__main__":  # ✅ CORREGIDO: __name__ == "__main__"
    # Test simple
    texto_prueba = "Este es un texto de prueba para verificar que el worker funciona correctamente."
    print("Probando Prometeo Worker...")
    for paso in digerir_documento_con_progreso(texto_prueba, "test.txt", "test"):
        print(paso)