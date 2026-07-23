"""Read-only system diagnosis for Atlas.

The public API returns JSON-serializable dictionaries and never repairs,
downloads, creates directories, or prints output.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from core.system.command_runner import run_command
from core.system.paths import AtlasPaths, get_paths
from core.system.result_types import CheckResult, DiagnosisResult

# Doctor must also work before Atlas dependencies (including python-dotenv) exist.
# Keep these dependency-free defaults aligned with core.config until a manifest
# becomes the single source of product metadata.
VERSION = "4.1.0"
MODELO_LOCAL = os.getenv("MODELO_LOCAL", "qwen3:8b")
URL_OLLAMA = os.getenv("URL_OLLAMA", "http://127.0.0.1:11434/api/chat")


PACKAGE_SPECS = {
    "streamlit": {"import": "streamlit", "severity": "critical"},
    "fastapi": {"import": "fastapi", "severity": "optional"},
    "uvicorn": {"import": "uvicorn", "severity": "optional"},
    "requests": {"import": "requests", "severity": "critical"},
    "dotenv": {"import": "dotenv", "distribution": "python-dotenv", "severity": "critical"},
    "openai": {"import": "openai", "severity": "critical"},
    "chromadb": {"import": "chromadb", "severity": "recommended"},
    "sentence_transformers": {
        "import": "sentence_transformers",
        "distribution": "sentence-transformers",
        "severity": "recommended",
    },
    "torch": {"import": "torch", "severity": "recommended"},
    "pypdf": {"import": "pypdf", "severity": "optional"},
    "pdf2image": {"import": "pdf2image", "severity": "optional"},
    "pytesseract": {"import": "pytesseract", "severity": "optional"},
    "PIL": {"import": "PIL", "distribution": "Pillow", "severity": "optional"},
    "vosk": {"import": "vosk", "severity": "optional"},
    "speech_recognition": {
        "import": "speech_recognition",
        "distribution": "SpeechRecognition",
        "severity": "optional",
    },
    "pyttsx3": {"import": "pyttsx3", "severity": "optional"},
    "edge_tts": {"import": "edge_tts", "distribution": "edge-tts", "severity": "optional"},
    "pyautogui": {"import": "pyautogui", "severity": "optional"},
    "duckduckgo_search": {
        "import": "duckduckgo_search",
        "distribution": "duckduckgo-search",
        "severity": "optional",
    },
    "groq": {"import": "groq", "severity": "optional"},
}

EXTERNAL_TOOLS = {
    "tesseract": {"command": "tesseract", "severity": "optional"},
    "poppler": {"command": "pdftoppm", "severity": "optional"},
    "ffmpeg": {"command": "ffmpeg", "severity": "optional"},
    "git": {"command": "git", "severity": "optional", "developer_only": True},
}

ENV_KEYS = ("NVIDIA_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY")
MIN_FREE_DISK_GB = 2.0
# Temporary compatibility exports for the existing Healer. Phase F will remove
# its dependency on Doctor internals in favor of the public result contract.
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
PYTHON_PACKAGES = list(PACKAGE_SPECS)
ATLAS_FOLDERS = ["memory", "backups", "logs", "cache", "chats", "chromadb"]


def _check(name: str, ok: bool, severity: str, message: str, **details: Any) -> CheckResult:
    return CheckResult(
        name=name,
        status="ok" if ok else "missing",
        severity=severity,
        message=message,
        details=details,
    )


def _detect_os() -> dict[str, Any]:
    return {
        "name": platform.system(),
        "version": platform.version(),
        "release": platform.release(),
        "architecture": platform.machine(),
    }


def _detect_python() -> dict[str, Any]:
    in_venv = sys.prefix != sys.base_prefix
    supported = (3, 11) <= sys.version_info[:2] <= (3, 13)
    return {
        "version": platform.python_version(),
        "executable": sys.executable,
        "in_venv": in_venv,
        "venv_path": sys.prefix if in_venv else None,
        "supported_version": supported,
    }


def _detect_cpu() -> dict[str, Any]:
    return {"model": platform.processor() or None, "logical_cores": os.cpu_count()}


def _detect_ram() -> dict[str, Optional[float]]:
    try:
        import psutil

        return {"total_gb": round(psutil.virtual_memory().total / (1024**3), 1)}
    except Exception:
        return {"total_gb": None}


def _detect_disk(path: Path) -> dict[str, Optional[float]]:
    try:
        usage = shutil.disk_usage(path)
        return {
            "free_gb": round(usage.free / (1024**3), 1),
            "total_gb": round(usage.total / (1024**3), 1),
        }
    except OSError:
        return {"free_gb": None, "total_gb": None}


def _detect_gpu() -> dict[str, Any]:
    executable = shutil.which("nvidia-smi")
    base = {
        "installed": executable is not None,
        "path": executable,
        "functional": False,
        "name": None,
        "vram_mb": None,
        "driver": None,
    }
    if not executable:
        return base
    result = run_command(
        [executable, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
        timeout=10,
    )
    if not result.success or not result.stdout.strip():
        base["error"] = result.error or result.stderr.strip() or "nvidia-smi failed"
        return base
    parts = [part.strip() for part in result.stdout.splitlines()[0].split(",")]
    try:
        vram_mb = int(float(parts[1]))
    except (IndexError, ValueError):
        vram_mb = None
    base.update(
        functional=True,
        name=parts[0] if parts else None,
        vram_mb=vram_mb,
        driver=parts[2] if len(parts) > 2 else None,
    )
    return base


def _ollama_tags_url() -> str:
    configured = URL_OLLAMA.rstrip("/")
    if "/api/" in configured:
        configured = configured.split("/api/", 1)[0]
    return configured + "/api/tags"


def _detect_ollama() -> dict[str, Any]:
    executable = shutil.which("ollama")
    result: dict[str, Any] = {
        "installed": executable is not None,
        "in_path": executable is not None,
        "executable": executable,
        "executable_works": False,
        "service_available": False,
        "functional": False,
        "models": [],
        "selected_model": MODELO_LOCAL,
        "selected_model_available": False,
    }
    if executable:
        version = run_command([executable, "--version"], timeout=10)
        result["executable_works"] = version.success
        result["version"] = version.stdout.strip() if version.success else None

    try:
        request = Request(_ollama_tags_url(), headers={"Accept": "application/json"})
        with urlopen(request, timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        models = [item.get("name") for item in payload.get("models", []) if item.get("name")]
        result["service_available"] = True
        result["models"] = models
        result["selected_model_available"] = MODELO_LOCAL in models
    except (OSError, URLError, ValueError, json.JSONDecodeError) as exc:
        result["service_error"] = type(exc).__name__

    result["functional"] = bool(result["service_available"] and result["selected_model_available"])
    return result


def _detect_python_packages(validate_imports: Optional[set[str]] = None) -> dict[str, dict[str, Any]]:
    packages: dict[str, dict[str, Any]] = {}
    selected = validate_imports or set()
    for key, spec in PACKAGE_SPECS.items():
        available = importlib.util.find_spec(spec["import"]) is not None
        importable: Optional[bool] = None
        import_error: Optional[str] = None
        if available and key in selected:
            command = run_command(
                [
                    sys.executable,
                    "-c",
                    "import importlib,sys; importlib.import_module(sys.argv[1])",
                    spec["import"],
                ],
                timeout=20,
            )
            importable = command.success
            if not command.success:
                stderr_lines = command.stderr.strip().splitlines()
                import_error = command.error or (stderr_lines[-1] if stderr_lines else "import failed")
        packages[key] = {
            "available": available,
            "found": available,
            "importable": importable,
            "functional": importable if importable is not None else None,
            "status": "missing" if not available else ("broken" if importable is False else ("importable" if importable else "found")),
            "import_name": spec["import"],
            "distribution": spec.get("distribution", spec["import"]),
            "severity": spec["severity"],
            "error": import_error,
        }
    return packages


def _detect_external_tools() -> dict[str, dict[str, Any]]:
    tools: dict[str, dict[str, Any]] = {}
    for name, spec in EXTERNAL_TOOLS.items():
        executable = shutil.which(spec["command"])
        tools[name] = {
            "installed": executable is not None,
            "in_path": executable is not None,
            "path": executable,
            "severity": spec["severity"],
            "developer_only": spec.get("developer_only", False),
        }
    return tools


def _read_env_presence(paths: AtlasPaths, environment: Mapping[str, str]) -> dict[str, bool]:
    present = {key: bool(environment.get(key, "").strip()) for key in ENV_KEYS}
    env_file = paths.project_root / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return present
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key in present and value and not value.startswith("#ATLAS_"):
            present[key] = True
    return present


def _detect_folders(paths: AtlasPaths) -> dict[str, dict[str, Any]]:
    expected = {
        "program": paths.program_dir,
        "data": paths.data_dir,
        "memory": paths.private_memory_dir,
        "chromadb": paths.chroma_dir,
        "config": paths.config_dir,
        "cache": paths.cache_dir,
        "logs": paths.logs_dir,
        "downloads": paths.downloads_dir,
        "temp": paths.temp_dir,
        "managed_bin": paths.managed_bin_dir,
        "models": paths.models_dir,
    }
    return {
        name: {
            "path": str(path),
            "exists": path.is_dir(),
            "writable": path.is_dir() and os.access(path, os.W_OK),
        }
        for name, path in expected.items()
    }


def _derive_capabilities(
    packages: Mapping[str, Mapping[str, Any]],
    tools: Mapping[str, Mapping[str, Any]],
    environment: Mapping[str, bool],
    ollama: Mapping[str, Any],
) -> dict[str, bool]:
    pkg = lambda name: bool(packages.get(name, {}).get("available"))
    tool = lambda name: bool(tools.get(name, {}).get("in_path"))
    return {
        "local_llm": bool(ollama.get("functional")),
        "cloud_llm_nvidia": pkg("openai") and environment.get("NVIDIA_API_KEY", False),
        "cloud_llm_groq": pkg("groq") and environment.get("GROQ_API_KEY", False),
        "cloud_llm_openai": pkg("openai") and environment.get("OPENAI_API_KEY", False),
        "rag": pkg("chromadb") and pkg("sentence_transformers") and pkg("torch"),
        "pdf_text": pkg("pypdf"),
        "ocr": pkg("pytesseract") and pkg("PIL") and tool("tesseract"),
        "pdf_ocr": pkg("pdf2image") and pkg("pytesseract") and tool("poppler") and tool("tesseract"),
        "audio_transcription": pkg("groq") and tool("ffmpeg") and environment.get("GROQ_API_KEY", False),
        "speech_input_online": pkg("speech_recognition"),
        "speech_input_offline": pkg("vosk"),
        "speech_output_online": pkg("edge_tts"),
        "speech_output_offline": pkg("pyttsx3"),
        "vision": pkg("pyautogui") and pkg("PIL"),
        "web_search": pkg("duckduckgo_search"),
    }


def _build_checks(
    python: Mapping[str, Any],
    disk: Mapping[str, Any],
    folders: Mapping[str, Mapping[str, Any]],
    packages: Mapping[str, Mapping[str, Any]],
    ollama: Mapping[str, Any],
    capabilities: Mapping[str, bool],
    execution_mode: str,
) -> list[CheckResult]:
    checks = [
        _check("python_version", python["supported_version"], "critical", f"Python {python['version']}"),
        _check("private_runtime", python["in_venv"] or execution_mode == "packaged", "recommended", "Private Python runtime"),
        _check(
            "disk_space",
            disk["free_gb"] is None or disk["free_gb"] >= MIN_FREE_DISK_GB,
            "critical",
            "Available disk space",
            free_gb=disk["free_gb"],
        ),
        _check("data_folder", folders["data"]["exists"], "critical", "Atlas data folder"),
        _check("data_writable", folders["data"]["writable"], "critical", "Atlas data folder is writable"),
        _check("streamlit", packages["streamlit"]["available"], "critical", "Streamlit UI package"),
        _check("llm_backend", any(capabilities[name] for name in ("local_llm", "cloud_llm_nvidia", "cloud_llm_groq", "cloud_llm_openai")), "critical", "At least one functional LLM backend"),
        _check("ollama", ollama["functional"], "recommended", "Configured local Ollama model"),
        _check("rag", capabilities["rag"], "recommended", "Semantic RAG stack"),
    ]
    return checks


def _score(checks: list[CheckResult]) -> int:
    weights = {"critical": 15, "recommended": 5, "optional": 1}
    return max(0, 100 - sum(weights.get(item.severity, 0) for item in checks if item.status != "ok"))


def _startup_profiles(
    checks: list[CheckResult], packages: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    failed = {item.name: item.message for item in checks if item.status != "ok"}
    common_names = ("python_version", "disk_space", "data_folder", "data_writable", "llm_backend")
    common_issues = [failed[name] for name in common_names if name in failed]

    requirements = {
        "ui": ("streamlit", "openai", "requests", "dotenv", "PIL", "pyautogui"),
        "cli": ("openai", "requests", "dotenv", "PIL", "pyautogui"),
        "api": ("fastapi", "uvicorn", "openai", "requests", "dotenv", "PIL", "pyautogui"),
    }
    profiles: dict[str, dict[str, Any]] = {}
    for profile, required_packages in requirements.items():
        issues = list(common_issues)
        for package in required_packages:
            package_state = packages.get(package, {})
            if not package_state.get("available", False):
                issues.append(f"Paquete requerido para {profile}: {package}")
            elif package_state.get("importable") is False:
                issues.append(f"Paquete encontrado pero no importable para {profile}: {package}")
        profiles[profile] = {
            "ready": not issues,
            "critical_issues": issues,
            "required_packages": list(required_packages),
        }
    return profiles


def diagnosticar_sistema(
    *,
    paths: Optional[AtlasPaths] = None,
    environment: Optional[Mapping[str, str]] = None,
    profile: str = "ui",
    deep_packages: bool = False,
) -> dict[str, Any]:
    """Inspect the current system and return a JSON-serializable report."""
    selected_paths = paths or get_paths()
    env = environment if environment is not None else os.environ
    system = _detect_os()
    python = _detect_python()
    cpu = _detect_cpu()
    ram = _detect_ram()
    disk = _detect_disk(selected_paths.program_dir)
    gpu = _detect_gpu()
    ollama = _detect_ollama()
    profile_requirements = {
        "ui": {"streamlit", "openai", "requests", "dotenv", "PIL", "pyautogui"},
        "cli": {"openai", "requests", "dotenv", "PIL", "pyautogui"},
        "api": {"fastapi", "uvicorn", "openai", "requests", "dotenv", "PIL", "pyautogui"},
    }
    if profile not in profile_requirements:
        raise ValueError(f"Perfil de inicio desconocido: {profile}")
    packages = _detect_python_packages(profile_requirements[profile] if deep_packages else None)
    tools = _detect_external_tools()
    environment_presence = _read_env_presence(selected_paths, env)
    folders = _detect_folders(selected_paths)
    capabilities = _derive_capabilities(packages, tools, environment_presence, ollama)
    checks = _build_checks(
        python, disk, folders, packages, ollama, capabilities, selected_paths.mode
    )
    profiles = _startup_profiles(checks, packages)
    if profile not in profiles:
        raise ValueError(f"Perfil de inicio desconocido: {profile}")
    critical = profiles[profile]["critical_issues"]
    warnings = [item.message for item in checks if item.severity == "recommended" and item.status != "ok"]
    recommendations = [f"Resolve: {message}" for message in critical + warnings]

    diagnosis = DiagnosisResult(
        atlas_version=VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        health_score=_score(checks),
        ready_to_start=profiles[profile]["ready"],
        execution_mode=selected_paths.mode,
        data_location=str(selected_paths.data_dir),
        executable_location=sys.executable,
        checks=checks,
        capabilities=capabilities,
        critical_issues=critical,
        warnings=warnings,
        recommendations=recommendations,
    ).to_dict()
    diagnosis.update(
        system=system,
        python=python,
        cpu=cpu,
        ram=ram,
        disk=disk,
        gpu=gpu,
        ollama=ollama,
        # Boolean legacy views keep the current Healer importable between phases.
        python_packages={name: item["available"] for name, item in packages.items()},
        python_package_details=packages,
        dependencies={
            name: {**item, "found": item["in_path"]} for name, item in tools.items()
        },
        environment=environment_presence,
        folders={
            "memory": folders["memory"]["exists"],
            "backups": (selected_paths.private_memory_dir / "backups").is_dir(),
            "logs": folders["logs"]["exists"],
            "cache": folders["cache"]["exists"],
            "chats": (selected_paths.private_memory_dir / "chats").is_dir(),
            "chromadb": folders["chromadb"]["exists"],
        },
        folder_details=folders,
        paths=selected_paths.to_dict(),
        selected_profile=profile,
        startup_profiles=profiles,
        package_validation="import" if deep_packages else "metadata",
    )
    return diagnosis


if __name__ == "__main__":
    print(json.dumps(diagnosticar_sistema(), indent=2, ensure_ascii=False))
