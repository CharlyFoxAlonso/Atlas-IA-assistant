"""Frontend-neutral, import-safe streaming boundary for one chat turn."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Literal


CHAT_STREAM_ERROR_MESSAGE = "No se pudo generar la respuesta."


@dataclass(frozen=True)
class ChatStreamEvent:
    """One ordered event emitted by the existing Atlas brain stream."""

    kind: Literal["status", "snapshot"]
    text: str


class ChatStreamError(RuntimeError):
    """Fixed public failure that never carries backend exception text."""

    def __init__(self) -> None:
        super().__init__(CHAT_STREAM_ERROR_MESSAGE)


class ChatStreamCancelled(Exception):
    """Cooperative cancellation observed between generator advances."""


def _raise_if_cancelled(cancelled: Callable[[], bool] | None) -> None:
    if cancelled is not None and cancelled():
        raise ChatStreamCancelled() from None


def _event(kind: Literal["status", "snapshot"], value: object) -> ChatStreamEvent:
    if not isinstance(value, str):
        raise TypeError("invalid_chat_stream_event")
    return ChatStreamEvent(kind=kind, text=value)


def stream_chat_turn(
    prompt: str,
    *,
    history: list[dict[str, str]],
    motor: str | None = None,
    modelo_nube: str | None = None,
    modelo_local: str | None = None,
    modelo_groq: str | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Iterator[ChatStreamEvent]:
    """Stream one isolated turn and commit caller history only on success.

    The body is intentionally lazy: importing ``core.chat_stream`` or creating
    this iterator does not import ``core.brain`` or contact a provider.
    ``history`` must be exclusively owned by the caller while the iterator is
    active.
    """

    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt_required")

    try:
        _raise_if_cancelled(cancelled)
        working_history = [dict(item) for item in history]

        brain = importlib.import_module("core.brain")
        _raise_if_cancelled(cancelled)

        upstream = None
        cancellation_observed = False
        with brain._usar_contexto_streaming(working_history):
            try:
                upstream = iter(
                    brain.pensar_con_streaming(
                        prompt,
                        motor=motor,
                        modelo_nube=modelo_nube,
                        modelo_local=modelo_local,
                        modelo_groq=modelo_groq,
                    )
                )
                while True:
                    _raise_if_cancelled(cancelled)
                    try:
                        pensamiento, respuesta = next(upstream)
                    except StopIteration:
                        break

                    _raise_if_cancelled(cancelled)
                    if pensamiento is not None:
                        if pensamiento:
                            yield _event("status", pensamiento)
                        _raise_if_cancelled(cancelled)
                    if respuesta is not None and respuesta:
                        yield _event("snapshot", respuesta)

                _raise_if_cancelled(cancelled)
            except ChatStreamCancelled:
                cancellation_observed = True
                raise
            finally:
                close = getattr(upstream, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        if not cancellation_observed:
                            raise

        _raise_if_cancelled(cancelled)
        history[:] = working_history
    except ChatStreamCancelled:
        raise
    except ChatStreamError:
        raise
    except Exception:
        raise ChatStreamError() from None
