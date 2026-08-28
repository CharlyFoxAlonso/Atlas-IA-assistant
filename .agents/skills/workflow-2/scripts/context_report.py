from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from workflow_lib import PROJECT_PROFILE, template_root


CONTEXT_PROFILES = Path(".agents/workflow-2/context-profiles.json")


def load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def normalized_characters(path: Path) -> int:
    text = path.read_bytes().decode("utf-8-sig")
    return len(text.replace("\r\n", "\n").replace("\r", "\n"))


def project_profile_path(root: Path, config: dict[str, object]) -> Path:
    project = config.get("project_profile", {})
    if not isinstance(project, dict):
        return root / PROJECT_PROFILE
    relative = project.get("optional_path", PROJECT_PROFILE.as_posix())
    candidate = Path(str(relative))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("project profile path must stay inside the repository")
    return root / candidate


def merge_project_profile(
    config: dict[str, object], project: dict[str, object]
) -> dict[str, object]:
    project_settings = config.get("project_profile", {})
    if not isinstance(project_settings, dict):
        raise ValueError("project_profile must be an object")
    expected_schema = project_settings.get("schema")
    if project.get("schema") != expected_schema:
        raise ValueError(f"project profile schema must be {expected_schema}")
    merged = json.loads(json.dumps(config))
    base_profiles = merged.get("profiles")
    project_profiles = project.get("profiles", {})
    if not isinstance(base_profiles, dict) or not isinstance(project_profiles, dict):
        raise ValueError("base and project profiles must be JSON objects")

    for role, extension in project_profiles.items():
        if role not in base_profiles or not isinstance(extension, dict):
            raise ValueError(f"invalid project context profile: {role}")
        profile = base_profiles[role]
        if not isinstance(profile, dict):
            raise ValueError(f"invalid base context profile: {role}")
        files = extension.get("append_files", [])
        if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            raise ValueError(f"project profile {role}.append_files must be strings")
        profile["files"] = [*profile.get("files", []), *files]
        for key in (
            "baseline_characters",
            "no_growth_limit_characters",
            "target_characters",
        ):
            if key in extension:
                profile[key] = extension[key]
    return merged


def apply_appends(
    config: dict[str, object], appends: Iterable[tuple[str, str]]
) -> dict[str, object]:
    settings = config.get("project_profile", {})
    expected_schema = settings.get("schema") if isinstance(settings, dict) else None
    project: dict[str, object] = {"schema": expected_schema, "profiles": {}}
    profiles = project["profiles"]
    assert isinstance(profiles, dict)
    for role, path in appends:
        extension = profiles.setdefault(role, {"append_files": []})
        if not isinstance(extension, dict):
            raise ValueError(f"invalid append role: {role}")
        files = extension["append_files"]
        assert isinstance(files, list)
        files.append(path)
    return merge_project_profile(config, project)


def parse_append(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("append values must use ROLE=PATH")
    role, path = value.split("=", 1)
    if not role or not path:
        raise argparse.ArgumentTypeError("append values must use ROLE=PATH")
    return role, path

def parse_roles(value: str) -> list[str]:
    aliases = {"plan-reviewer": "plan_reviewer"}
    roles = [aliases.get(role.strip(), role.strip()) for role in value.split(",")]
    if not roles or any(not role for role in roles):
        raise argparse.ArgumentTypeError("roles must be a comma-separated list")
    return roles


def select_roles(config: dict[str, object], roles: Iterable[str]) -> dict[str, object]:
    selected = list(roles)
    if not selected:
        return config
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("context profiles must be an object")
    unknown = sorted(set(selected) - set(profiles))
    if unknown:
        raise ValueError(f"unknown context roles: {', '.join(unknown)}")
    filtered = json.loads(json.dumps(config))
    filtered["profiles"] = {role: profiles[role] for role in selected}
    return filtered


def validate_config(root: Path, config: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if config.get("schema") != 1:
        errors.append("context profile schema must be 1")
    measurement = config.get("measurement")
    if not isinstance(measurement, dict):
        errors.append("context profile measurement must be an object")
    else:
        expected_method = {
            "encoding": "utf-8-sig",
            "include_entire_file": True,
            "newline_normalization": "lf",
            "unit": "unicode_code_points",
        }
        for key, expected in expected_method.items():
            if measurement.get(key) != expected:
                errors.append(f"context measurement {key} must be {expected!r}")
        tolerance = measurement.get("baseline_tolerance_percent")
        if not isinstance(tolerance, (int, float)) or not 0 <= tolerance <= 100:
            errors.append("baseline_tolerance_percent must be between 0 and 100")
        target = measurement.get("target_reduction_percent")
        if not isinstance(target, (int, float)) or not 0 < target < 100:
            errors.append("target_reduction_percent must be between 0 and 100")
    profiles = config.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        return [*errors, "context profiles must be a non-empty object"]

    project = config.get("project_profile")
    if not isinstance(project, dict):
        errors.append("project_profile must be an object")
    else:
        relative = Path(str(project.get("optional_path", "")))
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            errors.append("project_profile.optional_path must stay in repository")
        if project.get("schema") != 1:
            errors.append("project_profile.schema must be 1")

    for role, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"context profile {role} must be an object")
            continue
        files = profile.get("files")
        if not isinstance(files, list) or not files:
            errors.append(f"context profile {role}.files must be a non-empty list")
            continue
        if not all(isinstance(path, str) and path for path in files):
            errors.append(f"context profile {role}.files must contain paths")
            continue
        if len(files) != len(set(files)):
            errors.append(f"context profile {role} contains duplicate paths")
        for relative in files:
            candidate = Path(relative)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"context profile {role} path must stay in repository: {relative}")
            elif not (root / relative).is_file():
                errors.append(f"context profile {role} references missing file: {relative}")
        for key in (
            "baseline_characters",
            "no_growth_limit_characters",
            "target_characters",
        ):
            value = profile.get(key)
            if not isinstance(value, int) or value <= 0:
                errors.append(f"context profile {role}.{key} must be a positive integer")
    return errors


def measure(root: Path, config: dict[str, object]) -> dict[str, dict[str, object]]:
    profiles = config["profiles"]
    assert isinstance(profiles, dict)
    report: dict[str, dict[str, object]] = {}
    for role, profile in sorted(profiles.items()):
        assert isinstance(profile, dict)
        files = profile["files"]
        assert isinstance(files, list)
        characters = sum(normalized_characters(root / str(path)) for path in files)
        baseline = int(profile["baseline_characters"])
        target = int(profile["target_characters"])
        reduction = 100 * (baseline - characters) / baseline
        report[role] = {
            "baseline_characters": baseline,
            "characters": characters,
            "files": files,
            "no_growth_limit_characters": int(profile["no_growth_limit_characters"]),
            "reduction_percent": round(reduction, 2),
            "target_characters": target,
        }
    return report


def check_report(
    config: dict[str, object],
    report: dict[str, dict[str, object]],
    *,
    verify_baseline: bool,
    enforce_target: bool,
) -> list[str]:
    errors: list[str] = []
    measurement = config["measurement"]
    assert isinstance(measurement, dict)
    tolerance = float(measurement.get("baseline_tolerance_percent", 0))
    for role, result in report.items():
        characters = int(result["characters"])
        baseline = int(result["baseline_characters"])
        if characters > int(result["no_growth_limit_characters"]):
            errors.append(f"{role} exceeds its no-growth context limit")
        if enforce_target and characters > int(result["target_characters"]):
            errors.append(f"{role} has not reached its context reduction target")
        if verify_baseline:
            difference = 100 * abs(characters - baseline) / baseline
            if difference > tolerance:
                errors.append(
                    f"{role} baseline differs by {difference:.2f}% (tolerance {tolerance:.2f}%)"
                )
    return errors


def render(report: dict[str, dict[str, object]]) -> str:
    lines = ["Role\tFiles\tCharacters\tBaseline\tTarget\tReduction"]
    for role, result in report.items():
        lines.append(
            "\t".join(
                [
                    role,
                    str(len(result["files"])),
                    str(result["characters"]),
                    str(result["baseline_characters"]),
                    str(result["target_characters"]),
                    f"{result['reduction_percent']}%",
                ]
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure Workflow context profiles.")
    parser.add_argument("repository", nargs="?", type=Path, default=template_root())
    parser.add_argument("--project-profile", type=Path)
    parser.add_argument("--no-project-profile", action="store_true")
    parser.add_argument("--append", action="append", default=[], type=parse_append)
    parser.add_argument("--roles", type=parse_roles, default=[])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-baseline", action="store_true")
    parser.add_argument("--enforce-target", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = args.repository.resolve()
    try:
        config = load_object(root / CONTEXT_PROFILES)
        profile_path = args.project_profile
        if profile_path is None and not args.no_project_profile:
            candidate = project_profile_path(root, config)
            profile_path = candidate if candidate.is_file() else None
        if profile_path is not None:
            path = profile_path if profile_path.is_absolute() else root / profile_path
            config = merge_project_profile(config, load_object(path))
        config = apply_appends(config, args.append)
        config = select_roles(config, args.roles)
        errors = validate_config(root, config)
        if errors:
            raise ValueError("; ".join(errors))
        report = measure(root, config)
        errors = check_report(
            config,
            report,
            verify_baseline=args.verify_baseline,
            enforce_target=args.enforce_target,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(json.dumps(report, indent=2) if args.json else render(report))
    if args.check and errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
