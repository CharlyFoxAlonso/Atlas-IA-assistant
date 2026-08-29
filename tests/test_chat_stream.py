import json
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from unittest import mock

from core.chat_stream import (
    CHAT_STREAM_ERROR_MESSAGE,
    ChatStreamCancelled,
    ChatStreamError,
    ChatStreamEvent,
    stream_chat_turn,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_PREFIX = "ATLAS_TEST_RESULT="


class _FakeBrain:
    def __init__(self, stream_factory):
        self.stream_factory = stream_factory
        self.calls = []
        self.context_histories = []
        self._active_history = ContextVar(
            "fake_chat_stream_history",
            default=None,
        )

    @property
    def active_history(self):
        return self._active_history.get()

    @contextmanager
    def _usar_contexto_streaming(self, history):
        self.context_histories.append(history)
        token = self._active_history.set(history)
        try:
            yield
        finally:
            self._active_history.reset(token)

    def pensar_con_streaming(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return self.stream_factory(self)


@contextmanager
def _use_fake_brain(brain):
    with mock.patch(
        "core.chat_stream.importlib.import_module",
        return_value=brain,
    ) as importer:
        yield importer


def _isolated_environment(data_dir: Path) -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "TEMP", "TMP", "WINDIR")
        if key in os.environ
    }
    environment.update(
        {
            "ATLAS_DATA_DIR": str(data_dir),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONPATH": str(REPO_ROOT),
        }
    )
    return environment


def _run_isolated_brain(body: str) -> dict:
    bootstrap = r'''
import importlib
import json
import sys
import types

def install_module(name, **attributes):
    module = types.ModuleType(name)
    for attribute, value in attributes.items():
        setattr(module, attribute, value)
    sys.modules[name] = module

install_module("dotenv", load_dotenv=lambda *args, **kwargs: False)
install_module("requests", post=lambda *args, **kwargs: None)
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

brain = importlib.import_module("core.brain")
chat_stream = importlib.import_module("core.chat_stream")
'''
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        script = textwrap.dedent(bootstrap) + "\n" + textwrap.dedent(body)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=temp,
            env=_isolated_environment(temp / "data"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    if completed.returncode != 0:
        raise AssertionError(
            f"isolated brain test failed ({completed.returncode}): "
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
        raise AssertionError(
            f"isolated brain test returned no result: {completed.stdout!r}"
        )
    return json.loads(result_line)


class ChatStreamImportTests(unittest.TestCase):
    def test_import_and_iterator_creation_do_not_load_brain_or_providers(self):
        code = r'''
import sys
from core.chat_stream import stream_chat_turn

turn = stream_chat_turn("hola", history=[])
for name in (
    "core.brain",
    "dotenv",
    "requests",
    "openai",
    "groq",
    "nicegui",
):
    assert name not in sys.modules, name
assert iter(turn) is turn
'''
        completed = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(code)],
            cwd=REPO_ROOT,
            env=_isolated_environment(REPO_ROOT / "synthetic-data"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_invalid_prompt_fails_before_backend_import(self):
        for prompt in ("", "   ", None):
            with self.subTest(prompt=prompt):
                with mock.patch(
                    "core.chat_stream.importlib.import_module"
                ) as importer:
                    with self.assertRaisesRegex(
                        ValueError,
                        "^prompt_required$",
                    ):
                        list(stream_chat_turn(prompt, history=[]))
                importer.assert_not_called()


class ChatStreamAdapterTests(unittest.TestCase):
    def test_one_backend_call_and_ordered_cumulative_events(self):
        def stream(brain):
            yield "estado", "respuesta"
            yield None, "respuesta completa"
            brain.active_history.append(
                {"pregunta": "hola", "respuesta": "respuesta completa"}
            )

        brain = _FakeBrain(stream)
        history = []
        with _use_fake_brain(brain) as importer:
            events = list(
                stream_chat_turn(
                    "hola",
                    history=history,
                    motor="atlas",
                    modelo_local="modelo-falso",
                )
            )

        self.assertEqual(
            events,
            [
                ChatStreamEvent("status", "estado"),
                ChatStreamEvent("snapshot", "respuesta"),
                ChatStreamEvent("snapshot", "respuesta completa"),
            ],
        )
        self.assertEqual(
            brain.calls,
            [
                (
                    "hola",
                    {
                        "motor": "atlas",
                        "modelo_nube": None,
                        "modelo_local": "modelo-falso",
                        "modelo_groq": None,
                    },
                )
            ],
        )
        importer.assert_called_once_with("core.brain")
        self.assertEqual(
            history,
            [{"pregunta": "hola", "respuesta": "respuesta completa"}],
        )

    def test_history_is_unchanged_until_normal_completion(self):
        initial = {"pregunta": "anterior", "respuesta": "previa"}

        def stream(brain):
            self.assertIsNot(brain.active_history, history)
            self.assertIsNot(brain.active_history[0], initial)
            yield "estado", None
            yield None, "final"
            brain.active_history.append(
                {"pregunta": "actual", "respuesta": "final"}
            )

        history = [initial]
        brain = _FakeBrain(stream)
        with _use_fake_brain(brain):
            turn = stream_chat_turn("actual", history=history)
            self.assertEqual(next(turn), ChatStreamEvent("status", "estado"))
            self.assertEqual(history, [initial])
            self.assertEqual(next(turn), ChatStreamEvent("snapshot", "final"))
            self.assertEqual(history, [initial])
            with self.assertRaises(StopIteration):
                next(turn)

        self.assertEqual(
            history,
            [
                initial,
                {"pregunta": "actual", "respuesta": "final"},
            ],
        )
        self.assertIsNone(brain.active_history)

    def test_backend_error_after_partial_snapshot_is_fixed_and_rolls_back(self):
        private_error = r"token=private C:\Users\private\document.txt"

        def stream(brain):
            yield None, "parcial"
            brain.active_history.append(
                {"pregunta": "hola", "respuesta": "parcial"}
            )
            raise RuntimeError(private_error)

        history = [{"pregunta": "anterior", "respuesta": "previa"}]
        brain = _FakeBrain(stream)
        with _use_fake_brain(brain):
            turn = stream_chat_turn("hola", history=history)
            self.assertEqual(
                next(turn),
                ChatStreamEvent("snapshot", "parcial"),
            )
            with self.assertRaises(ChatStreamError) as captured:
                next(turn)

        self.assertEqual(str(captured.exception), CHAT_STREAM_ERROR_MESSAGE)
        self.assertNotIn("token=private", repr(captured.exception))
        self.assertNotIn("C:\\Users", repr(captured.exception))
        self.assertIsNone(captured.exception.__cause__)
        self.assertTrue(captured.exception.__suppress_context__)
        self.assertEqual(
            history,
            [{"pregunta": "anterior", "respuesta": "previa"}],
        )
        self.assertIsNone(brain.active_history)

    def test_cancellation_before_import_does_not_call_backend(self):
        with mock.patch(
            "core.chat_stream.importlib.import_module"
        ) as importer:
            with self.assertRaises(ChatStreamCancelled) as captured:
                list(
                    stream_chat_turn(
                        "hola",
                        history=[],
                        cancelled=lambda: True,
                    )
                )
        importer.assert_not_called()
        self.assertEqual(str(captured.exception), "")

    def test_cancellation_between_events_closes_upstream_and_rolls_back(self):
        cancellation = threading.Event()
        closed = []

        def stream(brain):
            try:
                yield "estado", "respuesta que no debe emitirse"
                brain.active_history.append(
                    {"pregunta": "hola", "respuesta": "respuesta"}
                )
            finally:
                closed.append(True)

        history = []
        brain = _FakeBrain(stream)
        with _use_fake_brain(brain):
            turn = stream_chat_turn(
                "hola",
                history=history,
                cancelled=cancellation.is_set,
            )
            self.assertEqual(next(turn), ChatStreamEvent("status", "estado"))
            cancellation.set()
            with self.assertRaises(ChatStreamCancelled):
                next(turn)

        self.assertEqual(closed, [True])
        self.assertEqual(history, [])
        self.assertIsNone(brain.active_history)

    def test_cancellation_after_last_snapshot_prevents_backend_completion(self):
        cancellation = threading.Event()
        completed = []
        closed = []

        def stream(brain):
            try:
                yield None, "final"
                brain.active_history.append(
                    {"pregunta": "hola", "respuesta": "final"}
                )
                completed.append(True)
            finally:
                closed.append(True)

        history = []
        brain = _FakeBrain(stream)
        with _use_fake_brain(brain):
            turn = stream_chat_turn(
                "hola",
                history=history,
                cancelled=cancellation.is_set,
            )
            self.assertEqual(next(turn), ChatStreamEvent("snapshot", "final"))
            cancellation.set()
            with self.assertRaises(ChatStreamCancelled):
                next(turn)

        self.assertEqual(completed, [])
        self.assertEqual(closed, [True])
        self.assertEqual(history, [])

    def test_two_threads_keep_histories_and_contexts_isolated(self):
        barrier = threading.Barrier(2)

        def stream(brain):
            current = brain.active_history
            label = current[0]["respuesta"]
            barrier.wait(timeout=5)
            yield None, f"respuesta-{label}"
            current.append(
                {"pregunta": f"pregunta-{label}", "respuesta": label}
            )

        brain = _FakeBrain(stream)
        first = [{"pregunta": "previa", "respuesta": "uno"}]
        second = [{"pregunta": "previa", "respuesta": "dos"}]

        with _use_fake_brain(brain):
            first_turn = stream_chat_turn("primera", history=first)
            second_turn = stream_chat_turn("segunda", history=second)
            with ThreadPoolExecutor(max_workers=2) as executor:
                first_future = executor.submit(list, first_turn)
                second_future = executor.submit(list, second_turn)
                first_events = first_future.result(timeout=10)
                second_events = second_future.result(timeout=10)

        self.assertEqual(
            first_events,
            [ChatStreamEvent("snapshot", "respuesta-uno")],
        )
        self.assertEqual(
            second_events,
            [ChatStreamEvent("snapshot", "respuesta-dos")],
        )
        self.assertEqual(first[-1]["respuesta"], "uno")
        self.assertEqual(second[-1]["respuesta"], "dos")
        self.assertNotEqual(first[-1], second[-1])
        self.assertIsNone(brain.active_history)


class BrainIntegrationTests(unittest.TestCase):
    def test_context_uses_working_history_and_restores_global_default(self):
        result = _run_isolated_brain(
            r'''
brain.HISTORIAL.clear()
brain.agregar_al_historial("global", "respuesta-global")
working = []
with brain._usar_contexto_streaming(working):
    brain.agregar_al_historial("aislada", "respuesta-aislada")
    inside = brain.formatear_historial()
    global_inside = list(brain.HISTORIAL)
outside = brain.formatear_historial()
print("ATLAS_TEST_RESULT=" + json.dumps({
    "working": working,
    "global_inside": global_inside,
    "inside": inside,
    "outside": outside,
}))
'''
        )
        self.assertEqual(
            result["working"],
            [{"pregunta": "aislada", "respuesta": "respuesta-aislada"}],
        )
        self.assertEqual(
            result["global_inside"],
            [{"pregunta": "global", "respuesta": "respuesta-global"}],
        )
        self.assertIn("aislada", result["inside"])
        self.assertNotIn("global", result["inside"])
        self.assertIn("global", result["outside"])

    def test_successful_isolated_turn_commits_without_global_history(self):
        result = _run_isolated_brain(
            r'''
brain.HISTORIAL.clear()
brain.verificar_reglas_y_forzar_respuesta = lambda pregunta: (True, "respuesta")
history = []
events = [event.__dict__ for event in chat_stream.stream_chat_turn(
    "hola",
    history=history,
)]
print("ATLAS_TEST_RESULT=" + json.dumps({
    "events": events,
    "history": history,
    "global": brain.HISTORIAL,
}))
'''
        )
        self.assertEqual(
            result["events"],
            [
                {"kind": "status", "text": "[Agente: interceptado] [Motor: reglas]"},
                {"kind": "snapshot", "text": "respuesta"},
            ],
        )
        self.assertEqual(
            result["history"],
            [{"pregunta": "hola", "respuesta": "respuesta"}],
        )
        self.assertEqual(result["global"], [])

    def test_isolated_history_preserves_max_history_policy(self):
        result = _run_isolated_brain(
            r'''
brain.HISTORIAL.clear()
brain.verificar_reglas_y_forzar_respuesta = lambda pregunta: (True, "nueva")
history = [
    {"pregunta": f"pregunta-{index}", "respuesta": f"respuesta-{index}"}
    for index in range(brain.MAX_HISTORIAL)
]
list(chat_stream.stream_chat_turn("actual", history=history))
print("ATLAS_TEST_RESULT=" + json.dumps({
    "max": brain.MAX_HISTORIAL,
    "length": len(history),
    "first": history[0],
    "last": history[-1],
    "global": brain.HISTORIAL,
}))
'''
        )
        self.assertEqual(result["length"], result["max"])
        self.assertEqual(
            result["first"],
            {"pregunta": "pregunta-1", "respuesta": "respuesta-1"},
        )
        self.assertEqual(
            result["last"],
            {"pregunta": "actual", "respuesta": "nueva"},
        )
        self.assertEqual(result["global"], [])

    def test_all_provider_failures_are_safe_in_isolated_mode(self):
        result = _run_isolated_brain(
            r'''
import os

class FailingRequests:
    @staticmethod
    def post(*args, **kwargs):
        raise RuntimeError(r"local-token C:\Users\private\local.txt")

brain.requests = FailingRequests()
brain.cargar_perfil_charly = lambda: ""
brain.cargar_prompt_agente = lambda agente: ""
brain.detectar_agente_con_modelo = lambda pregunta: "general"
brain.verificar_reglas_y_forzar_respuesta = lambda pregunta: (False, "")
brain.obtener_contexto_reglas = lambda: ""
brain.obtener_reglas_de_formato = lambda: ""
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("NVIDIA_API_KEY", None)
os.environ.pop("GROQ_API_KEY", None)

outcomes = {}
for motor in ("atlas", "prometeo", "groq"):
    history = []
    try:
        list(chat_stream.stream_chat_turn("hola", history=history, motor=motor))
    except chat_stream.ChatStreamError as exc:
        outcomes[motor] = {
            "message": str(exc),
            "repr": repr(exc),
            "history": history,
        }
    else:
        outcomes[motor] = {"message": "missing-error", "history": history}

print("ATLAS_TEST_RESULT=" + json.dumps({
    "outcomes": outcomes,
    "global": brain.HISTORIAL,
}))
'''
        )
        self.assertEqual(set(result["outcomes"]), {"atlas", "prometeo", "groq"})
        for outcome in result["outcomes"].values():
            self.assertEqual(outcome["message"], CHAT_STREAM_ERROR_MESSAGE)
            self.assertEqual(outcome["history"], [])
            self.assertNotIn("local-token", outcome["repr"])
            self.assertNotIn("C:\\Users", outcome["repr"])
            self.assertNotIn(".env", outcome["repr"])
        self.assertEqual(result["global"], [])

    def test_legacy_normal_intercepted_and_error_outputs_remain_unchanged(self):
        result = _run_isolated_brain(
            r'''
brain.cargar_perfil_charly = lambda: ""
brain.cargar_prompt_agente = lambda agente: ""
brain.detectar_agente_con_modelo = lambda pregunta: "general"
brain.obtener_contexto_reglas = lambda: ""
brain.obtener_reglas_de_formato = lambda: ""
original_stream_local = brain._stream_local

brain.HISTORIAL.clear()
brain.verificar_reglas_y_forzar_respuesta = lambda pregunta: (False, "")
brain._stream_local = lambda prompt, modelo: iter(("A", "B"))
normal = list(brain.pensar_con_streaming("normal", motor="atlas", modelo_local="fake"))
normal_history = list(brain.HISTORIAL)

brain.HISTORIAL.clear()
brain.verificar_reglas_y_forzar_respuesta = lambda pregunta: (True, "forzada")
intercepted = list(brain.pensar_con_streaming("regla", motor="atlas", modelo_local="fake"))
intercepted_history = list(brain.HISTORIAL)

def failing_stream(prompt, modelo):
    yield "parcial"
    raise RuntimeError("legacy-details")

brain.HISTORIAL.clear()
brain.verificar_reglas_y_forzar_respuesta = lambda pregunta: (False, "")
brain._stream_local = failing_stream
legacy_error = list(brain.pensar_con_streaming("error", motor="atlas", modelo_local="fake"))
legacy_error_history = list(brain.HISTORIAL)

class LegacyFailingRequests:
    @staticmethod
    def post(*args, **kwargs):
        raise RuntimeError("legacy-local")

brain.requests = LegacyFailingRequests()
brain._stream_local = original_stream_local
legacy_provider_error = list(brain._stream_local("prompt", "fake"))

print("ATLAS_TEST_RESULT=" + json.dumps({
    "normal": normal,
    "normal_history": normal_history,
    "intercepted": intercepted,
    "intercepted_history": intercepted_history,
    "legacy_error": legacy_error,
    "legacy_error_history": legacy_error_history,
    "legacy_provider_error": legacy_provider_error,
}))
'''
        )
        self.assertEqual(
            result["normal"],
            [
                ["[Agente: general] [Motor: atlas]", None],
                [None, "A"],
                [None, "AB"],
            ],
        )
        self.assertEqual(
            result["normal_history"],
            [{"pregunta": "normal", "respuesta": "AB"}],
        )
        self.assertEqual(
            result["intercepted"],
            [
                ["[Agente: interceptado] [Motor: reglas]", None],
                [None, "forzada"],
            ],
        )
        self.assertEqual(
            result["intercepted_history"],
            [{"pregunta": "regla", "respuesta": "forzada"}],
        )
        self.assertEqual(result["legacy_error"][-1], [None, "Error: legacy-details"])
        self.assertEqual(
            result["legacy_error_history"],
            [{"pregunta": "error", "respuesta": "parcial"}],
        )
        self.assertEqual(
            result["legacy_provider_error"],
            ["❌ Error en Atlas local: legacy-local"],
        )


if __name__ == "__main__":
    unittest.main()
