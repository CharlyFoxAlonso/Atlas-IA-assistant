import importlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from core.system.paths import (
    LegacyVectorStoreError,
    validate_vector_store_path,
)


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


class VectorPathPolicyTests(unittest.TestCase):
    def test_same_path_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            vector_path = Path(temp) / "vector_db"
            vector_path.mkdir()

            result = validate_vector_store_path(
                vector_path,
                legacy_path=vector_path,
            )

        self.assertEqual(result, vector_path.resolve())

    def test_configured_path_wins_when_it_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            configured = root / "configured" / "vector_db"
            legacy = root / "legacy" / "vector_db"
            configured.mkdir(parents=True)

            configured_only = validate_vector_store_path(
                configured,
                legacy_path=legacy,
            )
            legacy.mkdir(parents=True)
            both_existing = validate_vector_store_path(
                configured,
                legacy_path=legacy,
            )

        self.assertEqual(configured_only, configured.resolve())
        self.assertEqual(both_existing, configured.resolve())

    def test_neither_path_existing_allows_configured_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            configured = root / "configured" / "vector_db"
            legacy = root / "legacy" / "vector_db"

            result = validate_vector_store_path(
                configured,
                legacy_path=legacy,
            )

            self.assertEqual(result, configured.resolve())
            self.assertFalse(configured.exists())
            self.assertFalse(legacy.exists())

    def test_legacy_only_path_stops_without_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            configured = root / "configured" / "vector_db"
            legacy = root / "legacy" / "vector_db"
            marker = legacy / "legacy.marker"
            legacy.mkdir(parents=True)
            marker.write_text("synthetic", encoding="utf-8")

            with self.assertRaises(LegacyVectorStoreError) as raised:
                validate_vector_store_path(
                    configured,
                    legacy_path=legacy,
                )

            self.assertFalse(configured.exists())
            self.assertTrue(legacy.is_dir())
            self.assertTrue(marker.is_file())

        message = str(raised.exception)
        self.assertIn("Possible legacy vector store detected", message)
        self.assertIn("Automatic migration was intentionally not performed", message)


class VectorConfigurationTests(unittest.TestCase):
    def test_config_and_vector_store_share_absolute_authoritative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            expected_chroma = data_dir.resolve() / "vector_db"
            expected_manifest = expected_chroma / "index_manifest.json"
            result = _run_isolated(
                """
config = importlib.import_module("core.config")
vector_store = importlib.import_module("core.vector_store")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "config_chroma": config.CHROMA_PATH,
    "config_manifest": config.INDEX_MANIFEST_PATH,
    "vector_chroma": vector_store.CHROMA_PATH,
    "vector_collection": vector_store.COLLECTION_NAME,
    "config_collection": config.COLLECTION_NAME,
    "chroma_type": type(config.CHROMA_PATH).__name__,
    "chroma_imported": "chromadb" in sys.modules,
    "chroma_exists": Path(config.CHROMA_PATH).exists(),
    "complete": all(
        hasattr(vector_store, name)
        for name in ("CHROMA_PATH", "COLLECTION_NAME", "_get_collection")
    ),
}))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertEqual(Path(result["config_chroma"]), expected_chroma)
        self.assertEqual(Path(result["config_manifest"]), expected_manifest)
        self.assertEqual(result["vector_chroma"], result["config_chroma"])
        self.assertEqual(result["vector_collection"], result["config_collection"])
        self.assertEqual(result["chroma_type"], "str")
        self.assertFalse(result["chroma_imported"])
        self.assertFalse(result["chroma_exists"])
        self.assertTrue(result["complete"])

    def test_configured_vector_paths_are_independent_of_cwd(self):
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
config = importlib.import_module("core.config")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "chroma": config.CHROMA_PATH,
    "manifest": config.INDEX_MANIFEST_PATH,
}))
""",
                        cwd=cwd,
                        environment=_isolated_environment(
                            ATLAS_DATA_DIR=str(data_dir),
                        ),
                    )
                )

        self.assertEqual(results[0], results[1])

    def test_chroma_construction_receives_authoritative_absolute_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            expected_chroma = data_dir.resolve() / "vector_db"
            result = _run_isolated(
                """
created = {}

class FakeEmbedding:
    def __init__(self, model_name):
        created["embedding_model"] = model_name

class FakeClient:
    def __init__(self, path):
        created["client_path"] = path

    def get_or_create_collection(self, **kwargs):
        created["collection"] = kwargs["name"]
        created["metadata"] = kwargs["metadata"]
        return object()

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = FakeClient
utils = types.ModuleType("chromadb.utils")
utils.embedding_functions = types.SimpleNamespace(
    SentenceTransformerEmbeddingFunction=FakeEmbedding,
)
sys.modules["chromadb"] = chromadb
sys.modules["chromadb.utils"] = utils

vector_store = importlib.import_module("core.vector_store")
vector_store._get_collection()
created["directory_exists"] = Path(created["client_path"]).exists()
print("ATLAS_TEST_RESULT=" + json.dumps(created))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertEqual(Path(result["client_path"]), expected_chroma)
        self.assertTrue(Path(result["client_path"]).is_absolute())
        self.assertEqual(result["collection"], "atlas_rag")
        self.assertEqual(
            result["embedding_model"],
            "paraphrase-multilingual-MiniLM-L12-v2",
        )
        self.assertEqual(result["metadata"], {"hnsw:space": "cosine"})
        self.assertFalse(result["directory_exists"])

    def test_legacy_only_detection_precedes_chroma_construction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / "vector_db"
            marker = legacy / "legacy.marker"
            legacy.mkdir()
            marker.write_text("synthetic", encoding="utf-8")
            data_dir = root / "controlled-data"
            result = _run_isolated(
                """
created = {"persistent_client_calls": 0}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    raise AssertionError("PersistentClient must not run")

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
utils = types.ModuleType("chromadb.utils")
utils.embedding_functions = types.SimpleNamespace(
    SentenceTransformerEmbeddingFunction=lambda **kwargs: object(),
)
sys.modules["chromadb"] = chromadb
sys.modules["chromadb.utils"] = utils

vector_store = importlib.import_module("core.vector_store")
try:
    vector_store._get_collection()
except RuntimeError as error:
    created["error"] = str(error)
else:
    created["error"] = ""
created["configured_exists"] = Path(vector_store.CHROMA_PATH).exists()
created["legacy_exists"] = (Path.cwd() / "vector_db").exists()
created["marker_exists"] = (Path.cwd() / "vector_db" / "legacy.marker").exists()
print("ATLAS_TEST_RESULT=" + json.dumps(created))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertEqual(result["persistent_client_calls"], 0)
        self.assertIn("Possible legacy vector store detected", result["error"])
        self.assertFalse(result["configured_exists"])
        self.assertTrue(result["legacy_exists"])
        self.assertTrue(result["marker_exists"])


if __name__ == "__main__":
    unittest.main()
