import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.system.launcher import Launcher
from core.system.paths import AtlasPaths
from core.system.result_types import CommandResult, RepairResult


def paths_for(root: Path) -> AtlasPaths:
    return AtlasPaths(
        mode="development",
        program_dir=root,
        project_root=root,
        data_dir=root,
        private_memory_dir=root / "memory" / "Atlas_Memory",
        chroma_dir=root / "vector_db",
        config_dir=root,
        cache_dir=root / "cache",
        logs_dir=root / "logs",
        downloads_dir=root / "downloads",
        temp_dir=root / "temp",
        managed_bin_dir=root / "bin",
        models_dir=root / "models",
    )


class FakeHealer:
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def fix(self, component):
        self.calls.append(component)
        return RepairResult(component=component, success=True, dry_run=self.kwargs["dry_run"])


class LauncherTests(unittest.TestCase):
    def setUp(self):
        FakeHealer.calls = []

    def test_not_ready_never_starts_process(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "atlas_ui.py").touch()
            starter = Mock()
            result = Launcher(
                dry_run=False,
                paths=paths_for(root),
                diagnostician=lambda **_: {"ready_to_start": False},
                process_starter=starter,
            ).launch()
            self.assertFalse(result.success)
            self.assertFalse(result.started)
            starter.assert_not_called()

    def test_dry_run_returns_planned_command_without_starting(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "atlas_ui.py").touch()
            starter = Mock()
            result = Launcher(
                paths=paths_for(root),
                diagnostician=lambda **_: {"ready_to_start": True},
                process_starter=starter,
            ).launch(port=8501)
            self.assertTrue(result.success)
            self.assertFalse(result.started)
            self.assertEqual(result.command["status"], "planned")
            self.assertIn("8501", result.command["args"])
            starter.assert_not_called()

    def test_ready_ui_starts_with_argument_list(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "atlas_ui.py").touch()
            starter = Mock(return_value=CommandResult(["python"], None, pid=42))
            result = Launcher(
                dry_run=False,
                paths=paths_for(root),
                diagnostician=lambda **_: {"ready_to_start": True},
                process_starter=starter,
            ).launch()
            self.assertTrue(result.started)
            self.assertEqual(result.pid, 42)
            args = starter.call_args.args[0]
            self.assertEqual(args[1:4], ["-m", "streamlit", "run"])

    def test_authorized_safe_repairs_are_delegated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "run.py").touch()
            result = Launcher(
                paths=paths_for(root),
                diagnostician=lambda **_: {"ready_to_start": True},
                healer_factory=FakeHealer,
            ).launch(target="cli", authorized_repairs=["folders", "config"])
            self.assertTrue(result.success)
            self.assertEqual(FakeHealer.calls, ["folders", "config"])
            self.assertEqual(len(result.repairs), 2)

    def test_launcher_requests_target_specific_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "run.py").touch()
            diagnostician = Mock(return_value={"ready_to_start": True})
            result = Launcher(paths=paths_for(root), diagnostician=diagnostician).launch(target="cli")
            self.assertTrue(result.success)
            self.assertEqual(diagnostician.call_args.kwargs["profile"], "cli")

    def test_heavy_repairs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            result = Launcher(
                paths=paths_for(Path(temp)),
                diagnostician=lambda **_: {"ready_to_start": True},
            ).launch(authorized_repairs=["python_packages"])
            self.assertFalse(result.success)
            self.assertIn("python_packages", result.message)

    def test_invalid_target_and_port_are_rejected(self):
        launcher = Launcher(diagnostician=lambda **_: {"ready_to_start": True})
        with self.assertRaises(ValueError):
            launcher.launch(target="unknown")
        with self.assertRaises(ValueError):
            launcher.launch(port=70000)


if __name__ == "__main__":
    unittest.main()
