"""Draft and approval workflow for procedural memory via Hermes Skills."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

DRAFT_SCHEMA_VERSION = 1
DRAFT_DIR_NAME = "skill-drafts"
SKILL_CATEGORY = "procedural-memory"
SIMILARITY_THRESHOLD = 0.82


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str, fallback_seed: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if not slug:
        slug = f"procedural-{hashlib.sha256(fallback_seed.encode()).hexdigest()[:10]}"
    return slug[:64].rstrip("-")


def _skill_description(title: str) -> str:
    title_text = re.sub(r"\s+", " ", title).strip().rstrip(".!?")
    candidate = f"Use for {title_text}."
    if len(candidate) <= 60:
        return candidate
    shortened = candidate[:59].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if len(shortened) < 12:
        shortened = candidate[:59].rstrip(" ,;:-")
    return f"{shortened}."


def render_skill(title: str, detail: str) -> tuple[str, str, str]:
    """Convert one validated new_skills item to native SKILL.md content."""

    clean_title = re.sub(r"\s+", " ", title).strip().strip("#")
    clean_detail = detail.strip()
    seed = f"{clean_title}\0{clean_detail}"
    name = _slugify(clean_title, seed)
    description = _skill_description(clean_title)
    content = (
        "---\n"
        f"name: {json.dumps(name, ensure_ascii=False)}\n"
        f"description: {json.dumps(description, ensure_ascii=False)}\n"
        "---\n\n"
        f"# {clean_title}\n\n"
        "## Procedure\n\n"
        f"{clean_detail}\n"
    )
    return name, description, content


def _normalized_text(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


def _similarity(left: str, right: str) -> float:
    left_text = _normalized_text(left)
    right_text = _normalized_text(right)
    if not left_text or not right_text:
        return 0.0
    left_tokens = set(left_text.split())
    right_tokens = set(right_text.split())
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0
    sequence = SequenceMatcher(None, left_text, right_text).ratio()
    return max(jaccard, sequence)


def _parse_frontmatter(content: str, fallback_name: str) -> tuple[str, str, str]:
    try:
        from tools.skills_tool import _parse_frontmatter

        frontmatter, body = _parse_frontmatter(content)
        return (
            str(frontmatter.get("name") or fallback_name),
            str(frontmatter.get("description") or ""),
            str(body),
        )
    except (ImportError, ModuleNotFoundError):
        pass

    name = fallback_name
    description = ""
    body = content
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, flags=re.DOTALL)
    if match:
        frontmatter, body = match.groups()
        for line in frontmatter.splitlines():
            key, separator, value = line.partition(":")
            if not separator:
                continue
            parsed_value = value.strip().strip("'\"")
            if key.strip() == "name":
                name = parsed_value or name
            elif key.strip() == "description":
                description = parsed_value
    return name, description, body


def _skill_roots(hermes_home: Path) -> list[Path]:
    try:
        from agent.skill_utils import get_all_skills_dirs

        return [Path(path) for path in get_all_skills_dirs()]
    except (ImportError, ModuleNotFoundError):
        return [hermes_home / "skills"]


def _is_excluded(skill_md: Path) -> bool:
    try:
        from agent.skill_utils import is_excluded_skill_path

        return bool(is_excluded_skill_path(skill_md))
    except (ImportError, ModuleNotFoundError):
        return any(part.startswith(".") or part == "__pycache__" for part in skill_md.parts)


def discover_skills(hermes_home: str | Path) -> list[dict[str, str]]:
    """Read active local and external Hermes skills for redundancy checks."""

    skills: list[dict[str, str]] = []
    seen: set[str] = set()
    for root in _skill_roots(Path(hermes_home)):
        if not root.exists():
            continue
        for skill_md in sorted(root.rglob("SKILL.md")):
            if _is_excluded(skill_md):
                continue
            try:
                content = skill_md.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            try:
                name, description, body = _parse_frontmatter(content, skill_md.parent.name)
            except Exception:
                continue
            if name in seen:
                continue
            seen.add(name)
            skills.append(
                {
                    "name": name,
                    "description": description,
                    "content": body,
                    "path": str(skill_md),
                }
            )
    return skills


def find_redundancies(
    *,
    name: str,
    description: str,
    content: str,
    existing_skills: Iterable[Mapping[str, Any]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Return existing skills whose name/description/body is near-duplicate."""

    _, _, candidate_body = _parse_frontmatter(content, name)
    candidate_text = f"{description}\n{candidate_body}"
    matches: list[dict[str, Any]] = []
    for existing in existing_skills:
        existing_name = str(existing.get("name") or "")
        existing_description = str(existing.get("description") or "")
        existing_content = str(existing.get("content") or "")
        name_score = _similarity(name, existing_name)
        content_score = _similarity(
            candidate_text,
            f"{existing_description}\n{existing_content}",
        )
        score = max(name_score, content_score)
        if score < threshold:
            continue
        matches.append(
            {
                "name": existing_name,
                "path": str(existing.get("path") or ""),
                "score": round(score, 4),
                "name_score": round(name_score, 4),
                "content_score": round(content_score, 4),
            }
        )
    return sorted(matches, key=lambda item: (-float(item["score"]), str(item["name"])))


class SkillDraftStore:
    """File-backed audit store deliberately outside Hermes' active skills tree."""

    def __init__(self, hermes_home: str | Path) -> None:
        self.hermes_home = Path(hermes_home)
        self.root = self.hermes_home / "hermes-dual-memory" / DRAFT_DIR_NAME

    def _path(self, draft_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{16}", draft_id):
            raise ValueError("draft ID must be 16 lowercase hexadecimal characters")
        return self.root / f"{draft_id}.json"

    @staticmethod
    def _write_atomic(path: Path, record: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass

    def load(self, draft_id: str) -> dict[str, Any]:
        with self._path(draft_id).open(encoding="utf-8") as handle:
            record = json.load(handle)
        if not isinstance(record, dict):
            raise ValueError(f"invalid draft record: {draft_id}")
        return record

    def list(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        records = []
        for path in sorted(self.root.glob("*.json")):
            try:
                record = self.load(path.stem)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            records.append(record)
        return sorted(records, key=lambda item: (str(item.get("created_at", "")), str(item["id"])))

    @staticmethod
    def _validate_approval_record(record: Mapping[str, Any], draft_id: str) -> None:
        if record.get("schema_version") != DRAFT_SCHEMA_VERSION:
            raise ValueError("unsupported draft schema version")
        if record.get("id") != draft_id:
            raise ValueError("draft record ID does not match filename")
        name = str(record.get("name") or "")
        if len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError("draft skill name is invalid")
        if record.get("category") != SKILL_CATEGORY:
            raise ValueError("draft skill category is invalid")
        description = str(record.get("description") or "")
        if not description or len(description) > 60:
            raise ValueError("draft skill description is invalid")
        parsed_name, parsed_description, body = _parse_frontmatter(
            str(record.get("content") or ""),
            "",
        )
        if parsed_name != name or parsed_description != description or not body.strip():
            raise ValueError("draft SKILL.md content does not match its record")

    def create(
        self,
        *,
        session_id: str,
        title: str,
        detail: str,
        existing_skills: Iterable[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        title = title.strip()
        detail = detail.strip()
        if not title or not detail:
            raise ValueError("skill title and detail must be non-empty")
        digest_input = f"{session_id}\0{title}\0{detail}".encode()
        draft_id = hashlib.sha256(digest_input).hexdigest()[:16]
        path = self._path(draft_id)
        if path.exists():
            return self.load(draft_id)

        name, description, content = render_skill(title, detail)
        skills = list(existing_skills) if existing_skills is not None else discover_skills(self.hermes_home)
        redundancies = find_redundancies(
            name=name,
            description=description,
            content=content,
            existing_skills=skills,
        )
        record: dict[str, Any] = {
            "schema_version": DRAFT_SCHEMA_VERSION,
            "id": draft_id,
            "status": "candidate",
            "session_id": session_id,
            "source": "system-2-consolidation",
            "created_at": _utc_now(),
            "title": title,
            "detail": detail,
            "name": name,
            "description": description,
            "category": SKILL_CATEGORY,
            "content": content,
            "redundancy_matches": redundancies,
        }
        self._write_atomic(path, record)
        return record

    def finalize(self, draft_ids: Iterable[str]) -> list[dict[str, Any]]:
        """Expose staged candidates only after memory admission is persisted."""

        finalized = []
        for draft_id in draft_ids:
            record = self.load(draft_id)
            if record.get("status") == "candidate":
                record["status"] = "redundant" if record.get("redundancy_matches") else "pending"
                record["admitted_at"] = _utc_now()
                self._write_atomic(self._path(draft_id), record)
            finalized.append(record)
        return finalized

    def approve(
        self,
        draft_id: str,
        *,
        skill_creator: Callable[..., Any] | None = None,
        curator_marker: Callable[[str], Any] | None = None,
    ) -> dict[str, Any]:
        record = self.load(draft_id)
        self._validate_approval_record(record, draft_id)
        if record.get("status") == "redundant":
            raise ValueError("redundant draft cannot be approved")
        if record.get("status") == "approved":
            return record
        if record.get("status") != "pending":
            raise ValueError(f"draft status is not approvable: {record.get('status')}")

        final_path = (
            self.hermes_home
            / "skills"
            / str(record["category"])
            / str(record["name"])
            / "SKILL.md"
        )
        result: dict[str, Any] = {}
        if final_path.is_file():
            if final_path.read_text(encoding="utf-8") != str(record["content"]):
                raise RuntimeError("an active skill with different content already uses this name")
        else:
            creator = skill_creator or _native_skill_creator
            result_value = creator(
                name=str(record["name"]),
                content=str(record["content"]),
                category=str(record["category"]),
            )
            if isinstance(result_value, str):
                result_value = json.loads(result_value)
            if not isinstance(result_value, dict):
                raise RuntimeError("Hermes skill creator returned an invalid result")
            result = result_value
            if result.get("staged"):
                record["native_pending_id"] = result.get("pending_id")
                record["last_promotion_error"] = "Hermes native skill write gate requires approval"
                self._write_atomic(self._path(draft_id), record)
                raise RuntimeError(record["last_promotion_error"])
            if not result.get("success"):
                record["last_promotion_error"] = str(result.get("error") or "Hermes rejected skill")
                self._write_atomic(self._path(draft_id), record)
                raise RuntimeError(record["last_promotion_error"])
            result_path = Path(str(result.get("skill_md") or ""))
            if result_path.is_file():
                final_path = result_path

        if not final_path.is_file():
            raise RuntimeError("Hermes reported success but SKILL.md is missing")

        marker = curator_marker or _native_curator_marker
        try:
            marker(str(record["name"]))
        except Exception as exc:
            record["last_promotion_error"] = f"Curator provenance failed: {type(exc).__name__}"
            self._write_atomic(self._path(draft_id), record)
            raise RuntimeError(record["last_promotion_error"]) from exc

        record.pop("last_promotion_error", None)
        record.pop("native_pending_id", None)
        record["status"] = "approved"
        record["approved_at"] = _utc_now()
        record["final_path"] = str(final_path)
        self._write_atomic(self._path(draft_id), record)
        return record


def _native_skill_creator(*, name: str, content: str, category: str) -> dict[str, Any]:
    try:
        from tools.skill_manager_tool import skill_manage
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError("Hermes skill manager is unavailable") from exc
    return json.loads(skill_manage(action="create", name=name, content=content, category=category))


def _native_curator_marker(skill_name: str) -> None:
    try:
        from tools.skill_usage import mark_agent_created
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError("Hermes Curator usage API is unavailable") from exc
    mark_agent_created(skill_name)


def route_new_skills(
    *,
    report: Mapping[str, Any],
    session_id: str,
    hermes_home: str | Path,
    existing_skills: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Create non-active draft records for a trusted consolidation report."""

    if report.get("admission_status") != "trusted":
        return []
    store = SkillDraftStore(hermes_home)
    discovered = list(existing_skills) if existing_skills is not None else discover_skills(hermes_home)
    return [
        store.create(
            session_id=session_id,
            title=str(item["title"]),
            detail=str(item["detail"]),
            existing_skills=discovered,
        )
        for item in report.get("new_skills", [])
    ]


def finalize_skill_drafts(
    *,
    drafts: Iterable[Mapping[str, Any]],
    hermes_home: str | Path,
) -> list[dict[str, Any]]:
    """Transition candidate drafts after the shadow row becomes trusted."""

    return SkillDraftStore(hermes_home).finalize(str(draft["id"]) for draft in drafts)
