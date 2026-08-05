#!/usr/bin/env python3
"""Build a metadata-only, reviewable Obsidian import manifest.

This Pilot 0 tool never calls a model, Hermes, Mem0, or SQLite. It does not
modify the vault. The JSONL output is a private review artifact, not a memory
import queue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

SCHEMA_VERSION = 1
EXCLUDED_DIRS = {".obsidian", "00-inbox", "04-archive"}
EXCLUDED_PATH_MARKERS = {"dailyjournal", "dreamjournal", "news-digest"}
SENSITIVE_NAME_MARKERS = {
    "credential",
    "key",
    "password",
    "secret",
    "token",
    "private",
}
REVISION_SUFFIX = re.compile(r"\.\d{8}-\d{6}\.\d+$")
TAG_PATTERN = re.compile(r"(?<!\w)#([\w/-]+)")
WIKILINK_PATTERN = re.compile(r"\[\[[^\]]+\]\]")


class FileDecision:
    def __init__(self, classification: str, reasons: tuple[str, ...]) -> None:
        self.classification = classification
        self.reasons = reasons


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _revision_family(relative_path: Path) -> str:
    normalized = str(relative_path.with_suffix(""))
    return REVISION_SUFFIX.sub("", normalized)


def _metadata(path: Path) -> tuple[bool, list[str], int]:
    """Return frontmatter presence, tag names, and wikilink count; not content."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    has_frontmatter = bool(lines and lines[0].strip() == "---")
    tags = sorted(set(TAG_PATTERN.findall(text)))
    return has_frontmatter, tags, len(WIKILINK_PATTERN.findall(text))


def classify(relative_path: Path) -> FileDecision:
    parts = {part.casefold() for part in relative_path.parts[:-1]}
    filename = relative_path.name.casefold()
    if relative_path.suffix.casefold() != ".md":
        return FileDecision("excluded", ("non_markdown",))
    if parts & EXCLUDED_DIRS:
        return FileDecision("excluded", ("excluded_directory",))
    if any(marker in parts for marker in EXCLUDED_PATH_MARKERS):
        return FileDecision("excluded", ("temporal_collection",))
    if any(marker in filename for marker in SENSITIVE_NAME_MARKERS):
        return FileDecision("needs_review", ("sensitive_filename_marker",))
    return FileDecision("needs_review", ("requires_human_allowlist",))


def iter_manifest(vault: Path) -> Iterator[dict[str, object]]:
    for path in sorted(vault.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative_path = path.relative_to(vault)
        decision = classify(relative_path)
        stat = path.stat()
        has_frontmatter, tags, wikilink_count = _metadata(path)
        yield {
            "schema_version": SCHEMA_VERSION,
            "source_path": relative_path.as_posix(),
            "source_sha256": _sha256(path),
            "source_size_bytes": stat.st_size,
            "source_mtime_utc": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "frontmatter_present": has_frontmatter,
            "tags": tags,
            "wikilink_count": wikilink_count,
            "revision_family": _revision_family(relative_path),
            "classification": decision.classification,
            "classification_reasons": list(decision.reasons),
        }


def build_manifest(vault: Path, output: Path) -> dict[str, object]:
    vault = vault.resolve()
    if not vault.is_dir():
        raise ValueError(f"vault does not exist or is not a directory: {vault}")
    output = output.resolve()
    if output.is_relative_to(vault):
        raise ValueError("output must be outside the vault")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.stage")
    counts: Counter[str] = Counter()
    record_count = 0
    families: Counter[str] = Counter()
    with temporary.open("w", encoding="utf-8") as handle:
        for record in iter_manifest(vault):
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            counts[str(record["classification"])] += 1
            families[str(record["revision_family"])] += 1
            record_count += 1
        handle.flush()
        os.fsync(handle.fileno())
    temporary.chmod(0o600)
    temporary.replace(output)
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "metadata_only_dry_run",
        "vault": str(vault),
        "output": str(output),
        "created_at_utc": _utc_now(),
        "records": record_count,
        "classifications": dict(sorted(counts.items())),
        "duplicate_revision_families": sum(
            1 for count in families.values() if count > 1
        ),
        "memory_write": False,
        "semantic_analysis": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_manifest(args.vault, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
