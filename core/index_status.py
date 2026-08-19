"""Safe read-only presentation boundary for index status surfaces (IDX-C4).

The module stays dependency-light at import time.  IDX-C1 is imported only
when an explicit status request is made; presentation never acquires a writer
lock, repairs data, creates Chroma, or exposes document identities and paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Tuple


_STATE_PRESENTATION = {
    "HEALTHY": ("Saludable", "success"),
    "HEALTHY_EMPTY": ("Saludable y vacío", "success"),
    "DEGRADED": ("Degradado", "warning"),
    "INCONSISTENT": ("Inconsistente", "warning"),
    "UNAVAILABLE": ("No disponible", "error"),
}

_WRITER_LABELS = {
    "active": "Activo",
    "inactive": "Inactivo",
    "unknown": "Desconocido",
}

_FALLBACK_ISSUE_CODE = "consistency_verification_failed"
_FALLBACK_ISSUE_MESSAGE = (
    "Consistency verification encountered an internal error."
)
_FALLBACK_BUSY_MESSAGE = (
    "Index writer is busy; another indexing operation is active."
)


@dataclass(frozen=True)
class IndexIssueView:
    """Allowlisted issue exposed by IDX-C4."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True)
class IndexStatusView:
    """Path-free, content-free projection of ``ConsistencyReport``."""

    state: str
    state_label: str
    observed_state: str
    observed_state_label: str
    healthy: bool
    severity: str
    writer_state: str
    writer_label: str
    possibly_transient: bool
    sources_count: Optional[int]
    manifest_entries_count: Optional[int]
    chunk_count: Optional[int]
    divergences: Dict[str, int]
    orphan_count: Optional[int]
    issues: Tuple[IndexIssueView, ...]

    @classmethod
    def unavailable(cls) -> "IndexStatusView":
        label, severity = _STATE_PRESENTATION["UNAVAILABLE"]
        return cls(
            state="UNAVAILABLE",
            state_label=label,
            observed_state="UNAVAILABLE",
            observed_state_label=label,
            healthy=False,
            severity=severity,
            writer_state="unknown",
            writer_label=_WRITER_LABELS["unknown"],
            possibly_transient=True,
            sources_count=None,
            manifest_entries_count=None,
            chunk_count=None,
            divergences={},
            orphan_count=None,
            issues=(
                IndexIssueView(
                    _FALLBACK_ISSUE_CODE,
                    _FALLBACK_ISSUE_MESSAGE,
                ),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "state_label": self.state_label,
            "observed_state": self.observed_state,
            "observed_state_label": self.observed_state_label,
            "healthy": self.healthy,
            "severity": self.severity,
            "writer_state": self.writer_state,
            "writer_label": self.writer_label,
            "possibly_transient": self.possibly_transient,
            "sources_count": self.sources_count,
            "manifest_entries_count": self.manifest_entries_count,
            "chunk_count": self.chunk_count,
            "divergences": dict(self.divergences),
            "orphan_count": self.orphan_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class SyncPresentation:
    """Safe aggregate presentation for a ``SyncResult``."""

    busy: bool
    message: str


def _load_consistency_contract():
    """Load IDX-C1 only for an explicit query."""
    from core.index_consistency import (
        DivergenceCategory,
        VERIFICATION_LIMITATION,
        verificar_consistencia,
    )
    from core.vector_store import IDX_PUBLIC_ERROR_MESSAGES

    allowed_divergences = {
        category.value for category in DivergenceCategory
    }
    allowed_divergences.add(VERIFICATION_LIMITATION)
    return (
        verificar_consistencia,
        frozenset(allowed_divergences),
        dict(IDX_PUBLIC_ERROR_MESSAGES),
    )


def _writer_state(report: object) -> str:
    if not bool(getattr(report, "writer_state_known")):
        return "unknown"
    return "active" if bool(getattr(report, "writer_active")) else "inactive"


def _safe_issues(
    raw_issues: object,
    issue_messages: Mapping[str, str],
) -> Tuple[IndexIssueView, ...]:
    issues = []
    seen = set()
    for raw_issue in tuple(raw_issues):
        code = str(raw_issue).partition(":")[0].strip()
        if code not in issue_messages:
            code = _FALLBACK_ISSUE_CODE
        if code in seen:
            continue
        seen.add(code)
        message = issue_messages.get(code, _FALLBACK_ISSUE_MESSAGE)
        issues.append(IndexIssueView(code=code, message=message))
    return tuple(issues)


def _project_report(
    report: object,
    allowed_divergences: frozenset[str],
    issue_messages: Mapping[str, str],
) -> IndexStatusView:
    state = str(getattr(report, "published_state"))
    observed_state = str(getattr(report, "observed_state"))
    if state not in _STATE_PRESENTATION or observed_state not in _STATE_PRESENTATION:
        raise ValueError("unsupported consistency state")

    divergences = {}
    for key, value in dict(getattr(report, "divergences")).items():
        if key not in allowed_divergences:
            continue
        count = int(value)
        if count > 0:
            divergences[key] = count

    writer_state = _writer_state(report)
    state_label, severity = _STATE_PRESENTATION[state]
    observed_label, _ = _STATE_PRESENTATION[observed_state]
    return IndexStatusView(
        state=state,
        state_label=state_label,
        observed_state=observed_state,
        observed_state_label=observed_label,
        healthy=state in {"HEALTHY", "HEALTHY_EMPTY"},
        severity=severity,
        writer_state=writer_state,
        writer_label=_WRITER_LABELS[writer_state],
        possibly_transient=bool(getattr(report, "possibly_transient")),
        sources_count=int(getattr(report, "sources_count")),
        manifest_entries_count=int(getattr(report, "manifest_entries_count")),
        chunk_count=int(getattr(report, "chunk_count")),
        divergences=dict(sorted(divergences.items())),
        orphan_count=int(getattr(report, "orphan_count")),
        issues=_safe_issues(getattr(report, "issues"), issue_messages),
    )


def consultar_estado_indice(
    *,
    memoria_base: Optional[str] = None,
    manifest_path: Optional[str] = None,
    chroma_path: Optional[str] = None,
    collection_name: Optional[str] = None,
    lock_path: Optional[str] = None,
) -> IndexStatusView:
    """Run IDX-C1 once and return a safe status projection.

    Unexpected failures become a controlled ``UNAVAILABLE`` view.  Exception
    values, paths and document identities are never copied to the result.
    """
    options = {
        "memoria_base": memoria_base,
        "manifest_path": manifest_path,
        "chroma_path": chroma_path,
        "collection_name": collection_name,
        "lock_path": lock_path,
    }
    forwarded = {key: value for key, value in options.items() if value is not None}
    try:
        verifier, allowed_divergences, issue_messages = _load_consistency_contract()
        report = verifier(**forwarded)
        return _project_report(report, allowed_divergences, issue_messages)
    except Exception:
        return IndexStatusView.unavailable()


def consultar_estado_indice_si_solicitado(
    requested: bool,
    *,
    provider: Optional[Callable[..., IndexStatusView]] = None,
    **kwargs: Any,
) -> Optional[IndexStatusView]:
    """Execute the diagnosis only for an explicit user action."""
    if not requested:
        return None
    query = provider or consultar_estado_indice
    return query(**kwargs)


def _count_text(value: object) -> str:
    return "desconocido" if value is None else str(value)


def format_index_status_lines(
    status: IndexStatusView | Mapping[str, Any],
) -> Tuple[str, ...]:
    """Render only fields present in the safe IDX-C4 projection."""
    data = status.to_dict() if isinstance(status, IndexStatusView) else dict(status)
    lines = [f"Estado: {data['state']} — {data['state_label']}"]
    if data.get("observed_state") != data.get("state"):
        lines.append(
            "Estado observado: "
            f"{data['observed_state']} — {data['observed_state_label']}"
        )
    lines.append(
        f"Escritor: {data['writer_label']} ({data['writer_state']})"
    )
    if data.get("possibly_transient"):
        lines.append("Condición potencialmente transitoria.")
    lines.append(
        "Capas: "
        f"fuentes={_count_text(data.get('sources_count'))}, "
        f"manifiesto={_count_text(data.get('manifest_entries_count'))}, "
        f"chunks={_count_text(data.get('chunk_count'))}"
    )

    divergences = dict(data.get("divergences") or {})
    if divergences:
        rendered = ", ".join(
            f"{key}={value}" for key, value in sorted(divergences.items())
        )
        lines.append(f"Divergencias: {rendered}")
    else:
        lines.append("Divergencias: ninguna")
    lines.append(f"Huérfanos: {_count_text(data.get('orphan_count'))}")

    issues = tuple(data.get("issues") or ())
    if issues:
        rendered_issues = []
        for issue in issues:
            if isinstance(issue, IndexIssueView):
                issue_data = issue.to_dict()
            else:
                issue_data = dict(issue)
            rendered_issues.append(
                f"{issue_data['code']} — {issue_data['message']}"
            )
        lines.append("Issues: " + "; ".join(rendered_issues))
    else:
        lines.append("Issues: ninguno")
    return tuple(lines)


def _busy_public_message() -> str:
    try:
        from core.index_writer_lock import PUBLIC_BUSY_MESSAGES

        return PUBLIC_BUSY_MESSAGES["index_writer_busy"]
    except Exception:
        return _FALLBACK_BUSY_MESSAGE


def presentar_resultado_sincronizacion(result: object) -> SyncPresentation:
    """Present busy before touching aggregate counters."""
    if bool(getattr(result, "busy", False)):
        return SyncPresentation(busy=True, message=_busy_public_message())
    return SyncPresentation(
        busy=False,
        message=(
            f"Escaneados: {int(getattr(result, 'scanned'))} | "
            f"Nuevos: {int(getattr(result, 'indexed_new'))} | "
            f"Modificados: {int(getattr(result, 'reindexed_modified'))} | "
            f"Sin cambios: {int(getattr(result, 'skipped_unchanged'))} | "
            f"Retirados: {int(getattr(result, 'removed_deleted'))} | "
            f"Fallidos: {int(getattr(result, 'failed'))} "
            f"({float(getattr(result, 'duration_seconds')):.1f}s)"
        ),
    )
