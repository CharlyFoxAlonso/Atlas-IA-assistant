import os
import sys
from datetime import datetime
from agents.stats_researcher_folder import investigar_carpeta_v2

OUTPUT_DIR = "memory/Atlas_Memory/03_Conocimiento/Estudio"


def barra(actual, total, nombre):
    porcentaje = int((actual / total) * 100)
    bloques = int(porcentaje / 5)

    barra = "█" * bloques + "-" * (20 - bloques)

    sys.stdout.write(
        f"\r[{barra}] {porcentaje}% | {nombre[:45]}   "
    )
    sys.stdout.flush()


def exportar_estudio(ruta_carpeta):

    archivos = []

    for root, _, files in os.walk(ruta_carpeta):
        for f in files:
            archivos.append(os.path.join(root, f))

    total = len(archivos)

    if total == 0:
        print("No hay archivos para procesar")
        return {"error": "vacío"}

    print(f"\n🧠 Atlas Study Engine | {total} archivos detectados\n")

    resultados = []

    for i, path in enumerate(archivos, start=1):

        nombre = os.path.basename(path)

        barra(i, total, nombre)

        try:
            res = investigar_carpeta_v2(path)

            if res:
                resultados.append(res)

        except Exception as e:
            resultados.append(f"\nERROR en {nombre}: {str(e)}\n")

    print("\n\n✔ Procesamiento completado\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    nombre_salida = datetime.now().strftime("estudio_%Y-%m-%d_%H-%M-%S.md")

    salida = os.path.join(OUTPUT_DIR, nombre_salida)

    with open(salida, "w", encoding="utf-8") as f:
        f.write("# APUNTES GENERADOS POR ATLAS\n\n")
        f.write("\n\n".join(resultados))

    print("📄 Guardado en:", salida)

    return {
        "archivo": salida,
        "estado": "ok"
    }