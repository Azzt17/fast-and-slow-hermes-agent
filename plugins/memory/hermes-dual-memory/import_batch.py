"""Plan reviewed external-memory imports without writing runtime state."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

APPROVED_STATUSES = {"approved_stable", "approved_historical_only"}


def _evaluate_admission(content: str, *, llm_call: Any | None, timeout_seconds: float) -> Any:
    path = Path(__file__).with_name("admission.py")
    spec = importlib.util.spec_from_file_location("obsidian_import_admission", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load admission module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.evaluate_admission(
        content, llm_call=llm_call, timeout_seconds=timeout_seconds
    )


def _idempotency_key(candidate: Mapping[str, Any]) -> str:
    source_hash = str(candidate.get("source_sha256") or "").strip()
    candidate_id = str(candidate.get("candidate_id") or "").strip()
    if not source_hash or not candidate_id:
        raise ValueError("candidate requires candidate_id and source_sha256")
    return hashlib.sha256(f"{candidate_id}:{source_hash}".encode()).hexdigest()


def load_approved_candidates(path: str | Path) -> list[dict[str, Any]]:
    """Load only explicitly approved Pilot 1 records from a private JSONL ledger."""
    candidates: list[dict[str, Any]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("review_status") not in APPROVED_STATUSES:
            continue
        if not isinstance(record.get("fact"), str) or not record["fact"].strip():
            raise ValueError(f"ledger line {line_number}: approved candidate requires fact")
        record["idempotency_key"] = _idempotency_key(record)
        candidates.append(record)
    return candidates


def plan_import(candidates: Iterable[Mapping[str, Any]], *, batch_id: str | None = None) -> dict[str, Any]:
    """Return a no-write batch plan preserving temporal and admission gates."""
    batch_id = batch_id or f"obsidian-{uuid.uuid4()}"
    items: list[dict[str, str]] = []
    seen_keys: set[str] = set()
    for candidate in candidates:
        key = _idempotency_key(candidate)
        if key in seen_keys:
            raise ValueError(f"duplicate approved source candidate: {candidate['candidate_id']}")
        seen_keys.add(key)
        status = str(candidate.get("review_status"))
        temporal = "historical" if status == "approved_historical_only" else "current"
        items.append(
            {
                "candidate_id": str(candidate["candidate_id"]),
                "idempotency_key": key,
                "source_path": str(candidate["source_path"]),
                "source_sha256": str(candidate["source_sha256"]),
                "memory_type": "semantic",
                "temporal_visibility": temporal,
                "initial_shadow_status": "candidate",
                "admission": "required_fail_closed",
                "mem0_infer": "false",
                "rollback": "block_shadow_and_mark_batch_rolled_back",
                "fact": str(candidate["fact"]),
            }
        )
    return {
        "mode": "dry_run_only",
        "batch_id": batch_id,
        "profile": "default",
        "memory_write": False,
        "requires_explicit_write_approval": True,
        "items": items,
    }


def execute_import(
    plan: Mapping[str, Any],
    *,
    mem0_client: Any,
    shadow_store: Any,
    llm_call: Any | None,
    admission_timeout_seconds: float,
    write_approved: bool = False,
) -> list[dict[str, Any]]:
    """Execute an explicit reviewed plan; provider hooks never call this function."""
    if plan.get("memory_write"):
        raise ValueError("plan must originate from dry-run planner")
    if not write_approved:
        raise PermissionError("explicit write approval is required")
    results: list[dict[str, Any]] = []
    for item in plan.get("items", []):
        if shadow_store.import_provenance(item["idempotency_key"]):
            results.append({"candidate_id": item["candidate_id"], "status": "already_imported"})
            continue
        decision = _evaluate_admission(
            item["fact"],
            llm_call=llm_call,
            timeout_seconds=admission_timeout_seconds,
        )
        final_status = str(decision.status)
        if final_status not in ("trusted", "quarantined"):
            raise ValueError("admission must finalize trusted or quarantined")
        add_result = mem0_client.add(
            item["fact"],
            user_id="default",
            infer=False,
            metadata={
                "source": "obsidian-reviewed-import",
                "batch_id": plan["batch_id"],
                "candidate_id": item["candidate_id"],
                "temporal_visibility": item["temporal_visibility"],
            },
        )
        mem0_id = str(add_result["results"][0]["id"])
        memory_index_id = shadow_store.record_memory(
            mem0_id=mem0_id,
            session_id=f"import:{plan['batch_id']}",
            memory_type="semantic",
            importance_score=8,
            entities=[],
            relations=[],
            status=final_status,
            flagged_reason=decision.flagged_reason,
        )
        if item["temporal_visibility"] == "historical":
            shadow_store.mark_import_historical(memory_index_id)
        shadow_store.record_import_provenance(
            batch_id=plan["batch_id"],
            idempotency_key=item["idempotency_key"],
            memory_index_id=memory_index_id,
            candidate_id=item["candidate_id"],
            source_path=item["source_path"],
            source_sha256=item["source_sha256"],
            temporal_visibility=item["temporal_visibility"],
        )
        results.append({"candidate_id": item["candidate_id"], "status": final_status})
    return results
