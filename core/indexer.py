"""
core/indexer.py
Indexador semántico de Atlas_Memory (Atlas v4.1 — indexación incremental).

Tres operaciones conceptualmente distintas:

- indexar_archivo(ruta): indexa UN solo archivo (flujo normal tras ingerir).
- sincronizar_indice(): recorre la biblioteca y procesa SOLO diferencias
  (nuevos, modificados, sin cambios, eliminados, fallidos).
- reconstruir_indice_completo(): reindexa TODO; operación explícita de
  mantenimiento (por ejemplo, el comando `!indexar`).

La identidad de cada documento es su ruta relativa normalizada con '/'
(estable, portable e independiente de la ubicación absoluta del repo).
El estado conocido se persiste en un manifiesto local atómico
(vector_db/index_manifest.json) con SHA-256 de contenido.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

# Agregar la carpeta raíz al path para que funcione como script directo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config
from core.index_manifest import IndexManifest, ManifestEntry
from core.vector_store import (
    _variantes_ruta_legacy,
    agregar_documento,
    eliminar_documento,
)
from core.universal_loader import leer_archivo_con_info
from core.security import log_seguridad

# Aliases de compatibilidad (la fuente de verdad es core/config.py)
MEMORIA_BASE = config.BASE_MEMORIA
EXTENSIONES_PERMITIDAS = config.INDEX_SUPPORTED_EXTENSIONS

# Estados posibles de un resultado
STATUS_INDEXED = "indexed"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_DELETED = "deleted"
STATUS_NOT_FOUND = "not_found"


# ============================================
# RESULTADOS ESTRUCTURADOS
# ============================================

@dataclass
class IndexResult:
    """Resultado de indexar (o intentar indexar) un único archivo."""

    path: str
    status: str
    chunk_count: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DeleteResult:
    """Resultado de retirar un documento del índice."""

    path: str
    status: str
    chunks_removed: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SyncResult:
    """Resultado agregado de una sincronización o reconstrucción."""

    scanned: int = 0
    indexed_new: int = 0
    reindexed_modified: int = 0
    skipped_unchanged: int = 0
    removed_deleted: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    mode: str = "sync"  # "sync" | "rebuild"
    items: List[IndexResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


# ============================================
# HELPERS INTERNOS
# ============================================

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalizar_ruta_relativa(ruta: str) -> str:
    """Normaliza separadores a '/' para una identidad portable."""
    return ruta.replace("\\", "/")


def _ruta_relativa(ruta_archivo: str, memoria_base: str) -> str:
    """Ruta relativa normalizada respecto de Atlas_Memory."""
    return _normalizar_ruta_relativa(os.path.relpath(ruta_archivo, memoria_base))


def _resolver_contenida_en_base(ruta_archivo: str, memoria_base: str) -> Optional[str]:
    """
    Verifica que el archivo quede contenido dentro de la base de memoria.

    Resuelve base y archivo (incluidos '..', separadores y, cuando el
    sistema lo permite, symlinks/junctions) y exige que el archivo sea
    descendiente de la base. No se usa comparación de strings con
    startswith(): un prefijo similar tipo 'Atlas_Memory_Evil' no es
    descendiente de 'Atlas_Memory'.

    Returns:
        La ruta relativa normalizada con '/' si está contenida;
        None si queda fuera o si la ruta ES la propia base.
    """
    base_resolved = Path(memoria_base).resolve(strict=False)
    file_resolved = Path(ruta_archivo).resolve(strict=False)
    try:
        rel = file_resolved.relative_to(base_resolved)
    except ValueError:
        return None
    if not rel.parts or str(rel) == ".":
        return None
    return rel.as_posix()


def _sha256_archivo(ruta: str) -> str:
    """SHA-256 del contenido del archivo, leído por bloques."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def _iter_archivos(memoria_base: str):
    """Recorre recursivamente los archivos soportados de Atlas_Memory."""
    for root, dirs, files in os.walk(memoria_base):
        # Ignorar carpetas temporales o de sistema
        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and d not in config.INDEX_IGNORED_DIRS
        ]
        for archivo in sorted(files):
            extension = os.path.splitext(archivo)[1].lower()
            if extension in EXTENSIONES_PERMITIDAS:
                yield os.path.join(root, archivo)


def _indexar_en_manifest(ruta: str, base: str,
                         manifest: IndexManifest) -> IndexResult:
    """
    Núcleo de indexación de UN archivo. Actualiza `manifest` en memoria
    (el caller decide cuándo persistirlo). Nunca toca otros documentos.
    """
    inicio = time.perf_counter()
    rel = _ruta_relativa(ruta, base)
    log_seguridad("INDEX_FILE_STARTED", rel)

    try:
        resultado = leer_archivo_con_info(ruta)

        if not resultado.get("ok") or not resultado.get("contenido"):
            error = resultado.get("error", "contenido vacío")
            duracion = time.perf_counter() - inicio
            log_seguridad("INDEX_FILE_FAILED", f"{rel}: {error}")
            _marcar_error_en_manifest(manifest, rel, error)
            return IndexResult(rel, STATUS_FAILED, 0, duracion, error)

        contenido = resultado["contenido"]
        nombre = os.path.basename(ruta)
        metadata = {
            "nombre": nombre,
            "ruta": rel,
            "categoria": os.path.dirname(rel),
            "tamano_kb": resultado.get("tamano_kb", 0),
            "doc_id": rel,  # identidad estable (v4.1)
        }

        chunks = agregar_documento(doc_id=rel, texto=contenido, metadata=metadata)
        duracion = time.perf_counter() - inicio

        if chunks <= 0:
            error = "contenido vacío o muy corto para indexar"
            log_seguridad("INDEX_FILE_FAILED", f"{rel}: {error}")
            _marcar_error_en_manifest(manifest, rel, error)
            return IndexResult(rel, STATUS_FAILED, 0, duracion, error)

        stat = os.stat(ruta)
        manifest.upsert(ManifestEntry(
            relative_path=rel,
            content_sha256=_sha256_archivo(ruta),
            size_bytes=stat.st_size,
            modified_time_ns=stat.st_mtime_ns,
            indexed_at=_utc_now_iso(),
            chunk_count=chunks,
            last_operation="indexed",
            last_error=None,
        ))
        log_seguridad(
            "INDEX_FILE_COMPLETED",
            f"{rel}: {chunks} chunks en {duracion:.3f}s",
        )
        return IndexResult(rel, STATUS_INDEXED, chunks, duracion)

    except Exception as e:
        duracion = time.perf_counter() - inicio
        error = f"{type(e).__name__}: {e}"
        log_seguridad("INDEX_FILE_FAILED", f"{rel}: {error}")
        _marcar_error_en_manifest(manifest, rel, error)
        return IndexResult(rel, STATUS_FAILED, 0, duracion, error)


def _marcar_error_en_manifest(manifest: IndexManifest, rel: str,
                              error: str) -> None:
    """
    Registra el error en una entrada YA conocida sin tocar hash/mtime/size,
    para que la próxima sincronización lo reintente. No crea entradas
    nuevas: un documento que nunca se indexó no debe figurar como éxito.
    """
    entry = manifest.get(rel)
    if entry is not None:
        entry.last_operation = "failed"
        entry.last_error = error


# ============================================
# API PÚBLICA
# ============================================

def indexar_archivo(ruta_archivo: str,
                    memoria_base: Optional[str] = None,
                    manifest_path: Optional[str] = None) -> IndexResult:
    """
    Indexa UN solo archivo de Atlas_Memory y actualiza el manifiesto.

    Es la operación normal tras ingerir un documento nuevo. No recorre
    ni reconstruye el resto de la biblioteca.

    Args:
        ruta_archivo: Ruta del archivo a indexar.
        memoria_base: Raíz de Atlas_Memory (default: config.BASE_MEMORIA).
        manifest_path: Ruta del manifiesto (default: config.INDEX_MANIFEST_PATH).

    Returns:
        IndexResult con status "indexed" o "failed" (nunca lanza excepción).
    """
    inicio = time.perf_counter()
    base = memoria_base or MEMORIA_BASE
    ruta = os.fspath(ruta_archivo)

    if not os.path.isfile(ruta):
        error = f"archivo no encontrado: {ruta}"
        log_seguridad("INDEX_FILE_FAILED", error)
        return IndexResult(
            os.path.basename(ruta), STATUS_FAILED, 0,
            time.perf_counter() - inicio, error,
        )

    # Contención: el archivo debe quedar dentro de la base de memoria.
    # Se verifica ANTES de tocar loader, backend vectorial y manifiesto.
    rel_contenida = _resolver_contenida_en_base(ruta, base)
    if rel_contenida is None:
        error = "archivo fuera de la base de memoria"
        log_seguridad("INDEX_FILE_REJECTED", f"{ruta}: {error}")
        return IndexResult(
            os.path.basename(ruta), STATUS_FAILED, 0,
            time.perf_counter() - inicio, error,
        )

    extension = os.path.splitext(ruta)[1].lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        error = f"extensión no soportada: {extension}"
        log_seguridad("INDEX_FILE_FAILED", f"{ruta}: {error}")
        return IndexResult(
            os.path.basename(ruta), STATUS_FAILED, 0,
            time.perf_counter() - inicio, error,
        )

    manifest = IndexManifest.load(manifest_path)
    resultado = _indexar_en_manifest(ruta, base, manifest)
    try:
        manifest.save(manifest_path)
    except OSError as e:
        # La indexación en ChromaDB ya ocurrió; el manifiesto se puede
        # reconstruir con sincronizar_indice(). Se reporta, no se oculta.
        log_seguridad(
            "INDEX_MANIFEST_SAVE_ERROR",
            f"No se pudo guardar el manifiesto: {type(e).__name__}: {e}",
        )
        resultado.status = STATUS_FAILED
        resultado.error = f"indexado en ChromaDB pero falló el manifiesto: {e}"
    return resultado


def eliminar_documento_indexado(relative_path: str,
                                manifest_path: Optional[str] = None
                                ) -> DeleteResult:
    """
    Retira del índice un documento que ya no existe en disco.

    Elimina sus chunks de ChromaDB (esquema nuevo y antiguo) y su entrada
    del manifiesto. Es idempotente y no afecta documentos con nombres
    similares en otras carpetas.

    Returns:
        DeleteResult con status "deleted", "not_found" o "failed".
    """
    inicio = time.perf_counter()
    rel = _normalizar_ruta_relativa(relative_path)

    try:
        eliminados = eliminar_documento(
            rel, rutas_legacy=_variantes_ruta_legacy(rel)
        )
    except Exception as e:
        duracion = time.perf_counter() - inicio
        error = f"{type(e).__name__}: {e}"
        log_seguridad("INDEX_DELETE_FAILED", f"{rel}: {error}")
        return DeleteResult(rel, STATUS_FAILED, 0, duracion, error)

    manifest = IndexManifest.load(manifest_path)
    existia_en_manifest = manifest.remove(rel)
    try:
        manifest.save(manifest_path)
    except OSError as e:
        log_seguridad(
            "INDEX_MANIFEST_SAVE_ERROR",
            f"No se pudo guardar el manifiesto: {type(e).__name__}: {e}",
        )

    duracion = time.perf_counter() - inicio
    if eliminados > 0 or existia_en_manifest:
        log_seguridad(
            "INDEX_DOCUMENT_REMOVED",
            f"{rel}: {eliminados} chunks eliminados",
        )
        return DeleteResult(rel, STATUS_DELETED, eliminados, duracion)
    return DeleteResult(rel, STATUS_NOT_FOUND, 0, duracion)


def sincronizar_indice(memoria_base: Optional[str] = None,
                       manifest_path: Optional[str] = None
                       ) -> SyncResult:
    """
    Recorre la biblioteca y procesa SOLO las diferencias respecto del
    manifiesto: indexa nuevos, reindexa modificados, omite sin cambios,
    retira eliminados y reporta fallidos sin detenerse.

    La decisión definitiva es el SHA-256 del contenido; tamaño y mtime
    sólo se usan como atajo para no releer archivos intactos.
    """
    return _sincronizar(memoria_base, manifest_path, forzar=False)


def reconstruir_indice_completo(memoria_base: Optional[str] = None,
                                manifest_path: Optional[str] = None
                                ) -> SyncResult:
    """
    Reindexa TODOS los documentos de la biblioteca (modo "rebuild").

    Operación explícita de mantenimiento: la ingestión normal de un
    archivo nuevo NO debe invocarla. No borra la base vectorial;
    reemplaza cada documento por identidad estable y retira los que
    ya no existen en disco.
    """
    return _sincronizar(memoria_base, manifest_path, forzar=True)


def _sincronizar(memoria_base: Optional[str],
                 manifest_path: Optional[str],
                 forzar: bool) -> SyncResult:
    inicio = time.perf_counter()
    base = memoria_base or MEMORIA_BASE
    modo = "rebuild" if forzar else "sync"
    resultado = SyncResult(mode=modo)

    log_seguridad("INDEX_SYNC_STARTED", f"modo={modo} base={base}")

    if not os.path.exists(base):
        log_seguridad("INDEX_SYNC_FAILED", f"No existe la carpeta {base}")
        resultado.duration_seconds = time.perf_counter() - inicio
        return resultado

    manifest = IndexManifest.load(manifest_path)
    encontrados: Set[str] = set()

    for ruta in _iter_archivos(base):
        rel = _ruta_relativa(ruta, base)
        encontrados.add(rel)
        resultado.scanned += 1

        if not forzar:
            entry = manifest.get(rel)
            if entry is not None:
                try:
                    stat = os.stat(ruta)
                except OSError as e:
                    resultado.failed += 1
                    resultado.items.append(IndexResult(
                        rel, STATUS_FAILED, 0, 0.0,
                        f"{type(e).__name__}: {e}",
                    ))
                    continue

                # Atajo: tamaño y mtime intactos -> no releer ni recalcular.
                if (entry.size_bytes == stat.st_size
                        and entry.modified_time_ns == stat.st_mtime_ns):
                    resultado.skipped_unchanged += 1
                    resultado.items.append(IndexResult(rel, STATUS_SKIPPED))
                    log_seguridad("INDEX_DOCUMENT_SKIPPED", rel)
                    continue

                # Decisión definitiva: SHA-256 del contenido.
                try:
                    digest = _sha256_archivo(ruta)
                except OSError as e:
                    resultado.failed += 1
                    resultado.items.append(IndexResult(
                        rel, STATUS_FAILED, 0, 0.0,
                        f"{type(e).__name__}: {e}",
                    ))
                    continue

                if digest == entry.content_sha256:
                    # Sólo cambió el mtime: actualizar el atajo, no reindexar.
                    entry.size_bytes = stat.st_size
                    entry.modified_time_ns = stat.st_mtime_ns
                    resultado.skipped_unchanged += 1
                    resultado.items.append(IndexResult(rel, STATUS_SKIPPED))
                    log_seguridad("INDEX_DOCUMENT_SKIPPED", rel)
                    continue

                item = _indexar_en_manifest(ruta, base, manifest)
                if item.status == STATUS_INDEXED:
                    resultado.reindexed_modified += 1
                else:
                    resultado.failed += 1
                resultado.items.append(item)
                continue

        # Nuevo (o rebuild forzado de un conocido)
        conocido = manifest.get(rel) is not None
        item = _indexar_en_manifest(ruta, base, manifest)
        if item.status == STATUS_INDEXED:
            if forzar and conocido:
                resultado.reindexed_modified += 1
            elif forzar:
                resultado.indexed_new += 1
            elif conocido:
                resultado.reindexed_modified += 1
            else:
                resultado.indexed_new += 1
        else:
            resultado.failed += 1
        resultado.items.append(item)

    # Documentos registrados que ya no están en disco -> retirar del índice
    for rel in sorted(set(manifest.documents.keys()) - encontrados):
        try:
            eliminados = eliminar_documento(
                rel, rutas_legacy=_variantes_ruta_legacy(rel)
            )
        except Exception as e:
            resultado.failed += 1
            resultado.items.append(IndexResult(
                rel, STATUS_FAILED, 0, 0.0, f"{type(e).__name__}: {e}",
            ))
            log_seguridad("INDEX_DELETE_FAILED", f"{rel}: {type(e).__name__}: {e}")
            continue
        manifest.remove(rel)
        resultado.removed_deleted += 1
        resultado.items.append(IndexResult(rel, STATUS_DELETED, eliminados))
        log_seguridad("INDEX_DOCUMENT_REMOVED", f"{rel}: {eliminados} chunks")

    try:
        manifest.save(manifest_path)
    except OSError as e:
        log_seguridad(
            "INDEX_MANIFEST_SAVE_ERROR",
            f"No se pudo guardar el manifiesto: {type(e).__name__}: {e}",
        )
        resultado.failed += 1
        resultado.items.append(IndexResult(
            "(manifiesto)", STATUS_FAILED, 0, 0.0,
            f"error guardando manifiesto: {e}",
        ))

    resultado.duration_seconds = time.perf_counter() - inicio
    log_seguridad(
        "INDEX_SYNC_COMPLETED",
        f"modo={modo} escaneados={resultado.scanned} nuevos={resultado.indexed_new} "
        f"modificados={resultado.reindexed_modified} omitidos={resultado.skipped_unchanged} "
        f"eliminados={resultado.removed_deleted} fallidos={resultado.failed} "
        f"duracion={resultado.duration_seconds:.3f}s",
    )
    return resultado


# ============================================
# ALIAS DE COMPATIBILIDAD
# ============================================

def construir_indice(memoria_base: Optional[str] = None,
                     manifest_path: Optional[str] = None):
    """
    Alias de compatibilidad histórica: ejecuta una RECONSTRUCCIÓN COMPLETA
    explícita y devuelve la lista de archivos indexados (contrato anterior).

    Para el mantenimiento incremental habitual, usar sincronizar_indice().
    """
    print("🔄 Reconstrucción completa del índice (todos los documentos)...")
    resultado = reconstruir_indice_completo(
        memoria_base=memoria_base, manifest_path=manifest_path
    )
    for item in resultado.items:
        if item.status == STATUS_INDEXED:
            print(f"   ✅ {item.path}: {item.chunk_count} chunks")
        elif item.status == STATUS_DELETED:
            print(f"   🗑️ {item.path}: retirado ({item.chunk_count} chunks)")
        elif item.status == STATUS_FAILED:
            print(f"   ❌ {item.path}: {item.error}")
    indexados = [i.path for i in resultado.items if i.status == STATUS_INDEXED]
    print(
        f"\n✅ Reconstrucción completa: {len(indexados)} archivos indexados, "
        f"{resultado.removed_deleted} retirados, {resultado.failed} fallidos "
        f"en {resultado.duration_seconds:.1f}s"
    )
    return indexados


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 ATLAS INDEXER - Reconstruyendo índice semántico completo")
    print("=" * 60)
    archivos = construir_indice()
    print(f"\n📊 Total archivos indexados: {len(archivos)}")
    print("=" * 60)
