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
    READ_ONLY_WORKFLOW_COMMANDS,
    load_configuration,
    opencode_configuration,
    privacy_configuration,
    validate,
    validate_claude_read_only_agent,
    validate_opencode_agent,
    validate_rule_ownership,
    valid_opencode_expectation,
)
from workflow_lib import PROJECT_PROFILE, managed_source_files  # noqa: E402


class ContextReportTests(unittest.TestCase):
    def test_official_baseline_respects_approved_tolerance(self) -> None:
        config = load_object(REPOSITORY / CONTEXT_PROFILES)
        self.assertEqual(validate_config(REPOSITORY, config), [])
        report = measure(REPOSITORY, config)
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


class PermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        base, project, errors = load_configuration(REPOSITORY)
        if errors:
            raise AssertionError(errors)
        cls.roles, _, role_errors = opencode_configuration(base, project)
        if role_errors:
            raise AssertionError(role_errors)
        cls.privacy_denies, cls.privacy_allows, privacy_errors = (
            privacy_configuration(project)
        )
        if privacy_errors:
            raise AssertionError(privacy_errors)

    def _role_config(self, name: str) -> dict[str, object]:
        config = self.roles[name]
        self.assertIsInstance(config, dict)
        return dict(config)

    def _validate_agent(self, name: str, source: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / f"{name}.md"
            path.write_text(source, encoding="utf-8")
            return validate_opencode_agent(
                path,
                self._role_config(name),
                self.privacy_denies,
                self.privacy_allows,
            )

    def test_planner_denies_shell_by_default_without_workflow_commands(self) -> None:
        config = self._role_config("workflow-planner")
        self.assertEqual(config["edit"], "deny")
        self.assertEqual(config["external_directory"], "deny")
        self.assertEqual(config["shell_default"], "deny")
        self.assertEqual(config["shell_allow"], [])
        source = (REPOSITORY / ".opencode/agents/workflow-planner.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(self._validate_agent("workflow-planner", source), [])

    def test_plan_reviewer_has_only_official_workflow_commands(self) -> None:
        config = self._role_config("workflow-plan-reviewer")
        self.assertEqual(config["shell_allow"], READ_ONLY_WORKFLOW_COMMANDS)
        source = (
            REPOSITORY / ".opencode/agents/workflow-plan-reviewer.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(self._validate_agent("workflow-plan-reviewer", source), [])

    def test_read_only_role_rejects_shell_ask(self) -> None:
        source = (REPOSITORY / ".opencode/agents/workflow-planner.md").read_text(
            encoding="utf-8"
        )
        unsafe = source.replace('    "*": deny', '    "*": ask', 1)
        self.assertIn(
            "read-only OpenCode workflow-planner may not ask for shell pattern: *",
            self._validate_agent("workflow-planner", unsafe),
        )

    def test_read_only_role_rejects_wildcard_shell_allow(self) -> None:
        source = (REPOSITORY / ".opencode/agents/workflow-planner.md").read_text(
            encoding="utf-8"
        )
        unsafe = source.replace(
            '    "git diff --check": allow', '    "git diff *": allow', 1
        )
        self.assertIn(
            "read-only OpenCode workflow-planner has unsafe shell allow pattern: git diff *",
            self._validate_agent("workflow-planner", unsafe),
        )

    def test_read_only_role_rejects_external_directory_approval(self) -> None:
        config = self._role_config("workflow-planner")
        config["external_directory"] = "ask"
        self.assertIn(
            "read-only OpenCode role expectation workflow-planner must deny external_directory",
            valid_opencode_expectation("workflow-planner", config),
        )

    def test_read_only_role_rejects_compileall(self) -> None:
        config = self._role_config("workflow-plan-reviewer")
        config["shell_allow"] = [
            *config["shell_allow"],
            "python -B -m compileall .",
        ]
        self.assertIn(
            "read-only OpenCode role expectation workflow-plan-reviewer may not allow compileall",
            valid_opencode_expectation("workflow-plan-reviewer", config),
        )

    def test_read_only_role_rejects_unapproved_exact_command(self) -> None:
        config = self._role_config("workflow-plan-reviewer")
        config["shell_allow"] = [
            *config["shell_allow"],
            "python -c write_file.py",
        ]
        self.assertIn(
            "read-only OpenCode role expectation workflow-plan-reviewer has unsafe shell command: python -c write_file.py",
            valid_opencode_expectation("workflow-plan-reviewer", config),
        )

    def test_claude_planner_and_reviewer_exclude_mutating_tools_and_bash(self) -> None:
        for role in ("planner", "plan-reviewer"):
            path = REPOSITORY / f".claude/agents/workflow-{role}.md"
            self.assertEqual(validate_claude_read_only_agent(path, role), [])

    def test_claude_read_only_role_rejects_bash(self) -> None:
        source = (REPOSITORY / ".claude/agents/workflow-planner.md").read_text(
            encoding="utf-8"
        )
        unsafe = source.replace("tools: Read, Glob, Grep, Skill", "tools: Read, Glob, Grep, Bash, Skill")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow-planner.md"
            path.write_text(unsafe, encoding="utf-8")
            errors = validate_claude_read_only_agent(path, "planner")
        self.assertIn("Claude planner may not expose Bash", errors)


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

    def test_only_canonical_opencode_workflow_agents_remain(self) -> None:
        agents = REPOSITORY / ".opencode/agents"
        self.assertEqual(
            {path.name for path in agents.glob("*.md")},
            {
                "workflow-auditor.md",
                "workflow-builder.md",
                "workflow-plan-reviewer.md",
                "workflow-planner.md",
            },
        )

    def test_atlas_audit_profile_is_consolidated_in_canonical_agent(self) -> None:
        auditor = (
            REPOSITORY / ".opencode/agents/workflow-auditor.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Audit mode", auditor)
        self.assertIn("## Atlas-specific evidence", auditor)
        self.assertIn("PASS WITH OBSERVATIONS", auditor)
        self.assertNotIn("ACCEPT WITH FOLLOW-UP", auditor)


if __name__ == "__main__":
    unittest.main()
