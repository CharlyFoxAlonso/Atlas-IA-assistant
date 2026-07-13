"""Atlas startup coordinator.

Launcher diagnoses, delegates authorized repairs to Healer, re-diagnoses, and
starts an existing Atlas entry point. Installation and download logic stay in
Healer; application and AI logic stay outside this module.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

from core.system.command_runner import start_command
from core.system.doctor import diagnosticar_sistema
from core.system.healer import Healer, SAFE_COMPONENTS
from core.system.paths import AtlasPaths, get_paths
from core.system.result_types import CommandResult, LaunchResult
from core.system.operational_log import write_operational_event

LAUNCH_TARGETS = ("ui", "cli")


class Launcher:
    def __init__(
        self,
        *,
        dry_run: bool = True,
        paths: Optional[AtlasPaths] = None,
        diagnostician: Callable[..., dict] = diagnosticar_sistema,
        process_starter: Callable[..., CommandResult] = start_command,
        healer_factory: Callable[..., Healer] = Healer,
    ) -> None:
        self.dry_run = dry_run
        self.paths = paths or get_paths()
        self._diagnose = diagnostician
        self._start = process_starter
        self._healer_factory = healer_factory

    def _finalize(self, result: LaunchResult) -> LaunchResult:
        if not result.dry_run:
            write_operational_event(
                self.paths,
                component="launcher",
                event="launch_result",
                payload={
                    "success": result.success,
                    "started": result.started,
                    "message": result.message,
                    "pid": result.pid,
                    "repairs": result.repairs,
                    "command": result.command,
                },
            )
        return result

    def _fresh_diagnosis(self, profile: str = "ui") -> dict:
        try:
            return self._diagnose(paths=self.paths, profile=profile)
        except TypeError:
            return self._diagnose()

    def _entrypoint(self, target: str, port: int) -> tuple[list[str], Path]:
        if target not in LAUNCH_TARGETS:
            raise ValueError(f"Destino de arranque desconocido: {target}")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError("El puerto debe ser un entero entre 1 y 65535")

        if target == "cli":
            entrypoint = self.paths.program_dir / "run.py"
            return [sys.executable, str(entrypoint)], entrypoint

        entrypoint = self.paths.program_dir / "atlas_ui.py"
        return [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(entrypoint),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
        ], entrypoint

    def launch(
        self,
        *,
        target: str = "ui",
        port: int = 8401,
        authorized_repairs: Iterable[str] = (),
    ) -> LaunchResult:
        command, entrypoint = self._entrypoint(target, port)
        diagnosis = self._fresh_diagnosis(target)
        repairs: list[dict] = []

        authorized = list(dict.fromkeys(authorized_repairs))
        invalid = [name for name in authorized if name not in SAFE_COMPONENTS]
        if invalid:
            return self._finalize(LaunchResult(
                success=False,
                dry_run=self.dry_run,
                message=f"Reparaciones no autorizables automáticamente: {', '.join(invalid)}",
                diagnosis=diagnosis,
            ))

        if authorized:
            healer = self._healer_factory(
                diagnosis=diagnosis,
                dry_run=self.dry_run,
                allow_heavy=False,
                paths=self.paths,
            )
            for component in authorized:
                result = healer.fix(component)
                repairs.append(result.to_dict())
            if not self.dry_run:
                diagnosis = self._fresh_diagnosis(target)

        if not diagnosis.get("ready_to_start", False):
            return self._finalize(LaunchResult(
                success=False,
                dry_run=self.dry_run,
                message="Atlas todavía no reúne los requisitos críticos para iniciar",
                diagnosis=diagnosis,
                repairs=repairs,
                command={"args": command, "entrypoint": str(entrypoint)},
            ))

        if not entrypoint.is_file():
            return self._finalize(LaunchResult(
                success=False,
                dry_run=self.dry_run,
                message=f"No se encontró el punto de entrada de Atlas: {entrypoint.name}",
                diagnosis=diagnosis,
                repairs=repairs,
                command={"args": command, "entrypoint": str(entrypoint)},
            ))

        if self.dry_run:
            return self._finalize(LaunchResult(
                success=True,
                started=False,
                dry_run=True,
                message=f"Atlas {target} está listo para iniciar",
                diagnosis=diagnosis,
                repairs=repairs,
                command={"args": command, "entrypoint": str(entrypoint), "status": "planned"},
            ))

        started = self._start(command, cwd=self.paths.program_dir)
        return self._finalize(LaunchResult(
            success=started.started,
            started=started.started,
            dry_run=False,
            message=(f"Atlas {target} fue iniciado" if started.started else f"No se pudo iniciar Atlas {target}"),
            pid=started.pid,
            diagnosis=diagnosis,
            repairs=repairs,
            command=started.to_dict(),
        ))


def launch_atlas(**kwargs) -> dict:
    """Convenience API for future CLI, GUI bootstrapper, and installer use."""
    launcher_options = {
        key: kwargs.pop(key)
        for key in ("dry_run", "paths", "diagnostician", "process_starter", "healer_factory")
        if key in kwargs
    }
    return Launcher(**launcher_options).launch(**kwargs).to_dict()
