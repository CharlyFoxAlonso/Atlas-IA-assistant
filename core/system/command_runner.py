"""Safe subprocess execution shared by Doctor, Healer, and Launcher."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from core.system.result_types import CommandResult

_SECRET_MARKERS = ("key", "token", "secret", "password", "authorization")
_URL_CREDENTIALS = re.compile(r"(?P<scheme>https?://)(?P<credentials>[^/@\s]+@)", re.IGNORECASE)
_BEARER_TOKEN = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")


def _to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        for encoding in ("utf-8", "cp1252", "cp850"):
            try:
                return value.decode(encoding)
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace")
    return str(value)


def _redact(value: object, secrets: Iterable[str]) -> str:
    redacted = _to_text(value)
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "***")
    redacted = _URL_CREDENTIALS.sub(r"\g<scheme>***@", redacted)
    redacted = _BEARER_TOKEN.sub(r"\1***", redacted)
    return redacted


def _environment_secrets(env: Optional[Mapping[str, str]]) -> tuple[str, ...]:
    if env is None:
        return ()
    return tuple(
        value
        for key, value in env.items()
        if value and any(marker in key.lower() for marker in _SECRET_MARKERS)
    )


def _safe_args(args: Sequence[str], secrets: Iterable[str]) -> list[str]:
    known_secrets = tuple(secrets)
    safe: list[str] = []
    redact_next = False
    for raw in args:
        value = str(raw)
        lower = value.lower()
        if redact_next:
            safe.append("***")
            redact_next = False
        elif any(marker in lower for marker in _SECRET_MARKERS):
            if "=" in value:
                safe.append(value.split("=", 1)[0] + "=***")
            else:
                safe.append(value)
                redact_next = True
        else:
            safe.append(_redact(value, known_secrets))
    return safe


def _creation_flags(hide_window: bool) -> int:
    if os.name == "nt" and hide_window:
        return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return 0


def run_command(
    args: Sequence[str],
    *,
    timeout: Optional[float] = 30,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    hide_window: bool = True,
    secrets: Iterable[str] = (),
) -> CommandResult:
    if not args or any(not isinstance(arg, str) for arg in args):
        raise ValueError("args must be a non-empty sequence of strings")

    all_secrets = tuple(secrets) + _environment_secrets(env)
    safe_args = _safe_args(args, all_secrets)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(args),
            cwd=str(cwd) if cwd else None,
            env=dict(env) if env is not None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            creationflags=_creation_flags(hide_window),
            check=False,
        )
        return CommandResult(
            args=safe_args,
            returncode=completed.returncode,
            stdout=_redact(completed.stdout, all_secrets),
            stderr=_redact(completed.stderr, all_secrets),
            duration_seconds=round(time.monotonic() - started, 3),
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            args=safe_args,
            returncode=None,
            stdout=_redact(exc.stdout, all_secrets),
            stderr=_redact(exc.stderr, all_secrets),
            duration_seconds=round(time.monotonic() - started, 3),
            timed_out=True,
            error=f"Command timed out after {timeout} seconds",
        )
    except OSError as exc:
        return CommandResult(
            args=safe_args,
            returncode=None,
            duration_seconds=round(time.monotonic() - started, 3),
            started=False,
            error=str(exc),
        )


def start_command(
    args: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    hide_window: bool = True,
    secrets: Iterable[str] = (),
    startup_check_seconds: float = 0.2,
) -> CommandResult:
    """Start a long-running process and return immediately."""
    if not args or any(not isinstance(arg, str) for arg in args):
        raise ValueError("args must be a non-empty sequence of strings")
    all_secrets = tuple(secrets) + _environment_secrets(env)
    safe_args = _safe_args(args, all_secrets)
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            list(args),
            cwd=str(cwd) if cwd else None,
            env=dict(env) if env is not None else None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=_creation_flags(hide_window),
        )
        if startup_check_seconds > 0:
            time.sleep(startup_check_seconds)
            early_returncode = process.poll()
            if early_returncode is not None:
                return CommandResult(
                    args=safe_args,
                    returncode=early_returncode,
                    duration_seconds=round(time.monotonic() - started, 3),
                    started=False,
                    pid=process.pid,
                    error=f"Process exited during startup with code {early_returncode}",
                )
        return CommandResult(
            args=safe_args,
            returncode=None,
            duration_seconds=round(time.monotonic() - started, 3),
            pid=process.pid,
        )
    except OSError as exc:
        return CommandResult(
            args=safe_args,
            returncode=None,
            duration_seconds=round(time.monotonic() - started, 3),
            started=False,
            error=str(exc),
        )
