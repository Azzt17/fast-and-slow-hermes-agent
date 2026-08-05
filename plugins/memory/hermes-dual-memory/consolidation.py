"""Minimal System-2 consolidation pipeline for the dual-memory provider."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = (
    "summary",
    "new_skills",
    "anomalies",
    "entities",
    "relations",
    "memory_type",
    "importance_score",
)
MAX_NEW_SKILLS = 3
MAX_SKILL_TITLE_CHARS = 80
MAX_SKILL_DETAIL_CHARS = 1200
MAX_TRANSCRIPT_CHARS = 6_000
PROMPT_SYSTEM = (
    "Kamu adalah proses konsolidasi memori. Distilasi log mentah jadi entri "
    "terstruktur. Jangan tambahkan interpretasi yang tidak didukung teks. "
    "Field yang tidak relevan boleh dikosongkan. Isi new_skills hanya untuk "
    "prosedur reusable multi-langkah yang benar-benar berhasil didemonstrasikan "
    "dalam sesi; detail harus berupa instruksi lengkap yang dapat dijalankan "
    "ulang, bukan fakta atau ringkasan. Untuk sesi yang berisi keputusan/fakta "
    "yang dapat dipakai ulang, isi importance_score dengan nilai 1-10 yang "
    "mencerminkan kegunaan; gunakan 0 hanya bila benar-benar tidak ada informasi "
    "durable. Maksimal 3 new_skills; setiap title maksimal 80 karakter dan "
    "detail maksimal 1200 karakter. Summary maksimal 150 kata. Kembalikan JSON "
    "saja tanpa Markdown."
)


def build_prompt(session_id: str, rows: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Build the §4.3 prompt from the pending hot-tier rows."""

    transcript = "\n".join(
        f"[{row.get('timestamp', '')}] {row.get('role', 'unknown')}: {row.get('content', '')}"
        for row in rows
    )
    user_prompt = f"""Log mentah sesi {session_id}:
{transcript}

Hasilkan JSON dengan tepat field berikut:
{{
  "summary": "...",
  "new_skills": [{{"title": "...", "detail": "..."}}],
  "anomalies": ["..."],
  "entities": [{{"id": "...", "type": "...", "label": "..."}}],
  "relations": [{{"source": "...", "target": "...", "relation": "..."}}],
  "memory_type": "episodic|semantic",
  "importance_score": 0
}}"""
    return [
        {"role": "system", "content": PROMPT_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]


def chunk_rows(
    rows: list[Mapping[str, Any]], *, max_transcript_chars: int = MAX_TRANSCRIPT_CHARS
) -> list[list[Mapping[str, Any]]]:
    """Split ordered hot turns into bounded, whole-turn consolidation batches."""

    if max_transcript_chars <= 0:
        raise ValueError("max_transcript_chars must be positive")

    chunks: list[list[Mapping[str, Any]]] = []
    current: list[Mapping[str, Any]] = []
    current_chars = 0
    for row in rows:
        row_chars = len(str(row.get("content", "")))
        if current and current_chars + row_chars > max_transcript_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(row)
        current_chars += row_chars
    if current:
        chunks.append(current)
    return chunks


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, Mapping):
        if isinstance(response.get("content"), str):
            return response["content"]
        choices = response.get("choices")
        if choices:
            message = choices[0].get("message", {})
            return str(message.get("content", ""))
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        return str(getattr(message, "content", "") or "")
    return ""


def parse_report(raw: Any) -> dict[str, Any]:
    """Parse and validate a §4.3 report."""

    text = _response_text(raw).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    report = json.loads(text)
    if not isinstance(report, dict):
        raise ValueError("consolidation report must be a JSON object")
    missing = [field for field in REQUIRED_FIELDS if field not in report]
    if missing:
        raise ValueError(f"consolidation report missing fields: {', '.join(missing)}")
    if not isinstance(report["summary"], str):
        raise ValueError("summary must be a string")
    if not isinstance(report["new_skills"], list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("title"), str)
        and bool(item["title"].strip())
        and isinstance(item.get("detail"), str)
        and bool(item["detail"].strip())
        for item in report["new_skills"]
    ):
        raise ValueError("new_skills must be a list of non-empty {title, detail}")
    if len(report["new_skills"]) > MAX_NEW_SKILLS:
        raise ValueError(f"new_skills cannot exceed {MAX_NEW_SKILLS} items")
    if any(len(item["title"].strip()) > MAX_SKILL_TITLE_CHARS for item in report["new_skills"]):
        raise ValueError(f"new_skills title cannot exceed {MAX_SKILL_TITLE_CHARS} characters")
    if any(len(item["detail"].strip()) > MAX_SKILL_DETAIL_CHARS for item in report["new_skills"]):
        raise ValueError(f"new_skills detail cannot exceed {MAX_SKILL_DETAIL_CHARS} characters")
    report["new_skills"] = [
        {"title": item["title"].strip(), "detail": item["detail"].strip()}
        for item in report["new_skills"]
    ]
    if not isinstance(report["anomalies"], list) or not all(
        isinstance(item, str) for item in report["anomalies"]
    ):
        raise ValueError("anomalies must be a list of strings")
    if not isinstance(report["entities"], list) or not all(
        isinstance(item, dict)
        and all(isinstance(item.get(key, ""), str) for key in ("id", "type", "label"))
        for item in report["entities"]
    ):
        raise ValueError("entities must be a list of {id, type, label}")
    if not isinstance(report["relations"], list) or not all(
        isinstance(item, dict)
        and all(isinstance(item.get(key, ""), str) for key in ("source", "target", "relation"))
        for item in report["relations"]
    ):
        raise ValueError("relations must be a list of {source, target, relation}")
    if report["memory_type"] not in ("episodic", "semantic"):
        raise ValueError("memory_type must be episodic or semantic")
    score = report["importance_score"]
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
        raise ValueError("importance_score must be a number from 0 to 10")
    return report


def _parse_contradiction_decision(raw: Any) -> bool:
    text = _response_text(raw).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    decision = json.loads(text)
    if not isinstance(decision, dict) or not isinstance(decision.get("contradiction"), bool):
        raise ValueError("contradiction decision must contain a boolean contradiction field")
    return bool(decision["contradiction"])


def find_superseded_memories(
    *,
    report: Mapping[str, Any],
    llm_call: Callable[..., Any],
    mem0_client: Any,
    shadow_store: Any,
) -> list[str]:
    """Find old semantic shadows explicitly confirmed as contradictory."""

    if report["memory_type"] != "semantic":
        return []
    if not report["entities"]:
        return []
    new_relations = shadow_store.normalized_claims(report["entities"], report["relations"])

    superseded: list[str] = []
    for candidate in shadow_store.find_active_semantic_candidates(report["entities"]):
        old_relations = candidate.get("relations") or []
        try:
            old_memory = mem0_client.get(str(candidate["mem0_id"]))
        except Exception:
            logger.exception(
                "Unable to load old memory %s for contradiction check; preserving it",
                candidate.get("mem0_id"),
            )
            continue
        old_summary = str((old_memory or {}).get("memory") or "").strip()
        if not old_summary:
            continue
        messages = [
            {
                "role": "system",
                "content": (
                    "Tentukan apakah klaim lama dan baru benar-benar bertentangan sehingga "
                    "keduanya tidak dapat benar pada waktu yang sama. Kemiripan topik, tambahan "
                    "informasi, atau relasi multi-valued bukan kontradiksi. Kembalikan JSON saja: "
                    '{"contradiction": true|false, "reason": "..."}.'
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "old_summary": old_summary,
                        "new_summary": report["summary"],
                        "old_claims": old_relations,
                        "new_claims": new_relations,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        try:
            response = llm_call(
                task="memory_contradiction",
                messages=messages,
                temperature=0,
                max_tokens=300,
            )
            if _parse_contradiction_decision(response):
                superseded.append(str(candidate["mem0_id"]))
        except Exception:
            logger.exception(
                "Contradiction check failed for old memory %s; preserving it",
                candidate.get("mem0_id"),
            )
    return superseded


def _extract_mem0_id(result: Any) -> str:
    if not isinstance(result, dict):
        raise ValueError("Mem0 add result must be an object")
    results = result.get("results")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise ValueError("Mem0 add result did not contain results[0].id")
    mem0_id = str(results[0].get("id") or "").strip()
    if not mem0_id:
        raise ValueError("Mem0 add result did not contain results[0].id")
    return mem0_id


def consolidate_once(
    *,
    session_id: str,
    rows: list[Mapping[str, Any]],
    llm_call: Callable[..., Any],
    mem0_client: Any,
    shadow_store: Any,
    admission_check: Callable[[str], Any] | None = None,
    skill_router: Callable[[dict[str, Any]], list[dict[str, Any]]] | None = None,
    skill_finalizer: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
    user_id: str = "default",
) -> dict[str, Any]:
    """Run one consolidation, retrying malformed model output exactly once."""

    messages = build_prompt(session_id, rows)
    report: dict[str, Any] | None = None
    last_error: Exception | None = None
    attempt_messages = messages
    for attempt in range(2):
        try:
            response = llm_call(
                task="memory_consolidation",
                messages=attempt_messages,
                temperature=0,
                max_tokens=3000,
            )
            report = parse_report(response)
            break
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Consolidation attempt failed; retrying once: %s", exc)
                attempt_messages = messages + [
                    {
                        "role": "user",
                        "content": (
                            "Respons sebelumnya invalid atau terpotong. Ulangi dari log yang "
                            "sama sebagai satu object JSON valid dan ringkas. Patuhi batas: "
                            "summary <=150 kata, maksimal 3 new_skills, title <=80 karakter, "
                            "detail <=1200 karakter per skill. Jangan gunakan Markdown fence."
                        ),
                    }
                ]
            else:
                logger.exception("Consolidation failed for session %s", session_id)
    if report is None:
        assert last_error is not None
        raise last_error

    # Chroma accepts scalar metadata only (or non-empty primitive lists), while
    # §4.3 contains nested/possibly-empty collections. JSON strings preserve the
    # exact structured values without relying on backend-specific metadata rules.
    admission_content = "\n".join(
        [report["summary"]]
        + [
            f"Proposed skill: {item['title']}\n{item['detail']}"
            for item in report["new_skills"]
        ]
    )
    admission = admission_check(admission_content) if admission_check is not None else None
    final_status = str(getattr(admission, "status", "trusted"))
    flagged_reason = getattr(admission, "flagged_reason", None)
    report["admission_status"] = final_status
    report["flagged_reason"] = flagged_reason
    skill_drafts: list[dict[str, Any]] = []
    if final_status == "trusted" and report["new_skills"]:
        if skill_router is None or skill_finalizer is None:
            raise RuntimeError("trusted new_skills require procedural skill routing and finalization")
        skill_drafts = skill_router(report)
    report["skill_drafts"] = skill_drafts
    metadata = {
        "session_id": session_id,
        "source": "system-2-consolidation",
        "status": final_status,
        "shadow_index_version": 1,
        "summary": report["summary"],
        "new_skill_count": len(report["new_skills"]),
        "skill_draft_ids": json.dumps([draft["id"] for draft in skill_drafts]),
        "anomalies": json.dumps(report["anomalies"], ensure_ascii=False),
        "entities": json.dumps(report["entities"], ensure_ascii=False),
        "relations": json.dumps(report["relations"], ensure_ascii=False),
        "memory_type": report["memory_type"],
        "importance_score": report["importance_score"],
    }
    if flagged_reason:
        metadata["flagged_reason"] = str(flagged_reason)
    superseded = []
    if final_status == "trusted":
        superseded = find_superseded_memories(
            report=report,
            llm_call=llm_call,
            mem0_client=mem0_client,
            shadow_store=shadow_store,
        )
    logger.warning(
        "Mem0 add starting with infer=False session=%s metadata_fields=%s",
        session_id,
        ",".join(REQUIRED_FIELDS),
    )
    try:
        add_result = mem0_client.add(
            report["summary"],
            user_id=user_id,
            metadata=metadata,
            infer=False,
        )
    except TypeError as exc:
        raise RuntimeError(
            "Mem0 client must support add(..., infer=False); refusing "
            "to enable automatic extraction"
        ) from exc
    mem0_id = _extract_mem0_id(add_result)
    shadow_store.record_memory(
        mem0_id=mem0_id,
        session_id=session_id,
        memory_type=report["memory_type"],
        importance_score=report["importance_score"],
        entities=report["entities"],
        relations=report["relations"],
        status="candidate",
    )
    shadow_store.finalize_memory_admission(
        mem0_id=mem0_id,
        status=final_status,
        flagged_reason=flagged_reason,
        supersedes=superseded,
    )
    if skill_drafts:
        assert skill_finalizer is not None
        skill_drafts = skill_finalizer(skill_drafts)
        report["skill_drafts"] = skill_drafts
    logger.warning("Mem0 add completed with infer=False session=%s", session_id)
    return report
