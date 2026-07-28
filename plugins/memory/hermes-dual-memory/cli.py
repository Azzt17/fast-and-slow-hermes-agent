"""CLI approval workflow for hermes-dual-memory procedural drafts."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any


def _load_procedural() -> Any:
    path = Path(__file__).with_name("procedural.py")
    spec = importlib.util.spec_from_file_location("hermes_dual_memory_cli.procedural", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load procedural module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hermes_home() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except (ImportError, ModuleNotFoundError):
        return Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()


def _print_draft(record: dict[str, Any]) -> None:
    print(f"{record['id']}  {record['status']:9s}  {record['name']}")
    if record.get("redundancy_matches"):
        matches = ", ".join(
            f"{item['name']} ({float(item['score']):.2f})"
            for item in record["redundancy_matches"]
        )
        print(f"  redundancy: {matches}")
    if record.get("final_path"):
        print(f"  active: {record['final_path']}")


def hermes_dual_memory_command(args) -> int:
    procedural = _load_procedural()
    store = procedural.SkillDraftStore(_hermes_home())
    command = getattr(args, "skills_command", None)
    if command == "list":
        records = store.list()
        status = getattr(args, "status", None)
        if status:
            records = [record for record in records if record.get("status") == status]
        if getattr(args, "json", False):
            print(json.dumps(records, ensure_ascii=False, indent=2))
        elif not records:
            print("No procedural skill drafts.")
        else:
            for record in records:
                _print_draft(record)
        return 0
    if command == "show":
        record = store.load(args.draft_id)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0
    if command == "approve":
        try:
            record = store.approve(args.draft_id)
        except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"Approval failed: {exc}")
            return 1
        print(f"Approved {record['id']} -> {record['final_path']}")
        return 0
    print("Choose: skills list, skills show, or skills approve.")
    return 1


def register_cli(subparser) -> None:
    subparser.set_defaults(func=hermes_dual_memory_command)
    groups = subparser.add_subparsers(dest="dual_memory_group")
    skills = groups.add_parser("skills", help="Review and approve procedural skill drafts")
    skills.set_defaults(func=hermes_dual_memory_command)
    commands = skills.add_subparsers(dest="skills_command")

    list_parser = commands.add_parser("list", help="List procedural skill drafts")
    list_parser.add_argument(
        "--status",
        choices=("candidate", "pending", "redundant", "approved"),
    )
    list_parser.add_argument("--json", action="store_true")

    show_parser = commands.add_parser("show", help="Show one complete draft")
    show_parser.add_argument("draft_id")

    approve_parser = commands.add_parser("approve", help="Promote a pending draft to SKILL.md")
    approve_parser.add_argument("draft_id")


globals()["hermes-dual-memory_command"] = hermes_dual_memory_command
