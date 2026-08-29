import asyncio
import builtins
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

from atlas_nicegui.app import (
    CHAT_CANCELLED_MESSAGE,
    QUERY_FAILED_MESSAGE,
    STATUS_PLACEHOLDER,
    create_root,
)
from core.chat_stream import (
    CHAT_STREAM_ERROR_MESSAGE,
    ChatStreamCancelled,
    ChatStreamEvent,
)
from core.index_status import format_index_status_lines


REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeElement:
    def classes(self, _value):
        return self


class _FakeLabel(_FakeElement):
    def __init__(self, ui, text):
        self.ui = ui
        self._text = ""
        self.text = text

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = str(value)
        self.ui.mutation_threads.append(threading.get_ident())


class _FakeMarkdown(_FakeElement):
    def __init__(self, ui, content, *, sanitize):
        self.ui = ui
        self.sanitize = sanitize
        self._content = ""
        self.content = content

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        self._content = str(value)
        self.ui.mutation_threads.append(threading.get_ident())


class _FakeColumn(_FakeElement):
    def __init__(self, ui):
        self.ui = ui
        self.labels = []
        self.chat_messages = []

    def __enter__(self):
        self.ui._container_stack.append(self)
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.ui._container_stack.pop()

    def clear(self):
        self.labels.clear()
        self.chat_messages.clear()
        self.ui.mutation_threads.append(threading.get_ident())

    @property
    def lines(self):
        return tuple(label.text for label in self.labels)


class _FakeButton(_FakeElement):
    def __init__(self, ui, text, on_click):
        self.ui = ui
        self.text = text
        self.on_click = on_click
        self.enabled = True

    def disable(self):
        self.enabled = False
        self.ui.mutation_threads.append(threading.get_ident())

    def enable(self):
        self.enabled = True
        self.ui.mutation_threads.append(threading.get_ident())


class _FakeInput(_FakeElement):
    def __init__(self, ui, *, label, placeholder):
        self.ui = ui
        self.label = label
        self.placeholder = placeholder
        self.handlers = {}
        self.enabled = True
        self._value = ""

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.ui.mutation_threads.append(threading.get_ident())

    def on(self, event, handler):
        self.handlers[event] = handler
        return self

    def disable(self):
        self.enabled = False
        self.ui.mutation_threads.append(threading.get_ident())

    def enable(self):
        self.enabled = True
        self.ui.mutation_threads.append(threading.get_ident())


class _FakeChatMessage(_FakeElement):
    def __init__(self, ui, *, text, name, sent, text_html):
        self.ui = ui
        self.text = text
        self.name = name
        self.sent = sent
        self.text_html = text_html
        self.labels = []
        self.markdowns = []

    def __enter__(self):
        self.ui._container_stack.append(self)
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.ui._container_stack.pop()


class _FakeClient:
    def __init__(self):
        self.has_socket_connection = True
        self.is_deleted = False
        self.connect_handlers = []
        self.disconnect_handlers = []

    def on_connect(self, handler):
        self.connect_handlers.append(handler)

    def on_disconnect(self, handler):
        self.disconnect_handlers.append(handler)

    def disconnect(self):
        self.has_socket_connection = False
        for handler in tuple(self.disconnect_handlers):
            handler()

    def reconnect(self):
        self.has_socket_connection = True
        for handler in tuple(self.disconnect_handlers):
            handler()
        for handler in tuple(self.connect_handlers):
            handler()


class _FakeUI:
    def __init__(self, client=None):
        self.client = client or _FakeClient()
        self.context = SimpleNamespace(client=self.client)
        self.labels = []
        self.columns = []
        self.buttons = []
        self.inputs = []
        self.chat_messages = []
        self.markdowns = []
        self.run_calls = []
        self.mutation_threads = []
        self._container_stack = []

    def label(self, text):
        label = _FakeLabel(self, text)
        self.labels.append(label)
        if self._container_stack and hasattr(
            self._container_stack[-1], "labels"
        ):
            self._container_stack[-1].labels.append(label)
        return label

    def column(self):
        column = _FakeColumn(self)
        self.columns.append(column)
        return column

    def button(self, text, *, on_click):
        button = _FakeButton(self, text, on_click)
        self.buttons.append(button)
        return button

    def input(self, *, label, placeholder):
        input_element = _FakeInput(
            self,
            label=label,
            placeholder=placeholder,
        )
        self.inputs.append(input_element)
        return input_element

    def chat_message(
        self,
        *,
        text=None,
        name=None,
        sent=False,
        text_html=False,
    ):
        message = _FakeChatMessage(
            self,
            text=text,
            name=name,
            sent=sent,
            text_html=text_html,
        )
        self.chat_messages.append(message)
        if self._container_stack and hasattr(
            self._container_stack[-1], "chat_messages"
        ):
            self._container_stack[-1].chat_messages.append(message)
        return message

    def markdown(self, content, *, sanitize):
        markdown = _FakeMarkdown(self, content, sanitize=sanitize)
        self.markdowns.append(markdown)
        if self._container_stack and hasattr(
            self._container_stack[-1], "markdowns"
        ):
            self._container_stack[-1].markdowns.append(markdown)
        return markdown

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


async def _thread_io_bound(function, *args):
    return await asyncio.to_thread(function, *args)


class NiceGuiImportAndEntrypointTests(unittest.TestCase):
    def test_imports_do_not_load_nicegui_or_mutating_subsystems(self):
        code = """
import sys
import atlas_nicegui
import atlas_nicegui.app
import atlas_nicegui.__main__
for name in (
    'nicegui',
    'core.brain',
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
    def _build_page(
        self,
        *,
        provider,
        io_bound=_direct_io_bound,
        formatter=None,
        streamer=None,
        client=None,
    ):
        fake_ui = _FakeUI(client=client)
        kwargs = {
            "ui": fake_ui,
            "io_bound": io_bound,
            "provider": provider,
        }
        if formatter is not None:
            kwargs["formatter"] = formatter
        if streamer is not None:
            kwargs["streamer"] = streamer
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
        self.assertEqual(len(fake_ui.buttons), 4)
        self.assertEqual(fake_ui.columns[0].lines, (STATUS_PLACEHOLDER,))
        self.assertEqual(fake_ui.columns[2].lines, (STATUS_PLACEHOLDER,))

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
        second = asyncio.create_task(fake_ui.buttons[2].on_click())
        await started.wait()

        self.assertEqual(runner_calls, 2)
        self.assertFalse(fake_ui.buttons[0].enabled)
        self.assertFalse(fake_ui.buttons[2].enabled)

        release.set()
        await asyncio.gather(first, second)
        self.assertTrue(fake_ui.buttons[0].enabled)
        self.assertTrue(fake_ui.buttons[2].enabled)

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


class NiceGuiChatTests(unittest.IsolatedAsyncioTestCase):
    def _build_page(
        self,
        *,
        streamer,
        io_bound=_thread_io_bound,
        client=None,
    ):
        fake_ui = _FakeUI(client=client)
        root = create_root(
            ui=fake_ui,
            io_bound=io_bound,
            provider=lambda requested: _status(),
            streamer=streamer,
        )
        root()
        return fake_ui

    @staticmethod
    async def _send(fake_ui, prompt, *, enter=False):
        fake_ui.inputs[0].value = prompt
        if enter:
            await fake_ui.inputs[0].handlers["keydown.enter"]()
        else:
            await fake_ui.buttons[1].on_click()

    async def test_render_does_not_start_chat_or_provider(self):
        calls = []

        def streamer(prompt, *, history, cancelled):
            calls.append((prompt, history, cancelled))
            yield ChatStreamEvent("snapshot", "respuesta")

        fake_ui = self._build_page(streamer=streamer)

        self.assertEqual(calls, [])
        self.assertEqual(fake_ui.chat_messages, [])
        self.assertEqual(len(fake_ui.inputs), 1)
        self.assertEqual(len(fake_ui.buttons), 2)

    async def test_button_streams_once_in_worker_and_updates_ui_on_loop(self):
        loop_thread = threading.get_ident()
        worker_threads = []
        observed = []

        def streamer(prompt, *, history, cancelled):
            worker_threads.append(threading.get_ident())
            observed.append((prompt, tuple(history), cancelled()))
            yield ChatStreamEvent("status", "Pensando")
            yield ChatStreamEvent("snapshot", "Hola")
            yield ChatStreamEvent("snapshot", "Hola **mundo**")
            history.extend(
                (
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "Hola **mundo**"},
                )
            )

        io_bound_calls = []

        async def recording_io_bound(function, *args):
            io_bound_calls.append(function)
            return await asyncio.to_thread(function, *args)

        fake_ui = self._build_page(
            streamer=streamer,
            io_bound=recording_io_bound,
        )
        fake_ui.inputs[0].value = "<b>hola</b>"
        fake_ui.mutation_threads.clear()

        await fake_ui.buttons[1].on_click()

        self.assertEqual(len(io_bound_calls), 1)
        self.assertEqual(observed[0][:2], ("<b>hola</b>", ()))
        self.assertFalse(observed[0][2])
        self.assertEqual(len(set(worker_threads)), 1)
        self.assertNotEqual(worker_threads[0], loop_thread)
        self.assertTrue(fake_ui.mutation_threads)
        self.assertEqual(set(fake_ui.mutation_threads), {loop_thread})

        user_message, assistant_message = fake_ui.chat_messages
        self.assertEqual(user_message.text, "<b>hola</b>")
        self.assertTrue(user_message.sent)
        self.assertFalse(user_message.text_html)
        self.assertFalse(assistant_message.sent)
        self.assertFalse(assistant_message.text_html)
        self.assertTrue(fake_ui.markdowns[0].sanitize)
        self.assertEqual(fake_ui.markdowns[0].content, "Hola **mundo**")
        self.assertEqual(assistant_message.labels[0].text, "")
        self.assertEqual(fake_ui.inputs[0].value, "")
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

    async def test_enter_uses_same_submit_path(self):
        prompts = []

        def streamer(prompt, *, history, cancelled):
            prompts.append(prompt)
            yield ChatStreamEvent("snapshot", "respuesta")

        fake_ui = self._build_page(streamer=streamer)
        await self._send(fake_ui, "por Enter", enter=True)

        self.assertEqual(prompts, ["por Enter"])
        self.assertEqual(fake_ui.markdowns[0].content, "respuesta")

    async def test_duplicate_submit_is_ignored_while_turn_is_active(self):
        started = asyncio.Event()
        release = threading.Event()
        calls = []
        loop = asyncio.get_running_loop()

        def streamer(prompt, *, history, cancelled):
            calls.append(prompt)
            loop.call_soon_threadsafe(started.set)
            release.wait(timeout=2)
            yield ChatStreamEvent("snapshot", "terminado")

        fake_ui = self._build_page(streamer=streamer)
        fake_ui.inputs[0].value = "primero"
        first = asyncio.create_task(fake_ui.buttons[1].on_click())
        await asyncio.wait_for(started.wait(), timeout=1)

        fake_ui.inputs[0].value = "segundo"
        await fake_ui.inputs[0].handlers["keydown.enter"]()
        self.assertEqual(calls, ["primero"])

        release.set()
        await asyncio.wait_for(first, timeout=1)
        self.assertEqual(calls, ["primero"])
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

    async def test_sequential_turns_share_only_the_page_history(self):
        observed = []

        def streamer(prompt, *, history, cancelled):
            observed.append((prompt, tuple(dict(item) for item in history)))
            response = f"respuesta:{prompt}"
            yield ChatStreamEvent("snapshot", response)
            history.extend(
                (
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response},
                )
            )

        fake_ui = self._build_page(streamer=streamer)
        await self._send(fake_ui, "uno")
        await self._send(fake_ui, "dos")

        self.assertEqual(observed[0], ("uno", ()))
        self.assertEqual(
            observed[1],
            (
                "dos",
                (
                    {"role": "user", "content": "uno"},
                    {
                        "role": "assistant",
                        "content": "respuesta:uno",
                    },
                ),
            ),
        )

    async def test_two_pages_have_isolated_histories(self):
        observed = []

        def streamer(prompt, *, history, cancelled):
            observed.append((prompt, history, tuple(history)))
            yield ChatStreamEvent("snapshot", prompt.upper())
            history.extend(
                (
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": prompt.upper()},
                )
            )

        first_page = self._build_page(streamer=streamer)
        second_page = self._build_page(streamer=streamer)
        await self._send(first_page, "primera")
        await self._send(second_page, "segunda")

        self.assertEqual(observed[0][2], ())
        self.assertEqual(observed[1][2], ())
        self.assertIsNot(observed[0][1], observed[1][1])

    async def test_failure_replaces_partial_output_with_fixed_safe_message(self):
        def streamer(prompt, *, history, cancelled):
            yield ChatStreamEvent("snapshot", "respuesta parcial")
            raise RuntimeError(
                r"token=private C:\Users\private\document.txt"
            )

        fake_ui = self._build_page(streamer=streamer)
        await self._send(fake_ui, "fallar")

        self.assertEqual(
            fake_ui.markdowns[0].content,
            CHAT_STREAM_ERROR_MESSAGE,
        )
        rendered = " ".join(
            [
                fake_ui.markdowns[0].content,
                fake_ui.chat_messages[0].text,
                fake_ui.chat_messages[1].labels[0].text,
            ]
        )
        self.assertNotIn("token=private", rendered)
        self.assertNotIn("C:\\Users", rendered)
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

    async def test_transport_failure_after_partial_output_is_fixed_and_safe(self):
        observed_histories = []

        def streamer(prompt, *, history, cancelled):
            observed_histories.append(tuple(dict(item) for item in history))
            yield ChatStreamEvent("snapshot", "respuesta parcial")
            history.extend(
                (
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "respuesta parcial"},
                )
            )

        io_bound_calls = 0

        async def failing_io_bound(function, *args):
            nonlocal io_bound_calls
            io_bound_calls += 1
            result = await asyncio.to_thread(function, *args)
            if io_bound_calls == 1:
                raise RuntimeError(
                    r"token=private C:\Users\private\document.txt"
                )
            return result

        fake_ui = self._build_page(
            streamer=streamer,
            io_bound=failing_io_bound,
        )
        await self._send(fake_ui, "fallo de transporte")

        self.assertEqual(
            fake_ui.markdowns[0].content,
            CHAT_STREAM_ERROR_MESSAGE,
        )
        self.assertNotIn("token=private", fake_ui.markdowns[0].content)
        self.assertNotIn("C:\\Users", fake_ui.markdowns[0].content)
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

        await self._send(fake_ui, "segundo intento")
        self.assertEqual(observed_histories, [(), ()])

    async def test_none_worker_result_is_a_visible_safe_cancellation(self):
        calls = []

        def streamer(prompt, *, history, cancelled):
            calls.append(prompt)
            yield ChatStreamEvent("snapshot", "no debe ejecutarse")

        async def cancelled_io_bound(_function, *_args):
            return None

        fake_ui = self._build_page(
            streamer=streamer,
            io_bound=cancelled_io_bound,
        )
        await self._send(fake_ui, "cancelar")

        self.assertEqual(calls, [])
        self.assertEqual(
            fake_ui.markdowns[0].content,
            CHAT_CANCELLED_MESSAGE,
        )
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

    async def test_async_cancellation_reaches_worker_and_preserves_history(self):
        started = asyncio.Event()
        cancellation_seen = threading.Event()
        observed_histories = []
        calls = 0
        loop = asyncio.get_running_loop()

        def streamer(prompt, *, history, cancelled):
            nonlocal calls
            calls += 1
            observed_histories.append(tuple(dict(item) for item in history))
            if calls == 1:
                loop.call_soon_threadsafe(started.set)
                while not cancelled():
                    cancellation_seen.wait(timeout=0.01)
                cancellation_seen.set()
                raise ChatStreamCancelled()

            yield ChatStreamEvent("snapshot", "segundo completo")
            history.extend(
                (
                    {"role": "user", "content": prompt},
                    {
                        "role": "assistant",
                        "content": "segundo completo",
                    },
                )
            )

        fake_ui = self._build_page(streamer=streamer)
        fake_ui.inputs[0].value = "primero"
        first = asyncio.create_task(fake_ui.buttons[1].on_click())
        await asyncio.wait_for(started.wait(), timeout=1)

        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        cancellation_reached = await asyncio.to_thread(
            cancellation_seen.wait,
            1,
        )
        self.assertTrue(cancellation_reached)
        self.assertEqual(fake_ui.markdowns[0].content, "")
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

        await self._send(fake_ui, "segundo")
        self.assertEqual(observed_histories, [(), ()])
        self.assertEqual(fake_ui.markdowns[1].content, "segundo completo")

    async def test_disconnect_and_reconnect_cancel_old_turn_without_late_ui(self):
        client = _FakeClient()
        started = asyncio.Event()
        cancellation_seen = threading.Event()
        release_after_reconnect = threading.Event()
        observed_histories = []
        loop = asyncio.get_running_loop()

        def streamer(prompt, *, history, cancelled):
            observed_histories.append(tuple(dict(item) for item in history))
            if prompt == "primero":
                yield ChatStreamEvent("snapshot", "parcial")
                loop.call_soon_threadsafe(started.set)
                while not cancelled():
                    cancellation_seen.wait(timeout=0.01)
                cancellation_seen.set()
                release_after_reconnect.wait(timeout=2)
                yield ChatStreamEvent("snapshot", "evento tardío")
                history.append({"role": "assistant", "content": "incorrecto"})
                return

            yield ChatStreamEvent("snapshot", "nuevo turno")
            history.extend(
                (
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "nuevo turno"},
                )
            )

        fake_ui = self._build_page(streamer=streamer, client=client)
        fake_ui.inputs[0].value = "primero"
        first = asyncio.create_task(fake_ui.buttons[1].on_click())
        await asyncio.wait_for(started.wait(), timeout=1)
        for _ in range(100):
            if fake_ui.markdowns[0].content == "parcial":
                break
            await asyncio.sleep(0.01)
        self.assertEqual(fake_ui.markdowns[0].content, "parcial")

        mutations_before_disconnect = len(fake_ui.mutation_threads)
        client.disconnect()
        cancellation_reached = await asyncio.to_thread(
            cancellation_seen.wait,
            1,
        )
        self.assertTrue(cancellation_reached)
        self.assertEqual(
            len(fake_ui.mutation_threads),
            mutations_before_disconnect,
        )

        client.reconnect()
        release_after_reconnect.set()
        await asyncio.wait_for(first, timeout=1)

        self.assertEqual(fake_ui.markdowns[0].content, "parcial")
        self.assertNotEqual(
            fake_ui.markdowns[0].content,
            CHAT_CANCELLED_MESSAGE,
        )
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

        await self._send(fake_ui, "segundo")
        self.assertEqual(observed_histories, [(), ()])
        self.assertEqual(fake_ui.markdowns[1].content, "nuevo turno")

    async def test_reconnect_restores_controls_after_disconnected_completion(self):
        client = _FakeClient()
        started = asyncio.Event()
        cancellation_seen = threading.Event()
        observed_histories = []
        loop = asyncio.get_running_loop()

        def streamer(prompt, *, history, cancelled):
            observed_histories.append(tuple(dict(item) for item in history))
            if prompt == "primero":
                yield ChatStreamEvent("snapshot", "parcial")
                loop.call_soon_threadsafe(started.set)
                while not cancelled():
                    cancellation_seen.wait(timeout=0.01)
                cancellation_seen.set()
                raise ChatStreamCancelled()

            yield ChatStreamEvent("snapshot", "nuevo turno")
            history.extend(
                (
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "nuevo turno"},
                )
            )

        fake_ui = self._build_page(streamer=streamer, client=client)
        fake_ui.inputs[0].value = "primero"
        first = asyncio.create_task(fake_ui.buttons[1].on_click())
        await asyncio.wait_for(started.wait(), timeout=1)

        client.disconnect()
        cancellation_reached = await asyncio.to_thread(
            cancellation_seen.wait,
            1,
        )
        self.assertTrue(cancellation_reached)
        await asyncio.wait_for(first, timeout=1)
        self.assertFalse(fake_ui.inputs[0].enabled)
        self.assertFalse(fake_ui.buttons[1].enabled)

        client.reconnect()
        self.assertTrue(fake_ui.inputs[0].enabled)
        self.assertTrue(fake_ui.buttons[1].enabled)

        await self._send(fake_ui, "segundo")
        self.assertEqual(observed_histories, [(), ()])
        self.assertEqual(fake_ui.markdowns[1].content, "nuevo turno")


if __name__ == "__main__":
    unittest.main()
