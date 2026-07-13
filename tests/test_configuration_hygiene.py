import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET_KEYS = {
    "NVIDIA_API_KEY",
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
}


class ConfigurationHygieneTests(unittest.TestCase):
    def test_env_example_has_no_secret_values(self):
        values = {}
        for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key] = value
        self.assertTrue(SECRET_KEYS.issubset(values))
        for key in SECRET_KEYS:
            self.assertEqual(values[key], "", f"{key} must be empty in .env.example")

    def test_local_data_samples_are_ignored(self):
        samples = [
            ".env",
            "atlas_security.log",
            "cache/private.bin",
            "downloads/setup.exe",
            "logs/atlas.log",
            "models/model.gguf",
            "vector_db/chroma.sqlite3",
            "memory/Atlas_Memory/04_Universidad/private.md",
            "memory/Atlas_Memory/05_Proyectos/private.md",
        ]
        for sample in samples:
            process = subprocess.run(
                ["git", "check-ignore", sample],
                text=True,
                capture_output=True,
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(process.returncode, 0, f"Local path is not ignored: {sample}")

    def test_env_example_is_not_ignored(self):
        process = subprocess.run(
            ["git", "check-ignore", ".env.example"],
            text=True,
            capture_output=True,
            cwd=ROOT,
            check=False,
        )
        self.assertNotEqual(process.returncode, 0)


if __name__ == "__main__":
    unittest.main()
