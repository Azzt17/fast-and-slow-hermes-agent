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
PROMPT_SYSTEM = (
    "Kamu adalah proses konsolidasi memori. Distilasi log mentah jadi entri "
    "terstruktur. Jangan tambahkan interpretasi yang tidak didukung teks. "
    "Field yang tidak relevan boleh dikosongkan. Untuk sesi yang berisi keputusan/fakta yang dapat dipakai ulang, isi importance_score dengan nilai 1-10 yang mencerminkan kegunaan; gunakan 0 hanya bila benar-benar tidak ada informasi durable. Kembalikan JSON saja."
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
        isinstance(item, dict) and isinstance(item.get("title", ""), str)
        and isinstance(item.get("detail", ""), str)
        for item in report["new_skills"]
    ):
        raise ValueError("new_skills must be a list of {title, detail}")
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


def consolidate_once(
    *,
    session_id: str,
    rows: list[Mapping[str, Any]],
    llm_call: Callable[..., Any],
    mem0_client: Any,
) -> dict[str, Any]:
    """Run one consolidation, retrying malformed model output exactly once."""

    messages = build_prompt(session_id, rows)
    report: dict[str, Any] | None = None
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = llm_call(
                task="memory_consolidation",
                messages=messages,
                temperature=0,
                max_tokens=2000,
            )
            report = parse_report(response)
            break
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Consolidation attempt failed; retrying once: %s", exc)
            else:
                logger.exception("Consolidation failed for session %s", session_id)
    if report is None:
        assert last_error is not None
        raise last_error

    # Chroma accepts scalar metadata only (or non-empty primitive lists), while
    # §4.3 contains nested/possibly-empty collections. JSON strings preserve the
    # exact structured values without relying on backend-specific metadata rules.
    metadata = {
        "session_id": session_id,
        "source": "system-2-consolidation",
        "status": "trusted",
        "summary": report["summary"],
        "new_skills": json.dumps(report["new_skills"], ensure_ascii=False),
        "anomalies": json.dumps(report["anomalies"], ensure_ascii=False),
        "entities": json.dumps(report["entities"], ensure_ascii=False),
        "relations": json.dumps(report["relations"], ensure_ascii=False),
        "memory_type": report["memory_type"],
        "importance_score": report["importance_score"],
    }
    try:
        logger.warning(
            "Mem0 add starting with infer=False session=%s metadata_fields=%s",
            session_id,
            ",".join(REQUIRED_FIELDS),
        )
        mem0_client.add(
            report["summary"],
            user_id=session_id,
            metadata=metadata,
            infer=False,
        )
        logger.warning("Mem0 add completed with infer=False session=%s", session_id)
    except TypeError as exc:
        raise RuntimeError(
            "Mem0 client must support add(..., infer=False); refusing "
            "to enable automatic extraction"
        ) from exc
    return report
