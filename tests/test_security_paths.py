import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_PREFIX = "ATLAS_TEST_RESULT="


def _isolated_environment(**overrides: str) -> dict[str, str]:
    """Build a minimal child environment without leaking Atlas configuration."""
    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if key in os.environ
    }
    environment.update(
        {
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(REPO_ROOT),
        }
    )
    environment.update(overrides)
    return environment


def _run_isolated(
    body: str,
    *,
    cwd: Path,
    environment: dict[str, str],
) -> dict:
    """Run imports in a fresh interpreter with a fake dotenv module."""
    bootstrap = """
import importlib
import json
import sys
import types
from pathlib import Path

fake_dotenv = types.ModuleType("dotenv")
fake_dotenv.load_dotenv = lambda *args, **kwargs: False
sys.modules["dotenv"] = fake_dotenv
"""
    script = textwrap.dedent(bootstrap) + "\n" + textwrap.dedent(body)
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"isolated import failed ({completed.returncode}): "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    result_line = next(
        (
            line[len(RESULT_PREFIX):]
            for line in reversed(completed.stdout.splitlines())
            if line.startswith(RESULT_PREFIX)
        ),
        None,
    )
    if result_line is None:
        raise AssertionError(f"isolated import returned no result: {completed.stdout!r}")
    return json.loads(result_line)


def _git_status() -> str:
    completed = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
        check=True,
    )
    return completed.stdout


class SecurityPathTests(unittest.TestCase):
    def test_security_base_memoria_remains_str(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = _run_isolated(
                """
security = importlib.import_module("core.security")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "is_str": isinstance(security.BASE_MEMORIA, str),
}))
""",
                cwd=root,
                environment=_isolated_environment(),
            )

        self.assertTrue(result["is_str"])

    def test_security_and_config_share_base_memoria(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = _run_isolated(
                """
security = importlib.import_module("core.security")
config = importlib.import_module("core.config")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "security": security.BASE_MEMORIA,
    "config": config.BASE_MEMORIA,
}))
""",
                cwd=root,
                environment=_isolated_environment(),
            )

        self.assertEqual(result["security"], result["config"])

    def test_data_override_applies_to_security_alias_before_import(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            expected = str((data_dir / "memory" / "Atlas_Memory").resolve())
            result = _run_isolated(
                """
security = importlib.import_module("core.security")
config = importlib.import_module("core.config")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "security": security.BASE_MEMORIA,
    "config": config.BASE_MEMORIA,
}))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertEqual(result["config"], expected)
        self.assertEqual(result["security"], expected)

    def test_security_alias_is_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            results = []
            for name in ("first-cwd", "second-cwd"):
                cwd = root / name
                cwd.mkdir()
                results.append(
                    _run_isolated(
                        """
security = importlib.import_module("core.security")
config = importlib.import_module("core.config")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "security": security.BASE_MEMORIA,
    "security_resolved": str(Path(security.BASE_MEMORIA).resolve()),
    "config": config.BASE_MEMORIA,
}))
""",
                        cwd=cwd,
                        environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
                    )
                )

        self.assertEqual(results[0]["config"], results[1]["config"])
        self.assertEqual(results[0]["security"], results[0]["config"])
        self.assertEqual(results[1]["security"], results[1]["config"])
        self.assertEqual(
            results[0]["security_resolved"],
            results[1]["security_resolved"],
        )

    def test_imports_do_not_create_memory_or_git_visible_files(self):
        before_status = _git_status()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            result = _run_isolated(
                """
importlib.import_module("core.config")
importlib.import_module("core.security")
importlib.import_module("core.web_crawler")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "configured_memory_exists": (
        Path(__import__("os").environ["ATLAS_DATA_DIR"])
        / "memory"
        / "Atlas_Memory"
    ).exists(),
    "cwd_memory_exists": (Path.cwd() / "memory" / "Atlas_Memory").exists(),
}))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )
        after_status = _git_status()

        self.assertFalse(result["configured_memory_exists"])
        self.assertFalse(result["cwd_memory_exists"])
        self.assertEqual(after_status, before_status)

    def test_supported_import_orders_are_complete(self):
        orders = (
            ("core.security", "core.config", "core.web_crawler"),
            ("core.config", "core.security", "core.web_crawler"),
            ("core.web_crawler", "core.security", "core.config"),
        )
        for order in orders:
            with self.subTest(order=order), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                result = _run_isolated(
                    f"""
order = {order!r}
for module_name in order:
    importlib.import_module(module_name)
security = importlib.import_module("core.security")
config = importlib.import_module("core.config")
crawler = importlib.import_module("core.web_crawler")
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "security_symbol": hasattr(security, "BASE_MEMORIA"),
    "config_symbol": hasattr(config, "BASE_MEMORIA"),
    "crawler_symbol": hasattr(crawler, "WebCrawler"),
}}))
""",
                    cwd=root,
                    environment=_isolated_environment(),
                )

                self.assertTrue(result["security_symbol"])
                self.assertTrue(result["config_symbol"])
                self.assertTrue(result["crawler_symbol"])

    def test_web_crawler_accepts_explicit_temporary_memory_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            memory_root = root / "memory-root"
            destination = memory_root / "crawler-output"
            result = _run_isolated(
                """
from core.web_crawler import WebCrawler

memory_root = Path(__import__("os").environ["TEST_MEMORY_ROOT"])
destination = Path(__import__("os").environ["TEST_DESTINATION"])
crawler = WebCrawler(
    root_folder=str(destination),
    theme="contract-test",
    memory_root=str(memory_root),
    session=object(),
)
print("ATLAS_TEST_RESULT=" + json.dumps({
    "memory_root": str(crawler.memory_root),
    "destination": str(crawler.root_folder),
    "memory_root_exists": memory_root.exists(),
    "destination_exists": destination.exists(),
}))
""",
                cwd=root,
                environment=_isolated_environment(
                    TEST_MEMORY_ROOT=str(memory_root),
                    TEST_DESTINATION=str(destination),
                ),
            )

        self.assertEqual(result["memory_root"], str(memory_root.resolve()))
        self.assertEqual(result["destination"], str(destination.resolve()))
        self.assertFalse(result["memory_root_exists"])
        self.assertFalse(result["destination_exists"])


if __name__ == "__main__":
    unittest.main()
