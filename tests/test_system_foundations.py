import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.system.command_runner import run_command, start_command
from core.system.doctor import (
    _derive_capabilities,
    _detect_gpu,
    _detect_ollama,
    _detect_python_packages,
    _read_env_presence,
    _startup_profiles,
    diagnosticar_sistema,
)
from core.system.paths import get_paths
from core.system.result_types import CheckResult, CommandResult, DiagnosisResult


class ResultTypeTests(unittest.TestCase):
    def test_nested_results_are_json_serializable(self):
        result = DiagnosisResult(
            atlas_version="4.1.0",
            timestamp="2026-07-12T00:00:00Z",
            health_score=90,
            ready_to_start=True,
            execution_mode="development",
            data_location="data",
            executable_location="python",
            checks=[CheckResult("python", "ok", "critical")],
        )
        self.assertIn('"python"', json.dumps(result.to_dict()))


class PathsTests(unittest.TestCase):
    def test_development_preserves_existing_layout(self):
        paths = get_paths(packaged=False, environment={})
        self.assertEqual(paths.mode, "development")
        self.assertEqual(paths.private_memory_dir, paths.project_root / "memory" / "Atlas_Memory")
        self.assertEqual(paths.chroma_dir, paths.project_root / "vector_db")

    def test_packaged_separates_program_and_user_data(self):
        env = {"LOCALAPPDATA": "C:/Users/Test/AppData/Local", "APPDATA": "C:/Users/Test/AppData/Roaming"}
        paths = get_paths(packaged=True, executable=Path("C:/Program Files/Atlas/Atlas.exe"), environment=env)
        self.assertEqual(paths.mode, "packaged")
        self.assertNotEqual(paths.program_dir, paths.data_dir)
        self.assertTrue(str(paths.data_dir).replace("\\", "/").endswith("AppData/Local/Atlas"))


class CommandRunnerTests(unittest.TestCase):
    @patch("core.system.command_runner.subprocess.run")
    def test_nonzero_return_code_is_preserved(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess(["tool"], 7, "out", "err")
        result = run_command(["tool"])
        self.assertEqual(result.returncode, 7)
        self.assertFalse(result.success)
        self.assertFalse(mocked_run.call_args.kwargs["shell"])

    @patch("core.system.command_runner.subprocess.run")
    def test_timeout_is_structured(self, mocked_run):
        mocked_run.side_effect = subprocess.TimeoutExpired(["tool"], 1)
        result = run_command(["tool"], timeout=1)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.success)

    @patch("core.system.command_runner.subprocess.run")
    def test_secrets_are_redacted(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess(["tool"], 0, "secret-value", "")
        result = run_command(["tool", "--api-key", "secret-value"], secrets=["secret-value"])
        self.assertNotIn("secret-value", json.dumps(result.to_dict()))

    @patch("core.system.command_runner.subprocess.run")
    def test_timeout_decodes_byte_output(self, mocked_run):
        mocked_run.side_effect = subprocess.TimeoutExpired(
            ["tool"], 1, output="salida".encode("utf-8"), stderr=b"error"
        )
        result = run_command(["tool"], timeout=1)
        self.assertEqual(result.stdout, "salida")
        self.assertEqual(result.stderr, "error")

    @patch("core.system.command_runner.subprocess.run")
    def test_environment_and_url_credentials_are_redacted(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess(
            ["tool"], 0, "https://user:pass@example.com token-value", "Bearer abc.def"
        )
        result = run_command(
            ["tool"], env={"API_TOKEN": "token-value", "NORMAL": "visible"}
        )
        serialized = json.dumps(result.to_dict())
        self.assertNotIn("user:pass", serialized)
        self.assertNotIn("token-value", serialized)
        self.assertNotIn("abc.def", serialized)

    @patch("core.system.command_runner.time.sleep")
    @patch("core.system.command_runner.subprocess.Popen")
    def test_early_process_exit_is_reported(self, mocked_popen, _sleep):
        process = mocked_popen.return_value
        process.pid = 42
        process.poll.return_value = 7
        result = start_command(["tool"], startup_check_seconds=0.1)
        self.assertFalse(result.started)
        self.assertEqual(result.returncode, 7)
        self.assertIn("startup", result.error)


class DoctorTests(unittest.TestCase):
    @patch("core.system.doctor.run_command")
    @patch("core.system.doctor.importlib.util.find_spec", return_value=object())
    def test_deep_package_validation_is_isolated_and_structured(self, _find_spec, mocked_run):
        mocked_run.return_value = CommandResult(["python"], 1, stderr="broken import")
        packages = _detect_python_packages({"streamlit"})
        self.assertEqual(packages["streamlit"]["status"], "broken")
        self.assertFalse(packages["streamlit"]["importable"])
        self.assertIsNone(packages["torch"]["importable"])
        mocked_run.assert_called_once()

    def test_startup_profiles_have_independent_requirements(self):
        checks = [CheckResult("python_version", "ok", "critical", "Python")]
        packages = {
            name: {"available": name != "streamlit", "importable": None}
            for name in (
                "streamlit", "openai", "requests", "dotenv", "fastapi", "uvicorn", "PIL", "pyautogui"
            )
        }
        profiles = _startup_profiles(checks, packages)
        self.assertFalse(profiles["ui"]["ready"])
        self.assertTrue(profiles["cli"]["ready"])
        self.assertTrue(profiles["api"]["ready"])

    @patch("core.system.doctor.shutil.which", return_value=None)
    def test_gpu_absence_is_structured(self, _mocked_which):
        result = _detect_gpu()
        self.assertFalse(result["installed"])
        self.assertIsNone(result["vram_mb"])

    @patch("core.system.doctor.run_command")
    @patch("core.system.doctor.shutil.which", return_value="nvidia-smi")
    def test_failing_nvidia_smi_is_not_fatal(self, _mocked_which, mocked_run):
        mocked_run.return_value = type(
            "Result", (), {"success": False, "error": None, "stderr": "driver error"}
        )()
        result = _detect_gpu()
        self.assertTrue(result["installed"])
        self.assertFalse(result["functional"])

    @patch("core.system.doctor.urlopen")
    @patch("core.system.doctor.run_command")
    @patch("core.system.doctor.shutil.which", return_value=None)
    def test_ollama_not_installed_and_service_stopped(self, _which, _run, mocked_urlopen):
        mocked_urlopen.side_effect = OSError("offline")
        result = _detect_ollama()
        self.assertFalse(result["installed"])
        self.assertFalse(result["service_available"])
        self.assertFalse(result["functional"])

    def test_env_file_presence_never_exposes_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text(
                "NVIDIA_API_KEY=private-value\nGROQ_API_KEY=#ATLAS_GROQ_API_KEY\n",
                encoding="utf-8",
            )
            paths = get_paths(packaged=False, environment={})
            paths = type(paths)(**{**vars(paths), "project_root": root})
            result = _read_env_presence(paths, {})
            self.assertTrue(result["NVIDIA_API_KEY"])
            self.assertFalse(result["GROQ_API_KEY"])
            self.assertNotIn("private-value", json.dumps(result))

    def test_capabilities_require_complete_dependency_chains(self):
        packages = {
            name: {"available": False}
            for name in (
                "openai", "groq", "chromadb", "sentence_transformers", "torch",
                "pypdf", "pdf2image", "pytesseract", "PIL", "speech_recognition",
                "vosk", "edge_tts", "pyttsx3", "pyautogui", "duckduckgo_search",
            )
        }
        capabilities = _derive_capabilities(packages, {}, {}, {"functional": True})
        self.assertTrue(capabilities["local_llm"])
        self.assertFalse(capabilities["rag"])
        self.assertFalse(capabilities["ocr"])

    @patch("core.system.doctor._detect_ollama")
    @patch("core.system.doctor._detect_gpu")
    def test_public_diagnosis_is_json_serializable(self, mocked_gpu, mocked_ollama):
        mocked_gpu.return_value = {"installed": False, "functional": False, "vram_mb": None}
        mocked_ollama.return_value = {
            "installed": False,
            "functional": False,
            "service_available": False,
            "models": [],
        }
        report = diagnosticar_sistema(environment={})
        json.dumps(report)
        self.assertIn("ready_to_start", report)
        self.assertIn("capabilities", report)
        self.assertIsInstance(report["gpu"]["vram_mb"], type(None))
        self.assertIsInstance(report["python_packages"]["streamlit"], bool)
        self.assertIn("streamlit", report["python_package_details"])

    def test_legacy_healer_import_remains_available(self):
        from core.system.healer import Healer

        self.assertTrue(callable(Healer))


if __name__ == "__main__":
    unittest.main()
