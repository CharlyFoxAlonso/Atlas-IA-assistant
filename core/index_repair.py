"""Reparación conservadora del índice (IDX-C3).

Este módulo es el único escritor de la reparación. El diagnóstico y la
confirmación consumen la fotografía read-only de ``core.index_consistency``;
no reproducen su lógica ni crean una segunda semántica de consistencia.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Tuple

from core import config
from core.index_consistency import (
    ConsistencyState,
    DivergenceCategory,
    VERIFICATION_LIMITATION,
    _ConsistencySnapshot,
    _capturar_snapshot_consistencia,
    _sha256_archivo,
)
from core.index_manifest import IndexManifest, ManifestEntry
from core.index_writer_lock import (
    IndexWriterBusyError,
    PUBLIC_BUSY_MESSAGES,
    acquire_index_writer_lock,
    derive_lock_path_for_manifest,
)
from core.indexer import (
    STATUS_DELETED,
    STATUS_INDEXED,
    STATUS_NOT_FOUND,
    DeleteResult,
    IndexResult,
    eliminar_documento_indexado,
    indexar_archivo,
)
from core.vector_store import _tipo_error_seguro


_ALLOWED_CATEGORIES = frozenset(
    category.value for category in DivergenceCategory
) | {"unknown"}
_ALLOWED_STATUSES = frozenset(
    {"attempted", "repaired", "failed", "still_inconsistent", "skipped"}
)
_ALLOWED_ACTIONS = frozenset(
    {"reindex", "metadata_update", "remove", "remove_manifest_entry", "skip"}
)
_ALLOWED_BLOCKED_REASONS = frozenset(
    {
        "path_error",
        "manifest_corrupt",
        "manifest_schema_incompatible",
        "chroma_unavailable",
        "degraded_diagnosis",
        "unavailable",
        "malformed_manifest_entries",
        "verification_limitation",
        "chroma_collection_read_failed",
        "writer_target_mismatch",
    }
)

_REINDEX_CATEGORIES = frozenset(
    {
        DivergenceCategory.SOURCE_AND_MANIFEST_PRESENT_CHROMA_ABSENT.value,
        DivergenceCategory.SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT.value,
        DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_PRESENT.value,
        DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_ABSENT.value,
        DivergenceCategory.MANIFEST_ABSENT.value,
        DivergenceCategory.CHROMA_ABSENT.value,
        DivergenceCategory.CHROMA_COLLECTION_ABSENT.value,
        DivergenceCategory.MANIFEST_AND_CHROMA_EMPTY_SOURCES_PRESENT.value,
    }
)
_METADATA_STALE_CATEGORY = (
    DivergenceCategory.SOURCE_PRESENT_MANIFEST_METADATA_STALE_CONTENT_SAME.value
)
_CONTENT_STALE_CATEGORY = (
    DivergenceCategory.SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT.value
)
_SOURCE_ABSENT_MANIFEST_CATEGORY = (
    DivergenceCategory.SOURCE_ABSENT_MANIFEST_PRESENT.value
)
_SOURCE_ABSENT_CHROMA_CATEGORY = (
    DivergenceCategory.SOURCE_ABSENT_CHROMA_PRESENT.value
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _category_value(category: object) -> str:
    value = getattr(category, "value", category)
    return value if isinstance(value, str) and value in _ALLOWED_CATEGORIES else "unknown"


@dataclass(frozen=True)
class RepairItem:
    """Resultado público de una operación sobre una identidad."""

    identity: str
    category: str
    action: str
    status: str
    error_type: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "identity", str(self.identity))
        object.__setattr__(self, "category", _category_value(self.category))
        action = self.action if self.action in _ALLOWED_ACTIONS else "skip"
        status = self.status if self.status in _ALLOWED_STATUSES else "failed"
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "status", status)
        if self.error_type is not None:
            object.__setattr__(self, "error_type", _tipo_error_seguro(self.error_type))
        elif status == "failed":
            object.__setattr__(self, "error_type", "Exception")

    def to_dict(self) -> dict:
        return {
            "identity": self.identity,
            "category": self.category,
            "action": self.action,
            "status": self.status,
            "error_type": self.error_type,
        }


@dataclass(frozen=True)
class RepairReport:
    """Reporte serializable y sanitizado de IDX-C3."""

    pre_state: str
    post_state: str
    post_observed: str
    post_check_performed: bool
    success: bool
    blocked: bool
    blocked_reason: Optional[str]
    busy: bool
    busy_message: Optional[str]
    items: Tuple[RepairItem, ...] = field(default_factory=tuple)
    orphan_count: int = 0
    orphan_sample: Tuple[str, ...] = ()
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        reason = self.blocked_reason if self.blocked_reason in _ALLOWED_BLOCKED_REASONS else None
        object.__setattr__(self, "blocked_reason", reason if self.blocked else None)
        if self.busy:
            message = self.busy_message
            if message not in PUBLIC_BUSY_MESSAGES.values():
                message = PUBLIC_BUSY_MESSAGES["index_writer_busy"]
            object.__setattr__(self, "busy_message", message)
        else:
            object.__setattr__(self, "busy_message", None)
        valid_success = (
            self.post_check_performed
            and self.post_state in {
                ConsistencyState.HEALTHY.value,
                ConsistencyState.HEALTHY_EMPTY.value,
            }
            and not self.blocked
            and not self.busy
            and all(item.status not in {"failed", "still_inconsistent"} for item in self.items)
        )
        object.__setattr__(self, "success", bool(valid_success))

    def to_dict(self) -> dict:
        return {
            "pre_state": self.pre_state,
            "post_state": self.post_state,
            "post_observed": self.post_observed,
            "post_check_performed": self.post_check_performed,
            "success": self.success,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "busy": self.busy,
            "busy_message": self.busy_message,
            "items": [item.to_dict() for item in self.items],
            "orphan_count": self.orphan_count,
            "orphan_sample": list(self.orphan_sample),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
        }


def _safe_result_error_type(result: object) -> str:
    error = getattr(result, "error", None)
    return _tipo_error_seguro(error or "Exception")


def _item_from_index_result(
    identity: str,
    category: object,
    result: IndexResult,
) -> RepairItem:
    if result.status == STATUS_INDEXED:
        return RepairItem(
            identity=identity,
            category=_category_value(category),
            action="reindex",
            status="attempted",
        )
    return RepairItem(
        identity=identity,
        category=_category_value(category),
        action="reindex",
        status="failed",
        error_type=_safe_result_error_type(result),
    )


def _item_from_delete_result(identity: str, result: DeleteResult) -> RepairItem:
    if result.status in {STATUS_DELETED, STATUS_NOT_FOUND}:
        return RepairItem(
            identity=identity,
            category=_SOURCE_ABSENT_MANIFEST_CATEGORY,
            action="remove",
            status="attempted",
        )
    return RepairItem(
        identity=identity,
        category=_SOURCE_ABSENT_MANIFEST_CATEGORY,
        action="remove",
        status="failed",
        error_type=_safe_result_error_type(result),
    )


def _failed_item(identity: str, category: object, action: str, error: Exception) -> RepairItem:
    return RepairItem(
        identity=identity,
        category=_category_value(category),
        action=action,
        status="failed",
        error_type=_tipo_error_seguro(error),
    )


def _reparar_metadata_stale(
    *,
    identity: str,
    ruta_abs: str,
    entry: ManifestEntry,
    base: str,
    manifest_path: str,
    lock_path: str,
) -> RepairItem:
    """Actualiza solo size/mtime cuando el SHA validado sigue vigente."""
    action = "metadata_update"
    try:
        manifest = IndexManifest.load(manifest_path)
        live_entry = manifest.get(identity)

        # La validación de la fuente queda inmediatamente antes de cualquier
        # actualización del manifiesto. Cualquier cambio durante la carga del
        # estado vivo se observa aquí y deriva en reindexación.
        stat_before = os.stat(ruta_abs)
        digest = _sha256_archivo(ruta_abs)
        stat_after = os.stat(ruta_abs)
        if (
            digest != entry.content_sha256
            or stat_before.st_size != stat_after.st_size
            or stat_before.st_mtime_ns != stat_after.st_mtime_ns
        ):
            action = "reindex"
            result = indexar_archivo(
                ruta_abs,
                memoria_base=base,
                manifest_path=manifest_path,
                lock_path=lock_path,
            )
            return _item_from_index_result(
                identity,
                _CONTENT_STALE_CATEGORY,
                result,
            )

        if live_entry is None or live_entry.content_sha256 != digest:
            action = "reindex"
            result = indexar_archivo(
                ruta_abs,
                memoria_base=base,
                manifest_path=manifest_path,
                lock_path=lock_path,
            )
            return _item_from_index_result(
                identity,
                _METADATA_STALE_CATEGORY,
                result,
            )

        live_entry.size_bytes = stat_after.st_size
        live_entry.modified_time_ns = stat_after.st_mtime_ns
        manifest.save(manifest_path)
        return RepairItem(
            identity=identity,
            category=_METADATA_STALE_CATEGORY,
            action="metadata_update",
            status="attempted",
        )
    except Exception as exc:
        return _failed_item(
            identity,
            _METADATA_STALE_CATEGORY,
            action,
            exc,
        )


def _blocked_reason(snapshot: _ConsistencySnapshot) -> Optional[str]:
    report = snapshot.report
    if report.path_error:
        return "path_error"
    if report.manifest_corrupt:
        return "manifest_corrupt"
    if report.manifest_schema_incompatible:
        return "manifest_schema_incompatible"
    if report.chroma_unavailable:
        if any(issue.startswith("chroma_collection_read_failed:") for issue in report.issues):
            return "chroma_collection_read_failed"
        return "chroma_unavailable"
    if snapshot.manifest_malformed_entries:
        return "malformed_manifest_entries"
    if report.divergences.get(VERIFICATION_LIMITATION, 0) > 0:
        return "verification_limitation"
    # El pre-check ocurre bajo el lock propio, por lo que un estado observado
    # nominal puede publicarse DEGRADED únicamente por ese writer activo. La
    # excepción exige que el owner sea conocido y activo: un writer desconocido
    # sigue siendo un diagnóstico inseguro. El snapshot conserva sin excepciones
    # la semántica pública de IDX-C1.
    own_writer_degraded = (
        report.observed_state in {
            ConsistencyState.HEALTHY.value,
            ConsistencyState.HEALTHY_EMPTY.value,
        }
        and report.published_state == ConsistencyState.DEGRADED.value
        and report.writer_state_known
        and report.writer_active
    )
    if report.observed_state == ConsistencyState.DEGRADED.value:
        return "degraded_diagnosis"
    if (
        report.published_state == ConsistencyState.DEGRADED.value
        and not own_writer_degraded
    ):
        return "degraded_diagnosis"
    if report.observed_state == ConsistencyState.UNAVAILABLE.value:
        return "unavailable"
    return None


def _same_resolved_path(left: object, right: object) -> bool:
    return os.path.normcase(
        os.path.abspath(os.path.expanduser(os.fspath(left)))
    ) == os.path.normcase(
        os.path.abspath(os.path.expanduser(os.fspath(right)))
    )


def _writer_target_mismatch(
    *,
    manifest_path: str,
    chroma_path: str,
    collection_name: str,
    lock_path: Optional[str],
) -> bool:
    """Reject targets that the existing writer APIs cannot honor coherently."""
    if not _same_resolved_path(manifest_path, config.INDEX_MANIFEST_PATH):
        return True
    if not _same_resolved_path(chroma_path, config.CHROMA_PATH):
        return True
    if collection_name != config.COLLECTION_NAME:
        return True
    if lock_path is not None:
        expected_lock = derive_lock_path_for_manifest(config.INDEX_MANIFEST_PATH)
        if not _same_resolved_path(lock_path, expected_lock):
            return True
    return False


def _repair_sources(
    snapshot: _ConsistencySnapshot,
    *,
    lock_path: str,
) -> List[RepairItem]:
    items: List[RepairItem] = []
    for identity in snapshot.sources:
        category = snapshot.categories_by_identity.get(identity)
        try:
            if category in _REINDEX_CATEGORIES:
                ruta_abs = os.path.join(
                    snapshot.base,
                    identity.replace("/", os.sep),
                )
                result = indexar_archivo(
                    ruta_abs,
                    memoria_base=snapshot.base,
                    manifest_path=snapshot.manifest_path,
                    lock_path=lock_path,
                )
                items.append(_item_from_index_result(identity, category, result))
            elif category == _METADATA_STALE_CATEGORY:
                entry = snapshot.manifest_entries.get(identity)
                if entry is None:
                    result = indexar_archivo(
                        os.path.join(snapshot.base, identity.replace("/", os.sep)),
                        memoria_base=snapshot.base,
                        manifest_path=snapshot.manifest_path,
                        lock_path=lock_path,
                    )
                    items.append(_item_from_index_result(identity, category, result))
                else:
                    items.append(
                        _reparar_metadata_stale(
                            identity=identity,
                            ruta_abs=os.path.join(
                                snapshot.base,
                                identity.replace("/", os.sep),
                            ),
                            entry=entry,
                            base=snapshot.base,
                            manifest_path=snapshot.manifest_path,
                            lock_path=lock_path,
                        )
                    )
        except Exception as exc:
            items.append(_failed_item(identity, category, "reindex", exc))
    return items


def _repair_missing_sources(
    snapshot: _ConsistencySnapshot,
    *,
    lock_path: str,
) -> List[RepairItem]:
    items: List[RepairItem] = []
    missing = sorted(set(snapshot.manifest_entries) - set(snapshot.sources))
    usable_collection = (
        snapshot.report.chroma_root_present
        and snapshot.report.chroma_collection_present
        and not snapshot.report.chroma_unavailable
    )
    for identity in missing:
        try:
            if usable_collection:
                result = eliminar_documento_indexado(
                    identity,
                    manifest_path=snapshot.manifest_path,
                    lock_path=lock_path,
                )
                items.append(_item_from_delete_result(identity, result))
            else:
                manifest = IndexManifest.load(snapshot.manifest_path)
                manifest.remove(identity)
                manifest.save(snapshot.manifest_path)
                items.append(
                    RepairItem(
                        identity=identity,
                        category=_SOURCE_ABSENT_MANIFEST_CATEGORY,
                        action="remove_manifest_entry",
                        status="attempted",
                    )
                )
        except Exception as exc:
            action = "remove" if usable_collection else "remove_manifest_entry"
            items.append(
                _failed_item(
                    identity,
                    _SOURCE_ABSENT_MANIFEST_CATEGORY,
                    action,
                    exc,
                )
            )
    return items


def _report_orphans(snapshot: _ConsistencySnapshot) -> List[RepairItem]:
    return [
        RepairItem(
            identity=orphan_id,
            category=_SOURCE_ABSENT_CHROMA_CATEGORY,
            action="skip",
            status="skipped",
        )
        for orphan_id in snapshot.orphan_ids
    ]


def _confirm_items_from_snapshot(
    items: Iterable[RepairItem],
    snapshot: _ConsistencySnapshot,
) -> List[RepairItem]:
    report = snapshot.report
    cannot_confirm = (
        report.path_error
        or report.observed_state in {
            ConsistencyState.DEGRADED.value,
            ConsistencyState.UNAVAILABLE.value,
        }
        or report.published_state in {
            ConsistencyState.DEGRADED.value,
            ConsistencyState.UNAVAILABLE.value,
        }
    )
    sources = set(snapshot.sources)
    manifest_entries = set(snapshot.manifest_entries)
    confirmed: List[RepairItem] = []
    for item in items:
        if item.status != "attempted":
            confirmed.append(item)
            continue
        if cannot_confirm:
            confirmed.append(replace(item, status="still_inconsistent"))
            continue

        identity = item.identity
        if identity in sources:
            category = snapshot.categories_by_identity.get(identity)
            if category is None:
                confirmed.append(replace(item, status="repaired"))
            else:
                confirmed.append(
                    replace(
                        item,
                        category=_category_value(category),
                        status="still_inconsistent",
                    )
                )
            continue

        if identity in manifest_entries:
            confirmed.append(
                replace(
                    item,
                    category=_SOURCE_ABSENT_MANIFEST_CATEGORY,
                    status="still_inconsistent",
                )
            )
            continue

        if snapshot.chunks_by_identity.get(identity):
            confirmed.append(
                replace(
                    item,
                    category=_SOURCE_ABSENT_CHROMA_CATEGORY,
                    status="still_inconsistent",
                )
            )
            continue

        confirmed.append(replace(item, status="repaired"))
    return confirmed


def _confirmar_items_por_identidad(
    items: Iterable[RepairItem],
    snapshot: _ConsistencySnapshot,
) -> List[RepairItem]:
    """Nombre contractual de la confirmación basada en el snapshot final."""
    return _confirm_items_from_snapshot(items, snapshot)


def reparar_indice(
    memoria_base: Optional[str] = None,
    manifest_path: Optional[str] = None,
    chroma_path: Optional[str] = None,
    collection_name: Optional[str] = None,
    lock_path: Optional[str] = None,
) -> RepairReport:
    """Repara divergencias seguras bajo IDX-C2 y confirma fuera del lock."""
    started_at = _utc_now_iso()
    started_clock = time.perf_counter()
    base = memoria_base or config.BASE_MEMORIA
    manifest_ruta = manifest_path or config.INDEX_MANIFEST_PATH
    chroma_ruta = chroma_path or config.CHROMA_PATH
    nombre_coleccion = collection_name or config.COLLECTION_NAME
    pre_snapshot: Optional[_ConsistencySnapshot] = None
    resolved_lock: Optional[str] = None
    snapshot_lock_path: Optional[str] = None
    items: List[RepairItem] = []
    blocked_reason: Optional[str] = None

    target_mismatch = _writer_target_mismatch(
        manifest_path=manifest_ruta,
        chroma_path=chroma_ruta,
        collection_name=nombre_coleccion,
        lock_path=lock_path,
    )
    try:
        with acquire_index_writer_lock(
            lock_path=None if target_mismatch else lock_path,
            manifest_path=(
                config.INDEX_MANIFEST_PATH if target_mismatch else manifest_ruta
            ),
        ) as writer_lock:
            resolved_lock = str(writer_lock.lock_path)
            snapshot_lock_path = lock_path if target_mismatch else resolved_lock
            pre_snapshot = _capturar_snapshot_consistencia(
                memoria_base=base,
                manifest_path=manifest_ruta,
                chroma_path=chroma_ruta,
                collection_name=nombre_coleccion,
                lock_path=snapshot_lock_path,
            )
            if target_mismatch:
                blocked_reason = "writer_target_mismatch"
            else:
                blocked_reason = _blocked_reason(pre_snapshot)
                if blocked_reason is None:
                    items.extend(_repair_sources(pre_snapshot, lock_path=resolved_lock))
                    items.extend(_repair_missing_sources(pre_snapshot, lock_path=resolved_lock))
                    items.extend(_report_orphans(pre_snapshot))
    except IndexWriterBusyError as exc:
        finished_at = _utc_now_iso()
        return RepairReport(
            pre_state=ConsistencyState.UNAVAILABLE.value,
            post_state=ConsistencyState.UNAVAILABLE.value,
            post_observed=ConsistencyState.UNAVAILABLE.value,
            post_check_performed=False,
            success=False,
            blocked=False,
            blocked_reason=None,
            busy=True,
            busy_message=exc.public_message,
            items=(),
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=time.perf_counter() - started_clock,
        )
    except Exception as exc:
        # Los fallos de documentos se aíslan dentro de los helpers. Un
        # fallo global deja el diagnóstico bloqueado y no inventa una
        # identidad para representar una operación inexistente.
        blocked_reason = "degraded_diagnosis"
        items = []

    try:
        post_snapshot = _capturar_snapshot_consistencia(
            memoria_base=base,
            manifest_path=manifest_ruta,
            chroma_path=chroma_ruta,
            collection_name=nombre_coleccion,
            lock_path=snapshot_lock_path or resolved_lock or lock_path,
        )
    except Exception as exc:
        blocked_reason = blocked_reason or "unavailable"
        items = []
        finished_at = _utc_now_iso()
        return RepairReport(
            pre_state=(
                pre_snapshot.report.observed_state
                if pre_snapshot is not None
                else ConsistencyState.UNAVAILABLE.value
            ),
            post_state=ConsistencyState.UNAVAILABLE.value,
            post_observed=ConsistencyState.UNAVAILABLE.value,
            post_check_performed=True,
            success=False,
            blocked=True,
            blocked_reason=blocked_reason,
            busy=False,
            busy_message=None,
            items=tuple(items),
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=time.perf_counter() - started_clock,
        )
    if blocked_reason is None:
        items = _confirmar_items_por_identidad(items, post_snapshot)
    else:
        items = []

    post_report = post_snapshot.report
    finished_at = _utc_now_iso()
    return RepairReport(
        pre_state=(
            pre_snapshot.report.observed_state
            if pre_snapshot is not None
            else ConsistencyState.UNAVAILABLE.value
        ),
        post_state=post_report.published_state,
        post_observed=post_report.observed_state,
        post_check_performed=True,
        success=False,
        blocked=blocked_reason is not None,
        blocked_reason=blocked_reason,
        busy=False,
        busy_message=None,
        items=tuple(items),
        orphan_count=post_report.orphan_count,
        orphan_sample=post_report.orphan_sample,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=time.perf_counter() - started_clock,
    )


__all__ = [
    "RepairItem",
    "RepairReport",
    "reparar_indice",
]
