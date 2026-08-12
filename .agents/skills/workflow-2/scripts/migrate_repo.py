from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from workflow_lib import (
    INSTALL_STATE,
    atomic_write_bytes,
    git_root,
    git_snapshot,
    load_install_state,
    managed_source_files,
    merge_managed_block,
    relative_hashes,
    sha256_bytes,
    sha256_file,
    template_root,
)


@dataclass(frozen=True)
class Action:
    kind: str
    relative: str
    source: Path | None = None
    content: bytes | None = None


def plan(source_root: Path, target: Path) -> tuple[list[Action], list[str]]:
    state = load_install_state(target)
    installed_hashes = state.get("files", {})
    if not isinstance(installed_hashes, dict):
        installed_hashes = {}

    actions: list[Action] = []
    conflicts: list[str] = []
    for source in managed_source_files(source_root):
        rel = source.relative_to(source_root).as_posix()
        destination = target / Path(rel)
        if not destination.exists():
            actions.append(Action("CREATE", rel, source=source))
        elif sha256_file(destination) == sha256_file(source):
            actions.append(Action("KEEP", rel, source=source))
        elif installed_hashes.get(rel) == sha256_file(destination):
            actions.append(Action("UPDATE", rel, source=source))
        else:
            actions.append(Action("CONFLICT", rel, source=source))
            conflicts.append(rel)

    for name, claude in (("AGENTS.md", False), ("CLAUDE.md", True)):
        destination = target / name
        template = (source_root / name).read_bytes()
        existing = destination.read_bytes() if destination.exists() else None
        merged = merge_managed_block(existing, template, claude=claude)
        if existing == merged:
            actions.append(Action("KEEP", name, content=merged))
        else:
            actions.append(Action("UPDATE" if existing is not None else "CREATE", name, content=merged))
    return actions, conflicts


def apply(source_root: Path, target: Path, actions: list[Action]) -> None:
    for action in actions:
        if action.kind not in {"CREATE", "UPDATE"}:
            continue
        destination = target / Path(action.relative)
        data = action.content if action.content is not None else action.source.read_bytes()
        atomic_write_bytes(destination, data)

    source_files = managed_source_files(source_root)
    version = json.loads((source_root / ".agents/workflow-2/version.json").read_text(encoding="utf-8"))
    state = {
        "name": "workflow-2",
        "version": version["version"],
        "files": relative_hashes(source_root, source_files),
        "routing_blocks": {
            "AGENTS.md": sha256_bytes((target / "AGENTS.md").read_bytes()),
            "CLAUDE.md": sha256_bytes((target / "CLAUDE.md").read_bytes()),
        },
    }
    atomic_write_bytes(
        target / INSTALL_STATE,
        (json.dumps(state, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or apply a conservative Workflow 2.1 migration.")
    parser.add_argument("repository", type=Path)
    parser.add_argument("--source", type=Path, default=template_root())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    root = git_root(args.repository)
    if root is None:
        print("ERROR: target is not inside a Git repository.")
        return 2
    source_root = args.source.resolve()
    if not (source_root / ".agents/workflow-2/version.json").exists():
        print("ERROR: source does not contain a Workflow 2.1 template.")
        return 2

    actions, conflicts = plan(source_root, root)
    snapshot = git_snapshot(root)
    print(f"Repository: {root}")
    print(f"Mode: {'APPLY' if args.apply else 'PLAN'}")
    print(f"Dirty: {snapshot['dirty']}")
    for action in actions:
        print(f"{action.kind:8} {action.relative}")

    if conflicts:
        print("ERROR: locally modified managed files require manual resolution:")
        for conflict in conflicts:
            print(f"- {conflict}")
        return 4
    if not args.apply:
        return 0
    if snapshot["dirty"] and not args.allow_dirty:
        print("ERROR: refusing to apply to a dirty working tree. Review first or pass --allow-dirty explicitly.")
        return 3

    apply(source_root, root, actions)
    print("Applied Workflow 2.1. Run validate_workflow.py and review the complete Git diff.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
