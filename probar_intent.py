from core.intent import detectar_intencion

pruebas = [
    "lista los archivos",
    "mostrame las carpetas",
    "abre muestreo.pdf",
    "lee probabilidad",
    "busca información sobre estadística",
    "qué sabes sobre muestreo",
    "haceme un examen",
    "test de estadística",
    "hola cómo estás",
    "abre la puerta"
]

for p in pruebas:
    resultado = detectar_intencion(p)
    print(f"'{p}' → {resultado}")