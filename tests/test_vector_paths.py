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
RAW_CHROMA_ISSUE = (
    "raw_chroma_error_rejected: Chroma read access reported an unsafe "
    "external error. [Exception]"
)


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
import dataclasses
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
    "config_lock": config.INDEX_WRITER_LOCK_PATH,
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
        self.assertEqual(
            Path(result["config_lock"]),
            data_dir.resolve() / "index_writer.lock",
        )
        self.assertNotEqual(
            Path(result["config_lock"]).parent,
            Path(result["config_chroma"]),
        )
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
    "lock": config.INDEX_WRITER_LOCK_PATH,
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


class ChromaReadStatusAdapterTests(unittest.TestCase):
    """Adaptador de solo lectura de Chroma (IDX-C1, SDD §7.3 y §10)."""

    def _run_adapter(self, body: str, *, cwd: Path, data_dir: Path) -> dict:
        return _run_isolated(
            body,
            cwd=cwd,
            environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
        )

    def test_root_missing_reports_absent_without_client(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            chroma_root = root / "no-existe" / "vector_db"
            result = self._run_adapter(
                f"""
created = {{"persistent_client_calls": 0, "get_collection_calls": 0}}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    raise AssertionError("PersistentClient must not run")

class FakeClient:
    def get_collection(self, name):
        created["get_collection_calls"] += 1
        return object()

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
sys.modules["chromadb"] = chromadb

vector_store = importlib.import_module("core.vector_store")
acceso = vector_store._abrir_coleccion_existente(
    {str(chroma_root)!r}, "atlas_rag"
)
status = acceso.status
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "root_present": status.root_present,
    "collection_present": status.collection_present,
    "unavailable": status.unavailable,
    "error_code": status.error_code,
    "error_type": status.error_type,
    "error": status.error,
    "has_collection": acceso._collection is not None,
    "access_is_dataclass": dataclasses.is_dataclass(acceso),
    "status_fields": list(dataclasses.asdict(status)),
    "persistent_client_calls": created["persistent_client_calls"],
    "get_collection_calls": created["get_collection_calls"],
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertFalse(result["root_present"])
        self.assertFalse(result["collection_present"])
        self.assertFalse(result["unavailable"])
        self.assertIsNone(result["error"])
        self.assertFalse(result["has_collection"])
        self.assertFalse(result["access_is_dataclass"])
        self.assertEqual(
            result["status_fields"],
            [
                "root_present",
                "collection_present",
                "unavailable",
                "error_code",
                "error_type",
                "error",
            ],
        )
        self.assertEqual(result["persistent_client_calls"], 0)
        self.assertEqual(result["get_collection_calls"], 0)

    def test_root_without_sqlite_reports_collection_absent_without_client(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            chroma_root = root / "vector_db"
            chroma_root.mkdir()
            result = self._run_adapter(
                f"""
created = {{"persistent_client_calls": 0, "get_collection_calls": 0}}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    raise AssertionError("PersistentClient must not run")

class FakeClient:
    def get_collection(self, name):
        created["get_collection_calls"] += 1
        return object()

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
sys.modules["chromadb"] = chromadb

vector_store = importlib.import_module("core.vector_store")
acceso = vector_store._abrir_coleccion_existente(
    {str(chroma_root)!r}, "atlas_rag"
)
status = acceso.status
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "root_present": status.root_present,
    "collection_present": status.collection_present,
    "unavailable": status.unavailable,
    "has_collection": acceso._collection is not None,
    "persistent_client_calls": created["persistent_client_calls"],
    "get_collection_calls": created["get_collection_calls"],
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertTrue(result["root_present"])
        self.assertFalse(result["collection_present"])
        self.assertFalse(result["unavailable"])
        self.assertFalse(result["has_collection"])
        self.assertEqual(result["persistent_client_calls"], 0)
        self.assertEqual(result["get_collection_calls"], 0)

    def test_existing_root_opens_existing_collection_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            chroma_root = root / "vector_db"
            chroma_root.mkdir()
            (chroma_root / "chroma.sqlite3").write_text("synthetic", encoding="utf-8")
            result = self._run_adapter(
                f"""
created = {{"persistent_client_calls": 0, "get_collection_calls": 0,
           "get_or_create_calls": 0, "client_path": None}}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    created["client_path"] = path
    return FakeClient()

class FakeClient:
    def get_collection(self, name):
        created["get_collection_calls"] += 1
        created["collection_name"] = name
        return "coleccion-fake"

    def get_or_create_collection(self, **kwargs):
        created["get_or_create_calls"] += 1
        raise AssertionError("get_or_create_collection must not run")

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
sys.modules["chromadb"] = chromadb

vector_store = importlib.import_module("core.vector_store")
acceso = vector_store._abrir_coleccion_existente(
    {str(chroma_root)!r}, "atlas_rag"
)
status = acceso.status
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "root_present": status.root_present,
    "collection_present": status.collection_present,
    "unavailable": status.unavailable,
    "collection_is_fake": acceso._collection == "coleccion-fake",
    "status_has_collection": "collection" in dataclasses.asdict(status),
    "persistent_client_calls": created["persistent_client_calls"],
    "get_collection_calls": created["get_collection_calls"],
    "get_or_create_calls": created["get_or_create_calls"],
    "collection_name": created["collection_name"],
    "client_path": created["client_path"],
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertTrue(result["root_present"])
        self.assertTrue(result["collection_present"])
        self.assertFalse(result["unavailable"])
        self.assertTrue(result["collection_is_fake"])
        self.assertFalse(result["status_has_collection"])
        self.assertEqual(result["persistent_client_calls"], 1)
        self.assertEqual(result["get_collection_calls"], 1)
        self.assertEqual(result["get_or_create_calls"], 0)
        self.assertEqual(result["collection_name"], "atlas_rag")
        self.assertEqual(Path(result["client_path"]), chroma_root.resolve())

    def test_value_error_maps_to_collection_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            chroma_root = root / "vector_db"
            chroma_root.mkdir()
            (chroma_root / "chroma.sqlite3").write_text("synthetic", encoding="utf-8")
            result = self._run_adapter(
                f"""
created = {{"persistent_client_calls": 0, "get_collection_calls": 0}}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    return FakeClient()

class FakeClient:
    def get_collection(self, name):
        created["get_collection_calls"] += 1
        raise ValueError("Collection atlas_rag does not exist")

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
sys.modules["chromadb"] = chromadb

vector_store = importlib.import_module("core.vector_store")
acceso = vector_store._abrir_coleccion_existente(
    {str(chroma_root)!r}, "atlas_rag"
)
status = acceso.status
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "root_present": status.root_present,
    "collection_present": status.collection_present,
    "unavailable": status.unavailable,
    "error_code": status.error_code,
    "error_type": status.error_type,
    "error": status.error,
    "has_collection": acceso._collection is not None,
    "persistent_client_calls": created["persistent_client_calls"],
    "get_collection_calls": created["get_collection_calls"],
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertTrue(result["root_present"])
        self.assertFalse(result["collection_present"])
        self.assertFalse(result["unavailable"])
        self.assertIsNone(result["error"])
        self.assertFalse(result["has_collection"])
        self.assertEqual(result["persistent_client_calls"], 1)
        self.assertEqual(result["get_collection_calls"], 1)

    def test_other_error_maps_to_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            chroma_root = root / "vector_db"
            chroma_root.mkdir()
            (chroma_root / "chroma.sqlite3").write_text("synthetic", encoding="utf-8")
            result = self._run_adapter(
                f"""
created = {{"persistent_client_calls": 0, "get_collection_calls": 0}}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    return FakeClient()

class FakeClient:
    def get_collection(self, name):
        created["get_collection_calls"] += 1
        raise RuntimeError("backend caído")

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
sys.modules["chromadb"] = chromadb

vector_store = importlib.import_module("core.vector_store")
acceso = vector_store._abrir_coleccion_existente(
    {str(chroma_root)!r}, "atlas_rag"
)
status = acceso.status
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "root_present": status.root_present,
    "collection_present": status.collection_present,
    "unavailable": status.unavailable,
    "error_code": status.error_code,
    "error_type": status.error_type,
    "error": status.error,
    "has_collection": acceso._collection is not None,
    "persistent_client_calls": created["persistent_client_calls"],
    "get_collection_calls": created["get_collection_calls"],
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertTrue(result["root_present"])
        self.assertTrue(result["collection_present"])
        self.assertTrue(result["unavailable"])
        self.assertEqual(result["error_code"], "chroma_backend_unavailable")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertEqual(
            result["error"],
            "chroma_backend_unavailable: Chroma backend unavailable while "
            "opening existing collection. [RuntimeError]",
        )
        self.assertFalse(result["has_collection"])
        self.assertEqual(result["persistent_client_calls"], 1)
        self.assertEqual(result["get_collection_calls"], 1)

    def test_windows_path_in_error_is_sanitized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            chroma_root = root / "vector_db"
            chroma_root.mkdir()
            (chroma_root / "chroma.sqlite3").write_text("synthetic", encoding="utf-8")
            ruta_privada = r"C:\Users\delfa\AppData\Local\Temp\vector_db\chroma.sqlite3"
            result = self._run_adapter(
                f"""
created = {{"persistent_client_calls": 0, "get_collection_calls": 0}}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    return FakeClient()

class FakeClient:
    def get_collection(self, name):
        created["get_collection_calls"] += 1
        raise RuntimeError("no se pudo abrir {ruta_privada!r}")

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
sys.modules["chromadb"] = chromadb

vector_store = importlib.import_module("core.vector_store")
acceso = vector_store._abrir_coleccion_existente(
    {str(chroma_root)!r}, "atlas_rag"
)
status = acceso.status
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "unavailable": status.unavailable,
    "error_code": status.error_code,
    "error_type": status.error_type,
    "error": status.error,
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertTrue(result["unavailable"])
        self.assertEqual(result["error_code"], "chroma_backend_unavailable")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertNotIn("C:\\\\Users\\\\delfa", result["error"])
        self.assertNotIn("chroma.sqlite3", result["error"])
        self.assertEqual(
            result["error"],
            "chroma_backend_unavailable: Chroma backend unavailable while "
            "opening existing collection. [RuntimeError]",
        )

    def test_posix_path_in_error_is_sanitized(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            chroma_root = root / "vector_db"
            chroma_root.mkdir()
            (chroma_root / "chroma.sqlite3").write_text("synthetic", encoding="utf-8")
            ruta_privada = "/home/delfa/.atlas/vector_db/chroma.sqlite3"
            result = self._run_adapter(
                f"""
created = {{"persistent_client_calls": 0, "get_collection_calls": 0}}

def persistent_client(path):
    created["persistent_client_calls"] += 1
    return FakeClient()

class FakeClient:
    def get_collection(self, name):
        created["get_collection_calls"] += 1
        raise RuntimeError("no se pudo abrir {ruta_privada!r}")

chromadb = types.ModuleType("chromadb")
chromadb.PersistentClient = persistent_client
sys.modules["chromadb"] = chromadb

vector_store = importlib.import_module("core.vector_store")
acceso = vector_store._abrir_coleccion_existente(
    {str(chroma_root)!r}, "atlas_rag"
)
status = acceso.status
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "unavailable": status.unavailable,
    "error_code": status.error_code,
    "error_type": status.error_type,
    "error": status.error,
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertTrue(result["unavailable"])
        self.assertEqual(result["error_code"], "chroma_backend_unavailable")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertNotIn("/home/delfa", result["error"])
        self.assertEqual(
            result["error"],
            "chroma_backend_unavailable: Chroma backend unavailable while "
            "opening existing collection. [RuntimeError]",
        )

    def test_chroma_read_access_rejects_raw_error_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            raw_error = (
                r"C:\Users\delfa\private.txt SYNTHETIC_SECRET_TOKEN "
                r"\\server\share\private.txt //server/share/private.txt "
                "https://example.org/private/path http://localhost:8000/api "
                "docs/file.md core/module.py"
            )
            result = self._run_adapter(
                f"""
vector_store = importlib.import_module("core.vector_store")
status = vector_store.ChromaReadStatus(
    root_present=True,
    collection_present=True,
    unavailable=True,
    error={raw_error!r},
)
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "fields": list(dataclasses.asdict(status)),
    "error_code": status.error_code,
    "error_type": status.error_type,
    "error": status.error,
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertEqual(result["error_code"], "raw_chroma_error_rejected")
        self.assertEqual(result["error_type"], "Exception")
        self.assertNotIn("collection", result["fields"])
        self.assertEqual(
            result["error"],
            "raw_chroma_error_rejected: Chroma read access reported an unsafe "
            "external error. [Exception]",
        )
        self.assertNotIn("C:\\Users\\delfa", result["error"])
        self.assertNotIn("\\\\server\\share", result["error"])
        self.assertNotIn("//server/share", result["error"])
        self.assertNotIn("SYNTHETIC_SECRET_TOKEN", result["error"])
        self.assertNotIn("https://example.org/private/path", result["error"])
        self.assertNotIn("http://localhost:8000/api", result["error"])
        self.assertNotIn("docs/file.md", result["error"])
        self.assertNotIn("core/module.py", result["error"])

    def test_chroma_read_access_error_render_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            result = self._run_adapter(
                f"""
vector_store = importlib.import_module("core.vector_store")
primero = vector_store.ChromaReadStatus(
    root_present=True,
    collection_present=True,
    unavailable=True,
    error="mensaje normal sin rutas",
)
segundo = vector_store.ChromaReadStatus(
    root_present=True,
    collection_present=True,
    unavailable=True,
    error=primero.error,
)
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "primero": primero.error,
    "segundo": segundo.error,
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertEqual(result["primero"], RAW_CHROMA_ISSUE)
        self.assertEqual(result["segundo"], RAW_CHROMA_ISSUE)

    def test_chroma_read_access_handle_is_not_serializable_public_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            secret_handle = (
                r"C:\Users\delfa\private.txt SYNTHETIC_SECRET_TOKEN "
                "RAW_BACKEND_MESSAGE"
            )
            result = self._run_adapter(
                f"""
vector_store = importlib.import_module("core.vector_store")
status = vector_store.ChromaReadStatus(root_present=True, collection_present=True)
access = vector_store._ChromaReadAccess(status, collection={secret_handle!r})
try:
    dataclasses.asdict(access)
except TypeError as exc:
    asdict_error = type(exc).__name__
else:
    asdict_error = None
public = dataclasses.asdict(access.status)
print("ATLAS_TEST_RESULT=" + json.dumps({{
    "access_is_dataclass": dataclasses.is_dataclass(access),
    "asdict_error": asdict_error,
    "public": public,
    "access_dict": getattr(access, "__dict__", None),
    "handle_roundtrip": access._collection == {secret_handle!r},
}}))
""",
                cwd=root,
                data_dir=data_dir,
            )

        self.assertFalse(result["access_is_dataclass"])
        self.assertEqual(result["asdict_error"], "TypeError")
        self.assertNotIn("collection", result["public"])
        self.assertIsNone(result["access_dict"])
        self.assertTrue(result["handle_roundtrip"])
        public_text = json.dumps(result["public"])
        self.assertNotIn("SYNTHETIC_SECRET_TOKEN", public_text)
        self.assertNotIn("C:\\Users\\delfa", public_text)
        self.assertNotIn("RAW_BACKEND_MESSAGE", public_text)


if __name__ == "__main__":
    unittest.main()
