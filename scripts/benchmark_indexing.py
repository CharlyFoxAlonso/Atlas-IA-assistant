"""
scripts/benchmark_indexing.py
Benchmark reproducible del corte de indexación incremental (Atlas v4.1).

Compara la lógica ANTERIOR (reconstrucción completa tras cada operación)
con la NUEVA (indexación individual / sincronización incremental) sobre
fixtures temporales, SIN ChromaDB, SIN embeddings reales, SIN APIs y
SIN tocar memory/ ni vector_db reales.

La lógica "antes" es una réplica fiel del bucle del viejo
construir_indice(): recorrer TODO, abrir TODO y reindexar TODO.
El backend vectorial es un fake que cuenta llamadas y simula un costo
fijo pequeño por documento indexado (embeddings).

Uso:
    python scripts/benchmark_indexing.py

Aclaración: los tiempos del fake no representan la velocidad real de la
PC del usuario; la reducción en CANTIDAD DE OPERACIONES es la evidencia
válida. La ganancia real crece con el tamaño y costo de los documentos.
"""
import contextlib
import io
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.indexer as indexer
from core.universal_loader import leer_archivo_con_info

CONTENIDO = (
    "Texto de prueba suficientemente largo para superar el mínimo de "
    "cincuenta caracteres exigido por agregar_documento. " * 3
)

# Costo simulado de embeddings por documento (segundos)
COSTO_FAKE_POR_DOC = 0.0015


class Contador:
    """Métricas observables de una corrida."""

    def __init__(self):
        self.escaneados = 0
        self.abiertos = 0
        self.indexados = 0
        self.omitidos = 0
        self.llamadas_backend = 0
        self.duracion = 0.0


def _crear_fixture(base, n):
    for i in range(n):
        sub = os.path.join(base, f"carpeta_{i % 5}")
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, f"doc_{i:03d}.md"), "w", encoding="utf-8") as f:
            f.write(f"# Documento {i}\n\n{CONTENIDO}")


def _agregar_fake(contador):
    def agregar(doc_id, texto, metadata=None):
        contador.llamadas_backend += 1
        contador.indexados += 1
        time.sleep(COSTO_FAKE_POR_DOC)  # simula costo de embeddings
        return max(1, len(texto) // 500)
    return agregar


def _loader_espia(contador):
    def loader(ruta):
        contador.abiertos += 1
        return leer_archivo_con_info(ruta)
    return loader


def medir_antes(base, contador):
    """Réplica de la lógica vieja: recorrer y reindexar TODO."""
    agregar = _agregar_fake(contador)
    loader = _loader_espia(contador)
    t0 = time.perf_counter()
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for archivo in sorted(files):
            if os.path.splitext(archivo)[1].lower() in {'.md', '.pdf', '.txt',
                                                        '.docx', '.pptx'}:
                contador.escaneados += 1
                ruta = os.path.join(root, archivo)
                resultado = loader(ruta)
                if resultado.get("ok") and resultado.get("contenido"):
                    agregar(doc_id=os.path.relpath(ruta, base),
                            texto=resultado["contenido"])
    contador.duracion = time.perf_counter() - t0


def medir_despues_indexar_archivo(base, manifest_path, ruta_nueva, contador):
    """Lógica nueva tras ingerir: indexar SOLO el archivo nuevo."""
    with contextlib.redirect_stdout(io.StringIO()):
        t0 = time.perf_counter()
        with _patchear_indexer(contador):
            res = indexer.indexar_archivo(ruta_nueva, memoria_base=base,
                                          manifest_path=manifest_path)
        contador.duracion = time.perf_counter() - t0
    assert res.status == "indexed", res.error


def medir_despues_sync(base, manifest_path, contador):
    """Lógica nueva de mantenimiento: sincronización incremental."""
    with contextlib.redirect_stdout(io.StringIO()):
        t0 = time.perf_counter()
        with _patchear_indexer(contador):
            res = indexer.sincronizar_indice(memoria_base=base,
                                             manifest_path=manifest_path)
        contador.duracion = time.perf_counter() - t0
    contador.escaneados = res.scanned
    contador.omitidos = res.skipped_unchanged
    assert res.failed == 0, [i.error for i in res.items if i.status == "failed"]


@contextlib.contextmanager
def _patchear_indexer(contador):
    """Reemplaza loader y backend del indexer por versiones instrumentadas."""
    import unittest.mock as mock
    with mock.patch.object(indexer, "leer_archivo_con_info",
                           _loader_espia(contador)), \
         mock.patch.object(indexer, "agregar_documento",
                           _agregar_fake(contador)):
        yield


def _preparar_manifest(base, manifest_path):
    """Sincronización inicial NO medida (deja el manifiesto al día)."""
    class C(Contador):
        pass
    with contextlib.redirect_stdout(io.StringIO()):
        with _patchear_indexer(C()):
            indexer.sincronizar_indice(memoria_base=base,
                                       manifest_path=manifest_path)


def escenario(nombre, n_existentes, accion):
    """
    accion: "agregar_nuevo" | "sin_cambios" | "modificar_uno"
    Devuelve (Contador antes, Contador despues).
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "Atlas_Memory")
        manifest_path = os.path.join(tmp, "vector_db", "index_manifest.json")
        os.makedirs(base)
        _crear_fixture(base, n_existentes)

        antes, despues = Contador(), Contador()

        if accion == "agregar_nuevo":
            # El "antes" reconstruye todo tras agregar el archivo
            ruta_nueva = os.path.join(base, "carpeta_1", "doc_nuevo.md")
            with open(ruta_nueva, "w", encoding="utf-8") as f:
                f.write(f"# Nuevo\n\n{CONTENIDO}")
            medir_antes(base, antes)
            # El "después" parte de un manifiesto al día con los N existentes
            os.remove(ruta_nueva)
            _preparar_manifest(base, manifest_path)
            with open(ruta_nueva, "w", encoding="utf-8") as f:
                f.write(f"# Nuevo\n\n{CONTENIDO}")
            despues.escaneados = 1
            medir_despues_indexar_archivo(base, manifest_path, ruta_nueva, despues)

        elif accion == "sin_cambios":
            medir_antes(base, antes)
            _preparar_manifest(base, manifest_path)
            medir_despues_sync(base, manifest_path, despues)

        elif accion == "modificar_uno":
            medir_antes(base, antes)
            _preparar_manifest(base, manifest_path)
            ruta_mod = os.path.join(base, "carpeta_2", "doc_002.md")
            with open(ruta_mod, "a", encoding="utf-8") as f:
                f.write("\n\nCapítulo extra con contenido adicional modificado.")
            stat = os.stat(ruta_mod)
            os.utime(ruta_mod, ns=(stat.st_atime_ns,
                                   stat.st_mtime_ns + 1_000_000_000))
            medir_despues_sync(base, manifest_path, despues)
            despues.indexados = 1  # sólo el modificado

        return nombre, antes, despues


def main():
    import logging
    # Silenciar el log INFO del loader para una salida limpia del benchmark
    logging.getLogger("core.universal_loader").setLevel(logging.WARNING)

    print("=" * 78)
    print("BENCHMARK: indexación completa (antes) vs incremental (después)")
    print(f"Backend fake: {COSTO_FAKE_POR_DOC * 1000:.1f} ms simulados por documento")
    print("=" * 78)

    escenarios = [
        escenario("A: 10 existentes + 1 nuevo", 10, "agregar_nuevo"),
        escenario("B: 100 existentes + 1 nuevo", 100, "agregar_nuevo"),
        escenario("C: 100 sin cambios", 100, "sin_cambios"),
        escenario("D: 100 existentes + 1 modificado", 100, "modificar_uno"),
    ]

    header = (f"{'Escenario':<34} | {'Antes: idx':>10} | {'Después: idx':>12} | "
              f"{'T. antes':>9} | {'T. después':>10}")
    print(header)
    print("-" * len(header))
    for nombre, antes, despues in escenarios:
        print(f"{nombre:<34} | {antes.indexados:>10} | {despues.indexados:>12} | "
              f"{antes.duracion:>8.3f}s | {despues.duracion:>9.3f}s")

    print()
    print("Detalle de operaciones (abiertos = archivos leídos por el loader):")
    for nombre, antes, despues in escenarios:
        print(f"\n[{nombre}]")
        print(f"  ANTES:   escaneados={antes.escaneados} abiertos={antes.abiertos} "
              f"indexados={antes.indexados} backend_calls={antes.llamadas_backend}")
        print(f"  DESPUÉS: escaneados={despues.escaneados} abiertos={despues.abiertos} "
              f"indexados={despues.indexados} omitidos={despues.omitidos} "
              f"backend_calls={despues.llamadas_backend}")


if __name__ == "__main__":
    main()
