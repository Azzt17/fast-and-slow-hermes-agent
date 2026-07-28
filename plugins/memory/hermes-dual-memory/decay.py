"""Opportunistic episodic decay and cold compaction for Phase 5."""

from __future__ import annotations

import json
import logging
import math
import threading
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

DECAY_THRESHOLD = 0.3
COMPACTION_SIMILARITY_THRESHOLD = 0.75


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, Mapping):
        if "content" in response:
            return str(response["content"])
        choices = response.get("choices")
        if choices:
            return str(choices[0].get("message", {}).get("content", ""))
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        return str(getattr(message, "content", "") or "")
    return ""


def _parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("decay timestamp must not be empty")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def retrievability(row: Mapping[str, Any], *, now: datetime) -> float:
    """Compute the exact Phase 5 formula R(t)=exp(-t/S)."""

    baseline = _parse_timestamp(row.get("last_accessed") or row.get("t_created"))
    elapsed_days = max((now.astimezone(timezone.utc) - baseline).total_seconds() / 86400.0, 0.0)
    stability = max(float(row.get("stability") or 0.5), 0.5)
    return math.exp(-elapsed_days / stability)


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


def _bounded_llm_call(
    llm_call: Callable[..., Any],
    *,
    messages: list[dict[str, str]],
    timeout_seconds: float,
) -> dict[str, Any] | None:
    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _run() -> None:
        try:
            response = llm_call(
                task="memory_cold_compaction",
                messages=messages,
                temperature=0,
                max_tokens=1000,
                timeout=timeout_seconds,
            )
            text = _response_text(response).strip()
            if text.startswith("```"):
                text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            payload = json.loads(text)
            if not isinstance(payload, dict) or not isinstance(payload.get("summary"), str):
                raise ValueError("cold compaction output must contain summary")
            score = payload.get("importance_score", 0)
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
                raise ValueError("cold compaction importance_score must be 0-10")
            result_box["value"] = payload
        except BaseException as exc:
            error_box["error"] = exc

    thread = threading.Thread(target=_run, name="hermes-dual-memory-cold-llm", daemon=True)
    thread.start()
    thread.join(timeout=max(timeout_seconds, 0.01))
    if thread.is_alive():
        logger.warning("Cold compaction LLM timed out after %.2fs", timeout_seconds)
        return None
    if "error" in error_box:
        logger.warning("Cold compaction LLM failed: %s", error_box["error"])
        return None
    return result_box.get("value")


def _cold_clusters(
    cold_memories: list[dict[str, Any]],
    *,
    mem0_client: Any,
    user_id: str,
    similarity_threshold: float,
) -> tuple[list[list[str]], dict[str, str]]:
    cold_ids = {str(row["mem0_id"]) for row in cold_memories}
    contents: dict[str, str] = {}
    adjacency: dict[str, set[str]] = {mem0_id: set() for mem0_id in cold_ids}

    for mem0_id in cold_ids:
        try:
            memory = mem0_client.get(mem0_id)
            content = str((memory or {}).get("memory") or "").strip()
            if content:
                contents[mem0_id] = content
        except Exception as exc:
            logger.warning("Cold compaction skipped unreadable memory %s: %s", mem0_id, exc)

    for mem0_id, content in contents.items():
        try:
            raw = mem0_client.search(
                content,
                filters={"user_id": user_id},
                limit=max(len(cold_ids), 2),
                threshold=similarity_threshold,
            )
        except Exception as exc:
            logger.warning("Cold similarity search failed for %s: %s", mem0_id, exc)
            continue
        results = raw.get("results", []) if isinstance(raw, dict) else raw
        if not isinstance(results, list):
            continue
        for item in results:
            if not isinstance(item, dict):
                continue
            other_id = str(item.get("id") or "")
            score = float(item.get("score") or 0.0)
            if other_id in cold_ids and other_id != mem0_id and score >= similarity_threshold:
                adjacency[mem0_id].add(other_id)
                adjacency[other_id].add(mem0_id)

    clusters: list[list[str]] = []
    seen: set[str] = set()
    for mem0_id in sorted(cold_ids):
        if mem0_id in seen:
            continue
        stack = [mem0_id]
        component: list[str] = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - seen))
        if len(component) >= 2 and all(source_id in contents for source_id in component):
            clusters.append(sorted(component))
    return clusters, contents


def compact_cold_memories(
    *,
    shadow_store: Any,
    mem0_client: Any,
    llm_call: Callable[..., Any],
    user_id: str,
    now: datetime,
    timeout_seconds: float,
    admission_check: Callable[[str], Any] | None = None,
    similarity_threshold: float = COMPACTION_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    cold_memories = shadow_store.active_cold_memories()
    if len(cold_memories) < 2:
        return []
    clusters, contents = _cold_clusters(
        cold_memories,
        mem0_client=mem0_client,
        user_id=user_id,
        similarity_threshold=similarity_threshold,
    )
    importance = {str(row["mem0_id"]): float(row["importance_score"]) for row in cold_memories}
    compacted: list[dict[str, Any]] = []
    for cluster_index, source_ids in enumerate(clusters, start=1):
        messages = [
            {
                "role": "system",
                "content": (
                    "Ringkas cluster memori episodic dingin menjadi satu essence representatif. "
                    "Jangan menambah fakta. Kembalikan JSON saja dengan field summary dan "
                    "importance_score (0-10)."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"memories": [contents[source_id] for source_id in source_ids]},
                    ensure_ascii=False,
                ),
            },
        ]
        payload = _bounded_llm_call(
            llm_call,
            messages=messages,
            timeout_seconds=timeout_seconds,
        )
        if payload is None:
            continue
        summary = payload["summary"].strip()
        if not summary:
            logger.warning("Cold compaction returned an empty summary; cluster skipped")
            continue
        score = max(
            float(payload["importance_score"]),
            max(importance[source_id] for source_id in source_ids),
        )
        admission = admission_check(summary) if admission_check is not None else None
        final_status = str(getattr(admission, "status", "trusted"))
        flagged_reason = getattr(admission, "flagged_reason", None)
        metadata = {
            "session_id": f"cold-compaction:{now.date().isoformat()}:{cluster_index}",
            "source": "system-2-cold-compaction",
            "status": final_status,
            "shadow_index_version": 1,
            "memory_type": "episodic",
            "importance_score": score,
            "compacted_from": json.dumps(source_ids),
        }
        if flagged_reason:
            metadata["flagged_reason"] = str(flagged_reason)
        try:
            add_result = mem0_client.add(
                summary,
                user_id=user_id,
                metadata=metadata,
                infer=False,
            )
            compacted_mem0_id = _extract_mem0_id(add_result)
            shadow_store.record_compaction(
                compacted_mem0_id=compacted_mem0_id,
                session_id=metadata["session_id"],
                importance_score=score,
                source_mem0_ids=source_ids,
                status=final_status,
                flagged_reason=flagged_reason,
                compacted_at=now,
            )
        except Exception:
            logger.exception("Cold compaction write failed; source cluster preserved")
            continue
        compacted.append(
            {
                "mem0_id": compacted_mem0_id,
                "source_mem0_ids": source_ids,
                "summary": summary,
                "status": final_status,
            }
        )
    return compacted


def run_decay_cycle(
    *,
    shadow_store: Any,
    mem0_client: Any,
    llm_call: Callable[..., Any],
    user_id: str,
    now: datetime | None = None,
    already_claimed: bool = False,
    timeout_seconds: float = 8.0,
    admission_check: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not already_claimed and not shadow_store.claim_decay_cycle(now=current):
        return {"ran": False, "demoted": [], "compacted": []}

    demoted = [
        str(row["mem0_id"])
        for row in shadow_store.episodic_decay_candidates()
        if row["tier"] != "cold" and retrievability(row, now=current) < DECAY_THRESHOLD
    ]
    shadow_store.demote_memories(demoted, demoted_at=current)

    compacted: list[dict[str, Any]] = []
    if mem0_client is not None and llm_call is not None:
        try:
            compacted = compact_cold_memories(
                shadow_store=shadow_store,
                mem0_client=mem0_client,
                llm_call=llm_call,
                user_id=user_id,
                now=current,
                timeout_seconds=timeout_seconds,
                admission_check=admission_check,
            )
        except Exception:
            logger.exception("Cold compaction cycle failed; decay demotions remain committed")
    return {"ran": True, "demoted": demoted, "compacted": compacted}
