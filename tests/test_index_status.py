import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core.index_status import (
    IndexStatusView,
    consultar_estado_indice,
    consultar_estado_indice_si_solicitado,
    format_index_status_lines,
    presentar_resultado_sincronizacion,
)


ISSUE_MESSAGES = {
    "chroma_collection_read_failed": "Chroma collection could not be read.",
    "consistency_verification_failed": (
        "Consistency verification encountered an internal error."
    ),
}
ALLOWED_DIVERGENCES = {
    "manifest_absent",
    "source_absent_chroma_present",
    "verification_limitation",
}


def _report(
    state="HEALTHY",
    *,
    observed=None,
    writer_known=True,
    writer_active=False,
    transient=False,
    divergences=None,
    issues=(),
):
    return SimpleNamespace(
        published_state=state,
        observed_state=observed or state,
        writer_state_known=writer_known,
        writer_active=writer_active,
        possibly_transient=transient,
        sources_count=2,
        manifest_entries_count=2,
        chunk_count=5,
        divergences=dict(divergences or {}),
        orphan_count=1,
        orphan_sample=("private/document.md:chunk:0",),
        path_error=r"C:\Users\private\vector_db",
        issues=tuple(issues),
    )


def _query(report=None, *, error=None, **kwargs):
    verifier = Mock(return_value=report)
    if error is not None:
        verifier.side_effect = error
    contract = (verifier, frozenset(ALLOWED_DIVERGENCES), ISSUE_MESSAGES)
    patcher = patch(
        "core.index_status._load_consistency_contract",
        return_value=contract,
    )
    return verifier, patcher, kwargs


class IndexStatusProjectionTests(unittest.TestCase):
    def test_preserves_all_five_states_without_reclassification(self):
        expected = {
            "HEALTHY": (True, "success"),
            "HEALTHY_EMPTY": (True, "success"),
            "DEGRADED": (False, "warning"),
            "INCONSISTENT": (False, "warning"),
            "UNAVAILABLE": (False, "error"),
        }

        for state, (healthy, severity) in expected.items():
            with self.subTest(state=state):
                verifier, patcher, _ = _query(_report(state))
                with patcher:
                    status = consultar_estado_indice()
                self.assertEqual(status.state, state)
                self.assertEqual(status.observed_state, state)
                self.assertEqual(status.healthy, healthy)
                self.assertEqual(status.severity, severity)
                verifier.assert_called_once_with()

    def test_published_state_is_primary_and_observed_state_is_preserved(self):
        verifier, patcher, _ = _query(
            _report(
                "DEGRADED",
                observed="HEALTHY",
                writer_known=True,
                writer_active=True,
                transient=True,
            )
        )
        with patcher:
            status = consultar_estado_indice()

        self.assertEqual(status.state, "DEGRADED")
        self.assertEqual(status.observed_state, "HEALTHY")
        self.assertEqual(status.writer_state, "active")
        self.assertTrue(status.possibly_transient)
        verifier.assert_called_once_with()

    def test_writer_state_active_inactive_and_unknown(self):
        cases = (
            (True, True, "active"),
            (True, False, "inactive"),
            (False, False, "unknown"),
        )
        for known, active, expected in cases:
            with self.subTest(expected=expected):
                verifier, patcher, _ = _query(
                    _report(
                        "DEGRADED" if expected != "inactive" else "HEALTHY",
                        writer_known=known,
                        writer_active=active,
                        transient=expected != "inactive",
                    )
                )
                with patcher:
                    status = consultar_estado_indice()
                self.assertEqual(status.writer_state, expected)
                verifier.assert_called_once_with()

    def test_projection_filters_private_fields_unknown_keys_and_raw_errors(self):
        raw_secret = r"C:\Users\delfa\private\document.md token-secret"
        verifier, patcher, _ = _query(
            _report(
                "UNAVAILABLE",
                divergences={
                    "manifest_absent": 1,
                    raw_secret: 9,
                },
                issues=(
                    f"chroma_collection_read_failed: {raw_secret} [RuntimeError]",
                    f"unknown_issue: {raw_secret}",
                ),
            )
        )
        with patcher:
            status = consultar_estado_indice()

        serialized = json.dumps(status.to_dict())
        self.assertNotIn(raw_secret, serialized)
        self.assertNotIn("orphan_sample", serialized)
        self.assertNotIn("path_error", serialized)
        self.assertEqual(status.divergences, {"manifest_absent": 1})
        self.assertEqual(
            [issue.code for issue in status.issues],
            ["chroma_collection_read_failed", "consistency_verification_failed"],
        )
        verifier.assert_called_once_with()

    def test_unexpected_failure_is_safe_unavailable_with_unknown_counts(self):
        raw_secret = r"C:\Users\delfa\private\document.md token-secret"
        verifier, patcher, _ = _query(error=RuntimeError(raw_secret))
        with patcher:
            status = consultar_estado_indice()

        serialized = json.dumps(status.to_dict())
        self.assertEqual(status.state, "UNAVAILABLE")
        self.assertIsNone(status.sources_count)
        self.assertIsNone(status.manifest_entries_count)
        self.assertIsNone(status.chunk_count)
        self.assertNotIn(raw_secret, serialized)
        self.assertEqual(
            [issue.code for issue in status.issues],
            ["consistency_verification_failed"],
        )
        verifier.assert_called_once_with()

    def test_path_overrides_are_forwarded_only_to_idx_c1(self):
        verifier, patcher, _ = _query(_report())
        with patcher:
            consultar_estado_indice(
                memoria_base="synthetic-memory",
                manifest_path="synthetic-manifest",
                chroma_path="synthetic-chroma",
                lock_path="synthetic-lock",
            )
        verifier.assert_called_once_with(
            memoria_base="synthetic-memory",
            manifest_path="synthetic-manifest",
            chroma_path="synthetic-chroma",
            lock_path="synthetic-lock",
        )

    def test_formatted_lines_use_only_the_safe_projection(self):
        status = IndexStatusView.unavailable()
        rendered = "\n".join(format_index_status_lines(status))
        self.assertIn("UNAVAILABLE", rendered)
        self.assertIn("desconocido", rendered)
        self.assertNotIn("Traceback", rendered)


class ExplicitActionTests(unittest.TestCase):
    def test_false_action_never_calls_the_diagnosis(self):
        provider = Mock()
        result = consultar_estado_indice_si_solicitado(False, provider=provider)
        self.assertIsNone(result)
        provider.assert_not_called()

    def test_true_action_calls_the_diagnosis_once(self):
        expected = IndexStatusView.unavailable()
        provider = Mock(return_value=expected)
        result = consultar_estado_indice_si_solicitado(True, provider=provider)
        self.assertIs(result, expected)
        provider.assert_called_once_with()


class SyncPresentationTests(unittest.TestCase):
    def test_busy_is_explicit_and_never_reads_zero_counters(self):
        class BusyResult:
            busy = True

            def __getattr__(self, name):
                raise AssertionError(f"busy must not inspect {name}")

        presentation = presentar_resultado_sincronizacion(BusyResult())
        self.assertTrue(presentation.busy)
        self.assertIn("busy", presentation.message.lower())
        self.assertNotIn("Escaneados", presentation.message)

    def test_non_busy_keeps_the_aggregate_counts(self):
        result = SimpleNamespace(
            busy=False,
            scanned=5,
            indexed_new=1,
            reindexed_modified=2,
            skipped_unchanged=1,
            removed_deleted=1,
            failed=0,
            duration_seconds=0.25,
        )
        presentation = presentar_resultado_sincronizacion(result)
        self.assertFalse(presentation.busy)
        self.assertIn("Escaneados: 5", presentation.message)
        self.assertIn("Fallidos: 0", presentation.message)


if __name__ == "__main__":
    unittest.main()
