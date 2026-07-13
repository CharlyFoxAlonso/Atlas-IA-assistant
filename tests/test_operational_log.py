import json
import tempfile
import unittest
from pathlib import Path

from core.system.operational_log import write_operational_event
from core.system.paths import AtlasPaths


def make_paths(root: Path) -> AtlasPaths:
    return AtlasPaths(
        mode="development",
        program_dir=root,
        project_root=root,
        data_dir=root,
        private_memory_dir=root / "memory",
        chroma_dir=root / "vector_db",
        config_dir=root,
        cache_dir=root / "cache",
        logs_dir=root / "logs",
        downloads_dir=root / "downloads",
        temp_dir=root / "temp",
        managed_bin_dir=root / "bin",
        models_dir=root / "models",
    )


class OperationalLogTests(unittest.TestCase):
    def test_event_is_json_and_secrets_are_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            write_operational_event(
                paths,
                component="test",
                event="example",
                payload={"API_KEY": "private-value", "safe": "visible"},
            )
            line = (paths.logs_dir / "atlas-system.log").read_text(encoding="utf-8").strip()
            payload = json.loads(line)
            self.assertEqual(payload["API_KEY"], "***")
            self.assertEqual(payload["safe"], "visible")
            self.assertNotIn("private-value", line)


if __name__ == "__main__":
    unittest.main()
