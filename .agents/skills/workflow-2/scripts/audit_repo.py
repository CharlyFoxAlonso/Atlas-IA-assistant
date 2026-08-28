from __future__ import annotations

import argparse
import json
from pathlib import Path

from workflow_lib import (
    BEGIN,
    changed_agent_surface,
    git_root,
    git_snapshot,
    surface_inventory,
)


def audit(path: Path) -> dict[str, object]:
    root = git_root(path)
    if root is None:
        return {
            "repository": str(path.resolve()),
            "decision": "INVALID",
            "reasons": ["The path is not inside a Git repository."],
        }

    git = git_snapshot(root)
    surfaces = surface_inventory(root)
    reasons: list[str] = []
    decision = "READY"

    if git["detached"]:
        decision = "DEFER"
        reasons.append("HEAD is detached; verify that this is not a temporary worktree.")
    if changed_agent_surface(git["changes"]):
        decision = "DEFER"
        reasons.append("Agent configuration already has uncommitted changes.")
    elif len(git["changes"]) > 5:
        decision = "DEFER"
        reasons.append("The working tree has broad active changes.")
    elif git["dirty"] and decision == "READY":
        decision = "MANUAL_REVIEW"
        reasons.append("The working tree is dirty; verify non-overlap before applying.")
    if len(git["worktrees"]) > 1 and decision == "READY":
        decision = "MANUAL_REVIEW"
        reasons.append("Multiple worktrees exist; confirm the primary checkout and branch.")
    if len(surfaces) >= 12 and decision == "READY":
        decision = "MANUAL_REVIEW"
        reasons.append("The repository has a rich existing agent setup that needs preservation review.")
    if not reasons:
        reasons.append("No blocking migration condition was detected.")

    agents_path = root / "AGENTS.md"
    claude_path = root / "CLAUDE.md"
    return {
        "repository": str(root),
        "decision": decision,
        "reasons": reasons,
        "git": git,
        "surfaces": surfaces,
        "workflow_2": {
            "agents_routing": agents_path.exists() and BEGIN in agents_path.read_text(encoding="utf-8", errors="replace"),
            "claude_routing": claude_path.exists() and BEGIN in claude_path.read_text(encoding="utf-8", errors="replace"),
            "installed": (root / ".agents/workflow-2/version.json").exists(),
        },
    }


def markdown(report: dict[str, object]) -> str:
    lines = [
        f"# Repository audit: `{report['repository']}`",
        "",
        f"Decision: **{report['decision']}**",
        "",
    ]
    for reason in report.get("reasons", []):
        lines.append(f"- {reason}")
    git = report.get("git")
    if isinstance(git, dict):
        lines.extend(
            [
                "",
                f"- Branch: `{git.get('branch') or '(detached)'}`",
                f"- HEAD: `{git.get('head', '')}`",
                f"- Dirty: `{git.get('dirty', False)}`",
                f"- Worktrees: `{len(git.get('worktrees', []))}`",
                f"- Agent surfaces: `{len(report.get('surfaces', []))}`",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a repository before Workflow 2.1 migration.")
    parser.add_argument("repository", type=Path)
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    report = audit(args.repository)
    print(markdown(report) if args.markdown else json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["decision"] != "INVALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
