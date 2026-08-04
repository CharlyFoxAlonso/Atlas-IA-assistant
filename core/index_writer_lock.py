"""Fail-fast single-writer lock for Atlas indexing operations.

The lock is file based so it works on Windows without POSIX-only primitives.
It is intentionally conservative: ambiguous owner state is treated as busy.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import psutil


LOCK_SCHEMA_VERSION = 1

PUBLIC_BUSY_MESSAGES = {
    "index_writer_busy": "Index writer is busy; another indexing operation is active.",
    "lock_path_mismatch": "Index writer lock path mismatch in current context.",
    "index_writer_state_ambiguous": "Index writer lock state is ambiguous.",
}


class IndexWriterBusyError(RuntimeError):
    """Raised when a writer cannot acquire exclusivity immediately."""

    def __init__(self, code: str = "index_writer_busy"):
        safe_code = code if code in PUBLIC_BUSY_MESSAGES else "index_writer_busy"
        self.code = safe_code
        self.public_message = PUBLIC_BUSY_MESSAGES[safe_code]
        super().__init__(self.public_message)


@dataclass(frozen=True)
class IndexWriterState:
    """Read-only public writer state for IDX-C1."""

    writer_state_known: bool
    writer_active: bool
    possibly_transient: bool


@dataclass(frozen=True)
class _LockMetadata:
    schema_version: int
    pid: int
    process_create_time: float
    token: str
    created_at_utc: str

    def to_json(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "pid": self.pid,
            "process_create_time": self.process_create_time,
            "token": self.token,
            "created_at_utc": self.created_at_utc,
        }


@dataclass(frozen=True)
class _ReadLockMetadata:
    pid: int
    process_create_time: float
    token: str


class _ThreadLockContext(threading.local):
    lock_path: Optional[Path] = None
    depth: int = 0
    owner: Optional["IndexWriterLock"] = None


_thread_context = _ThreadLockContext()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_lock_path() -> Path:
    from core import config

    return Path(config.INDEX_WRITER_LOCK_PATH).expanduser().resolve()


def derive_lock_path_for_manifest(manifest_path: str | os.PathLike[str]) -> Path:
    """Derive the writer lock path from effective manifest persistence.

    A manifest inside a vector store directory gets a sibling lock in the data
    directory so the lock stays outside ``vector_db``. Other explicit manifest
    paths use their parent directory as the effective persistence root.
    """
    manifest = Path(manifest_path).expanduser().resolve()
    parent = manifest.parent
    root = parent.parent if parent.name == "vector_db" else parent
    return (root / "index_writer.lock").resolve()


def resolve_index_writer_lock_path(
    *,
    lock_path: Optional[str | os.PathLike[str]] = None,
    manifest_path: Optional[str | os.PathLike[str]] = None,
) -> Path:
    if lock_path is not None:
        return Path(lock_path).expanduser().resolve()
    if manifest_path is not None:
        return derive_lock_path_for_manifest(manifest_path)
    return _default_lock_path()


def _metadata_for_current_process() -> _LockMetadata:
    process = psutil.Process(os.getpid())
    return _LockMetadata(
        schema_version=LOCK_SCHEMA_VERSION,
        pid=os.getpid(),
        process_create_time=float(process.create_time()),
        token=uuid.uuid4().hex,
        created_at_utc=_utc_now_iso(),
    )


def _parse_metadata(raw: object) -> Optional[_ReadLockMetadata]:
    if not isinstance(raw, dict):
        return None
    try:
        schema_version = int(raw["schema_version"])
        pid = int(raw["pid"])
        create_time = float(raw["process_create_time"])
        token = str(raw["token"])
    except (KeyError, TypeError, ValueError):
        return None
    if schema_version != LOCK_SCHEMA_VERSION or pid <= 0 or not token:
        return None
    return _ReadLockMetadata(
        pid=pid,
        process_create_time=create_time,
        token=token,
    )


def _read_metadata(lock_path: Path) -> Optional[_ReadLockMetadata]:
    try:
        with open(lock_path, "r", encoding="utf-8") as handle:
            return _parse_metadata(json.load(handle))
    except (OSError, json.JSONDecodeError):
        return None


def _same_identity(left: _ReadLockMetadata, right: _ReadLockMetadata) -> bool:
    return (
        left.pid == right.pid
        and left.process_create_time == right.process_create_time
        and left.token == right.token
    )


def _owner_process_state(metadata: _ReadLockMetadata) -> str:
    """Return active, stale or ambiguous for an on-disk owner."""
    try:
        process = psutil.Process(metadata.pid)
        current_create_time = float(process.create_time())
    except psutil.NoSuchProcess:
        return "stale"
    except (psutil.AccessDenied, psutil.ZombieProcess):
        return "ambiguous"

    if current_create_time != metadata.process_create_time:
        return "ambiguous"
    return "active"


def _recover_stale_lock_once(lock_path: Path, first_read: _ReadLockMetadata) -> bool:
    if _owner_process_state(first_read) != "stale":
        return False

    second_read = _read_metadata(lock_path)
    if second_read is None or not _same_identity(first_read, second_read):
        return False

    try:
        os.unlink(lock_path)
    except OSError:
        return False
    return True


class IndexWriterLock:
    """Owner handle for a lock acquired by this process."""

    def __init__(self, lock_path: Path, metadata: _LockMetadata):
        self.lock_path = lock_path
        self._metadata = metadata
        self._released = False

    @classmethod
    def acquire(cls, lock_path: Path) -> "IndexWriterLock":
        metadata = _metadata_for_current_process()
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        for attempt in range(2):
            try:
                fd = os.open(
                    str(lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
            except FileExistsError:
                if attempt == 1:
                    raise IndexWriterBusyError("index_writer_busy")
                existing = _read_metadata(lock_path)
                if existing is None:
                    raise IndexWriterBusyError("index_writer_state_ambiguous")
                if not _recover_stale_lock_once(lock_path, existing):
                    raise IndexWriterBusyError("index_writer_busy")
                continue

            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(metadata.to_json(), handle, ensure_ascii=True, sort_keys=True)
                    handle.flush()
                    os.fsync(handle.fileno())
            except Exception:
                try:
                    os.unlink(lock_path)
                except OSError:
                    pass
                raise
            return cls(lock_path, metadata)

        raise IndexWriterBusyError("index_writer_busy")

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        current = _read_metadata(self.lock_path)
        if current is None:
            return
        own = _ReadLockMetadata(
            pid=self._metadata.pid,
            process_create_time=self._metadata.process_create_time,
            token=self._metadata.token,
        )
        if not _same_identity(current, own):
            return
        try:
            os.unlink(self.lock_path)
        except OSError:
            pass


class _IndexWriterLockContext:
    def __init__(
        self,
        *,
        lock_path: Optional[str | os.PathLike[str]] = None,
        manifest_path: Optional[str | os.PathLike[str]] = None,
    ):
        self.lock_path = resolve_index_writer_lock_path(
            lock_path=lock_path,
            manifest_path=manifest_path,
        )
        self._owner: Optional[IndexWriterLock] = None
        self._reentrant = False

    def __enter__(self) -> "_IndexWriterLockContext":
        current_path = _thread_context.lock_path
        if current_path is not None:
            if current_path != self.lock_path:
                raise IndexWriterBusyError("lock_path_mismatch")
            _thread_context.depth += 1
            self._reentrant = True
            return self

        self._owner = IndexWriterLock.acquire(self.lock_path)
        _thread_context.lock_path = self.lock_path
        _thread_context.depth = 1
        _thread_context.owner = self._owner
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._reentrant:
            _thread_context.depth -= 1
            return

        try:
            if self._owner is not None:
                self._owner.release()
        finally:
            _thread_context.lock_path = None
            _thread_context.depth = 0
            _thread_context.owner = None


def acquire_index_writer_lock(
    *,
    lock_path: Optional[str | os.PathLike[str]] = None,
    manifest_path: Optional[str | os.PathLike[str]] = None,
) -> _IndexWriterLockContext:
    return _IndexWriterLockContext(lock_path=lock_path, manifest_path=manifest_path)


def inspect_index_writer_state(
    *,
    lock_path: Optional[str | os.PathLike[str]] = None,
    manifest_path: Optional[str | os.PathLike[str]] = None,
) -> IndexWriterState:
    """Inspect writer state without creating, deleting, recovering or logging."""
    resolved = resolve_index_writer_lock_path(lock_path=lock_path, manifest_path=manifest_path)
    if not resolved.exists():
        return IndexWriterState(
            writer_state_known=True,
            writer_active=False,
            possibly_transient=False,
        )

    metadata = _read_metadata(resolved)
    if metadata is None:
        return IndexWriterState(
            writer_state_known=False,
            writer_active=False,
            possibly_transient=True,
        )

    state = _owner_process_state(metadata)
    if state == "active":
        return IndexWriterState(
            writer_state_known=True,
            writer_active=True,
            possibly_transient=True,
        )
    if state == "stale":
        return IndexWriterState(
            writer_state_known=True,
            writer_active=False,
            possibly_transient=False,
        )
    return IndexWriterState(
        writer_state_known=False,
        writer_active=False,
        possibly_transient=True,
    )
