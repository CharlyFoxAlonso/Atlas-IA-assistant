import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from core.index_repair import RepairItem, RepairReport
from core.index_status import IndexIssueView, IndexStatusView
from core.system.healer import ALL_COMPONENTS, HEAVY_COMPONENTS, SAFE_COMPONENTS, Healer
from core.system.paths import AtlasPaths
from core.system.result_types import CommandResult, RepairResult


def make_paths(root: Path, mode: str = "development") -> AtlasPaths:
    return AtlasPaths(
        mode=mode,
        program_dir=root / "program",
        project_root=root,
        data_dir=root / "data",
        private_memory_dir=root / "memory",
        chroma_dir=root / "vector_db",
        config_dir=root / "config",
        cache_dir=root / "cache",
        logs_dir=root / "logs",
        downloads_dir=root / "downloads",
        temp_dir=root / "temp",
        managed_bin_dir=root / "bin",
        models_dir=root / "models",
    )


def diagnosis(**ollama_overrides):
    ollama = {
        "installed": False,
        "executable": None,
        "service_available": False,
        "selected_model": "qwen3:8b",
        "selected_model_available": False,
    }
    ollama.update(ollama_overrides)
    return {"health_score": 50, "python": {"in_venv": False}, "ollama": ollama}


def index_status(state="INCONSISTENT"):
    labels = {
        "HEALTHY": "Saludable",
        "HEALTHY_EMPTY": "Saludable y vacío",
        "DEGRADED": "Degradado",
        "INCONSISTENT": "Inconsistente",
        "UNAVAILABLE": "No disponible",
    }
    return IndexStatusView(
        state=state,
        state_label=labels[state],
        observed_state=state,
        observed_state_label=labels[state],
        healthy=state in {"HEALTHY", "HEALTHY_EMPTY"},
        severity="success" if state in {"HEALTHY", "HEALTHY_EMPTY"} else "warning",
        writer_state="inactive",
        writer_label="Inactivo",
        possibly_transient=state == "DEGRADED",
        sources_count=2,
        manifest_entries_count=1,
        chunk_count=3,
        divergences=(
            {"source_present_manifest_absent_chroma_absent": 1}
            if state == "INCONSISTENT"
            else {}
        ),
        orphan_count=1,
        issues=(IndexIssueView("manifest_absent", "Index manifest is absent."),),
    )


def repair_report(
    *,
    post_state="HEALTHY",
    post_observed="HEALTHY",
    post_check_performed=True,
    blocked=False,
    blocked_reason=None,
    busy=False,
    busy_message=None,
    items=(),
    orphan_count=0,
    orphan_sample=(),
):
    return RepairReport(
        pre_state="INCONSISTENT",
        post_state=post_state,
        post_observed=post_observed,
        post_check_performed=post_check_performed,
        success=True,
        blocked=blocked,
        blocked_reason=blocked_reason,
        busy=busy,
        busy_message=busy_message,
        items=items,
        orphan_count=orphan_count,
        orphan_sample=orphan_sample,
    )


class HealerTests(unittest.TestCase):
    def setUp(self):
        self._log_patcher = patch("core.system.healer.write_operational_event")
        self.operational_log = self._log_patcher.start()

    def tearDown(self):
        self._log_patcher.stop()

    def test_default_is_dry_run_and_does_not_create_folders(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            result = Healer(diagnosis(), paths=paths).fix("folders")
            self.assertTrue(result.dry_run)
            self.assertFalse(result.changed)
            self.assertFalse(paths.data_dir.exists())

    def test_folder_repair_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            healer = Healer(diagnosis(), dry_run=False, paths=paths, diagnostician=lambda **_: diagnosis())
            first = healer.fix("folders")
            second = healer.fix("folders")
            self.assertTrue(first.changed)
            self.assertFalse(second.changed)
            self.assertTrue(second.success)

    def test_existing_config_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            paths.config_dir.mkdir(parents=True)
            env_file = paths.config_dir / ".env"
            env_file.write_text("NVIDIA_API_KEY=keep-me\n", encoding="utf-8")
            result = Healer(diagnosis(), dry_run=False, paths=paths).fix("config")
            self.assertFalse(result.changed)
            self.assertEqual(env_file.read_text(encoding="utf-8"), "NVIDIA_API_KEY=keep-me\n")

    def test_new_config_contains_no_api_key_placeholder(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = make_paths(Path(temp))
            result = Healer(diagnosis(), dry_run=False, paths=paths, diagnostician=lambda **_: diagnosis()).fix("config")
            content = (paths.config_dir / ".env").read_text(encoding="utf-8")
            self.assertTrue(result.success)
            self.assertNotIn("API_KEY", content)
            self.assertNotIn("#ATLAS_", content)

    def test_heavy_action_requires_explicit_consent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements.txt").write_text("requests>=2\n", encoding="utf-8")
            runner = Mock()
            result = Healer(
                diagnosis(), dry_run=False, allow_heavy=False, paths=make_paths(root, "packaged"), command_runner=runner
            ).fix("python_packages")
            self.assertFalse(result.success)
            self.assertEqual(result.actions[0]["reason"], "consent_required")
            runner.assert_not_called()

    def test_requirements_install_checks_return_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requirements.txt").write_text("requests>=2\n", encoding="utf-8")
            runner = Mock(return_value=CommandResult(["pip"], 2, stderr="failed"))
            result = Healer(
                diagnosis(),
                dry_run=False,
                allow_heavy=True,
                paths=make_paths(root, "packaged"),
                command_runner=runner,
                diagnostician=lambda **_: diagnosis(),
            ).fix("python_packages")
            self.assertFalse(result.success)
            self.assertIn("failed", result.errors)

    def test_model_pull_is_not_repeated_when_present(self):
        runner = Mock()
        result = Healer(
            diagnosis(
                installed=True,
                executable="ollama",
                service_available=True,
                selected_model_available=True,
            ),
            dry_run=False,
            allow_heavy=True,
            command_runner=runner,
        ).fix("ollama_model")
        self.assertTrue(result.success)
        self.assertFalse(result.changed)
        runner.assert_not_called()

    def test_fix_all_isolates_partial_failure(self):
        healer = Healer(diagnosis())
        with self.assertLogs("core.system.healer", level="ERROR"), patch.object(
            healer,
            "fix",
            side_effect=[RuntimeError("boom"), healer.fix_config(), healer.verify_venv(), healer.fix_ollama_service()],
        ):
            report = healer.fix_all()
        self.assertFalse(report["success"])
        self.assertEqual(len(report["results"]), 4)
        self.assertIn("RuntimeError", report["results"][0]["errors"][0])

    def test_index_preview_is_read_only_and_skips_doctor(self):
        status_provider = Mock(return_value=index_status())
        repairer = Mock()
        diagnostician = Mock(side_effect=AssertionError("Doctor must not run"))
        healer = Healer(
            diagnosis={},
            diagnostician=diagnostician,
            index_status_provider=status_provider,
            index_repairer=repairer,
        )

        with patch("core.index_writer_lock.acquire_index_writer_lock") as acquire_lock:
            result = healer.fix("index_consistency")

        self.assertTrue(result.success)
        self.assertTrue(result.dry_run)
        self.assertFalse(result.changed)
        self.assertEqual(result.risk, "moderate")
        self.assertEqual(result.actions[0]["status"], "planned")
        self.assertEqual(result.actions[0]["index_status"]["state"], "INCONSISTENT")
        self.assertIsNone(result.diagnosis_before)
        self.assertIsNone(result.diagnosis_after)
        status_provider.assert_called_once_with()
        repairer.assert_not_called()
        diagnostician.assert_not_called()
        acquire_lock.assert_not_called()
        self.operational_log.assert_not_called()

    def test_index_preview_state_matrix(self):
        expectations = {
            "HEALTHY": (True, "not_needed"),
            "HEALTHY_EMPTY": (True, "not_needed"),
            "INCONSISTENT": (True, "planned"),
            "DEGRADED": (False, "blocked"),
            "UNAVAILABLE": (False, "blocked"),
        }
        for state, expected in expectations.items():
            with self.subTest(state=state):
                result = Healer(
                    diagnosis={},
                    index_status_provider=Mock(return_value=index_status(state)),
                    index_repairer=Mock(),
                ).fix("index_consistency")
                self.assertEqual((result.success, result.actions[0]["status"]), expected)
                self.assertFalse(result.changed)

    def test_index_apply_projects_success_without_private_identifiers(self):
        report = repair_report(
            items=(
                RepairItem(
                    identity=r"C:\\Users\\private\\secret-notes.pdf",
                    category="source_present_manifest_absent_chroma_absent",
                    action="reindex",
                    status="repaired",
                ),
            ),
            orphan_count=2,
            orphan_sample=(r"C:\\Users\\private\\orphan.pdf",),
        )
        repairer = Mock(return_value=report)
        status_provider = Mock()
        result = Healer(
            diagnosis={},
            dry_run=False,
            index_status_provider=status_provider,
            index_repairer=repairer,
        ).fix("index_consistency")

        payload = json.dumps(result.to_dict())
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(result.risk, "moderate")
        self.assertEqual(result.actions[0]["status"], "completed")
        self.assertEqual(result.actions[0]["orphan_count"], 2)
        self.assertNotIn("identity", payload)
        self.assertNotIn("orphan_sample", payload)
        self.assertNotIn("secret-notes", payload)
        self.assertNotIn("orphan.pdf", payload)
        self.assertIsNone(result.diagnosis_before)
        self.assertIsNone(result.diagnosis_after)
        repairer.assert_called_once_with()
        status_provider.assert_not_called()

    def test_index_apply_classifies_non_success_outcomes(self):
        cases = {
            "busy": repair_report(
                post_state="UNAVAILABLE",
                post_observed="UNAVAILABLE",
                post_check_performed=False,
                busy=True,
                busy_message="Index writer is busy; another indexing operation is active.",
            ),
            "blocked": repair_report(
                post_state="UNAVAILABLE",
                post_observed="UNAVAILABLE",
                blocked=True,
                blocked_reason="manifest_corrupt",
            ),
            "partial": repair_report(
                post_state="INCONSISTENT",
                post_observed="INCONSISTENT",
                items=(
                    RepairItem("a", "manifest_absent", "reindex", "repaired"),
                    RepairItem("b", "manifest_absent", "reindex", "failed", "RuntimeError"),
                ),
            ),
            "failed": repair_report(
                post_state="INCONSISTENT",
                post_observed="INCONSISTENT",
                items=(RepairItem("a", "manifest_absent", "reindex", "failed", "ValueError"),),
            ),
            "still_inconsistent": repair_report(
                post_state="INCONSISTENT",
                post_observed="INCONSISTENT",
                items=(RepairItem("a", "manifest_absent", "reindex", "still_inconsistent"),),
            ),
        }
        for expected_status, report in cases.items():
            with self.subTest(expected_status=expected_status):
                result = Healer(
                    diagnosis={},
                    dry_run=False,
                    index_repairer=Mock(return_value=report),
                ).fix("index_consistency")
                self.assertFalse(result.success)
                self.assertEqual(result.actions[0]["status"], expected_status)

    def test_index_provider_failure_is_controlled_and_path_free(self):
        private_message = r"C:\\Users\\private\\vector_db failed"
        result = Healer(
            diagnosis={},
            index_status_provider=Mock(side_effect=RuntimeError(private_message)),
            index_repairer=Mock(),
        ).fix("index_consistency")

        payload = json.dumps(result.to_dict())
        self.assertFalse(result.success)
        self.assertEqual(result.actions[0]["status"], "unavailable")
        self.assertEqual(result.errors, ["RuntimeError"])
        self.assertNotIn(private_message, payload)
        self.assertNotIn("private", payload)

    def test_index_apply_failure_and_invalid_contract_are_controlled(self):
        private_message = r"C:\\Users\\private\\manifest.json failed"
        cases = (
            Mock(side_effect=OSError(private_message)),
            Mock(return_value={"success": True, "identity": private_message}),
        )
        for repairer in cases:
            with self.subTest(repairer=repairer):
                result = Healer(
                    diagnosis={},
                    dry_run=False,
                    index_repairer=repairer,
                ).fix("index_consistency")
                payload = json.dumps(result.to_dict())
                self.assertFalse(result.success)
                self.assertEqual(result.actions[0]["status"], "unavailable")
                self.assertNotIn(private_message, payload)
                self.assertNotIn("manifest.json", payload)

    def test_index_apply_rejects_semantically_invalid_final_reports(self):
        cases = {
            "attempted_after_post_check": repair_report(
                items=(
                    RepairItem("a", "manifest_absent", "reindex", "attempted"),
                ),
            ),
            "busy_with_post_check": repair_report(
                post_state="UNAVAILABLE",
                post_observed="UNAVAILABLE",
                post_check_performed=True,
                busy=True,
                busy_message="Index writer is busy; another indexing operation is active.",
            ),
            "busy_with_items": repair_report(
                post_state="UNAVAILABLE",
                post_observed="UNAVAILABLE",
                post_check_performed=False,
                busy=True,
                busy_message="Index writer is busy; another indexing operation is active.",
                items=(RepairItem("a", "manifest_absent", "skip", "skipped"),),
            ),
            "non_busy_without_post_check": repair_report(
                post_state="UNAVAILABLE",
                post_observed="UNAVAILABLE",
                post_check_performed=False,
            ),
            "blocked_with_items": repair_report(
                post_state="UNAVAILABLE",
                post_observed="UNAVAILABLE",
                blocked=True,
                blocked_reason="manifest_corrupt",
                items=(RepairItem("a", "manifest_absent", "skip", "skipped"),),
            ),
            "busy_and_blocked": repair_report(
                post_state="UNAVAILABLE",
                post_observed="UNAVAILABLE",
                post_check_performed=False,
                blocked=True,
                blocked_reason="unavailable",
                busy=True,
                busy_message="Index writer is busy; another indexing operation is active.",
            ),
        }
        for case, report in cases.items():
            with self.subTest(case=case):
                result = Healer(
                    diagnosis={},
                    dry_run=False,
                    index_repairer=Mock(return_value=report),
                ).fix("index_consistency")
                self.assertFalse(result.success)
                self.assertFalse(result.changed)
                self.assertEqual(result.actions[0]["status"], "unavailable")

    def test_index_projection_falls_back_to_allowlisted_public_values(self):
        report = repair_report(
            post_state="UNAVAILABLE",
            post_observed="UNAVAILABLE",
            blocked=True,
            blocked_reason=r"C:\\Users\\private\\blocked",
        )
        result = Healer(
            diagnosis={},
            dry_run=False,
            index_repairer=Mock(return_value=report),
        ).fix("index_consistency")

        self.assertEqual(result.actions[0]["blocked_reason"], "unavailable")
        self.assertNotIn("private", json.dumps(result.to_dict()))

    def test_index_component_is_explicit_and_excluded_from_automatic_repairs(self):
        repairer = Mock()
        healer = Healer(diagnosis(), index_repairer=repairer)
        with patch.object(
            healer,
            "fix",
            side_effect=lambda component: RepairResult(
                component=component,
                success=True,
                dry_run=True,
            ),
        ) as fixer:
            healer.fix_all(include_heavy=True)

        called_components = [call.args[0] for call in fixer.call_args_list]
        self.assertIn("index_consistency", ALL_COMPONENTS)
        self.assertNotIn("index_consistency", SAFE_COMPONENTS)
        self.assertNotIn("index_consistency", HEAVY_COMPONENTS)
        self.assertNotIn("index_consistency", called_components)
        repairer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
