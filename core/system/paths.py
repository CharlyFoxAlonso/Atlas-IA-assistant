"""Central path policy for development and future packaged Atlas builds.

This module only calculates paths. It never creates, moves, or deletes data.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional


@dataclass(frozen=True)
class AtlasPaths:
    mode: str
    program_dir: Path
    project_root: Path
    data_dir: Path
    private_memory_dir: Path
    chroma_dir: Path
    config_dir: Path
    cache_dir: Path
    logs_dir: Path
    downloads_dir: Path
    temp_dir: Path
    managed_bin_dir: Path
    models_dir: Path

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in vars(self).items()}


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def _env_path(env: Mapping[str, str], name: str, fallback: Path) -> Path:
    value = env.get(name)
    return Path(value).expanduser().resolve() if value else fallback.resolve()


def get_paths(
    *,
    packaged: Optional[bool] = None,
    executable: Optional[Path] = None,
    environment: Optional[Mapping[str, str]] = None,
) -> AtlasPaths:
    """Return the path layout without touching the filesystem.

    ``ATLAS_DATA_DIR`` and ``ATLAS_MEMORY_DIR`` are explicit migration-safe
    overrides. Development keeps using the repository's existing data layout.
    """
    env = environment if environment is not None else os.environ
    frozen = is_packaged() if packaged is None else packaged
    module_root = Path(__file__).resolve().parents[2]
    exe = Path(executable or sys.executable).resolve()

    if not frozen:
        project_root = module_root
        program_dir = project_root
        data_dir = _env_path(env, "ATLAS_DATA_DIR", project_root)
        memory_dir = _env_path(env, "ATLAS_MEMORY_DIR", data_dir / "memory" / "Atlas_Memory")
        config_dir = project_root
        cache_dir = data_dir / "cache"
        logs_dir = data_dir / "logs"
        chroma_dir = data_dir / "vector_db"
    else:
        program_dir = exe.parent
        project_root = program_dir
        local_app_data = Path(env.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        roaming_app_data = Path(env.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        data_dir = _env_path(env, "ATLAS_DATA_DIR", local_app_data / "Atlas")
        # Private memory stays outside program files and can later be user-selected.
        memory_dir = _env_path(env, "ATLAS_MEMORY_DIR", data_dir / "memory")
        config_dir = roaming_app_data / "Atlas"
        cache_dir = data_dir / "cache"
        logs_dir = data_dir / "logs"
        chroma_dir = data_dir / "vector_db"

    return AtlasPaths(
        mode="packaged" if frozen else "development",
        program_dir=program_dir,
        project_root=project_root,
        data_dir=data_dir,
        private_memory_dir=memory_dir,
        chroma_dir=chroma_dir,
        config_dir=config_dir.resolve(),
        cache_dir=cache_dir,
        logs_dir=logs_dir,
        downloads_dir=data_dir / "downloads",
        temp_dir=data_dir / "temp",
        managed_bin_dir=data_dir / "bin",
        models_dir=data_dir / "models",
    )
