#!/usr/bin/env python3
"""Validate and atomically deploy canonical static Hermes profile assets."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILES_ROOT = REPO_ROOT / "profiles"
PROFILE_TARGETS = {
    "default": Path.home() / ".hermes",
    "research": Path.home() / ".hermes" / "profiles" / "research",
}
MEMORY_LIMITS = {"MEMORY.md": 2200, "USER.md": 1375}
MANAGED_SKILLS = {
    "default": (
        "asa-daily-checkin",
        "asa-deep-discussion",
        "asa-night-review",
        "hermes-dual-memory-operations",
    ),
    "research": (
        "hermes-dual-memory-operations",
        "nellie-research-workflow",
    ),
}


def _ensure_hermes_imports() -> None:
    candidates = [
        Path(os.environ.get("HERMES_SOURCE_ROOT", "")).expanduser(),
        Path.home() / ".hermes" / "hermes-agent",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / "agent").is_dir():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return
    raise RuntimeError(
        "Hermes source unavailable; set HERMES_SOURCE_ROOT to hermes-agent"
    )


def _copy_atomic(source: Path, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, stage_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".stage", dir=target.parent
    )
    stage = Path(stage_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(source.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        stage.chmod(mode)
        stage.replace(target)
    except BaseException:
        stage.unlink(missing_ok=True)
        raise


def _profile_files(profile: str) -> list[tuple[Path, Path, int]]:
    source_root = PROFILES_ROOT / profile
    target_root = PROFILE_TARGETS[profile]
    files = [
        (source_root / "SOUL.md", target_root / "SOUL.md", 0o600),
        (
            source_root / "memories" / "MEMORY.md",
            target_root / "memories" / "MEMORY.md",
            0o600,
        ),
        (
            source_root / "memories" / "USER.md",
            target_root / "memories" / "USER.md",
            0o600,
        ),
    ]
    profile_descriptor = source_root / "profile.yaml"
    if profile_descriptor.is_file():
        files.append(
            (profile_descriptor, target_root / "profile.yaml", 0o600)
        )
    for skill_file in sorted((source_root / "skills").glob("*/SKILL.md")):
        files.append(
            (
                skill_file,
                target_root / "skills" / skill_file.parent.name / "SKILL.md",
                0o600,
            )
        )
    return files


def validate_static() -> dict[str, object]:
    _ensure_hermes_imports()
    try:
        from agent.prompt_builder import _scan_context_content
        from agent.skill_utils import parse_frontmatter
        from tools.skill_manager_tool import _validate_frontmatter
        from tools.threat_patterns import scan_for_threats
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Run with Hermes source on PYTHONPATH and its venv Python"
        ) from error

    report: dict[str, object] = {"profiles": {}}
    for profile in PROFILE_TARGETS:
        source_root = PROFILES_ROOT / profile
        profile_report: dict[str, object] = {"skills": []}
        soul = (source_root / "SOUL.md").read_text(encoding="utf-8")
        if _scan_context_content(soul, "SOUL.md").startswith("[BLOCKED:"):
            raise ValueError(f"{profile}: SOUL.md blocked by context scanner")
        profile_report["soul_chars"] = len(soul)

        for memory_name, limit in MEMORY_LIMITS.items():
            path = source_root / "memories" / memory_name
            content = path.read_text(encoding="utf-8").rstrip("\n")
            entries = [item.strip() for item in content.split("\n§\n") if item.strip()]
            if not entries or "\n§\n".join(entries) != content:
                raise ValueError(f"{profile}: {memory_name} is not canonical § format")
            if len(content) > limit:
                raise ValueError(f"{profile}: {memory_name} exceeds {limit} chars")
            for entry in entries:
                findings = scan_for_threats(entry, scope="strict")
                if findings:
                    raise ValueError(
                        f"{profile}: {memory_name} blocked by {','.join(findings)}"
                    )
            profile_report[memory_name] = {
                "chars": len(content),
                "entries": len(entries),
            }

        skill_names: set[str] = set()
        for skill_file in sorted((source_root / "skills").glob("*/SKILL.md")):
            raw = skill_file.read_text(encoding="utf-8")
            error = _validate_frontmatter(raw, new_skill=True)
            if error:
                raise ValueError(f"{skill_file}: {error}")
            frontmatter, _ = parse_frontmatter(raw)
            name = str(frontmatter["name"])
            if name != skill_file.parent.name:
                raise ValueError(f"{skill_file}: folder/frontmatter name mismatch")
            if name in skill_names:
                raise ValueError(f"{profile}: duplicate skill {name}")
            skill_names.add(name)
            findings = scan_for_threats(raw, scope="context")
            if findings:
                raise ValueError(f"{skill_file}: blocked by {','.join(findings)}")
            profile_report["skills"].append(name)
        report["profiles"][profile] = profile_report

    workspace = PROFILES_ROOT / "research" / "workspace" / ".hermes.md"
    content = workspace.read_text(encoding="utf-8")
    if _scan_context_content(content, ".hermes.md").startswith("[BLOCKED:"):
        raise ValueError("research workspace context blocked by scanner")
    report["research_workspace_chars"] = len(content)
    return report


def deploy(profiles: list[str], workspace: Path | None) -> dict[str, object]:
    report = validate_static()
    deployed: list[str] = []
    removed: list[str] = []
    for profile in profiles:
        for source, target, mode in _profile_files(profile):
            _copy_atomic(source, target, mode)
            deployed.append(str(target))
        for skill_name in MANAGED_SKILLS[profile]:
            skill_directory = PROFILE_TARGETS[profile] / "skills" / skill_name
            skill_file = skill_directory / "SKILL.md"
            if skill_file.exists():
                skill_file.unlink()
                removed.append(str(skill_file))
            try:
                skill_directory.rmdir()
            except OSError:
                pass
    if workspace is not None:
        source = PROFILES_ROOT / "research" / "workspace" / ".hermes.md"
        _copy_atomic(source, workspace / ".hermes.md", 0o664)
        deployed.append(str(workspace / ".hermes.md"))
    report["deployed"] = deployed
    report["removed"] = removed
    return report


def verify_deployment(
    profiles: list[str], workspace: Path | None
) -> dict[str, object]:
    """Verify deployed static assets match canonical sources byte-for-byte."""
    verified: list[str] = []
    for profile in profiles:
        for source, target, mode in _profile_files(profile):
            if not target.is_file() or target.read_bytes() != source.read_bytes():
                raise ValueError(f"{profile}: deployed asset differs: {target}")
            if target.stat().st_mode & 0o777 != mode:
                raise ValueError(f"{profile}: deployed asset mode differs: {target}")
            verified.append(str(target))
        for skill_name in MANAGED_SKILLS[profile]:
            skill_file = PROFILE_TARGETS[profile] / "skills" / skill_name / "SKILL.md"
            if skill_file.exists():
                raise ValueError(f"{profile}: legacy managed skill remains: {skill_file}")
    if workspace is not None:
        source = PROFILES_ROOT / "research" / "workspace" / ".hermes.md"
        target = workspace / ".hermes.md"
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            raise ValueError(f"research workspace differs: {target}")
        verified.append(str(target))
    return {"verified": verified}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=("default", "research", "all"),
        default="all",
    )
    parser.add_argument("--research-workspace", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--verify-deployed", action="store_true")
    args = parser.parse_args()
    profiles = list(PROFILE_TARGETS) if args.profile == "all" else [args.profile]
    if args.validate_only:
        report = validate_static()
    elif args.verify_deployed:
        report = verify_deployment(profiles, args.research_workspace)
    else:
        report = deploy(profiles, args.research_workspace)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
