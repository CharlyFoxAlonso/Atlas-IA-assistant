"""Explicit, conservative repairs for the Atlas runtime.

Healer is dry-run by default. It never downloads or installs software merely
because it was imported or executed as a module.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from core.system.command_runner import run_command, start_command
from core.system.doctor import MODELO_LOCAL, diagnosticar_sistema
from core.system.paths import AtlasPaths, get_paths
from core.system.result_types import CommandResult, RepairResult
from core.system.operational_log import write_operational_event

logger = logging.getLogger(__name__)

SAFE_COMPONENTS = ("folders", "config", "venv", "ollama_service")
HEAVY_COMPONENTS = ("python_packages", "ollama_model")
CONTROLLED_COMPONENTS = ("index_consistency",)
ALL_COMPONENTS = SAFE_COMPONENTS + HEAVY_COMPONENTS + CONTROLLED_COMPONENTS

_INDEX_STATES = frozenset(
    {"HEALTHY", "HEALTHY_EMPTY", "DEGRADED", "INCONSISTENT", "UNAVAILABLE"}
)
_INDEX_PREVIEW_READY_STATES = frozenset(
    {"HEALTHY", "HEALTHY_EMPTY", "INCONSISTENT"}
)
_INDEX_HEALTHY_STATES = frozenset({"HEALTHY", "HEALTHY_EMPTY"})
_INDEX_BLOCKED_REASONS = frozenset(
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


def _default_index_status_provider() -> object:
    from core.index_status import consultar_estado_indice

    return consultar_estado_indice()


def _default_index_repairer() -> object:
    from core.index_repair import reparar_indice

    return reparar_indice()


def _safe_index_error_type(error: object) -> str:
    try:
        from core.vector_store import _tipo_error_seguro

        return _tipo_error_seguro(error)
    except Exception:
        return "Exception"


def _safe_index_state(value: object) -> str:
    return value if isinstance(value, str) and value in _INDEX_STATES else "UNAVAILABLE"


class Healer:
    def __init__(
        self,
        diagnosis: Optional[dict] = None,
        *,
        dry_run: bool = True,
        allow_heavy: bool = False,
        paths: Optional[AtlasPaths] = None,
        command_runner: Callable[..., CommandResult] = run_command,
        process_starter: Callable[..., CommandResult] = start_command,
        diagnostician: Callable[..., dict] = diagnosticar_sistema,
        index_status_provider: Optional[Callable[[], object]] = None,
        index_repairer: Optional[Callable[[], object]] = None,
    ) -> None:
        self.paths = paths or get_paths()
        self.dry_run = dry_run
        self.allow_heavy = allow_heavy
        self._run = command_runner
        self._start = process_starter
        self._diagnose = diagnostician
        self._index_status_provider = (
            index_status_provider
            if index_status_provider is not None
            else _default_index_status_provider
        )
        self._index_repairer = (
            index_repairer
            if index_repairer is not None
            else _default_index_repairer
        )
        self.diagnosis = diagnosis if diagnosis is not None else self._fresh_diagnosis()

    def _fresh_diagnosis(self) -> dict:
        try:
            return self._diagnose(paths=self.paths)
        except TypeError:
            # Makes a simple zero-argument test double possible.
            return self._diagnose()

    def _result(
        self,
        component: str,
        *,
        success: bool,
        changed: bool = False,
        risk: str = "safe",
        message: str = "",
        actions: Optional[list[dict]] = None,
        errors: Optional[list[str]] = None,
        include_diagnosis: bool = True,
    ) -> RepairResult:
        result = RepairResult(
            component=component,
            success=success,
            changed=changed,
            dry_run=self.dry_run,
            risk=risk,
            message=message,
            actions=actions or [],
            errors=errors or [],
            diagnosis_before=self.diagnosis if include_diagnosis else None,
        )
        logger.info(
            "Atlas repair component=%s success=%s changed=%s dry_run=%s risk=%s",
            component,
            success,
            changed,
            self.dry_run,
            risk,
        )
        if not self.dry_run:
            write_operational_event(
                self.paths,
                component="healer",
                event="repair_result",
                payload={
                    "repair": component,
                    "success": success,
                    "changed": changed,
                    "risk": risk,
                    "message": message,
                    "actions": actions or [],
                    "errors": errors or [],
                },
            )
        return result

    def _finish(self, result: RepairResult, *, rediagnose: bool = True) -> RepairResult:
        if rediagnose and not self.dry_run and result.success:
            result.diagnosis_after = self._fresh_diagnosis()
            self.diagnosis = result.diagnosis_after
        return result

    def _blocked_heavy(self, component: str, action: str) -> Optional[RepairResult]:
        if self.dry_run:
            return None
        if self.allow_heavy:
            return None
        return self._result(
            component,
            success=False,
            risk="heavy",
            message=f"Consentimiento explícito requerido para {action}",
            actions=[{"action": action, "status": "blocked", "reason": "consent_required"}],
        )

    def fix(self, component: str) -> RepairResult:
        handlers = {
            "folders": self.fix_folders,
            "config": self.fix_config,
            "venv": self.verify_venv,
            "python_packages": self.fix_python_packages,
            "ollama_service": self.fix_ollama_service,
            "ollama_model": self.fix_ollama_model,
            "index_consistency": self.fix_index_consistency,
        }
        try:
            handler = handlers[component]
        except KeyError as exc:
            raise ValueError(f"Componente desconocido: {component}") from exc
        return handler()

    def _index_unavailable_result(self, error: object) -> RepairResult:
        error_type = _safe_index_error_type(error)
        return self._result(
            "index_consistency",
            success=False,
            changed=False,
            risk="moderate",
            message="No se pudo obtener un resultado seguro para el índice",
            actions=[
                {
                    "action": (
                        "preview_index_repair" if self.dry_run else "repair_index"
                    ),
                    "status": "unavailable",
                }
            ],
            errors=[error_type],
            include_diagnosis=False,
        )

    def _preview_index_consistency(self) -> RepairResult:
        try:
            from core.index_status import IndexStatusView

            status = self._index_status_provider()
            if type(status) is not IndexStatusView:
                raise TypeError("invalid index status contract")
            state = _safe_index_state(status.state)
            observed_state = _safe_index_state(status.observed_state)
            if state != status.state or observed_state != status.observed_state:
                raise ValueError("invalid index status state")
            status_payload = status.to_dict()
        except Exception as exc:
            return self._index_unavailable_result(exc)

        if state in _INDEX_HEALTHY_STATES:
            action_status = "not_needed"
            message = "El índice ya está convergente; no se requiere reparación"
        elif state == "INCONSISTENT":
            action_status = "planned"
            message = (
                "La reparación conservadora está disponible; usá --apply para autorizarla"
            )
        else:
            action_status = "blocked"
            message = "El diagnóstico actual no permite una reparación automática segura"

        return self._result(
            "index_consistency",
            success=state in _INDEX_PREVIEW_READY_STATES,
            changed=False,
            risk="moderate",
            message=message,
            actions=[
                {
                    "action": "preview_index_repair",
                    "status": action_status,
                    "index_status": status_payload,
                }
            ],
            include_diagnosis=False,
        )

    @staticmethod
    def _index_apply_status(report: object, items: list[dict]) -> str:
        if report.busy:
            return "busy"
        if report.blocked:
            return "blocked"
        if report.success:
            return "completed"

        actionable = [item for item in items if item["status"] != "skipped"]
        repaired = any(item["status"] == "repaired" for item in actionable)
        has_divergence = (
            any(
                item["status"] in {"failed", "still_inconsistent"}
                for item in actionable
            )
            or report.post_state not in _INDEX_HEALTHY_STATES
        )
        if repaired and has_divergence:
            return "partial"
        if actionable and all(item["status"] == "failed" for item in actionable):
            return "failed"
        return "still_inconsistent"

    def _apply_index_consistency(self) -> RepairResult:
        try:
            from core.index_repair import RepairItem, RepairReport
            from core.index_writer_lock import PUBLIC_BUSY_MESSAGES

            report = self._index_repairer()
            if type(report) is not RepairReport:
                raise TypeError("invalid index repair contract")
            states = (report.pre_state, report.post_state, report.post_observed)
            if any(_safe_index_state(state) != state for state in states):
                raise ValueError("invalid index repair state")
            if type(report.post_check_performed) is not bool:
                raise TypeError("invalid post-check contract")
            if (
                type(report.success) is not bool
                or type(report.blocked) is not bool
                or type(report.busy) is not bool
            ):
                raise TypeError("invalid index outcome contract")
            if type(report.items) is not tuple:
                raise TypeError("invalid repair items contract")
            if type(report.orphan_count) is not int or report.orphan_count < 0:
                raise ValueError("invalid orphan count")

            safe_items = []
            for ordinal, item in enumerate(report.items, start=1):
                if type(item) is not RepairItem:
                    raise TypeError("invalid repair item contract")
                safe_items.append(
                    {
                        "item": ordinal,
                        "category": item.category,
                        "action": item.action,
                        "status": item.status,
                        "error_type": (
                            _safe_index_error_type(item.error_type)
                            if item.error_type is not None
                            else None
                        ),
                    }
                )

            if report.busy:
                if report.blocked or report.post_check_performed or safe_items:
                    raise ValueError("contradictory busy repair report")
            elif not report.post_check_performed:
                raise ValueError("missing final post-check")
            if report.blocked and safe_items:
                raise ValueError("blocked repair report contains items")
            if any(item["status"] == "attempted" for item in safe_items):
                raise ValueError("unconfirmed repair item")

            expected_success = (
                report.post_check_performed
                and report.post_state in _INDEX_HEALTHY_STATES
                and not report.blocked
                and not report.busy
                and all(
                    item["status"] in {"repaired", "skipped"}
                    for item in safe_items
                )
            )
            if report.success is not expected_success:
                raise ValueError("contradictory repair success")

            blocked_reason = None
            if report.blocked:
                blocked_reason = (
                    report.blocked_reason
                    if report.blocked_reason in _INDEX_BLOCKED_REASONS
                    else "unavailable"
                )
            busy_message = None
            if report.busy:
                allowed_busy_messages = frozenset(PUBLIC_BUSY_MESSAGES.values())
                busy_message = (
                    report.busy_message
                    if report.busy_message in allowed_busy_messages
                    else PUBLIC_BUSY_MESSAGES["index_writer_busy"]
                )

            outcome_status = self._index_apply_status(report, safe_items)
        except Exception as exc:
            return self._index_unavailable_result(exc)

        messages = {
            "busy": "El índice está ocupado; no se ejecutó ninguna reparación",
            "blocked": "La reparación fue bloqueada por un diagnóstico no seguro",
            "completed": "La reparación fue confirmada por el post-check",
            "partial": "La reparación fue parcial y el índice no convergió por completo",
            "failed": "Las operaciones de reparación fallaron",
            "still_inconsistent": "El post-check confirmó que el índice sigue inconsistente",
        }
        errors = []
        if outcome_status == "busy":
            errors.append("index_writer_busy")
        elif outcome_status == "blocked":
            errors.append(blocked_reason or "unavailable")
        else:
            errors.extend(
                item["error_type"] or "Exception"
                for item in safe_items
                if item["status"] == "failed"
            )
            errors.extend(
                "still_inconsistent"
                for item in safe_items
                if item["status"] == "still_inconsistent"
            )
            if not report.success and not errors:
                errors.append("post_check_not_healthy")

        return self._result(
            "index_consistency",
            success=report.success,
            changed=any(item["status"] == "repaired" for item in safe_items),
            risk="moderate",
            message=messages[outcome_status],
            actions=[
                {
                    "action": "repair_index",
                    "status": outcome_status,
                    "pre_state": report.pre_state,
                    "post_state": report.post_state,
                    "post_observed": report.post_observed,
                    "post_check_performed": report.post_check_performed,
                    "blocked": report.blocked,
                    "blocked_reason": blocked_reason,
                    "busy": report.busy,
                    "busy_message": busy_message,
                    "orphan_count": report.orphan_count,
                    "items": safe_items,
                }
            ],
            errors=errors,
            include_diagnosis=False,
        )

    def fix_index_consistency(self) -> RepairResult:
        """Preview or explicitly invoke IDX-C3 without duplicating its policy."""
        if self.dry_run:
            return self._preview_index_consistency()
        return self._apply_index_consistency()

    def fix_folders(self) -> RepairResult:
        targets = {
            "data": self.paths.data_dir,
            "memory": self.paths.private_memory_dir,
            "chromadb": self.paths.chroma_dir,
            "config": self.paths.config_dir,
            "cache": self.paths.cache_dir,
            "logs": self.paths.logs_dir,
            "downloads": self.paths.downloads_dir,
            "temp": self.paths.temp_dir,
            "managed_bin": self.paths.managed_bin_dir,
            "models": self.paths.models_dir,
        }
        missing = [(name, path) for name, path in targets.items() if not path.is_dir()]
        if not missing:
            return self._result("folders", success=True, message="Las carpetas ya están preparadas")

        actions = [
            {"action": "create_directory", "target": str(path), "status": "planned"}
            for _, path in missing
        ]
        if self.dry_run:
            return self._result(
                "folders",
                success=True,
                changed=False,
                message=f"Se crearían {len(missing)} carpetas",
                actions=actions,
            )

        errors: list[str] = []
        changed = False
        for index, (name, path) in enumerate(missing):
            try:
                path.mkdir(parents=True, exist_ok=True)
                actions[index]["status"] = "completed"
                changed = True
            except OSError as exc:
                actions[index]["status"] = "failed"
                errors.append(f"{name}: {exc}")
        return self._finish(
            self._result(
                "folders",
                success=not errors,
                changed=changed,
                message="Carpetas procesadas",
                actions=actions,
                errors=errors,
            )
        )

    def fix_config(self) -> RepairResult:
        """Create a minimal config file only when none exists; never append keys."""
        env_path = self.paths.config_dir / ".env"
        if env_path.exists():
            return self._result("config", success=True, message="La configuración existente se conservó")
        action = {"action": "create_config", "target": str(env_path), "status": "planned"}
        if self.dry_run:
            return self._result(
                "config",
                success=True,
                message="Se crearía una configuración mínima sin secretos",
                actions=[action],
            )
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text(
                "# Atlas - configuración local (no incluir secretos en backups)\n"
                f"MODELO_LOCAL={MODELO_LOCAL}\n"
                "URL_OLLAMA=http://127.0.0.1:11434/api/chat\n",
                encoding="utf-8",
            )
            action["status"] = "completed"
            return self._finish(
                self._result(
                    "config",
                    success=True,
                    changed=True,
                    message="Configuración mínima creada sin claves API",
                    actions=[action],
                )
            )
        except OSError as exc:
            action["status"] = "failed"
            return self._result(
                "config", success=False, message="No se pudo crear la configuración", actions=[action], errors=[str(exc)]
            )

    def verify_venv(self) -> RepairResult:
        python = self.diagnosis.get("python", {})
        private_runtime = bool(python.get("in_venv") or self.paths.mode == "packaged")
        return self._result(
            "venv",
            success=private_runtime,
            risk="safe",
            message=(
                "Atlas usa un runtime privado"
                if private_runtime
                else "Atlas está usando Python global; no se crea un entorno automáticamente"
            ),
            actions=[{"action": "verify_private_runtime", "status": "ok" if private_runtime else "warning"}],
        )

    def fix_python_packages(self) -> RepairResult:
        requirements = self.paths.project_root / "requirements.txt"
        action = {
            "action": "install_requirements",
            "target": str(requirements),
            "status": "planned",
        }
        if not requirements.is_file():
            return self._result(
                "python_packages",
                success=False,
                risk="heavy",
                message="No se encontró requirements.txt",
                actions=[{**action, "status": "failed"}],
            )
        try:
            requirement_lines = [
                line.strip()
                for line in requirements.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
        except OSError as exc:
            return self._result(
                "python_packages", success=False, risk="heavy", message="No se pudo leer requirements.txt", errors=[str(exc)]
            )
        action["requirements_count"] = len(requirement_lines)
        if not requirement_lines:
            return self._result("python_packages", success=True, risk="heavy", message="No hay requisitos para instalar")
        if self.dry_run:
            return self._result(
                "python_packages",
                success=True,
                risk="heavy",
                message=f"Se instalarían {len(requirement_lines)} requisitos desde el archivo curado",
                actions=[action],
            )
        blocked = self._blocked_heavy("python_packages", "instalar paquetes Python")
        if blocked:
            return blocked
        if not (sys.prefix != sys.base_prefix or self.paths.mode == "packaged"):
            action["status"] = "blocked"
            return self._result(
                "python_packages",
                success=False,
                risk="heavy",
                message="Se rechazó instalar paquetes en el Python global",
                actions=[action],
            )
        command = self._run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            timeout=None,
            cwd=self.paths.project_root,
        )
        action.update(status="completed" if command.success else "failed", command=command.to_dict())
        return self._finish(
            self._result(
                "python_packages",
                success=command.success,
                changed=command.success,
                risk="heavy",
                message="Instalación de requisitos finalizada" if command.success else "Falló la instalación de requisitos",
                actions=[action],
                errors=[] if command.success else [command.error or command.stderr or "pip returned an error"],
            )
        )

    def fix_ollama_service(self) -> RepairResult:
        ollama = self.diagnosis.get("ollama", {})
        if ollama.get("service_available"):
            return self._result("ollama_service", success=True, message="El servicio de Ollama ya responde")
        executable = ollama.get("executable")
        if not executable:
            return self._result(
                "ollama_service",
                success=False,
                risk="moderate",
                message="Ollama no está instalado o no fue encontrado en PATH",
            )
        action = {"action": "start_ollama_service", "executable": executable, "status": "planned"}
        if self.dry_run:
            return self._result(
                "ollama_service", success=True, risk="moderate", message="Se iniciaría el servicio de Ollama", actions=[action]
            )
        command = self._start([executable, "serve"], cwd=self.paths.program_dir)
        action.update(status="started" if command.started else "failed", command=command.to_dict())
        if not command.started:
            return self._result(
                "ollama_service",
                success=False,
                risk="moderate",
                message="No se pudo iniciar Ollama",
                actions=[action],
                errors=[command.error or "unknown process error"],
            )
        # Give the local service a bounded chance to become ready.
        latest = self.diagnosis
        for _ in range(10):
            time.sleep(0.5)
            latest = self._fresh_diagnosis()
            if latest.get("ollama", {}).get("service_available"):
                self.diagnosis = latest
                return self._finish(
                    self._result(
                        "ollama_service",
                        success=True,
                        changed=True,
                        risk="moderate",
                        message="El servicio de Ollama está disponible",
                        actions=[action],
                    ),
                    rediagnose=False,
                )
        return self._result(
            "ollama_service",
            success=False,
            changed=True,
            risk="moderate",
            message="Ollama se inició pero no respondió dentro del plazo",
            actions=[action],
            errors=["service_start_timeout"],
        )

    def fix_ollama_model(self) -> RepairResult:
        ollama = self.diagnosis.get("ollama", {})
        target = str(ollama.get("selected_model") or MODELO_LOCAL)
        if ollama.get("selected_model_available"):
            return self._result("ollama_model", success=True, risk="heavy", message=f"El modelo {target} ya está disponible")
        executable = ollama.get("executable")
        if not executable or not ollama.get("service_available"):
            return self._result(
                "ollama_model",
                success=False,
                risk="heavy",
                message="Ollama debe estar instalado y disponible antes de descargar un modelo",
            )
        action = {"action": "pull_ollama_model", "model": target, "status": "planned"}
        if self.dry_run:
            return self._result(
                "ollama_model", success=True, risk="heavy", message=f"Se descargaría el modelo {target}", actions=[action]
            )
        blocked = self._blocked_heavy("ollama_model", f"descargar el modelo {target}")
        if blocked:
            return blocked
        command = self._run([executable, "pull", target], timeout=None, cwd=self.paths.program_dir)
        action.update(status="completed" if command.success else "failed", command=command.to_dict())
        return self._finish(
            self._result(
                "ollama_model",
                success=command.success,
                changed=command.success,
                risk="heavy",
                message=f"Modelo {target} descargado" if command.success else f"Falló la descarga de {target}",
                actions=[action],
                errors=[] if command.success else [command.error or command.stderr or "ollama pull returned an error"],
            )
        )

    def fix_all(self, *, include_heavy: bool = False) -> dict:
        components = list(SAFE_COMPONENTS)
        if include_heavy:
            components.extend(HEAVY_COMPONENTS)
        before = self.diagnosis
        results: list[RepairResult] = []
        for component in components:
            try:
                results.append(self.fix(component))
            except Exception as exc:  # isolate component failures
                logger.exception("Unexpected Atlas repair failure: %s", component)
                results.append(
                    self._result(
                        component,
                        success=False,
                        message="Fallo inesperado aislado",
                        errors=[f"{type(exc).__name__}: {exc}"],
                    )
                )
        after = self.diagnosis if self.dry_run else self._fresh_diagnosis()
        return {
            "success": all(result.success for result in results),
            "dry_run": self.dry_run,
            "diagnosis_before": before,
            "diagnosis_after": after,
            "results": [result.to_dict() for result in results],
        }


if __name__ == "__main__":
    print("Healer no ejecuta reparaciones automáticamente. Usá la futura CLI de core.system.")
