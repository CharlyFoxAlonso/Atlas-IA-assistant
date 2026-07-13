import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.system.healer import Healer
from core.system.paths import AtlasPaths
from core.system.result_types import CommandResult


def make_paths(root: Path, mode: str = "development") -> AtlasPaths:
    return AtlasPaths(
        mode=mode,
        program_dir=root / "program",
        project_root=root,
        data_dir=root / "data",
        private_memory_dir=root / "memory",
        chroma_dir=root / "vector_db",
        config_dir=root / "config",
        cache_dir=root / "cache",
        logs_dir=root / "logs",
        downloads_dir=root / "downloads",
        temp_dir=root / "temp",
        managed_bin_dir=root / "bin",
        models_dir=root / "models",
    )


def diagnosis(**ollama_overrides):
    ollama = {
        "installed": False,
        "executable": None,
        "service_available": False,
        "selected_model": "qwen3:8b",
        "selected_model_available": False,
    }
    ollama.update(ollama_overrides)
    return {"health_score": 50, "python": {"in_venv": False}, "ollama": ollama}


class HealerTests(unittest.TestCase):
    def setUp(self):
        self._log_patcher = patch("core.system.healer.write_operational_event")
        self._log_patcher.start()

    def tearDown(self):
        self._log_patcher.stop()

    def test_default_is_dry_run_and_does_not_create_folders(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            result = Healer(diagnosis(), paths=paths).fix("folders")
            self.assertTrue(result.dry_run)
            self.assertFalse(result.changed)
            self.assertFalse(paths.data_dir.exists())

    def test_folder_repair_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            healer = Healer(diagnosis(), dry_run=False, paths=paths, diagnostician=lambda **_: diagnosis())
            first = healer.fix("folders")
            second = healer.fix("folders")
            self.assertTrue(first.changed)
            self.assertFalse(second.changed)
            self.assertTrue(second.success)

    def test_existing_config_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            paths.config_dir.mkdir(parents=True)
            env_file = paths.config_dir / ".env"
            env_file.write_text("NVIDIA_API_KEY=keep-me\n", encoding="utf-8")
            result = Healer(diagnosis(), dry_run=False, paths=paths).fix("config")
            self.assertFalse(result.changed)
            self.assertEqual(env_file.read_text(encoding="utf-8"), "NVIDIA_API_KEY=keep-me\n")

    def test_new_config_contains_no_api_key_placeholder(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            result = Healer(diagnosis(), dry_run=False, paths=paths, diagnostician=lambda **_: diagnosis()).fix("config")
            content = (paths.config_dir / ".env").read_text(encoding="utf-8")
            self.assertTrue(result.success)
            self.assertNotIn("API_KEY", content)
            self.assertNotIn("#ATLAS_", content)

    def test_heavy_action_requires_explicit_consent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements.txt").write_text("requests>=2\n", encoding="utf-8")
            runner = Mock()
            result = Healer(
                diagnosis(), dry_run=False, allow_heavy=False, paths=make_paths(root, "packaged"), command_runner=runner
            ).fix("python_packages")
            self.assertFalse(result.success)
            self.assertEqual(result.actions[0]["reason"], "consent_required")
            runner.assert_not_called()

    def test_requirements_install_checks_return_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements.txt").write_text("requests>=2\n", encoding="utf-8")
            runner = Mock(return_value=CommandResult(["pip"], 2, stderr="failed"))
            result = Healer(
                diagnosis(),
                dry_run=False,
                allow_heavy=True,
                paths=make_paths(root, "packaged"),
                command_runner=runner,
                diagnostician=lambda **_: diagnosis(),
            ).fix("python_packages")
            self.assertFalse(result.success)
            self.assertIn("failed", result.errors)

    def test_model_pull_is_not_repeated_when_present(self):
        runner = Mock()
        result = Healer(
            diagnosis(
                installed=True,
                executable="ollama",
                service_available=True,
                selected_model_available=True,
            ),
            dry_run=False,
            allow_heavy=True,
            command_runner=runner,
        ).fix("ollama_model")
        self.assertTrue(result.success)
        self.assertFalse(result.changed)
        runner.assert_not_called()

    def test_fix_all_isolates_partial_failure(self):
        healer = Healer(diagnosis())
        with self.assertLogs("core.system.healer", level="ERROR"), patch.object(
            healer,
            "fix",
            side_effect=[RuntimeError("boom"), healer.fix_config(), healer.verify_venv(), healer.fix_ollama_service()],
        ):
            report = healer.fix_all()
        self.assertFalse(report["success"])
        self.assertEqual(len(report["results"]), 4)
        self.assertIn("RuntimeError", report["results"][0]["errors"][0])


if __name__ == "__main__":
    unittest.main()
