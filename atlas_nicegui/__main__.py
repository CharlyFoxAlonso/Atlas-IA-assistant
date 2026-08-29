"""Explicit development entry point for the parallel NiceGUI shell."""

from __future__ import annotations

import os


def main() -> None:
    """Start NiceGUI locally without changing the Streamlit launcher."""
    from core.system.paths import get_paths

    os.environ["NICEGUI_STORAGE_PATH"] = str(
        get_paths().temp_dir / "nicegui"
    )

    from nicegui import run, ui

    from atlas_nicegui.app import create_root

    root = create_root(ui=ui, io_bound=run.io_bound)
    ui.run(
        root,
        host="127.0.0.1",
        port=8402,
        show=False,
        on_air=None,
        native=False,
        reload=False,
    )


if __name__ == "__main__":
    main()
