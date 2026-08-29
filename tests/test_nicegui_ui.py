import asyncio
import builtins
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

from atlas_nicegui.app import (
    QUERY_FAILED_MESSAGE,
    STATUS_PLACEHOLDER,
    create_root,
)
from core.index_status import format_index_status_lines


REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeElement:
    def classes(self, _value):
        return self


class _FakeLabel(_FakeElement):
    def __init__(self, text):
        self.text = str(text)


class _FakeColumn(_FakeElement):
    def __init__(self, ui):
        self.ui = ui
        self.labels = []

    def __enter__(self):
        self.ui._container_stack.append(self)
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.ui._container_stack.pop()

    def clear(self):
        self.labels.clear()

    @property
    def lines(self):
        return tuple(label.text for label in self.labels)


class _FakeButton(_FakeElement):
    def __init__(self, text, on_click):
        self.text = text
        self.on_click = on_click
        self.enabled = True

    def disable(self):
        self.enabled = False

    def enable(self):
        self.enabled = True


class _FakeUI:
    def __init__(self):
        self.labels = []
        self.columns = []
        self.buttons = []
        self.run_calls = []
        self._container_stack = []

    def label(self, text):
        label = _FakeLabel(text)
        self.labels.append(label)
        if self._container_stack:
            self._container_stack[-1].labels.append(label)
        return label

    def column(self):
        column = _FakeColumn(self)
        self.columns.append(column)
        return column

    def button(self, text, *, on_click):
        button = _FakeButton(text, on_click)
        self.buttons.append(button)
        return button

    def run(self, *args, **kwargs):
        self.run_calls.append((args, kwargs))


def _status(state="HEALTHY", writer_state="inactive"):
    labels = {
        "HEALTHY": "Saludable",
        "HEALTHY_EMPTY": "Saludable y vacío",
        "DEGRADED": "Degradado",
        "INCONSISTENT": "Inconsistente",
        "UNAVAILABLE": "No disponible",
    }
    writer_labels = {
        "active": "Activo",
        "inactive": "Inactivo",
        "unknown": "Desconocido",
    }
    severities = {
        "HEALTHY": "success",
        "HEALTHY_EMPTY": "success",
        "DEGRADED": "warning",
        "INCONSISTENT": "warning",
        "UNAVAILABLE": "error",
    }
    return {
        "state": state,
        "state_label": labels[state],
        "observed_state": state,
        "observed_state_label": labels[state],
        "healthy": state in {"HEALTHY", "HEALTHY_EMPTY"},
        "severity": severities[state],
        "writer_state": writer_state,
        "writer_label": writer_labels[writer_state],
        "possibly_transient": writer_state != "inactive",
        "sources_count": 2,
        "manifest_entries_count": 2,
        "chunk_count": 4,
        "divergences": {},
        "orphan_count": 0,
        "issues": (),
    }


async def _direct_io_bound(function, *args):
    return function(*args)


class NiceGuiImportAndEntrypointTests(unittest.TestCase):
    def test_imports_do_not_load_nicegui_or_mutating_subsystems(self):
        code = """
import sys
import atlas_nicegui
import atlas_nicegui.app
import atlas_nicegui.__main__
for name in (
    'nicegui',
    'core.index_repair',
    'core.index_writer_lock',
    'sentence_transformers',
    'chromadb',
    'ollama',
):
    assert name not in sys.modules, name
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_main_sets_storage_before_import_and_uses_fixed_local_run_contract(self):
        from atlas_nicegui import __main__ as entrypoint

        fake_ui = _FakeUI()
        fake_run = SimpleNamespace(io_bound=_direct_io_bound)
        fake_nicegui = ModuleType("nicegui")
        fake_nicegui.ui = fake_ui
        fake_nicegui.run = fake_run
        original_import = builtins.__import__

        with tempfile.TemporaryDirectory() as temp_dir:
            expected_storage = str(Path(temp_dir) / "temp" / "nicegui")
            observed_storage = []

            def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name == "nicegui":
                    observed_storage.append(
                        os.environ.get("NICEGUI_STORAGE_PATH")
                    )
                    return fake_nicegui
                return original_import(name, globals, locals, fromlist, level)

            fake_paths = SimpleNamespace(temp_dir=Path(temp_dir) / "temp")
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("NICEGUI_STORAGE_PATH", None)
                with mock.patch(
                    "core.system.paths.get_paths",
                    return_value=fake_paths,
                ), mock.patch("builtins.__import__", side_effect=guarded_import):
                    entrypoint.main()

            self.assertEqual(observed_storage, [expected_storage])

        self.assertEqual(len(fake_ui.run_calls), 1)
        args, kwargs = fake_ui.run_calls[0]
        self.assertEqual(len(args), 1)
        self.assertTrue(callable(args[0]))
        self.assertEqual(
            kwargs,
            {
                "host": "127.0.0.1",
                "port": 8402,
                "show": False,
                "on_air": None,
                "native": False,
                "reload": False,
            },
        )
        self.assertEqual(fake_ui.columns, [])
        self.assertEqual(fake_ui.buttons, [])


class NiceGuiPageTests(unittest.IsolatedAsyncioTestCase):
    def _build_page(self, *, provider, io_bound=_direct_io_bound, formatter=None):
        fake_ui = _FakeUI()
        kwargs = {
            "ui": fake_ui,
            "io_bound": io_bound,
            "provider": provider,
        }
        if formatter is not None:
            kwargs["formatter"] = formatter
        root = create_root(**kwargs)
        root()
        return fake_ui, root

    async def test_render_and_rerender_do_not_query_automatically(self):
        calls = []

        def provider(requested):
            calls.append(requested)
            return _status()

        fake_ui, root = self._build_page(provider=provider)
        root()

        self.assertEqual(calls, [])
        self.assertEqual(len(fake_ui.buttons), 2)
        self.assertEqual(fake_ui.columns[0].lines, (STATUS_PLACEHOLDER,))
        self.assertEqual(fake_ui.columns[1].lines, (STATUS_PLACEHOLDER,))

    async def test_click_queries_once_and_renders_exact_formatter_lines(self):
        calls = []
        expected_status = _status("INCONSISTENT", "unknown")
        expected_lines = ("línea uno", "línea dos")

        def provider(requested):
            calls.append(requested)
            return expected_status

        formatter_calls = []

        def formatter(status):
            formatter_calls.append(status)
            return expected_lines

        fake_ui, _ = self._build_page(
            provider=provider,
            formatter=formatter,
        )
        button = fake_ui.buttons[0]
        await button.on_click()

        self.assertEqual(calls, [True])
        self.assertEqual(formatter_calls, [expected_status])
        self.assertEqual(fake_ui.columns[0].lines, expected_lines)
        self.assertTrue(button.enabled)

    async def test_concurrent_second_click_on_same_page_is_ignored(self):
        started = asyncio.Event()
        release = asyncio.Event()
        runner_calls = []
        provider_calls = []

        def provider(requested):
            provider_calls.append(requested)
            return _status()

        async def blocked_io_bound(function, *args):
            runner_calls.append((function, args))
            started.set()
            await release.wait()
            return function(*args)

        fake_ui, _ = self._build_page(
            provider=provider,
            io_bound=blocked_io_bound,
        )
        button = fake_ui.buttons[0]
        first = asyncio.create_task(button.on_click())
        await started.wait()

        self.assertFalse(button.enabled)
        await button.on_click()
        self.assertEqual(len(runner_calls), 1)

        release.set()
        await first
        self.assertEqual(provider_calls, [True])
        self.assertTrue(button.enabled)

    async def test_two_page_instances_have_independent_guards(self):
        started = asyncio.Event()
        release = asyncio.Event()
        runner_calls = 0

        def provider(requested):
            return _status()

        async def blocked_io_bound(function, *args):
            nonlocal runner_calls
            runner_calls += 1
            if runner_calls == 2:
                started.set()
            await release.wait()
            return function(*args)

        fake_ui, root = self._build_page(
            provider=provider,
            io_bound=blocked_io_bound,
        )
        root()
        first = asyncio.create_task(fake_ui.buttons[0].on_click())
        second = asyncio.create_task(fake_ui.buttons[1].on_click())
        await started.wait()

        self.assertEqual(runner_calls, 2)
        self.assertFalse(fake_ui.buttons[0].enabled)
        self.assertFalse(fake_ui.buttons[1].enabled)

        release.set()
        await asyncio.gather(first, second)
        self.assertTrue(fake_ui.buttons[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

    async def test_ordinary_error_is_fixed_safe_message_and_restores_button(self):
        async def failing_io_bound(_function, *_args):
            raise RuntimeError(
                r"token=private C:\Users\private\document.txt"
            )

        fake_ui, _ = self._build_page(
            provider=lambda requested: _status(),
            io_bound=failing_io_bound,
        )
        button = fake_ui.buttons[0]
        await button.on_click()

        self.assertEqual(fake_ui.columns[0].lines, (QUERY_FAILED_MESSAGE,))
        rendered = " ".join(fake_ui.columns[0].lines)
        self.assertNotIn("token=private", rendered)
        self.assertNotIn("C:\\Users", rendered)
        self.assertTrue(button.enabled)

    async def test_none_result_is_normalized_to_cancellation(self):
        formatter_calls = []

        async def cancelled_io_bound(_function, *_args):
            return None

        fake_ui, _ = self._build_page(
            provider=lambda requested: _status(),
            io_bound=cancelled_io_bound,
            formatter=lambda status: formatter_calls.append(status),
        )
        button = fake_ui.buttons[0]

        with self.assertRaises(asyncio.CancelledError):
            await button.on_click()

        self.assertEqual(formatter_calls, [])
        self.assertEqual(fake_ui.columns[0].lines, (STATUS_PLACEHOLDER,))
        self.assertTrue(button.enabled)

    async def test_raised_cancellation_propagates_without_replacing_status(self):
        formatter_calls = []

        async def cancelled_io_bound(_function, *_args):
            raise asyncio.CancelledError()

        fake_ui, _ = self._build_page(
            provider=lambda requested: _status(),
            io_bound=cancelled_io_bound,
            formatter=lambda status: formatter_calls.append(status),
        )
        button = fake_ui.buttons[0]

        with self.assertRaises(asyncio.CancelledError):
            await button.on_click()

        self.assertEqual(formatter_calls, [])
        self.assertEqual(fake_ui.columns[0].lines, (STATUS_PLACEHOLDER,))
        self.assertTrue(button.enabled)

    async def test_all_states_and_writer_states_use_existing_formatter(self):
        cases = (
            ("HEALTHY", "inactive"),
            ("HEALTHY_EMPTY", "active"),
            ("DEGRADED", "unknown"),
            ("INCONSISTENT", "inactive"),
            ("UNAVAILABLE", "unknown"),
        )
        for state, writer_state in cases:
            with self.subTest(state=state, writer_state=writer_state):
                status = _status(state, writer_state)
                fake_ui, _ = self._build_page(
                    provider=lambda requested, value=status: value,
                )
                await fake_ui.buttons[0].on_click()
                self.assertEqual(
                    fake_ui.columns[0].lines,
                    format_index_status_lines(status),
                )


if __name__ == "__main__":
    unittest.main()
