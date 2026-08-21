import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.system.__main__ import (
    EXIT_ARGUMENT_ERROR,
    EXIT_NOT_READY,
    EXIT_OK,
    EXIT_OPERATION_FAILED,
    main,
)
from core.system.result_types import LaunchResult, RepairResult


def diagnosis(ready=True, warnings=None, in_venv=True, index_state=None):
    report = {
        "atlas_version": "4.1.0",
        "health_score": 90,
        "ready_to_start": ready,
        "execution_mode": "development",
        "data_location": "data",
        "python": {"version": "3.13", "executable": "python", "in_venv": in_venv},
        "critical_issues": [] if ready else ["backend"],
        "warnings": warnings or [],
        "capabilities": {"local_llm": True},
        "environment": {"NVIDIA_API_KEY": True},
    }
    if index_state is not None:
        labels = {
            "HEALTHY": "Saludable",
            "HEALTHY_EMPTY": "Saludable y vacío",
            "DEGRADED": "Degradado",
            "INCONSISTENT": "Inconsistente",
            "UNAVAILABLE": "No disponible",
        }
        report["index_consistency"] = {
            "state": index_state,
            "state_label": labels[index_state],
            "observed_state": index_state,
            "observed_state_label": labels[index_state],
            "healthy": index_state in {"HEALTHY", "HEALTHY_EMPTY"},
            "severity": "success" if index_state in {"HEALTHY", "HEALTHY_EMPTY"} else "warning",
            "writer_state": "inactive",
            "writer_label": "Inactivo",
            "possibly_transient": False,
            "sources_count": 1,
            "manifest_entries_count": 1,
            "chunk_count": 2,
            "divergences": {},
            "orphan_count": 0,
            "issues": [],
        }
    return report


def index_status_payload(state="INCONSISTENT"):
    labels = {
        "HEALTHY": "Saludable",
        "HEALTHY_EMPTY": "Saludable y vacío",
        "DEGRADED": "Degradado",
        "INCONSISTENT": "Inconsistente",
        "UNAVAILABLE": "No disponible",
    }
    return {
        "state": state,
        "state_label": labels[state],
        "observed_state": state,
        "observed_state_label": labels[state],
        "healthy": state in {"HEALTHY", "HEALTHY_EMPTY"},
        "severity": "success" if state in {"HEALTHY", "HEALTHY_EMPTY"} else "warning",
        "writer_state": "inactive",
        "writer_label": "Inactivo",
        "possibly_transient": state == "DEGRADED",
        "sources_count": 2,
        "manifest_entries_count": 1,
        "chunk_count": 3,
        "divergences": {"manifest_absent": 1} if state == "INCONSISTENT" else {},
        "orphan_count": 0,
        "issues": [],
    }


def index_preview_result(state="INCONSISTENT"):
    ready = state in {"HEALTHY", "HEALTHY_EMPTY", "INCONSISTENT"}
    action_status = (
        "not_needed"
        if state in {"HEALTHY", "HEALTHY_EMPTY"}
        else "planned" if state == "INCONSISTENT" else "blocked"
    )
    return RepairResult(
        "index_consistency",
        success=ready,
        dry_run=True,
        risk="moderate",
        message="Vista previa del índice disponible" if ready else "Diagnóstico no reparable automáticamente",
        actions=[
            {
                "action": "preview_index_repair",
                "status": action_status,
                "index_status": index_status_payload(state),
            }
        ],
    )


def index_apply_result(*, status="completed", success=True, items=None):
    return RepairResult(
        "index_consistency",
        success=success,
        changed=status in {"completed", "partial"},
        dry_run=False,
        risk="moderate",
        message="Reparación completada" if success else "Reparación no convergente",
        actions=[
            {
                "action": "repair_index",
                "status": status,
                "pre_state": "INCONSISTENT",
                "post_state": "HEALTHY" if success else "INCONSISTENT",
                "post_observed": "HEALTHY" if success else "INCONSISTENT",
                "post_check_performed": status != "busy",
                "blocked": status == "blocked",
                "blocked_reason": "manifest_corrupt" if status == "blocked" else None,
                "busy": status == "busy",
                "busy_message": (
                    "Index writer is busy; another indexing operation is active."
                    if status == "busy"
                    else None
                ),
                "orphan_count": 1,
                "items": items or [],
            }
        ],
    )


class CliTests(unittest.TestCase):
    def test_default_only_prints_help(self):
        output = io.StringIO()
        with patch("core.system.__main__.diagnosticar_sistema") as doctor, patch(
            "core.system.__main__.Healer"
        ) as healer, patch("core.system.__main__.Launcher") as launcher:
            code = main([], stdout=output)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("python -m core.system doctor", output.getvalue())
        doctor.assert_not_called()
        healer.assert_not_called()
        launcher.assert_not_called()

    @patch("core.system.__main__.diagnosticar_sistema", return_value=diagnosis())
    def test_doctor_json_is_valid_and_contains_no_secret_value(self, doctor):
        output = io.StringIO()
        code = main(["doctor", "--json"], stdout=output)
        payload = json.loads(output.getvalue())
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(payload["environment"]["NVIDIA_API_KEY"])
        self.assertNotIn("secret-value", output.getvalue())
        doctor.assert_called_once_with(
            profile="ui",
            deep_packages=False,
            include_index_consistency=True,
        )

    @patch("core.system.__main__.diagnosticar_sistema", return_value=diagnosis(False, in_venv=False))
    def test_doctor_not_ready_and_explains_global_python(self, _doctor):
        output = io.StringIO()
        code = main(["doctor"], stdout=output)
        self.assertEqual(code, EXIT_NOT_READY)
        self.assertIn("Python global", output.getvalue())
        self.assertIn(".venv", output.getvalue())

    @patch("core.system.__main__.diagnosticar_sistema", return_value=diagnosis(True, warnings=["optional degraded"]))
    def test_doctor_warning_uses_exit_one(self, _doctor):
        code = main(["doctor"], stdout=io.StringIO())
        self.assertEqual(code, EXIT_NOT_READY)

    @patch(
        "core.system.__main__.diagnosticar_sistema",
        return_value=diagnosis(
            True,
            warnings=["Index consistency: UNAVAILABLE"],
            index_state="UNAVAILABLE",
        ),
    )
    def test_human_doctor_renders_controlled_unavailable_index(self, _doctor):
        output = io.StringIO()
        code = main(["doctor"], stdout=output)
        rendered = output.getvalue()
        self.assertEqual(code, EXIT_NOT_READY)
        self.assertIn("Estado del índice", rendered)
        self.assertIn("UNAVAILABLE", rendered)
        self.assertIn("Escritor: Inactivo", rendered)
        self.assertNotIn("Traceback", rendered)

    def test_argument_error_uses_exit_two(self):
        error = io.StringIO()
        code = main(["heal", "python_packages", "--apply"], stderr=error)
        self.assertEqual(code, EXIT_ARGUMENT_ERROR)
        self.assertIn("--allow-heavy", error.getvalue())

    def test_argparse_error_uses_exit_two_and_supplied_stderr(self):
        error = io.StringIO()
        code = main(["unknown-command"], stderr=error)
        self.assertEqual(code, EXIT_ARGUMENT_ERROR)
        self.assertIn("invalid choice", error.getvalue())

    def test_explicit_help_uses_exit_zero(self):
        output = io.StringIO()
        code = main(["--help"], stdout=output)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("SEGURIDAD:", output.getvalue())

    def test_help_command_lists_all_commands(self):
        output = io.StringIO()
        code = main(["help"], stdout=output)
        self.assertEqual(code, EXIT_OK)
        for command in ("doctor", "heal", "launch"):
            self.assertIn(command, output.getvalue())

    def test_help_for_specific_command(self):
        output = io.StringIO()
        code = main(["help", "doctor"], stdout=output)
        self.assertEqual(code, EXIT_OK)
        self.assertIn("--profile", output.getvalue())
        self.assertIn("--deep", output.getvalue())

    @patch("core.system.__main__.Healer")
    def test_heal_defaults_to_dry_run_without_side_effects(self, healer_class):
        healer = healer_class.return_value
        healer.fix.return_value = RepairResult("folders", success=True, dry_run=True, message="planned")
        output = io.StringIO()
        code = main(["heal", "folders", "--json"], stdout=output)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(json.loads(output.getvalue())["dry_run"])
        healer_class.assert_called_once_with(dry_run=True, allow_heavy=False)

    @patch("core.system.__main__.Healer")
    def test_apply_is_required_for_real_repair(self, healer_class):
        healer = healer_class.return_value
        healer.fix.return_value = RepairResult("folders", success=True, dry_run=False)
        code = main(["heal", "folders", "--apply"], stdout=io.StringIO())
        self.assertEqual(code, EXIT_OK)
        healer_class.assert_called_once_with(dry_run=False, allow_heavy=False)

    @patch("core.system.__main__.Healer")
    def test_index_heal_defaults_to_read_only_preview(self, healer_class):
        healer_class.return_value.fix.return_value = index_preview_result()
        output = io.StringIO()

        code = main(["heal", "index_consistency", "--json"], stdout=output)

        payload = json.loads(output.getvalue())
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["results"][0]["actions"][0]["status"], "planned")
        healer_class.assert_called_once_with(
            diagnosis={},
            dry_run=True,
            allow_heavy=False,
        )

    @patch("core.system.__main__.Healer")
    def test_index_heal_apply_is_explicit(self, healer_class):
        healer_class.return_value.fix.return_value = index_apply_result()

        code = main(
            ["heal", "index_consistency", "--apply", "--json"],
            stdout=io.StringIO(),
        )

        self.assertEqual(code, EXIT_OK)
        healer_class.assert_called_once_with(
            diagnosis={},
            dry_run=False,
            allow_heavy=False,
        )

    @patch("core.system.__main__.Healer")
    def test_index_preview_degraded_uses_exit_one(self, healer_class):
        healer_class.return_value.fix.return_value = index_preview_result("DEGRADED")

        code = main(["heal", "index_consistency"], stdout=io.StringIO())

        self.assertEqual(code, EXIT_NOT_READY)

    def test_index_apply_non_success_outcomes_use_exit_three(self):
        for outcome in ("busy", "blocked", "partial", "failed", "still_inconsistent"):
            with self.subTest(outcome=outcome), patch("core.system.__main__.Healer") as healer_class:
                healer_class.return_value.fix.return_value = index_apply_result(
                    status=outcome,
                    success=False,
                )
                code = main(
                    ["heal", "index_consistency", "--apply"],
                    stdout=io.StringIO(),
                )
                self.assertEqual(code, EXIT_OPERATION_FAILED)

    @patch("core.system.__main__.Healer")
    def test_human_index_busy_is_never_presented_as_success(self, healer_class):
        healer_class.return_value.fix.return_value = index_apply_result(
            status="busy",
            success=False,
        )
        output = io.StringIO()

        code = main(
            ["heal", "index_consistency", "--apply"],
            stdout=output,
        )

        self.assertEqual(code, EXIT_OPERATION_FAILED)
        self.assertIn("OCUPADO", output.getvalue())
        self.assertNotIn("[OK] index_consistency", output.getvalue())

    @patch("core.system.__main__.Healer")
    def test_human_index_partial_lists_anonymous_item_statuses(self, healer_class):
        healer_class.return_value.fix.return_value = index_apply_result(
            status="partial",
            success=False,
            items=[
                {
                    "item": 1,
                    "category": "manifest_absent",
                    "action": "reindex",
                    "status": "failed",
                    "error_type": "RuntimeError",
                },
                {
                    "item": 2,
                    "category": "manifest_absent",
                    "action": "reindex",
                    "status": "still_inconsistent",
                    "error_type": None,
                },
            ],
        )
        output = io.StringIO()

        code = main(
            ["heal", "index_consistency", "--apply"],
            stdout=output,
        )

        rendered = output.getvalue()
        self.assertEqual(code, EXIT_OPERATION_FAILED)
        self.assertIn("RESULTADO PARCIAL", rendered)
        self.assertIn("item 1", rendered)
        self.assertIn("still_inconsistent", rendered)
        self.assertNotIn("identity", rendered)

    def test_launcher_never_accepts_index_repair(self):
        error = io.StringIO()
        with patch("core.system.__main__.Launcher") as launcher_class:
            code = main(
                ["launch", "--repair", "index_consistency"],
                stderr=error,
            )
        self.assertEqual(code, EXIT_ARGUMENT_ERROR)
        self.assertIn("invalid choice", error.getvalue())
        launcher_class.assert_not_called()

    @patch("core.system.__main__.Launcher")
    def test_launch_defaults_to_dry_run(self, launcher_class):
        launcher_class.return_value.launch.return_value = LaunchResult(
            success=True, dry_run=True, message="ready", diagnosis=diagnosis()
        )
        output = io.StringIO()
        code = main(["launch", "--json"], stdout=output)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(json.loads(output.getvalue())["dry_run"])
        launcher_class.assert_called_once_with(dry_run=True)

    @patch("core.system.__main__.Launcher")
    def test_failed_launch_uses_exit_three(self, launcher_class):
        launcher_class.return_value.launch.return_value = LaunchResult(
            success=False, dry_run=False, message="failed", diagnosis=diagnosis(False)
        )
        code = main(["launch", "--apply"], stdout=io.StringIO())
        self.assertEqual(code, EXIT_OPERATION_FAILED)
        launcher_class.assert_called_once_with(dry_run=False)


class CliProcessTests(unittest.TestCase):
    def test_real_help_process_exits_zero(self):
        process = subprocess.run(
            [sys.executable, "-m", "core.system", "help"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, EXIT_OK)
        self.assertIn("doctor", process.stdout)

    def test_real_invalid_argument_process_exits_two(self):
        process = subprocess.run(
            [sys.executable, "-m", "core.system", "unknown"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, EXIT_ARGUMENT_ERROR)


if __name__ == "__main__":
    unittest.main()
