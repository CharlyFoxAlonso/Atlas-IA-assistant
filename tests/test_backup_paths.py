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
    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if key in os.environ
    }
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
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
    completed = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(bootstrap + body)],
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
            f"isolated backup check failed ({completed.returncode}): "
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
        raise AssertionError(f"isolated backup returned no result: {completed.stdout!r}")
    return json.loads(result_line)


class BackupPathTests(unittest.TestCase):
    def test_import_has_no_backup_or_traversal_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = _run_isolated(
                """
from unittest.mock import patch

before = sorted(path.name for path in Path.cwd().iterdir())
with patch("os.walk") as walk, patch("zipfile.ZipFile") as zip_file:
    importlib.import_module("scripts.backup_atlas")
after = sorted(path.name for path in Path.cwd().iterdir())
print("ATLAS_TEST_RESULT=" + json.dumps({
    "before": before,
    "after": after,
    "walk_calls": walk.call_count,
    "zip_calls": zip_file.call_count,
    "config_imported": "core.config" in sys.modules,
}))
""",
                cwd=root,
                environment=_isolated_environment(),
            )

        self.assertEqual(result["before"], result["after"])
        self.assertEqual(result["walk_calls"], 0)
        self.assertEqual(result["zip_calls"], 0)
        self.assertFalse(result["config_imported"])

    def test_backup_uses_configured_source_and_stable_vector_zip_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            data_dir = root / "external-data"
            vector_dir = data_dir / "vector_db"
            (vector_dir / "nested").mkdir(parents=True)
            (vector_dir / "chroma.sqlite3").write_text("synthetic", encoding="utf-8")
            (vector_dir / "nested" / "index.bin").write_text(
                "synthetic",
                encoding="utf-8",
            )
            result = _run_isolated(
                """
import zipfile

backup = importlib.import_module("scripts.backup_atlas")
archive = Path(backup.crear_backup_atlas())
with zipfile.ZipFile(archive) as zip_file:
    names = sorted(zip_file.namelist())
print("ATLAS_TEST_RESULT=" + json.dumps({
    "names": names,
    "stdout_encoding": sys.stdout.encoding,
    "absolute_member": any(
        name.startswith(("/", "\\\\")) or ":" in name
        for name in names
    ),
    "source_name_exposed": any("external-data" in name for name in names),
}))
""",
                cwd=project,
                environment=_isolated_environment(
                    ATLAS_DATA_DIR=str(data_dir),
                    PYTHONIOENCODING="cp1252",
                ),
            )

        self.assertIn("vector_db/chroma.sqlite3", result["names"])
        self.assertIn("vector_db/nested/index.bin", result["names"])
        self.assertEqual(result["stdout_encoding"].lower(), "cp1252")
        self.assertFalse(result["absolute_member"])
        self.assertFalse(result["source_name_exposed"])

    def test_configured_source_wins_when_legacy_also_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            legacy = project / "vector_db"
            configured = root / "external-data" / "vector_db"
            legacy.mkdir(parents=True)
            configured.mkdir(parents=True)
            (legacy / "legacy-only.bin").write_text("synthetic", encoding="utf-8")
            (configured / "configured-only.bin").write_text(
                "synthetic",
                encoding="utf-8",
            )
            result = _run_isolated(
                """
import zipfile

backup = importlib.import_module("scripts.backup_atlas")
archive = Path(backup.crear_backup_atlas())
with zipfile.ZipFile(archive) as zip_file:
    names = sorted(zip_file.namelist())
print("ATLAS_TEST_RESULT=" + json.dumps({"names": names}))
""",
                cwd=project,
                environment=_isolated_environment(
                    ATLAS_DATA_DIR=str(root / "external-data"),
                ),
            )

        self.assertIn("vector_db/configured-only.bin", result["names"])
        self.assertNotIn("vector_db/legacy-only.bin", result["names"])

    def test_legacy_only_backup_stops_without_archive_or_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            legacy = project / "vector_db"
            marker = legacy / "legacy.marker"
            legacy.mkdir(parents=True)
            marker.write_text("synthetic", encoding="utf-8")
            data_dir = root / "external-data"
            result = _run_isolated(
                """
backup = importlib.import_module("scripts.backup_atlas")
try:
    backup.crear_backup_atlas()
except RuntimeError as error:
    message = str(error)
else:
    message = ""
print("ATLAS_TEST_RESULT=" + json.dumps({
    "message": message,
    "archives": sorted(path.name for path in Path.cwd().glob("Atlas_Backup_*.zip")),
    "legacy_exists": (Path.cwd() / "vector_db").is_dir(),
    "marker_exists": (Path.cwd() / "vector_db" / "legacy.marker").is_file(),
    "configured_exists": (
        Path(__import__("os").environ["ATLAS_DATA_DIR"]) / "vector_db"
    ).exists(),
}))
""",
                cwd=project,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertIn("Possible legacy vector store detected", result["message"])
        self.assertIn(
            "Automatic migration was intentionally not performed",
            result["message"],
        )
        self.assertEqual(result["archives"], [])
        self.assertTrue(result["legacy_exists"])
        self.assertTrue(result["marker_exists"])
        self.assertFalse(result["configured_exists"])


if __name__ == "__main__":
    unittest.main()
