from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY / ".agents/skills/workflow-2/scripts"
sys.path.insert(0, str(SCRIPTS))

from context_report import (  # noqa: E402
    CONTEXT_PROFILES,
    check_report,
    load_object,
    measure,
    merge_project_profile,
    normalized_characters,
    parse_roles,
    select_roles,
    validate_config,
)
from validate_workflow import (  # noqa: E402
    opencode_configuration,
    privacy_configuration,
    validate,
    validate_rule_ownership,
)
from workflow_lib import PROJECT_PROFILE, managed_source_files  # noqa: E402


class ContextReportTests(unittest.TestCase):
    def test_official_baseline_matches_approved_plan(self) -> None:
        config = load_object(REPOSITORY / CONTEXT_PROFILES)
        self.assertEqual(validate_config(REPOSITORY, config), [])
        report = measure(REPOSITORY, config)
        self.assertEqual(
            {role: result["characters"] for role, result in report.items()},
            {
                "auditor": 43858,
                "builder": 45511,
                "plan_reviewer": 42352,
                "planner": 41880,
            },
        )
        self.assertEqual(
            check_report(
                config, report, verify_baseline=True, enforce_target=False
            ),
            [],
        )

    def test_role_alias_and_selection(self) -> None:
        config = load_object(REPOSITORY / CONTEXT_PROFILES)
        roles = parse_roles("planner,plan-reviewer,builder,auditor")
        selected = select_roles(config, roles)
        self.assertEqual(
            list(selected["profiles"]),
            ["planner", "plan_reviewer", "builder", "auditor"],
        )

    def test_measurement_removes_bom_and_normalizes_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.md"
            path.write_bytes(b"\xef\xbb\xbfA\r\nB\rC")
            self.assertEqual(normalized_characters(path), 5)

    def test_project_profile_extends_roles_without_changing_context(self) -> None:
        base = load_object(REPOSITORY / CONTEXT_PROFILES)
        project = load_object(REPOSITORY / PROJECT_PROFILE)
        merged = merge_project_profile(base, project)
        self.assertEqual(merged["profiles"], base["profiles"])
        roles, commands, errors = opencode_configuration(merged, project)
        self.assertEqual(errors, [])
        self.assertEqual(set(roles), set(base["opencode"]["roles"]))
        self.assertEqual(set(commands), set(base["opencode"]["commands"]))
        denies, allows, privacy_errors = privacy_configuration(project)
        self.assertEqual(privacy_errors, [])
        self.assertIn("memory/**", denies)
        self.assertIn("*.env.example", allows)

    def test_context_paths_cannot_escape_repository(self) -> None:
        config = load_object(REPOSITORY / CONTEXT_PROFILES)
        config["profiles"]["planner"]["files"].append("../outside.md")
        errors = validate_config(REPOSITORY, config)
        self.assertIn(
            "context profile planner path must stay in repository: ../outside.md",
            errors,
        )


class OwnershipTests(unittest.TestCase):
    def test_current_rule_ownership_has_full_coverage(self) -> None:
        self.assertEqual(validate_rule_ownership(REPOSITORY), [])

    def test_duplicate_rule_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rules.md").write_text(
                "# Rules\n\n## One\n\nFirst.\n\n## Two\n\nSecond.\n",
                encoding="utf-8",
            )
            ownership = {
                "schema": 1,
                "scan_roots": [{"path": "rules.md", "scope": "project"}],
                "rules": [
                    {
                        "id": "same",
                        "rule": "One",
                        "owner": "rules.md#One",
                        "scope": "project",
                        "file": "rules.md",
                        "section": "One",
                    },
                    {
                        "id": "same",
                        "rule": "Two",
                        "owner": "rules.md#Two",
                        "scope": "project",
                        "file": "rules.md",
                        "section": "Two",
                    },
                ],
            }
            self.assertIn(
                "rule has multiple owners: same",
                validate_rule_ownership(root, ownership),
            )

    def test_broken_unowned_and_escaping_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rules.md").write_text(
                "# Rules\n\n## Existing\n\nRule.\n", encoding="utf-8"
            )
            ownership = {
                "schema": 1,
                "scan_roots": [{"path": "rules.md", "scope": "project"}],
                "rules": [
                    {
                        "id": "broken",
                        "rule": "Broken",
                        "owner": "rules.md#Missing",
                        "scope": "project",
                        "file": "rules.md",
                        "section": "Missing",
                    },
                    {
                        "id": "escape",
                        "rule": "Escape",
                        "owner": "../outside.md#Rule",
                        "scope": "project",
                        "file": "../outside.md",
                        "section": "Rule",
                    },
                ],
            }
            errors = validate_rule_ownership(root, ownership)
            self.assertIn(
                "rule ownership reference is broken: rules.md#Missing", errors
            )
            self.assertIn("rule section has no owner: rules.md#Existing", errors)
            self.assertIn(
                "rule ownership file must stay in repository: ../outside.md",
                errors,
            )

    def test_duplicate_heading_outside_fence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rules.md").write_text(
                "# Rules\n\n## Same\n\nFirst.\n\n## Same\n\nSecond.\n",
                encoding="utf-8",
            )
            ownership = {
                "schema": 1,
                "scan_roots": [{"path": "rules.md", "scope": "project"}],
                "rules": [
                    {
                        "id": "same",
                        "rule": "Same",
                        "owner": "rules.md#Same",
                        "scope": "project",
                        "file": "rules.md",
                        "section": "Same",
                    }
                ],
            }
            self.assertIn(
                "duplicate heading in rules.md: Same",
                validate_rule_ownership(root, ownership),
            )


class IntegrationTests(unittest.TestCase):
    def test_atlas_project_artifacts_exist(self) -> None:
        self.assertTrue((REPOSITORY / PROJECT_PROFILE).is_file())
        self.assertTrue((REPOSITORY / "tests/test_workflow_2.py").is_file())

    def test_current_repository_passes_end_to_end(self) -> None:
        self.assertEqual(validate(REPOSITORY), [])

    def test_project_profile_is_not_a_managed_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / ".agents/workflow-2/core.md"
            canonical.parent.mkdir(parents=True)
            canonical.write_text("core", encoding="utf-8")
            project = root / PROJECT_PROFILE
            project.write_text(json.dumps({"schema": 1}), encoding="utf-8")
            managed = {
                path.relative_to(root).as_posix()
                for path in managed_source_files(root)
            }
            self.assertIn(".agents/workflow-2/core.md", managed)
            self.assertNotIn(PROJECT_PROFILE.as_posix(), managed)


if __name__ == "__main__":
    unittest.main()
