import importlib
import os
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path

from core.system.paths import get_paths


_MISSING = object()


@contextmanager
def isolated_config_import(environment: dict[str, str], cwd: Path):
    """Import core.config without reading the repository's real .env file."""
    original_cwd = Path.cwd()
    original_environment = os.environ.copy()
    original_config_module = sys.modules.get("core.config", _MISSING)
    original_dotenv_module = sys.modules.get("dotenv", _MISSING)
    core_package = importlib.import_module("core")
    original_config_attribute = getattr(core_package, "config", _MISSING)

    fake_dotenv = types.ModuleType("dotenv")
    fake_dotenv.load_dotenv = lambda *args, **kwargs: False

    try:
        os.environ.clear()
        os.environ.update(environment)
        os.chdir(cwd)
        sys.modules.pop("core.config", None)
        sys.modules["dotenv"] = fake_dotenv
        config = importlib.import_module("core.config")
        yield config
    finally:
        sys.modules.pop("core.config", None)
        if original_config_module is not _MISSING:
            sys.modules["core.config"] = original_config_module

        sys.modules.pop("dotenv", None)
        if original_dotenv_module is not _MISSING:
            sys.modules["dotenv"] = original_dotenv_module

        if original_config_attribute is _MISSING:
            try:
                delattr(core_package, "config")
            except AttributeError:
                pass
        else:
            core_package.config = original_config_attribute

        os.chdir(original_cwd)
        os.environ.clear()
        os.environ.update(original_environment)


class PathIntegrationTests(unittest.TestCase):
    def test_environment_mapping_respects_temporary_data_override(self):
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp) / "atlas-data"
            paths = get_paths(
                packaged=False,
                environment={"ATLAS_DATA_DIR": str(data_dir)},
            )

            self.assertEqual(paths.data_dir, data_dir.resolve())
            self.assertEqual(
                paths.private_memory_dir,
                data_dir.resolve() / "memory" / "Atlas_Memory",
            )
            self.assertEqual(paths.chroma_dir, data_dir.resolve() / "vector_db")
            self.assertEqual(
                paths.index_writer_lock_path,
                data_dir.resolve() / "index_writer.lock",
            )
            self.assertNotEqual(paths.index_writer_lock_path.parent, paths.chroma_dir)
            self.assertFalse(data_dir.exists())

    def test_successive_calls_reflect_environment_changes_without_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            first_data_dir = Path(temp) / "first"
            second_data_dir = Path(temp) / "second"
            original = os.environ.get("ATLAS_DATA_DIR", _MISSING)
            try:
                os.environ["ATLAS_DATA_DIR"] = str(first_data_dir)
                first = get_paths(packaged=False)
                os.environ["ATLAS_DATA_DIR"] = str(second_data_dir)
                second = get_paths(packaged=False)
            finally:
                if original is _MISSING:
                    os.environ.pop("ATLAS_DATA_DIR", None)
                else:
                    os.environ["ATLAS_DATA_DIR"] = original

            self.assertEqual(first.data_dir, first_data_dir.resolve())
            self.assertEqual(second.data_dir, second_data_dir.resolve())
            self.assertNotEqual(first.data_dir, second.data_dir)

    def test_development_layout_is_preserved_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            original_cwd = Path.cwd()
            try:
                os.chdir(temp)
                paths = get_paths(packaged=False, environment={})
            finally:
                os.chdir(original_cwd)

            self.assertEqual(
                paths.private_memory_dir,
                paths.project_root / "memory" / "Atlas_Memory",
            )
            self.assertEqual(
                paths.private_memory_dir / "03_Conocimiento",
                paths.project_root / "memory" / "Atlas_Memory" / "03_Conocimiento",
            )
            self.assertEqual(
                paths.private_memory_dir / "00_Sistema" / "Prompts",
                paths.project_root / "memory" / "Atlas_Memory" / "00_Sistema" / "Prompts",
            )
            self.assertEqual(
                paths.index_writer_lock_path,
                paths.project_root / "index_writer.lock",
            )

    def test_config_constants_are_captured_at_import_time(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            initial_data_dir = root / "initial"
            later_data_dir = root / "later"
            environment = {"ATLAS_DATA_DIR": str(initial_data_dir)}

            with isolated_config_import(environment, root) as config:
                captured = (
                    config.BASE_MEMORIA,
                    config.BASE_ESTUDIO,
                    config.BASE_PROMPTS,
                )
                os.environ["ATLAS_DATA_DIR"] = str(later_data_dir)
                live_paths = get_paths(packaged=False)

                self.assertEqual(
                    captured,
                    (
                        config.BASE_MEMORIA,
                        config.BASE_ESTUDIO,
                        config.BASE_PROMPTS,
                    ),
                )
                self.assertEqual(live_paths.data_dir, later_data_dir.resolve())
                self.assertTrue(all(isinstance(value, str) for value in captured))

    def test_isolated_config_import_uses_central_path_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            environment = {"ATLAS_DATA_DIR": str(data_dir)}
            expected = get_paths(packaged=False, environment=environment)
            expected_chroma = data_dir.resolve() / "vector_db"
            expected_manifest = expected_chroma / "index_manifest.json"
            expected_lock = data_dir.resolve() / "index_writer.lock"

            with isolated_config_import(environment, root) as config:
                self.assertEqual(config.BASE_MEMORIA, str(expected.private_memory_dir))
                self.assertEqual(
                    config.BASE_ESTUDIO,
                    str(expected.private_memory_dir / "03_Conocimiento"),
                )
                self.assertEqual(
                    config.BASE_PROMPTS,
                    str(expected.private_memory_dir / "00_Sistema" / "Prompts"),
                )
                self.assertEqual(config.CHROMA_PATH, str(expected_chroma))
                self.assertEqual(config.INDEX_MANIFEST_PATH, str(expected_manifest))
                self.assertEqual(config.INDEX_WRITER_LOCK_PATH, str(expected_lock))
                self.assertIsInstance(config.CHROMA_PATH, str)
                self.assertTrue(Path(config.CHROMA_PATH).is_absolute())
                self.assertTrue(Path(config.INDEX_MANIFEST_PATH).is_absolute())
                self.assertTrue(Path(config.INDEX_WRITER_LOCK_PATH).is_absolute())
                self.assertEqual(
                    Path(config.INDEX_MANIFEST_PATH).parent,
                    Path(config.CHROMA_PATH),
                )
                self.assertNotEqual(
                    Path(config.INDEX_WRITER_LOCK_PATH).parent,
                    Path(config.CHROMA_PATH),
                )


if __name__ == "__main__":
    unittest.main()
