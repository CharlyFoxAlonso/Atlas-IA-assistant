from core.brain import pensar

print("Probando el cerebro de Atlas...\n")

# Prueba 1: Pregunta sobre estudio
print("1. Pregunta sobre estadística:")
respuesta = pensar("¿Qué es el muestreo aleatorio simple?")
print(respuesta[:500])  # Primeros 500 caracteres
print("\n" + "=" * 60 + "\n")

# Prueba 2: Pregunta general
print("2. Pregunta general:")
respuesta = pensar("¿Qué archivos tienes en la memoria?")
print(respuesta[:500])