"""Minimal, import-safe NiceGUI shell for Atlas."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from typing import Any

from core.index_status import (
    consultar_estado_indice_si_solicitado,
    format_index_status_lines,
)


QUERY_FAILED_MESSAGE = "No se pudo consultar el estado del índice."
STATUS_PLACEHOLDER = (
    "El estado del índice se consultará únicamente cuando lo solicites."
)


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
) -> Callable[[], None]:
    """Create one NiceGUI page without running diagnostics or a server."""

    def root() -> None:
        in_flight = False

        ui.label("Atlas").classes("text-h4")
        ui.label("Estado del índice").classes("text-h5")
        ui.label(
            "Consulta read-only del diagnóstico existente de Atlas."
        )

        status_container = ui.column()
        _replace_status_lines(ui, status_container, (STATUS_PLACEHOLDER,))

        button = None

        async def query_index_status() -> None:
            nonlocal in_flight
            if in_flight:
                return

            in_flight = True
            try:
                button.disable()
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
                in_flight = False
                button.enable()

        button = ui.button(
            "Consultar estado del índice",
            on_click=query_index_status,
        )

    return root
