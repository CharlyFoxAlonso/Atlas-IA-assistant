from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from fnmatch import fnmatchcase
from pathlib import Path

from context_report import (
    CONTEXT_PROFILES,
    load_object,
    measure,
    merge_project_profile,
    project_profile_path,
    validate_config,
)
from workflow_lib import BEGIN, END, INSTALL_STATE, sha256_file, template_root


REQUIRED = [
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/workflow-2/version.json",
    ".agents/workflow-2/context-profiles.json",
    ".agents/workflow-2/rule-ownership.json",
    ".agents/workflow-2/core.md",
    ".agents/workflow-2/contracts/handoffs.md",
    ".agents/workflow-2/policies/engineering.md",
    ".agents/workflow-2/policies/testing.md",
    ".agents/workflow-2/policies/git.md",
    ".agents/workflow-2/policies/security.md",
    ".agents/workflow-2/policies/debugging.md",
    ".agents/workflow-2/policies/prototypes.md",
    ".agents/workflow-2/policies/definition-of-done.md",
    ".agents/workflow-2/roles/planner.md",
    ".agents/workflow-2/roles/plan-reviewer.md",
    ".agents/workflow-2/roles/builder.md",
    ".agents/workflow-2/roles/auditor.md",
    ".agents/skills/workflow-2/SKILL.md",
    ".agents/skills/workflow-2/agents/openai.yaml",
    ".agents/skills/workflow-2/scripts/context_report.py",
    ".opencode/agents/workflow-planner.md",
    ".opencode/agents/workflow-plan-reviewer.md",
    ".opencode/agents/workflow-builder.md",
    ".opencode/agents/workflow-auditor.md",
    ".opencode/commands/workflow-plan.md",
    ".opencode/commands/workflow-review-plan.md",
    ".opencode/commands/workflow-build.md",
    ".opencode/commands/workflow-audit.md",
    ".claude/agents/workflow-planner.md",
    ".claude/agents/workflow-plan-reviewer.md",
    ".claude/agents/workflow-builder.md",
    ".claude/agents/workflow-auditor.md",
    ".claude/skills/workflow-2-claude/SKILL.md",
]


COMMON_OPENCODE_PERMISSIONS = {
    "glob": "allow",
    "grep": "allow",
    "list": "allow",
    "lsp": "allow",
    "task": "deny",
    "webfetch": "ask",
    "websearch": "ask",
}

RULE_OWNERSHIP = Path(".agents/workflow-2/rule-ownership.json")
SECTION = re.compile(r"^##\s+(.+?)\s*$")


def frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    return None if end < 0 else text[4:end]


def top_level_value(text: str, key: str) -> str | None:
    block = frontmatter(text)
    if block is None:
        return None
    prefix = f"{key}:"
    for line in block.splitlines():
        if not line.startswith(" ") and line.startswith(prefix):
            return line.split(":", 1)[1].strip().strip('"\'')
    return None


def permission_value(text: str, key: str) -> str | None:
    block = frontmatter(text)
    if block is None:
        return None
    in_permission = False
    prefix = f"{key}:"
    for line in block.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            in_permission = stripped == "permission:"
        elif in_permission and indent == 2 and stripped.startswith(prefix):
            value = stripped.split(":", 1)[1].strip()
            return value.strip('"\'') or None
    return None


def permission_rules(text: str, key: str) -> list[tuple[str, str]]:
    block = frontmatter(text)
    if block is None:
        return []
    rules: list[tuple[str, str]] = []
    in_permission = False
    in_rules = False
    for line in block.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            in_permission = stripped == "permission:"
            in_rules = False
        elif in_permission and indent == 2:
            in_rules = stripped == f"{key}:"
        elif in_permission and in_rules and indent == 4 and ":" in stripped:
            pattern, effect = stripped.rsplit(":", 1)
            rules.append((pattern.strip().strip('"\''), effect.strip().strip('"\'')))
        elif in_rules and indent <= 2:
            in_rules = False
    return rules


def pattern_matches(pattern: str, resource: str) -> bool:
    if pattern.endswith(" *") and resource == pattern[:-2]:
        return True
    return fnmatchcase(resource, pattern)


def effective_permission(rules: list[tuple[str, str]], resource: str) -> str | None:
    result = None
    for pattern, effect in rules:
        if pattern_matches(pattern, resource):
            result = effect
    return result


def validate_opencode_agent(
    path: Path,
    config: dict[str, object],
    privacy_denies: list[str],
    privacy_allows: list[str],
) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    name = path.stem
    expected_permissions = {
        **COMMON_OPENCODE_PERMISSIONS,
        "edit": str(config["edit"]),
        "external_directory": str(config["external_directory"]),
    }
    for key, expected in expected_permissions.items():
        if permission_value(text, key) != expected:
            errors.append(f"OpenCode {name} must set {key}: {expected}")

    skill_rules = permission_rules(text, "skill")
    if effective_permission(skill_rules, "unrelated-skill") != "ask":
        errors.append(f"OpenCode {name} must ask before loading unrelated skills")
    skills = config.get("skills")
    if not isinstance(skills, list):
        errors.append(f"OpenCode {name} has an invalid expected skill configuration")
    else:
        for skill in skills:
            if (str(skill), "allow") not in skill_rules:
                errors.append(f"OpenCode {name} must explicitly allow skill {skill}")

    shell_default = str(config["shell_default"])
    if permission_value(text, "bash") != shell_default:
        errors.append(f"OpenCode {name} must default shell commands to {shell_default}")
    read_rules = permission_rules(text, "read")
    if effective_permission(read_rules, "ordinary.md") != "allow":
        errors.append(f"OpenCode {name} must allow ordinary repository reads")
    for pattern in privacy_denies:
        if effective_permission(read_rules, pattern) != "deny":
            errors.append(f"OpenCode {name} must deny private read pattern: {pattern}")
    for pattern in privacy_allows:
        if effective_permission(read_rules, pattern) != "allow":
            errors.append(f"OpenCode {name} must allow safe read pattern: {pattern}")
    return errors


def valid_opencode_expectation(name: str, config: object) -> list[str]:
    if not isinstance(config, dict):
        return [f"OpenCode role expectation {name} must be an object"]
    errors: list[str] = []
    for key in ("edit", "external_directory", "shell_default"):
        if config.get(key) not in {"allow", "ask", "deny"}:
            errors.append(f"OpenCode role expectation {name}.{key} is invalid")
    skills = config.get("skills")
    if not isinstance(skills, list) or not all(isinstance(skill, str) for skill in skills):
        errors.append(f"OpenCode role expectation {name}.skills must be strings")
    return errors


def validate_opencode_commands(root: Path, commands: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for name, expectation in commands.items():
        if not isinstance(expectation, dict):
            errors.append(f"OpenCode command expectation {name} must be an object")
            continue
        agent = expectation.get("agent")
        subtask = expectation.get("subtask")
        if not isinstance(agent, str) or (
            subtask is not None and not isinstance(subtask, str)
        ):
            errors.append(f"OpenCode command expectation {name} is invalid")
            continue
        path = root / f".opencode/commands/{name}.md"
        if not path.is_file():
            errors.append(f"missing configured OpenCode command: {name}")
            continue
        text = path.read_text(encoding="utf-8")
        if top_level_value(text, "agent") != agent:
            errors.append(f"OpenCode command {name} must use agent {agent}")
        if subtask is not None and top_level_value(text, "subtask") != subtask:
            errors.append(f"OpenCode command {name} must set subtask: {subtask}")
    return errors


def load_configuration(
    root: Path,
) -> tuple[dict[str, object], dict[str, object], list[str]]:
    errors: list[str] = []
    try:
        base = load_object(root / CONTEXT_PROFILES)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {}, {}, [f"invalid context profiles: {exc}"]

    project: dict[str, object] = {}
    try:
        candidate = project_profile_path(root, base)
    except ValueError as exc:
        errors.append(f"invalid project workflow profile path: {exc}")
        candidate = root / "__invalid_project_profile__"
    if candidate.is_file():
        try:
            project = load_object(candidate)
            base = merge_project_profile(base, project)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"invalid project workflow profile: {exc}")
    errors.extend(validate_config(root, base))
    return base, project, errors


def opencode_configuration(
    base: dict[str, object], project: dict[str, object]
) -> tuple[dict[str, object], dict[str, object], list[str]]:
    errors: list[str] = []
    opencode = base.get("opencode")
    if not isinstance(opencode, dict):
        return {}, {}, ["context profiles must define opencode expectations"]
    roles = opencode.get("roles")
    commands = opencode.get("commands")
    if not isinstance(roles, dict) or not isinstance(commands, dict):
        return {}, {}, ["opencode roles and commands must be objects"]

    merged_roles = dict(roles)
    project_opencode = project.get("opencode", {})
    if not isinstance(project_opencode, dict):
        errors.append("project profile opencode must be an object")
    else:
        project_roles = project_opencode.get("roles", {})
        if not isinstance(project_roles, dict):
            errors.append("project profile opencode.roles must be an object")
        else:
            merged_roles.update(project_roles)

    return merged_roles, commands, errors


def privacy_configuration(
    project: dict[str, object],
) -> tuple[list[str], list[str], list[str]]:
    errors: list[str] = []
    opencode = project.get("opencode", {})
    if not isinstance(opencode, dict):
        return [], [], ["project profile opencode must be an object"]
    values: list[list[str]] = []
    for key in ("privacy_read_denies", "privacy_read_allows"):
        configured = opencode.get(key)
        if not isinstance(configured, list) or not configured or not all(
            isinstance(item, str) and item for item in configured
        ):
            errors.append(f"project profile opencode.{key} must contain patterns")
            values.append([])
        else:
            values.append(configured)
    return values[0], values[1], errors


def markdown_rule_sections(
    path: Path, relative: str, duplicate_headings: list[str] | None = None
) -> set[str]:
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    sections: set[str] = set()
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end >= 0:
            sections.add(f"{relative}#frontmatter")
            text = text[end + 5 :]

    headings: list[str] = []
    current = "@document"
    has_content = False
    fenced = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = SECTION.match(line)
        if match:
            if has_content:
                sections.add(f"{relative}#{current}")
            current = match.group(1)
            headings.append(current)
            has_content = False
            continue
        if (
            stripped
            and not stripped.startswith("# ")
            and not (stripped.startswith("<!--") and stripped.endswith("-->"))
        ):
            has_content = True
    if has_content:
        sections.add(f"{relative}#{current}")
    if duplicate_headings is not None:
        duplicate_headings.extend(
            heading for heading, count in Counter(headings).items() if count > 1
        )
    return sections


def scan_markdown_files(root: Path, relative: str) -> tuple[list[Path], str | None]:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return [], f"rule ownership scan path must stay in repository: {relative}"
    path = root / candidate
    if path.is_file():
        return [path], None
    if path.is_dir():
        files = sorted(
            item
            for item in path.rglob("*")
            if item.is_file() and item.suffix.lower() == ".md"
        )
        return files, None
    return [], f"rule ownership scan root is missing: {relative}"


def validate_rule_ownership(
    root: Path, ownership: dict[str, object] | None = None
) -> list[str]:
    errors: list[str] = []
    try:
        config = ownership if ownership is not None else load_object(root / RULE_OWNERSHIP)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [f"invalid rule ownership: {exc}"]

    if config.get("schema") != 1:
        errors.append("rule ownership schema must be 1")
    scan_roots = config.get("scan_roots")
    rules = config.get("rules")
    if not isinstance(scan_roots, list):
        return [*errors, "rule ownership scan_roots must be a list"]
    if not isinstance(rules, list):
        return [*errors, "rule ownership rules must be a list"]

    discovered: set[str] = set()
    discovered_files: set[str] = set()
    for scan_root in scan_roots:
        if not isinstance(scan_root, dict):
            errors.append("rule ownership scan roots must be objects")
            continue
        relative = scan_root.get("path")
        scope = scan_root.get("scope")
        if not isinstance(relative, str) or not relative:
            errors.append("rule ownership scan root has an invalid path")
            continue
        if scope not in {"canonical", "project"}:
            errors.append(f"rule ownership scan root has invalid scope: {relative}")
        paths, scan_error = scan_markdown_files(root, relative)
        if scan_error:
            errors.append(scan_error)
            continue
        for path in paths:
            file_relative = path.relative_to(root).as_posix()
            if file_relative in discovered_files:
                continue
            discovered_files.add(file_relative)
            duplicate_headings: list[str] = []
            discovered.update(
                markdown_rule_sections(path, file_relative, duplicate_headings)
            )
            for heading in sorted(duplicate_headings):
                errors.append(f"duplicate heading in {file_relative}: {heading}")

    ids: list[str] = []
    owners: list[str] = []
    for item in rules:
        if not isinstance(item, dict):
            errors.append("rule ownership entries must be objects")
            continue
        rule_id = item.get("id")
        owner = item.get("owner")
        rule = item.get("rule")
        scope = item.get("scope")
        file = item.get("file")
        section = item.get("section")
        if not isinstance(rule_id, str) or not rule_id:
            errors.append("rule ownership entry has an invalid id")
        else:
            ids.append(rule_id)
        if not isinstance(rule, str) or not rule:
            errors.append(f"rule ownership {rule_id} has an invalid rule")
        if scope not in {"canonical", "project"}:
            errors.append(f"rule ownership {rule_id} has an invalid scope")
        if not isinstance(file, str) or not file:
            errors.append(f"rule ownership {rule_id} has an invalid file")
        elif Path(file).is_absolute() or ".." in Path(file).parts:
            errors.append(f"rule ownership file must stay in repository: {file}")
        if not isinstance(section, str) or not section:
            errors.append(f"rule ownership {rule_id} has an invalid section")
        if not isinstance(owner, str) or not owner:
            errors.append(f"rule ownership {rule_id} has an invalid owner")
        else:
            owners.append(owner)
            if isinstance(file, str) and isinstance(section, str):
                expected_owner = f"{file}#{section}"
                if owner != expected_owner:
                    errors.append(
                        f"rule ownership {rule_id} owner must be {expected_owner}"
                    )

    for rule_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"rule has multiple owners: {rule_id}")
    for owner, count in Counter(owners).items():
        if count > 1:
            errors.append(f"rule owner is assigned more than once: {owner}")
    for owner in sorted(set(owners) - discovered):
        errors.append(f"rule ownership reference is broken: {owner}")
    for owner in sorted(discovered - set(owners)):
        errors.append(f"rule section has no owner: {owner}")
    return errors


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    if errors:
        return errors

    workflow_config, project_config, config_errors = load_configuration(root)
    errors.extend(config_errors)
    if not config_errors:
        context_report = measure(root, workflow_config)
        for role, result in context_report.items():
            if int(result["characters"]) > int(result["no_growth_limit_characters"]):
                errors.append(f"context profile {role} exceeds its no-growth limit")
    opencode_roles, opencode_commands, opencode_errors = opencode_configuration(
        workflow_config, project_config
    )
    errors.extend(opencode_errors)
    privacy_denies, privacy_allows, privacy_errors = privacy_configuration(
        project_config
    )
    errors.extend(privacy_errors)
    errors.extend(validate_rule_ownership(root))

    agents = (root / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")
    if BEGIN not in agents or END not in agents:
        errors.append("AGENTS.md is missing the managed routing block")
    if BEGIN not in claude or END not in claude or "@AGENTS.md" not in claude:
        errors.append("CLAUDE.md must import AGENTS.md inside or alongside its managed block")

    version_path = root / ".agents/workflow-2/version.json"
    version_value: str | None = None
    try:
        version = json.loads(version_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid version.json: {exc}")
    else:
        if version.get("name") != "workflow-2" or not version.get("version"):
            errors.append("version.json has an invalid name or version")
        else:
            version_value = str(version["version"])

    if version_value is not None:
        expected_marker = f"<!-- workflow-2:managed version={version_value} -->"
        managed_root = root / ".agents/workflow-2"
        for path in sorted(managed_root.rglob("*.md")):
            first_line = path.read_text(encoding="utf-8-sig").splitlines()[0]
            if first_line != expected_marker:
                relative = path.relative_to(root).as_posix()
                errors.append(f"managed version marker is inconsistent: {relative}")

    skill = (root / ".agents/skills/workflow-2/SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: workflow-2\n"):
        errors.append("canonical SKILL.md has invalid frontmatter")
    if "TODO" in skill:
        errors.append("canonical SKILL.md still contains TODO placeholders")

    for name, config in opencode_roles.items():
        expectation_errors = valid_opencode_expectation(name, config)
        errors.extend(expectation_errors)
        if expectation_errors:
            continue
        assert isinstance(config, dict)
        path = root / f".opencode/agents/{name}.md"
        if not path.is_file():
            errors.append(f"missing configured OpenCode agent: {name}")
            continue
        errors.extend(
            validate_opencode_agent(path, config, privacy_denies, privacy_allows)
        )

    errors.extend(validate_opencode_commands(root, opencode_commands))

    for role in ("planner", "plan-reviewer", "auditor"):
        claude_role = (root / f".claude/agents/workflow-{role}.md").read_text(encoding="utf-8")
        if "permissionMode: plan" not in claude_role or "disallowedTools:" not in claude_role:
            errors.append(f"Claude {role} must be read-only")

    if "Edit" not in (root / ".claude/agents/workflow-builder.md").read_text(encoding="utf-8"):
        errors.append("Claude Builder must include Edit")

    state_path = root / INSTALL_STATE
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid install-state.json: {exc}")
        else:
            files = state.get("files", {})
            if isinstance(files, dict):
                for rel, expected in files.items():
                    path = root / rel
                    if not path.exists():
                        errors.append(f"installed managed file is missing: {rel}")
                    elif sha256_file(path) != expected:
                        errors.append(f"installed managed file was modified locally: {rel}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Workflow 2.0 template or installation."
    )
    parser.add_argument("repository", nargs="?", type=Path, default=template_root())
    args = parser.parse_args()
    root = args.repository.resolve()
    errors = validate(root)
    if errors:
        print("Workflow 2.0 validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Workflow 2.0 validation passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
