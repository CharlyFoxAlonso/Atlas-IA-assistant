"""
core/index_consistency.py
Verificador de consistencia de solo lectura (IDX-C1) para Atlas v4.1.

Clasifica el estado del índice comparando las tres capas definidas por la
SDD `docs/spec/atlas-v4.1-incremental-indexing-sdd.md` (secciones 5-7, 10-11):
source documents (filesystem), manifiesto (index_manifest.json) y ChromaDB
(colección atlas_rag). Produce un `ConsistencyReport` con el estado
observado, el estado publicado y las divergencias por categoría.

Contrato de solo lectura (SDD §7):
1. No escribe, renombra, respalda, borra ni repara nada.
2. No invoca `IndexManifest.load` (respaldaría un manifiesto corrupto):
   el manifiesto se inspecciona por vía de lectura no mutante (JSON crudo
   + validación estructural propia). La corrupción se reporta como
   `manifest_corrupt` y un schema no soportado como
   `manifest_schema_incompatible`, sin crear `.bak`.
3. No crea almacenamiento Chroma: usa el adaptador interno
   `core.vector_store._abrir_coleccion_existente` (solo colecciones
   existentes, sin get_or_create ni PersistentClient sobre rutas
   inexistentes).
4. No embebe, no indexa y no contacta proveedores: usa identidades,
   metadatos, estadísticas del filesystem y metadatos de Chroma.
5. Reporta corrupción o indisponibilidad sin convertirlas en un estado
   vacío saludable (`UNAVAILABLE` nunca deriva en `HEALTHY_EMPTY`).
6. Nunca lanza por condiciones de datos: se reportan en el reporte.

Decisiones locales documentadas (para revisión del Auditor):
- Los fallos de `os.stat` sobre una fuente recién enumerada se clasifican
  como `source_absent_manifest_present` (fuente no observable en el
  momento de la verificación; la existencia de las fuentes pertenece al
  filesystem, SDD §3).
- Los fallos de lectura SHA-256 (archivo legible para stat pero no para
  contenido) se reportan como limitación activa de verificación: se
  registra la clave `"verification_limitation"` en `divergences` (extensión
  documentada del dict, NO un miembro del enum congelado) y fuerzan
  `DEGRADED` (SDD §5: "limitaciones activas de verificación").
- Los chunks sin identidad útil (`doc_id` ni `ruta`) o cuya identidad no
  corresponde a fuente ni entrada se reportan como huérfanos
  (`source_absent_chroma_present`, SDD §6), nunca se purgan.
- `divergences` contiene solo categorías accionables o limitaciones; las
  categorías nominales (`source_and_manifest_and_chroma_present`,
  `all_layers_empty`) no se registran (el estado saludable se comunica con
  `observed_state`).
- El inventario de fuentes se implementa localmente usando la política de
  `core.config` (`INDEX_SUPPORTED_EXTENSIONS`, `INDEX_IGNORED_DIRS`), sin
  importar helpers privados de `core.indexer` ni elevarlos a API pública
  (SDD §10).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core import config
from core.index_manifest import ManifestEntry
from core.index_writer_lock import inspect_index_writer_state
from core.system.paths import LegacyVectorStoreError, validate_vector_store_path
from core.vector_store import (
    ChromaReadStatus,
    IDX_PUBLIC_ERROR_MESSAGES,
    _abrir_coleccion_existente,
    _tipo_error_seguro,
)

# Límite de la muestra de chunks huérfanos incluida en el reporte.
ORPHAN_SAMPLE_LIMIT = 10

# Clave documentada para limitaciones activas de verificación (ver docstring).
VERIFICATION_LIMITATION = "verification_limitation"


class ConsistencyState(str, Enum):
    """Estados de consistencia del índice (SDD §5)."""

    HEALTHY = "HEALTHY"
    HEALTHY_EMPTY = "HEALTHY_EMPTY"
    INCONSISTENT = "INCONSISTENT"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class DivergenceCategory(str, Enum):
    """Categorías de divergencia requeridas (SDD §6). Identificadores estables."""

    SOURCE_AND_MANIFEST_AND_CHROMA_PRESENT = "source_and_manifest_and_chroma_present"
    SOURCE_AND_MANIFEST_PRESENT_CHROMA_ABSENT = "source_and_manifest_present_chroma_absent"
    SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT = "source_present_manifest_stale_chroma_present"
    SOURCE_PRESENT_MANIFEST_METADATA_STALE_CONTENT_SAME = "source_present_manifest_metadata_stale_content_same"
    SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_PRESENT = "source_present_manifest_absent_chroma_present"
    SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_ABSENT = "source_present_manifest_absent_chroma_absent"
    SOURCE_ABSENT_MANIFEST_PRESENT = "source_absent_manifest_present"
    SOURCE_ABSENT_CHROMA_PRESENT = "source_absent_chroma_present"
    MANIFEST_ABSENT = "manifest_absent"
    MANIFEST_CORRUPT = "manifest_corrupt"
    MANIFEST_SCHEMA_INCOMPATIBLE = "manifest_schema_incompatible"
    CHROMA_ABSENT = "chroma_absent"
    CHROMA_COLLECTION_ABSENT = "chroma_collection_absent"
    CHROMA_UNAVAILABLE = "chroma_unavailable"
    MANIFEST_AND_CHROMA_EMPTY_SOURCES_PRESENT = "manifest_and_chroma_empty_sources_present"
    ALL_LAYERS_EMPTY = "all_layers_empty"


# Categorías nominales (no se registran en `divergences`).
_CATEGORIAS_NOMINALES = {
    DivergenceCategory.SOURCE_AND_MANIFEST_AND_CHROMA_PRESENT.value,
    DivergenceCategory.ALL_LAYERS_EMPTY.value,
}

_CATEGORIAS_ACCIONABLES = {
    categoria.value
    for categoria in DivergenceCategory
    if categoria.value not in _CATEGORIAS_NOMINALES
}


_ISSUE_COMPONENTS = {
    "legacy_vector_store_detected": "paths",
    "chroma_backend_unavailable": "chroma",
    "chroma_collection_read_failed": "chroma",
    "consistency_verification_failed": "consistency",
    "raw_chroma_error_rejected": "chroma",
}


@dataclass(frozen=True)
class ConsistencyIssue:
    code: str
    component: str
    public_message: str
    error_type: str


class _ChromaCollectionReadFailed(RuntimeError):
    def __init__(self, error_type: str):
        super().__init__()
        self.error_type = _tipo_error_seguro(error_type)


@dataclass(frozen=True)
class ConsistencyReport:
    """Reporte de consistencia del índice (IDX-C1).

    Campos:
        observed_state: Estado derivado del modelo SDD §5 (nunca se persiste).
        published_state: Estado publicado considerando el estado del escritor
            (SDD §11.2): mientras `writer_state_known=False`, un resultado
            nominal HEALTHY o HEALTHY_EMPTY se publica como DEGRADED.
        divergences: Categorías accionables detectadas (clave -> cantidad).
            Puede incluir `verification_limitation` (extensión documentada).
        orphan_sample: Muestra de hasta ORPHAN_SAMPLE_LIMIT ids de chunks
            huérfanos; `orphan_count` es el total.
        path_error: Mensaje público allowlisted si la ruta vectorial
            configurada no pudo validarse (política INV-4); en ese caso el
            almacenamiento vectorial no se inspecciona.
        issues: Errores observados durante la verificación (backend Chroma
            inaccesible, path_error), renderizados desde allowlist para no
            exponer rutas absolutas privadas (OBS-02).
    """

    observed_state: str
    published_state: str
    divergences: Dict[str, int] = field(default_factory=dict)
    orphan_sample: Tuple[str, ...] = ()
    orphan_count: int = 0
    sources_count: int = 0
    manifest_entries_count: int = 0
    chunk_count: int = 0
    manifest_present: bool = False
    manifest_corrupt: bool = False
    manifest_schema_incompatible: bool = False
    chroma_root_present: bool = False
    chroma_collection_present: bool = False
    chroma_unavailable: bool = False
    path_error: Optional[str] = None
    issues: Tuple[str, ...] = ()
    writer_state_known: bool = False
    writer_active: bool = False
    possibly_transient: bool = True
    checked_at: str = ""


@dataclass(frozen=True)
class _ConsistencySnapshot:
    """Fotografía privada y read-only compartida por IDX-C1 e IDX-C3."""

    base: str
    manifest_path: str
    chroma_path: str
    collection_name: str
    report: ConsistencyReport
    sources: Tuple[str, ...]
    manifest_entries: Dict[str, ManifestEntry]
    manifest_malformed_entries: int
    chunks_by_identity: Dict[str, Tuple[str, ...]]
    orphan_ids: Tuple[str, ...]
    categories_by_identity: Dict[str, Optional[str]]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sumar(divergencias: Dict[str, int], categoria: DivergenceCategory,
           cantidad: int = 1) -> None:
    clave = categoria.value
    divergencias[clave] = divergencias.get(clave, 0) + cantidad


def _crear_issue(code: str, error: object = None) -> ConsistencyIssue:
    """Construye un issue público desde la allowlist de Atlas."""
    if code not in IDX_PUBLIC_ERROR_MESSAGES or code not in _ISSUE_COMPONENTS:
        code = "consistency_verification_failed"
        error = None
    return ConsistencyIssue(
        code=code,
        component=_ISSUE_COMPONENTS[code],
        public_message=IDX_PUBLIC_ERROR_MESSAGES[code],
        error_type=_tipo_error_seguro(error or "Exception"),
    )


def _render_issue(issue: ConsistencyIssue) -> str:
    return f"{issue.code}: {issue.public_message} [{issue.error_type}]"


def _agregar_issue(issues: List[ConsistencyIssue], issue: ConsistencyIssue) -> None:
    clave = (issue.code, issue.component, issue.error_type)
    if all((i.code, i.component, i.error_type) != clave for i in issues):
        issues.append(issue)


def _inventariar_fuentes(memoria_base: str) -> List[str]:
    """Recorre BASE_MEMORIA con el mismo filtro que el indexador.

    Reutiliza la política de `core.config` (extensiones soportadas y
    carpetas ignoradas); no duplica literales ni importa helpers privados
    de `core.indexer` (SDD §10).
    """
    fuentes: List[str] = []
    if not os.path.isdir(memoria_base):
        return fuentes
    for root, dirs, files in os.walk(memoria_base):
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") and d not in config.INDEX_IGNORED_DIRS
        ]
        for archivo in sorted(files):
            extension = os.path.splitext(archivo)[1].lower()
            if extension in config.INDEX_SUPPORTED_EXTENSIONS:
                ruta_abs = os.path.join(root, archivo)
                rel = os.path.relpath(ruta_abs, memoria_base).replace("\\", "/")
                fuentes.append(rel)
    return sorted(fuentes)


def _sha256_archivo(ruta: str) -> str:
    """SHA-256 del contenido, leído por bloques (solo lectura)."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


@dataclass
class _ManifestLectura:
    """Lectura no mutante del manifiesto (SDD §7.2)."""

    present: bool = False
    corrupt: bool = False
    schema_incompatible: bool = False
    entries: Dict[str, ManifestEntry] = field(default_factory=dict)
    malformed_entries: int = 0


def _leer_manifiesto_sin_mutacion(manifest_path: str) -> _ManifestLectura:
    """Inspecciona el manifiesto por vía de lectura no mutante.

    Nunca respalda ni reconstruye (no crea `.bak`): un JSON inválido o una
    estructura no conforme se reportan como corruptos; un JSON legible con
    `schema_version` no soportado se reporta como incompatible. Las
    entradas malformadas aislables se descartan y se cuentan (→ DEGRADED,
    SDD §5).
    """
    ruta = Path(manifest_path)
    if not ruta.is_file():
        return _ManifestLectura()

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return _ManifestLectura(present=True, corrupt=True)

    if not isinstance(raw, dict) or not isinstance(raw.get("documents", {}), dict):
        return _ManifestLectura(present=True, corrupt=True)

    try:
        schema = int(raw.get("schema_version", -1))
    except (TypeError, ValueError):
        return _ManifestLectura(present=True, corrupt=True)
    if schema != config.INDEX_SCHEMA_VERSION:
        return _ManifestLectura(present=True, schema_incompatible=True)

    lectura = _ManifestLectura(present=True)
    for rel_path, data in raw["documents"].items():
        try:
            entry = ManifestEntry.from_dict(data)
        except (KeyError, TypeError, ValueError):
            lectura.malformed_entries += 1
            continue
        if not entry.relative_path:
            lectura.malformed_entries += 1
            continue
        lectura.entries[entry.relative_path] = entry
    return lectura


def _leer_chunks_por_documento(collection) -> Tuple[Dict[str, List[str]], List[str], int]:
    """Lee ids y metadatos de la colección existente sin embeddings.

    Returns:
        (chunks_por_doc, orphan_ids, total): mapa identidad normalizada ->
        ids de chunks, ids de chunks sin identidad útil, total de chunks.
    """
    try:
        resultado = collection.get(include=["metadatas"])
    except Exception as exc:
        raise _ChromaCollectionReadFailed(_tipo_error_seguro(exc)) from exc

    ids = resultado.get("ids", []) or []
    metadatas = resultado.get("metadatas", []) or []
    chunks_por_doc: Dict[str, List[str]] = {}
    orphan_ids: List[str] = []
    for cid, md in zip(ids, metadatas):
        if not isinstance(md, dict):
            orphan_ids.append(cid)
            continue
        identidad = md.get("doc_id") or md.get("ruta")
        if not identidad:
            orphan_ids.append(cid)
            continue
        rel = str(identidad).replace("\\", "/")
        chunks_por_doc.setdefault(rel, []).append(cid)
    return chunks_por_doc, orphan_ids, len(ids)


def _clasificar_fuente(rel: str, entry: Optional[ManifestEntry], chunks: int,
                       ruta_abs: str, divergencias: Dict[str, int]) -> Optional[str]:
    """Clasifica una fuente contra su entrada y sus chunks (SDD §6)."""
    if entry is None:
        categoria = (
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_PRESENT
            if chunks > 0
            else DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_ABSENT
        )
        _sumar(divergencias, categoria)
        return categoria.value

    if chunks == 0:
        categoria = DivergenceCategory.SOURCE_AND_MANIFEST_PRESENT_CHROMA_ABSENT
        _sumar(divergencias, categoria)
        return categoria.value

    try:
        stat = os.stat(ruta_abs)
    except OSError:
        # Fuente no observable en el momento de la verificación: la
        # existencia de las fuentes pertenece al filesystem (SDD §3), por
        # lo que se trata como ausente.
        categoria = DivergenceCategory.SOURCE_ABSENT_MANIFEST_PRESENT
        _sumar(divergencias, categoria)
        return categoria.value

    if stat.st_size == entry.size_bytes and stat.st_mtime_ns == entry.modified_time_ns:
        # Atajo: tamaño y mtime intactos -> huella vigente sin releer (SDD §7.4).
        return None

    try:
        digest = _sha256_archivo(ruta_abs)
    except OSError:
        # Contenido no legible: limitación activa de verificación (SDD §5).
        divergencias[VERIFICATION_LIMITATION] = (
            divergencias.get(VERIFICATION_LIMITATION, 0) + 1
        )
        return VERIFICATION_LIMITATION

    if digest == entry.content_sha256:
        categoria = DivergenceCategory.SOURCE_PRESENT_MANIFEST_METADATA_STALE_CONTENT_SAME
        _sumar(divergencias, categoria)
        return categoria.value
    else:
        categoria = DivergenceCategory.SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT
        _sumar(divergencias, categoria)
        return categoria.value

    return None


def _capturar_snapshot_consistencia(
    memoria_base: Optional[str] = None,
    manifest_path: Optional[str] = None,
    chroma_path: Optional[str] = None,
    collection_name: Optional[str] = None,
    lock_path: Optional[str] = None,
) -> _ConsistencySnapshot:
    """Verifica la consistencia del índice en modo SOLO LECTURA (IDX-C1).

    Args:
        memoria_base: Raíz de los source documents (default config.BASE_MEMORIA).
        manifest_path: Ruta del manifiesto (default config.INDEX_MANIFEST_PATH).
        chroma_path: Ruta del almacenamiento vectorial configurado
            (default config.CHROMA_PATH); se valida con
            `validate_vector_store_path` (política INV-4).
        collection_name: Nombre de la colección (default config.COLLECTION_NAME).

    Returns:
        _ConsistencySnapshot. Nunca lanza por condiciones de datos.
    """
    base = memoria_base or config.BASE_MEMORIA
    manifest_ruta = manifest_path or config.INDEX_MANIFEST_PATH
    chroma_ruta = chroma_path or config.CHROMA_PATH
    nombre_coleccion = collection_name or config.COLLECTION_NAME

    checked_at = _utc_now_iso()
    divergencias: Dict[str, int] = {}
    path_error: Optional[str] = None
    path_issue: Optional[ConsistencyIssue] = None
    issues: List[ConsistencyIssue] = []

    # Valores por defecto para el reporte (se rellenan durante la verificación).
    fuentes: List[str] = []
    manifest = _ManifestLectura()
    chroma = ChromaReadStatus()
    chunks_por_doc: Dict[str, List[str]] = {}
    orphan_ids: List[str] = []
    total_chunks = 0
    orphan_count = 0
    orphan_sample: Tuple[str, ...] = ()
    categorias_por_identidad: Dict[str, Optional[str]] = {}

    try:
        # 1. Ruta vectorial autoritativa (solo lectura; política INV-4).
        try:
            chroma_resuelto = str(validate_vector_store_path(chroma_ruta))
        except LegacyVectorStoreError as e:
            path_issue = _crear_issue("legacy_vector_store_detected", e)
            chroma_resuelto = None

        # 2. Inventario de fuentes con el filtro de config.
        fuentes = _inventariar_fuentes(base)

        # 3. Manifiesto por vía de lectura no mutante.
        manifest = _leer_manifiesto_sin_mutacion(manifest_ruta)

        # 4. Acceso Chroma de solo lectura (adaptador interno).
        if chroma_resuelto is not None:
            acceso_chroma = _abrir_coleccion_existente(
                chroma_resuelto, nombre_coleccion
            )
            chroma = acceso_chroma.status
            coleccion = acceso_chroma._collection
            if coleccion is not None and not chroma.unavailable:
                try:
                    chunks_por_doc, orphan_ids, total_chunks = _leer_chunks_por_documento(
                        coleccion
                    )
                except _ChromaCollectionReadFailed as e:
                    # La colección existe pero no se puede leer: backend
                    # inaccesible (SDD §6 chroma_unavailable).
                    chroma = ChromaReadStatus(
                        root_present=True,
                        collection_present=True,
                        unavailable=True,
                        error_code="chroma_collection_read_failed",
                        error_type=e.error_type,
                    )
                except Exception as exc:
                    chroma = ChromaReadStatus(
                        root_present=True,
                        collection_present=True,
                        unavailable=True,
                        error_code="chroma_collection_read_failed",
                        error_type=_tipo_error_seguro(exc),
                    )

        # 5. Clasificación por fuente.
        for rel in fuentes:
            ruta_abs = os.path.join(base, rel.replace("/", os.sep))
            categorias_por_identidad[rel] = _clasificar_fuente(
                rel,
                manifest.entries.get(rel),
                len(chunks_por_doc.get(rel, [])),
                ruta_abs,
                divergencias,
            )

        # 6. Entradas de manifiesto sin fuente en disco.
        for rel in sorted(set(manifest.entries) - set(fuentes)):
            categorias_por_identidad[rel] = (
                DivergenceCategory.SOURCE_ABSENT_MANIFEST_PRESENT.value
            )
            _sumar(divergencias, DivergenceCategory.SOURCE_ABSENT_MANIFEST_PRESENT)

        # 7. Chunks huérfanos: sin fuente y sin entrada de manifiesto.
        huérfanos = list(orphan_ids)
        for rel, ids in chunks_por_doc.items():
            if rel not in fuentes and rel not in manifest.entries:
                huérfanos.extend(ids)
        orphan_ids = huérfanos
        orphan_count = len(orphan_ids)
        # Orden determinista (OBS-04): no depende del orden de inserción de
        # dicts, de Chroma ni de los fakes.
        orphan_sample = tuple(sorted(orphan_ids)[:ORPHAN_SAMPLE_LIMIT])
        if orphan_count:
            _sumar(
                divergencias,
                DivergenceCategory.SOURCE_ABSENT_CHROMA_PRESENT,
                orphan_count,
            )

        # 8. Categorías globales de capa.
        manifest_vacio_valido = (
            manifest.present
            and not manifest.corrupt
            and not manifest.schema_incompatible
            and len(manifest.entries) == 0
        )
        manifest_ausente_o_vacio = not manifest.present or manifest_vacio_valido
        chroma_vacio = (
            chroma.root_present
            and chroma.collection_present
            and not chroma.unavailable
            and total_chunks == 0
        )
        chroma_ausente_o_vacio = (
            not chroma.root_present or not chroma.collection_present or chroma_vacio
        )
        capas_sin_datos = manifest_ausente_o_vacio and chroma_ausente_o_vacio

        if fuentes and capas_sin_datos:
            _sumar(divergencias, DivergenceCategory.MANIFEST_AND_CHROMA_EMPTY_SOURCES_PRESENT)
        elif not fuentes and capas_sin_datos:
            # all_layers_empty: nominal HEALTHY_EMPTY, no se registra.
            pass
        else:
            if not manifest.present:
                if fuentes or total_chunks > 0:
                    _sumar(divergencias, DivergenceCategory.MANIFEST_ABSENT)
            elif manifest.corrupt:
                _sumar(divergencias, DivergenceCategory.MANIFEST_CORRUPT)
            elif manifest.schema_incompatible:
                _sumar(divergencias, DivergenceCategory.MANIFEST_SCHEMA_INCOMPATIBLE)

            if chroma.unavailable:
                _sumar(divergencias, DivergenceCategory.CHROMA_UNAVAILABLE)
            elif not chroma.root_present:
                if fuentes or manifest.entries:
                    _sumar(divergencias, DivergenceCategory.CHROMA_ABSENT)
            elif not chroma.collection_present:
                if fuentes or manifest.entries:
                    _sumar(divergencias, DivergenceCategory.CHROMA_COLLECTION_ABSENT)

        # 9. Derivación del estado (SDD §5 reglas 1-9, prioridad estricta).
        if (
            manifest.corrupt
            or manifest.schema_incompatible
            or chroma.unavailable
        ):
            observed = ConsistencyState.UNAVAILABLE
        elif any(clave in _CATEGORIAS_ACCIONABLES for clave in divergencias):
            observed = ConsistencyState.INCONSISTENT
        elif (
            manifest.malformed_entries > 0
            or divergencias.get(VERIFICATION_LIMITATION, 0) > 0
            or path_issue is not None
        ):
            observed = ConsistencyState.DEGRADED
        elif (
            not fuentes
            and not manifest.entries
            and total_chunks == 0
        ):
            observed = ConsistencyState.HEALTHY_EMPTY
        else:
            observed = ConsistencyState.HEALTHY

    except Exception as exc:  # pragma: no cover - red de seguridad del contrato
        # Contrato: el verificador nunca lanza por condiciones de datos.
        # Un fallo interno inesperado se reporta como limitación activa de
        # verificación (DEGRADED), no como excepción.
        divergencias = {VERIFICATION_LIMITATION: 1}
        observed = ConsistencyState.DEGRADED
        path_issue = _crear_issue("consistency_verification_failed", exc)

    # Frontera final del reporte (OBS-02): no confiar en adaptadores/fakes.
    issues_renderizados: List[str] = []
    issues_estructurados: List[ConsistencyIssue] = []
    for issue in issues:
        _agregar_issue(issues_estructurados, issue)
    if chroma.error_code:
        _agregar_issue(
            issues_estructurados,
            _crear_issue(chroma.error_code, chroma.error_type),
        )
    if path_issue:
        path_error = _render_issue(path_issue)
        _agregar_issue(issues_estructurados, path_issue)
    for issue in issues_estructurados:
        issues_renderizados.append(_render_issue(issue))

    # IDX-C2: read-only writer inspection degrades only nominal states when
    # the writer is active or the lock state is unknown.
    writer_state = inspect_index_writer_state(
        lock_path=lock_path,
        manifest_path=manifest_ruta,
    )
    writer_state_known = writer_state.writer_state_known
    writer_active = writer_state.writer_active
    possibly_transient = writer_state.possibly_transient
    if (
        observed in (ConsistencyState.HEALTHY, ConsistencyState.HEALTHY_EMPTY)
        and (not writer_state_known or writer_active)
    ):
        published = ConsistencyState.DEGRADED
    else:
        published = observed

    report = ConsistencyReport(
        observed_state=observed.value,
        published_state=published.value,
        divergences=dict(sorted(divergencias.items())),
        orphan_sample=orphan_sample,
        orphan_count=orphan_count,
        sources_count=len(fuentes),
        manifest_entries_count=len(manifest.entries),
        chunk_count=total_chunks,
        manifest_present=manifest.present,
        manifest_corrupt=manifest.corrupt,
        manifest_schema_incompatible=manifest.schema_incompatible,
        chroma_root_present=chroma.root_present,
        chroma_collection_present=chroma.collection_present,
        chroma_unavailable=chroma.unavailable,
        path_error=path_error,
        issues=tuple(issues_renderizados),
        writer_state_known=writer_state_known,
        writer_active=writer_active,
        possibly_transient=possibly_transient,
        checked_at=checked_at,
    )
    return _ConsistencySnapshot(
        base=base,
        manifest_path=manifest_ruta,
        chroma_path=chroma_ruta,
        collection_name=nombre_coleccion,
        report=report,
        sources=tuple(sorted(fuentes)),
        manifest_entries=dict(manifest.entries),
        manifest_malformed_entries=manifest.malformed_entries,
        chunks_by_identity={
            identidad: tuple(ids)
            for identidad, ids in chunks_por_doc.items()
        },
        orphan_ids=tuple(orphan_ids),
        categories_by_identity=dict(categorias_por_identidad),
    )


def verificar_consistencia(
    memoria_base: Optional[str] = None,
    manifest_path: Optional[str] = None,
    chroma_path: Optional[str] = None,
    collection_name: Optional[str] = None,
    lock_path: Optional[str] = None,
) -> ConsistencyReport:
    """API pública read-only de IDX-C1, preservada sin cambios."""
    return _capturar_snapshot_consistencia(
        memoria_base=memoria_base,
        manifest_path=manifest_path,
        chroma_path=chroma_path,
        collection_name=collection_name,
        lock_path=lock_path,
    ).report
