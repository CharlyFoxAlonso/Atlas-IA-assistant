from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_lib import BEGIN, END, INSTALL_STATE, sha256_file, template_root


REQUIRED = [
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/workflow-2/version.json",
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
    ".opencode/agents/workflow-planner.md",
    ".opencode/agents/workflow-plan-reviewer.md",
    ".opencode/agents/workflow-builder.md",
    ".opencode/agents/workflow-auditor.md",
    ".claude/agents/workflow-planner.md",
    ".claude/agents/workflow-plan-reviewer.md",
    ".claude/agents/workflow-builder.md",
    ".claude/agents/workflow-auditor.md",
    ".claude/skills/workflow-2-claude/SKILL.md",
]


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")

    if errors:
        return errors

    agents = (root / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    claude = (root / "CLAUDE.md").read_text(encoding="utf-8", errors="replace")
    if BEGIN not in agents or END not in agents:
        errors.append("AGENTS.md is missing the managed routing block")
    if BEGIN not in claude or END not in claude or "@AGENTS.md" not in claude:
        errors.append("CLAUDE.md must import AGENTS.md inside or alongside its managed block")

    version_path = root / ".agents/workflow-2/version.json"
    try:
        version = json.loads(version_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid version.json: {exc}")
    else:
        if version.get("name") != "workflow-2" or not version.get("version"):
            errors.append("version.json has an invalid name or version")

    skill = (root / ".agents/skills/workflow-2/SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: workflow-2\n"):
        errors.append("canonical SKILL.md has invalid frontmatter")
    if "TODO" in skill:
        errors.append("canonical SKILL.md still contains TODO placeholders")

    for role in ("planner", "plan-reviewer", "auditor"):
        open_role = (root / f".opencode/agents/workflow-{role}.md").read_text(encoding="utf-8")
        if "edit: deny" not in open_role:
            errors.append(f"OpenCode {role} must deny edits")
        claude_role = (root / f".claude/agents/workflow-{role}.md").read_text(encoding="utf-8")
        if "permissionMode: plan" not in claude_role or "disallowedTools:" not in claude_role:
            errors.append(f"Claude {role} must be read-only")

    if "edit: allow" not in (root / ".opencode/agents/workflow-builder.md").read_text(encoding="utf-8"):
        errors.append("OpenCode Builder must allow edits")
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
    parser = argparse.ArgumentParser(description="Validate a Workflow 2.0 template or installation.")
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
