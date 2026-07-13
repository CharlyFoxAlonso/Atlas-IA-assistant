"""Serializable result contracts for Atlas system operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class SerializableResult:
    """Small shared helper that keeps public results JSON-friendly."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CheckResult(SerializableResult):
    name: str
    status: str
    severity: str
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: Optional[str] = None


@dataclass
class DiagnosisResult(SerializableResult):
    atlas_version: str
    timestamp: str
    health_score: int
    ready_to_start: bool
    execution_mode: str
    data_location: str
    executable_location: str
    checks: List[CheckResult] = field(default_factory=list)
    capabilities: Dict[str, bool] = field(default_factory=dict)
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class RepairResult(SerializableResult):
    component: str
    success: bool
    changed: bool = False
    dry_run: bool = False
    risk: str = "safe"
    message: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    diagnosis_before: Optional[Dict[str, Any]] = None
    diagnosis_after: Optional[Dict[str, Any]] = None


@dataclass
class LaunchResult(SerializableResult):
    success: bool
    started: bool = False
    dry_run: bool = False
    message: str = ""
    pid: Optional[int] = None
    diagnosis: Optional[Dict[str, Any]] = None
    repairs: List[Dict[str, Any]] = field(default_factory=list)
    command: Optional[Dict[str, Any]] = None


@dataclass
class CommandResult(SerializableResult):
    args: List[str]
    returncode: Optional[int]
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    timed_out: bool = False
    started: bool = True
    pid: Optional[int] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.started and not self.timed_out and self.returncode == 0


@dataclass
class DownloadResult(SerializableResult):
    url: str
    destination: str
    success: bool
    bytes_downloaded: int = 0
    sha256: Optional[str] = None
    hash_verified: bool = False
    duration_seconds: float = 0.0
    error: Optional[str] = None
