from core.director import analizar

pruebas = [
    "lista los archivos",
    "mostrame las carpetas",
    "abre muestreo",
    "busca información sobre probabilidad",
    "hola cómo estás"
]

for p in pruebas:
    print(f"\n{'=' * 60}")
    print(f"PREGUNTA: {p}")
    print('=' * 60)
    resultado = analizar(p)
    
    if resultado is None:
        print("→ CHAT (brain.py debería responder)")
    else:
        print(resultado[:500])  # Primeros 500 caracteres