from agents.stats_researcher import investigar_pdf

# Prueba con un PDF de tu carpeta de estadística
ruta_pdf = r"C:\Users\delfa\Documents\Atlas\memory\Atlas_Memory\03_Conocimiento\Estadistica\muestreo probabilistico.pdf"

print("Investigando PDF...")
resultado = investigar_pdf(ruta_pdf)

print("\n" + "=" * 60)
print("RESULTADO:")
print("=" * 60)
print(resultado[:1500])  # Primeros 1500 caracteres