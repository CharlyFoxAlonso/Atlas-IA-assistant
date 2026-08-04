import json
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import psutil

from core.index_writer_lock import (
    IndexWriterBusyError,
    IndexWriterLock,
    acquire_index_writer_lock,
    derive_lock_path_for_manifest,
    inspect_index_writer_state,
)


def _queue_get(queue, timeout=10):
    return queue.get(timeout=timeout)


def _worker_hold_lock(lock_path, ready, release, out):
    try:
        with acquire_index_writer_lock(lock_path=lock_path):
            out.put(("acquired", None, None))
            ready.set()
            release.wait(10)
    except IndexWriterBusyError as error:
        out.put(("busy", error.code, error.public_message))
    except Exception as error:
        out.put(("error", type(error).__name__, str(error)))


def _worker_try_lock(lock_path, out):
    try:
        with acquire_index_writer_lock(lock_path=lock_path):
            out.put(("acquired", None, None))
    except IndexWriterBusyError as error:
        out.put(("busy", error.code, error.public_message))
    except Exception as error:
        out.put(("error", type(error).__name__, str(error)))


def _worker_die_with_lock(lock_path):
    with acquire_index_writer_lock(lock_path=lock_path):
        os._exit(0)


def _write_metadata(lock_path, *, pid=None, create_time=None, token="token"):
    process = psutil.Process(os.getpid())
    payload = {
        "schema_version": 1,
        "pid": os.getpid() if pid is None else pid,
        "process_create_time": (
            float(process.create_time()) if create_time is None else create_time
        ),
        "token": token,
        "created_at_utc": "2026-08-04T00:00:00+00:00",
    }
    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    Path(lock_path).write_text(json.dumps(payload), encoding="utf-8")
    return payload


class IndexWriterLockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock_path = self.root / "index_writer.lock"

    def test_two_real_processes_compete_fail_fast(self):
        ctx = multiprocessing.get_context("spawn")
        ready = ctx.Event()
        release = ctx.Event()
        out = ctx.Queue()
        holder = ctx.Process(
            target=_worker_hold_lock,
            args=(str(self.lock_path), ready, release, out),
        )
        holder.start()
        try:
            self.assertTrue(ready.wait(10))
            self.assertEqual(_queue_get(out)[0], "acquired")

            contender_out = ctx.Queue()
            contender = ctx.Process(
                target=_worker_try_lock,
                args=(str(self.lock_path), contender_out),
            )
            contender.start()
            contender.join(10)
            self.assertFalse(contender.is_alive())
            self.assertEqual(
                _queue_get(contender_out),
                (
                    "busy",
                    "index_writer_busy",
                    "Index writer is busy; another indexing operation is active.",
                ),
            )
        finally:
            release.set()
            holder.join(10)
            if holder.is_alive():
                holder.terminate()
                holder.join(10)

    def test_same_resolved_path_reenters(self):
        with acquire_index_writer_lock(lock_path=self.lock_path) as first:
            with acquire_index_writer_lock(lock_path=self.lock_path.resolve()) as second:
                self.assertEqual(first.lock_path, second.lock_path)
                self.assertTrue(self.lock_path.exists())
        self.assertFalse(self.lock_path.exists())

    def test_different_path_in_same_context_fails_safe(self):
        other = self.root / "other.lock"
        with acquire_index_writer_lock(lock_path=self.lock_path):
            with self.assertRaises(IndexWriterBusyError) as raised:
                with acquire_index_writer_lock(lock_path=other):
                    pass
        self.assertEqual(raised.exception.code, "lock_path_mismatch")
        self.assertFalse(other.exists())

    def test_dead_owner_is_recovered_once(self):
        ctx = multiprocessing.get_context("spawn")
        owner = ctx.Process(target=_worker_die_with_lock, args=(str(self.lock_path),))
        owner.start()
        owner.join(10)
        self.assertFalse(owner.is_alive())
        self.assertTrue(self.lock_path.exists())

        with acquire_index_writer_lock(lock_path=self.lock_path):
            self.assertTrue(self.lock_path.exists())
        self.assertFalse(self.lock_path.exists())

    def test_active_owner_is_not_recovered(self):
        ctx = multiprocessing.get_context("spawn")
        ready = ctx.Event()
        release = ctx.Event()
        out = ctx.Queue()
        holder = ctx.Process(
            target=_worker_hold_lock,
            args=(str(self.lock_path), ready, release, out),
        )
        holder.start()
        try:
            self.assertTrue(ready.wait(10))
            self.assertEqual(_queue_get(out)[0], "acquired")
            with self.assertRaises(IndexWriterBusyError) as raised:
                with acquire_index_writer_lock(lock_path=self.lock_path):
                    pass
            self.assertEqual(raised.exception.code, "index_writer_busy")
        finally:
            release.set()
            holder.join(10)
            if holder.is_alive():
                holder.terminate()
                holder.join(10)

    def test_pid_reuse_is_not_recovered(self):
        process = psutil.Process(os.getpid())
        _write_metadata(
            self.lock_path,
            pid=os.getpid(),
            create_time=float(process.create_time()) + 1000.0,
        )
        with self.assertRaises(IndexWriterBusyError):
            with acquire_index_writer_lock(lock_path=self.lock_path):
                pass
        self.assertTrue(self.lock_path.exists())

    def test_ambiguous_owner_state_is_not_recovered(self):
        _write_metadata(self.lock_path)
        real_process = psutil.Process
        calls = {"count": 0}

        def fake_process(pid):
            calls["count"] += 1
            if calls["count"] == 1:
                return real_process(pid)
            raise psutil.AccessDenied(pid=pid)

        with mock.patch("core.index_writer_lock.psutil.Process", side_effect=fake_process):
            with self.assertRaises(IndexWriterBusyError):
                with acquire_index_writer_lock(lock_path=self.lock_path):
                    pass
        self.assertTrue(self.lock_path.exists())

    def test_partial_or_corrupt_metadata_is_not_recovered(self):
        self.lock_path.write_text("{", encoding="utf-8")
        with self.assertRaises(IndexWriterBusyError) as corrupt:
            with acquire_index_writer_lock(lock_path=self.lock_path):
                pass
        self.assertEqual(corrupt.exception.code, "index_writer_state_ambiguous")

        self.lock_path.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
        with self.assertRaises(IndexWriterBusyError) as partial:
            with acquire_index_writer_lock(lock_path=self.lock_path):
                pass
        self.assertEqual(partial.exception.code, "index_writer_state_ambiguous")

    def test_non_owner_does_not_release(self):
        with acquire_index_writer_lock(lock_path=self.lock_path):
            payload = json.loads(self.lock_path.read_text(encoding="utf-8"))
            payload["token"] = "different-owner"
            self.lock_path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertTrue(self.lock_path.exists())

    def test_exception_releases_lock(self):
        with self.assertRaises(RuntimeError):
            with acquire_index_writer_lock(lock_path=self.lock_path):
                raise RuntimeError("synthetic")
        self.assertFalse(self.lock_path.exists())

    def test_temporary_persistences_are_independent(self):
        ctx = multiprocessing.get_context("spawn")
        first_manifest = self.root / "a" / "vector_db" / "index_manifest.json"
        second_manifest = self.root / "b" / "vector_db" / "index_manifest.json"
        first_lock = derive_lock_path_for_manifest(first_manifest)
        second_lock = derive_lock_path_for_manifest(second_manifest)
        self.assertNotEqual(first_lock, second_lock)

        ready_a = ctx.Event()
        ready_b = ctx.Event()
        release = ctx.Event()
        out = ctx.Queue()
        first = ctx.Process(
            target=_worker_hold_lock,
            args=(str(first_lock), ready_a, release, out),
        )
        second = ctx.Process(
            target=_worker_hold_lock,
            args=(str(second_lock), ready_b, release, out),
        )
        first.start()
        second.start()
        try:
            self.assertTrue(ready_a.wait(10))
            self.assertTrue(ready_b.wait(10))
            statuses = {_queue_get(out)[0], _queue_get(out)[0]}
            self.assertEqual(statuses, {"acquired"})
        finally:
            release.set()
            first.join(10)
            second.join(10)
            for process in (first, second):
                if process.is_alive():
                    process.terminate()
                    process.join(10)

    def test_inspect_is_read_only_and_reports_absent_lock(self):
        state = inspect_index_writer_state(lock_path=self.lock_path)
        self.assertTrue(state.writer_state_known)
        self.assertFalse(state.writer_active)
        self.assertFalse(state.possibly_transient)
        self.assertFalse(self.lock_path.exists())


if __name__ == "__main__":
    unittest.main()
