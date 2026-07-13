"""Persistent, rotating, secret-safe operational audit log."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from core.system.paths import AtlasPaths

_SENSITIVE_MARKERS = ("key", "token", "secret", "password", "authorization")
_WRITE_LOCK = threading.Lock()


def _sanitize(value: Any, key: str = "") -> Any:
    if any(marker in key.lower() for marker in _SENSITIVE_MARKERS):
        return "***" if value not in (None, "", False) else value
    if isinstance(value, Mapping):
        return {str(item_key): _sanitize(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def write_operational_event(
    paths: AtlasPaths,
    *,
    component: str,
    event: str,
    payload: Mapping[str, Any],
) -> None:
    """Append one JSON event. Logging failures never break Atlas operations."""
    try:
        payload_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_id": uuid4().hex,
            "component": component,
            "event": event,
            **_sanitize(dict(payload)),
        }
        with _WRITE_LOCK:
            paths.logs_dir.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(
                (paths.logs_dir / "atlas-system.log").resolve(),
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            try:
                record = logging.LogRecord(
                    name="atlas.system.audit",
                    level=logging.INFO,
                    pathname="",
                    lineno=0,
                    msg=json.dumps(payload_record, ensure_ascii=False, sort_keys=True),
                    args=(),
                    exc_info=None,
                )
                handler.setFormatter(logging.Formatter("%(message)s"))
                handler.emit(record)
            finally:
                handler.close()
    except Exception:
        logging.getLogger(__name__).exception("No se pudo escribir el log operativo de Atlas")
