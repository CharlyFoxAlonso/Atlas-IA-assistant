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
    """Import core.brain with inert dependencies and a non-reading dotenv."""
    bootstrap = """
import importlib
import json
import sys
import types
from pathlib import Path

def install_module(name, **attributes):
    module = types.ModuleType(name)
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    sys.modules[name] = module

install_module("dotenv", load_dotenv=lambda *args, **kwargs: False)
install_module("requests")
install_module("openai", OpenAI=object)
install_module("core.file_loader", leer_archivo_estudio=lambda path: "")
install_module(
    "core.memory_manager",
    analizar_conversacion=lambda pregunta, respuesta: [],
)
install_module(
    "core.router",
    detectar_agente_con_modelo=lambda pregunta: "general",
    cargar_prompt_agente=lambda agente: "",
)
install_module(
    "core.web_search",
    buscar_web=lambda pregunta, max_resultados=5: [],
    formatear_resultados_web=lambda resultados: "",
)
install_module("core.security", log_seguridad=lambda evento, detalle: None)
install_module(
    "core.vector_store",
    buscar_relevante=lambda *args, **kwargs: [],
    busqueda_hibrida=lambda *args, **kwargs: [],
)
install_module(
    "core.temp_rules",
    obtener_contexto_reglas=lambda: "",
    verificar_reglas_y_forzar_respuesta=lambda pregunta: (False, ""),
    obtener_reglas_de_formato=lambda: "",
)
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


class BrainPathTests(unittest.TestCase):
    def test_symbols_match_config_with_preserved_types_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            result = _run_isolated(
                """
brain = importlib.import_module("core.brain")
config = importlib.import_module("core.config")
names = ("BASE_ESTUDIO", "BASE_PROMPTS", "MAX_HISTORIAL")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "brain": [getattr(brain, name) for name in names],
    "config": [getattr(config, name) for name in names],
    "brain_types": [type(getattr(brain, name)).__name__ for name in names],
    "config_types": [type(getattr(config, name)).__name__ for name in names],
    "paths_absolute": [
        Path(brain.BASE_ESTUDIO).is_absolute(),
        Path(brain.BASE_PROMPTS).is_absolute(),
    ],
}))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertEqual(result["brain"], result["config"])
        self.assertEqual(result["brain_types"], result["config_types"])
        self.assertEqual(result["brain_types"], ["str", "str", "int"])
        self.assertEqual(result["paths_absolute"], [True, True])

    def test_data_override_applies_when_set_before_import(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            memory_dir = data_dir.resolve() / "memory" / "Atlas_Memory"
            result = _run_isolated(
                """
brain = importlib.import_module("core.brain")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "study": brain.BASE_ESTUDIO,
    "prompts": brain.BASE_PROMPTS,
}))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertEqual(
            Path(result["study"]),
            memory_dir / "03_Conocimiento",
        )
        self.assertEqual(
            Path(result["prompts"]),
            memory_dir / "00_Sistema" / "Prompts",
        )

    def test_paths_do_not_change_with_cwd(self):
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
brain = importlib.import_module("core.brain")
print("ATLAS_TEST_RESULT=" + json.dumps({
    "study": brain.BASE_ESTUDIO,
    "prompts": brain.BASE_PROMPTS,
}))
""",
                        cwd=cwd,
                        environment=_isolated_environment(
                            ATLAS_DATA_DIR=str(data_dir),
                        ),
                    )
                )

        self.assertEqual(results[0], results[1])

    def test_config_import_failure_is_not_masked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "controlled-data"
            result = _run_isolated(
                """
from importlib.abc import MetaPathFinder

class BlockConfigImport(MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "core.config":
            raise ModuleNotFoundError("blocked core.config for regression test")
        return None

sys.meta_path.insert(0, BlockConfigImport())
try:
    importlib.import_module("core.brain")
except ModuleNotFoundError as error:
    outcome = {
        "failed": True,
        "message": str(error),
    }
else:
    outcome = {
        "failed": False,
        "message": "",
    }
print("ATLAS_TEST_RESULT=" + json.dumps(outcome))
""",
                cwd=root,
                environment=_isolated_environment(ATLAS_DATA_DIR=str(data_dir)),
            )

        self.assertTrue(result["failed"])
        self.assertIn("blocked core.config", result["message"])


if __name__ == "__main__":
    unittest.main()
