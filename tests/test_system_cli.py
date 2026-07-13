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


def diagnosis(ready=True, warnings=None, in_venv=True):
    return {
        "atlas_version": "3.9",
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
    def test_doctor_json_is_valid_and_contains_no_secret_value(self, _doctor):
        output = io.StringIO()
        code = main(["doctor", "--json"], stdout=output)
        payload = json.loads(output.getvalue())
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(payload["environment"]["NVIDIA_API_KEY"])
        self.assertNotIn("secret-value", output.getvalue())

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
