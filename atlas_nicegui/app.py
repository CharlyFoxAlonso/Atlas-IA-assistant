"""Minimal, import-safe NiceGUI shell for Atlas."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from contextlib import suppress
import threading
from typing import Any

from core.chat_stream import (
    CHAT_STREAM_ERROR_MESSAGE,
    ChatStreamCancelled,
    ChatStreamError,
    ChatStreamEvent,
    stream_chat_turn,
)
from core.index_status import (
    consultar_estado_indice_si_solicitado,
    format_index_status_lines,
)


CHAT_CANCELLED_MESSAGE = "Generación cancelada."
CHAT_PENDING_MESSAGE = "Generando..."
QUERY_FAILED_MESSAGE = "No se pudo consultar el estado del índice."
STATUS_PLACEHOLDER = (
    "El estado del índice se consultará únicamente cuando lo solicites."
)

_CHAT_COMPLETED = "completed"
_CHAT_CANCELLED = "cancelled"
_CHAT_FAILED = "failed"


def _client_is_usable(client: Any) -> bool:
    return bool(client.has_socket_connection) and not bool(client.is_deleted)


def _silence_background_task(task: asyncio.Task[Any]) -> None:
    if task.cancelled():
        return
    with suppress(asyncio.CancelledError, Exception):
        task.exception()


def _drain_chat_stream(
    streamer: Callable[..., Any],
    prompt: str,
    history: list[dict[str, str]],
    cancellation: threading.Event,
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[ChatStreamEvent],
) -> str:
    """Drain one complete stream in a worker and relay typed UI events."""
    terminal = _CHAT_FAILED
    iterator = None

    try:
        if cancellation.is_set():
            terminal = _CHAT_CANCELLED
        else:
            iterator = iter(
                streamer(
                    prompt,
                    history=history,
                    cancelled=cancellation.is_set,
                )
            )
            while True:
                if cancellation.is_set():
                    terminal = _CHAT_CANCELLED
                    break
                try:
                    event = next(iterator)
                except StopIteration:
                    terminal = _CHAT_COMPLETED
                    break

                if cancellation.is_set():
                    terminal = _CHAT_CANCELLED
                    break
                if not isinstance(event, ChatStreamEvent) or event.kind not in {
                    "status",
                    "snapshot",
                }:
                    terminal = _CHAT_FAILED
                    break
                loop.call_soon_threadsafe(queue.put_nowait, event)
    except ChatStreamCancelled:
        terminal = _CHAT_CANCELLED
    except ChatStreamError:
        terminal = _CHAT_FAILED
    except Exception:
        terminal = _CHAT_FAILED
    finally:
        close = getattr(iterator, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                if terminal != _CHAT_CANCELLED:
                    terminal = _CHAT_FAILED

    return terminal


async def _wait_for_chat_worker(
    worker: asyncio.Task[Any],
    queue: asyncio.Queue[ChatStreamEvent],
    apply_event: Callable[[ChatStreamEvent], None],
) -> str | None:
    """Apply relayed events on the UI loop until the worker terminates."""
    pending_event: asyncio.Task[ChatStreamEvent] | None = None
    try:
        while not worker.done():
            pending_event = asyncio.create_task(queue.get())
            done, _ = await asyncio.wait(
                (worker, pending_event),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if pending_event in done:
                apply_event(pending_event.result())
                pending_event = None
                continue

            pending_event.cancel()
            with suppress(asyncio.CancelledError):
                await pending_event
            pending_event = None

        # Thread-safe queue callbacks are scheduled before the worker returns.
        # Yield once so the final snapshot is visible before applying terminal state.
        await asyncio.sleep(0)
        while not queue.empty():
            apply_event(queue.get_nowait())
        return await worker
    finally:
        if pending_event is not None and not pending_event.done():
            pending_event.cancel()
            with suppress(asyncio.CancelledError):
                await pending_event


def _replace_status_lines(
    ui: Any,
    container: Any,
    lines: Iterable[str],
) -> None:
    container.clear()
    with container:
        for line in lines:
            ui.label(str(line))


def create_root(
    *,
    ui: Any,
    io_bound: Callable[..., Any],
    provider: Callable[..., Any] = consultar_estado_indice_si_solicitado,
    formatter: Callable[[Any], Iterable[str]] = format_index_status_lines,
    streamer: Callable[..., Any] = stream_chat_turn,
) -> Callable[[], None]:
    """Create one NiceGUI page without running diagnostics or a server."""

    def root() -> None:
        index_in_flight = False
        chat_in_flight = False
        history: list[dict[str, str]] = []
        active_cancellation: threading.Event | None = None
        client = ui.context.client

        def cancel_active_turn() -> None:
            if active_cancellation is not None:
                active_cancellation.set()

        client.on_disconnect(cancel_active_turn)

        ui.label("Atlas").classes("text-h4")
        ui.label("Estado del índice").classes("text-h5")
        ui.label(
            "Consulta read-only del diagnóstico existente de Atlas."
        )

        status_container = ui.column()
        _replace_status_lines(ui, status_container, (STATUS_PLACEHOLDER,))

        status_button = None

        async def query_index_status() -> None:
            nonlocal index_in_flight
            if index_in_flight:
                return

            index_in_flight = True
            try:
                status_button.disable()
                status = await io_bound(provider, True)
                if status is None:
                    raise asyncio.CancelledError()
                lines = tuple(formatter(status))
                _replace_status_lines(ui, status_container, lines)
            except asyncio.CancelledError:
                raise
            except Exception:
                _replace_status_lines(
                    ui,
                    status_container,
                    (QUERY_FAILED_MESSAGE,),
                )
            finally:
                index_in_flight = False
                status_button.enable()

        status_button = ui.button(
            "Consultar estado del índice",
            on_click=query_index_status,
        )

        ui.label("Chat").classes("text-h5")
        ui.label("Conversación temporal, aislada en esta página.")
        chat_container = ui.column()
        chat_input = None
        send_button = None

        async def submit_chat() -> None:
            nonlocal chat_in_flight, active_cancellation

            if chat_in_flight or not _client_is_usable(client):
                return
            value = chat_input.value
            prompt = value.strip() if isinstance(value, str) else ""
            if not prompt:
                return

            chat_in_flight = True
            cancellation = threading.Event()
            active_cancellation = cancellation
            turn_history = [dict(item) for item in history]
            worker: asyncio.Task[Any] | None = None

            chat_input.disable()
            send_button.disable()
            chat_input.value = ""

            with chat_container:
                ui.chat_message(
                    text=prompt,
                    name="Vos",
                    sent=True,
                    text_html=False,
                )
                with ui.chat_message(
                    name="Atlas",
                    sent=False,
                    text_html=False,
                ):
                    assistant_output = ui.markdown("", sanitize=True)
                    chat_status = ui.label(CHAT_PENDING_MESSAGE)

            def apply_event(event: ChatStreamEvent) -> None:
                if cancellation.is_set() or not _client_is_usable(client):
                    return
                if event.kind == "status":
                    chat_status.text = event.text
                else:
                    assistant_output.content = event.text

            def apply_terminal(terminal: str) -> None:
                if not _client_is_usable(client):
                    return
                chat_status.text = ""
                if terminal == _CHAT_CANCELLED:
                    assistant_output.content = CHAT_CANCELLED_MESSAGE
                elif terminal == _CHAT_FAILED:
                    assistant_output.content = CHAT_STREAM_ERROR_MESSAGE

            try:
                loop = asyncio.get_running_loop()
                queue: asyncio.Queue[ChatStreamEvent] = asyncio.Queue()
                worker = asyncio.create_task(
                    io_bound(
                        _drain_chat_stream,
                        streamer,
                        prompt,
                        turn_history,
                        cancellation,
                        loop,
                        queue,
                    )
                )
                terminal = await _wait_for_chat_worker(
                    worker,
                    queue,
                    apply_event,
                )
                cancellation_was_requested = cancellation.is_set()
                if terminal is None:
                    cancellation.set()
                    terminal = _CHAT_CANCELLED
                elif terminal not in {
                    _CHAT_COMPLETED,
                    _CHAT_CANCELLED,
                    _CHAT_FAILED,
                }:
                    terminal = _CHAT_FAILED

                if not cancellation_was_requested:
                    if terminal == _CHAT_COMPLETED:
                        history[:] = turn_history
                    apply_terminal(terminal)
            except asyncio.CancelledError:
                cancellation.set()
                if worker is not None:
                    worker.cancel()
                    worker.add_done_callback(_silence_background_task)
                raise
            except Exception:
                cancellation_was_requested = cancellation.is_set()
                cancellation.set()
                if worker is not None and not worker.done():
                    worker.cancel()
                    worker.add_done_callback(_silence_background_task)
                if not cancellation_was_requested:
                    apply_terminal(_CHAT_FAILED)
            finally:
                if active_cancellation is cancellation:
                    active_cancellation = None
                chat_in_flight = False
                if _client_is_usable(client):
                    chat_input.enable()
                    send_button.enable()

        chat_input = ui.input(
            label="Mensaje",
            placeholder="Escribí tu consulta",
        )
        send_button = ui.button("Enviar", on_click=submit_chat)
        chat_input.on("keydown.enter", submit_chat)

        def restore_chat_controls() -> None:
            if chat_in_flight or not _client_is_usable(client):
                return
            chat_input.enable()
            send_button.enable()

        client.on_connect(restore_chat_controls)

    return root
