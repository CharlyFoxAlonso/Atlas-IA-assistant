from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Iterable


BEGIN = "<!-- workflow-2:begin -->"
END = "<!-- workflow-2:end -->"
INSTALL_STATE = Path(".agents/workflow-2/install-state.json")


def template_root() -> Path:
    return Path(__file__).resolve().parents[4]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def git_root(repo: Path) -> Path | None:
    result = run_git(repo, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def git_snapshot(repo: Path) -> dict[str, object]:
    branch = run_git(repo, "branch", "--show-current")
    head = run_git(repo, "rev-parse", "HEAD")
    status = run_git(repo, "status", "--porcelain=v1", "--branch")
    worktrees = run_git(repo, "worktree", "list", "--porcelain")
    status_lines = status.stdout.splitlines()
    changes = [line for line in status_lines if not line.startswith("##")]
    worktree_paths = [
        line.removeprefix("worktree ")
        for line in worktrees.stdout.splitlines()
        if line.startswith("worktree ")
    ]
    return {
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "detached": not bool(branch.stdout.strip()),
        "status": status_lines,
        "changes": changes,
        "dirty": bool(changes),
        "worktrees": worktree_paths,
    }


def decode_preserving(data: bytes) -> tuple[str, str, bool, str]:
    bom = data.startswith(b"\xef\xbb\xbf")
    payload = data[3:] if bom else data
    try:
        text = payload.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        text = payload.decode("cp1252")
        encoding = "cp1252"
    newline = "\r\n" if b"\r\n" in data else "\n"
    return text.replace("\r\n", "\n"), encoding, bom, newline


def encode_preserving(text: str, encoding: str, bom: bool, newline: str) -> bytes:
    normalized = text.replace("\r\n", "\n").replace("\n", newline)
    payload = normalized.encode(encoding)
    return (b"\xef\xbb\xbf" + payload) if bom and encoding == "utf-8" else payload


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".workflow-2.tmp")
    temp.write_bytes(data)
    temp.replace(path)


def extract_managed_block(text: str) -> str:
    start = text.index(BEGIN)
    finish = text.index(END, start) + len(END)
    return text[start:finish]


def merge_managed_block(existing: bytes | None, template: bytes, claude: bool) -> bytes:
    template_text, _, _, _ = decode_preserving(template)
    block = extract_managed_block(template_text)
    if existing is None:
        return template

    text, encoding, bom, newline = decode_preserving(existing)
    if BEGIN in text and END in text:
        start = text.index(BEGIN)
        finish = text.index(END, start) + len(END)
        merged = text[:start] + block + text[finish:]
    else:
        if claude and "@AGENTS.md" in text:
            block = block.replace("@AGENTS.md\n\n", "")
        merged = text.rstrip() + "\n\n" + block + "\n"
    return encode_preserving(merged, encoding, bom, newline)


def managed_source_files(source_root: Path) -> list[Path]:
    candidates: list[Path] = []
    recursive_roots = [
        source_root / ".agents/workflow-2",
        source_root / ".agents/skills/workflow-2",
        source_root / ".claude/skills/workflow-2-claude",
    ]
    for root in recursive_roots:
        if root.exists():
            candidates.extend(path for path in root.rglob("*") if path.is_file())

    glob_roots = [
        (source_root / ".opencode/agents", "workflow-*.md"),
        (source_root / ".opencode/commands", "workflow-*.md"),
        (source_root / ".claude/agents", "workflow-*.md"),
    ]
    for root, pattern in glob_roots:
        if root.exists():
            candidates.extend(root.glob(pattern))

    result = []
    for path in sorted(set(candidates)):
        rel = path.relative_to(source_root)
        if rel == INSTALL_STATE or "__pycache__" in rel.parts or path.suffix == ".pyc":
            continue
        result.append(path)
    return result


def load_install_state(repo: Path) -> dict[str, object]:
    path = repo / INSTALL_STATE
    if not path.exists():
        return {"files": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"files": {}}
    return value if isinstance(value, dict) else {"files": {}}


def relative_hashes(root: Path, files: Iterable[Path]) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in files
    }


def surface_inventory(repo: Path) -> list[dict[str, object]]:
    roots = [
        repo / "AGENTS.md",
        repo / "CLAUDE.md",
        repo / "opencode.json",
        repo / ".agents",
        repo / ".opencode/agents",
        repo / ".opencode/commands",
        repo / ".claude/agents",
        repo / ".claude/rules",
        repo / ".claude/skills",
    ]
    files: set[Path] = set()
    for root in roots:
        if root.is_file():
            files.add(root)
        elif root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() and "node_modules" not in path.parts:
                    files.add(path)
    return [
        {
            "path": path.relative_to(repo).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path)[:12],
        }
        for path in sorted(files)
    ]


def changed_agent_surface(changes: Iterable[str]) -> bool:
    markers = ("AGENTS.md", "CLAUDE.md", ".agents/", ".opencode/", ".claude/")
    return any(any(marker in line.replace("\\", "/") for marker in markers) for line in changes)
