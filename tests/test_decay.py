from __future__ import annotations

import importlib.util
import json
import math
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins" / "memory" / "hermes-dual-memory"


def load_provider_module():
    spec = importlib.util.spec_from_file_location(
        "hermes_dual_memory_decay_test",
        PLUGIN_DIR / "__init__.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeMem0:
    def __init__(self):
        self.memories: dict[str, dict[str, object]] = {}
        self.add_calls: list[tuple[str, dict[str, object]]] = []

    def seed(self, mem0_id: str, content: str, *, session_id: str = "seed") -> None:
        self.memories[mem0_id] = {
            "id": mem0_id,
            "memory": content,
            "metadata": {"session_id": session_id, "status": "trusted"},
            "created_at": "2026-07-01T00:00:00Z",
            "score": 0.95,
        }

    def get(self, mem0_id):
        return self.memories.get(mem0_id)

    def search(self, query, **kwargs):
        del query, kwargs
        return {"results": [dict(memory) for memory in self.memories.values()]}

    def add(self, content, **kwargs):
        mem0_id = f"compacted-{len(self.add_calls) + 1}"
        self.add_calls.append((content, kwargs))
        self.memories[mem0_id] = {
            "id": mem0_id,
            "memory": content,
            "metadata": dict(kwargs["metadata"]),
            "created_at": "2026-07-28T00:00:00Z",
            "score": 0.95,
        }
        return {"results": [{"id": mem0_id, "memory": content, "event": "ADD"}]}


class DecayTest(unittest.TestCase):
    def setUp(self):
        self.module = load_provider_module()
        self.now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)

    def add_shadow(
        self,
        store,
        mem0_id: str,
        *,
        memory_type: str = "episodic",
        importance_score: int = 4,
    ) -> None:
        store.record_memory(
            mem0_id=mem0_id,
            session_id=f"session-{mem0_id}",
            memory_type=memory_type,
            importance_score=importance_score,
            entities=[],
            relations=[],
        )

    def age_shadow(self, store, mem0_id: str, *, days: float) -> None:
        timestamp = self.module._storage.db_timestamp(self.now - timedelta(days=days))
        with store.connect() as conn:
            conn.execute(
                """
                UPDATE memory_index
                SET t_created = ?, last_accessed = ?
                WHERE mem0_id = ?
                """,
                (timestamp, timestamp, mem0_id),
            )

    def test_decay_formula_and_basic_demotion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)
            self.add_shadow(store, "episodic-old", importance_score=4)
            self.age_shadow(store, "episodic-old", days=4)

            row = store.episodic_decay_candidates()[0]
            self.assertAlmostEqual(
                self.module._decay.retrievability(row, now=self.now),
                math.exp(-4 / 2),
            )
            result = self.module._decay.run_decay_cycle(
                shadow_store=store,
                mem0_client=None,
                llm_call=None,
                user_id="default",
                now=self.now,
                already_claimed=True,
            )

            self.assertEqual(result["demoted"], ["episodic-old"])
            self.assertEqual(store.fetch_memory_index()[0]["tier"], "cold")

    def test_semantic_memory_is_fully_excluded_from_decay(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)
            self.add_shadow(store, "episodic-old", memory_type="episodic")
            self.add_shadow(store, "semantic-old", memory_type="semantic")
            self.age_shadow(store, "episodic-old", days=30)
            self.age_shadow(store, "semantic-old", days=30)

            result = self.module._decay.run_decay_cycle(
                shadow_store=store,
                mem0_client=None,
                llm_call=None,
                user_id="default",
                now=self.now,
                already_claimed=True,
            )
            rows = {row["mem0_id"]: row for row in store.fetch_memory_index()}

            self.assertEqual(result["demoted"], ["episodic-old"])
            self.assertEqual(rows["episodic-old"]["tier"], "cold")
            self.assertEqual(rows["semantic-old"]["tier"], "warm")
            self.assertEqual(rows["semantic-old"]["access_count"], 0)

    def test_cold_memory_promotes_after_two_accesses_within_seven_days(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)
            self.add_shadow(store, "cold-recalled", importance_score=4)
            store.demote_memories(["cold-recalled"], demoted_at=self.now)

            store.record_accesses(["cold-recalled"], accessed_at=self.now + timedelta(days=1))
            first = store.fetch_memory_index()[0]
            self.assertEqual(first["tier"], "cold")
            store.record_accesses(["cold-recalled"], accessed_at=self.now + timedelta(days=2))
            second = store.fetch_memory_index()[0]

            self.assertEqual(second["tier"], "warm")
            self.assertEqual(second["access_count"], 2)
            self.assertAlmostEqual(second["stability"], 4.5)

    def test_cold_memory_does_not_promote_after_seven_day_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)
            self.add_shadow(store, "cold-expired", importance_score=4)
            store.demote_memories(["cold-expired"], demoted_at=self.now)

            store.record_accesses(["cold-expired"], accessed_at=self.now + timedelta(days=8))
            store.record_accesses(["cold-expired"], accessed_at=self.now + timedelta(days=9))
            row = store.fetch_memory_index()[0]

            self.assertEqual(row["tier"], "cold")
            self.assertEqual(row["access_count"], 2)

    def test_retrieval_updates_access_metrics_only_when_consumed(self):
        mem0 = FakeMem0()
        mem0.seed("retrieved", "Representative episodic memory.")
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self.module.MemoryProvider()
            provider.initialize(
                "session-retrieval",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: '{"c0":true}',
            )
            for thread in list(provider._maintenance_threads):
                thread.join(timeout=1)
            self.add_shadow(provider._store, "retrieved", importance_score=4)

            provider.queue_prefetch("representative")
            for thread in list(provider._prefetch_threads):
                thread.join(timeout=1)
            self.assertEqual(provider._store.fetch_memory_index()[0]["access_count"], 0)
            provider.prefetch("representative")
            row = provider._store.fetch_memory_index()[0]

            self.assertEqual(row["access_count"], 1)
            self.assertAlmostEqual(row["stability"], 3.0)
            self.assertIsNotNone(row["last_accessed"])
            provider.shutdown()

    def test_cold_compaction_preserves_source_lineage(self):
        mem0 = FakeMem0()
        mem0.seed("cold-a", "Trip to Toraja included a coffee farm visit.")
        mem0.seed("cold-b", "During the Toraja trip, coffee beans were sampled.")
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)
            self.add_shadow(store, "cold-a", importance_score=4)
            self.add_shadow(store, "cold-b", importance_score=6)
            store.demote_memories(["cold-a", "cold-b"], demoted_at=self.now)

            result = self.module._decay.run_decay_cycle(
                shadow_store=store,
                mem0_client=mem0,
                llm_call=lambda **_: json.dumps(
                    {
                        "summary": "A Toraja trip centered on visiting and sampling at coffee farms.",
                        "importance_score": 5,
                    }
                ),
                user_id="default",
                now=self.now,
                already_claimed=True,
            )
            rows = {row["mem0_id"]: row for row in store.fetch_memory_index()}

            self.assertEqual(len(result["compacted"]), 1)
            self.assertEqual(
                mem0.memories["compacted-1"]["memory"],
                "A Toraja trip centered on visiting and sampling at coffee farms.",
            )
            self.assertEqual(rows["compacted-1"]["tier"], "warm")
            self.assertEqual(rows["compacted-1"]["importance_score"], 6)
            self.assertIsNotNone(rows["cold-a"]["t_invalid"])
            self.assertIsNotNone(rows["cold-b"]["t_invalid"])
            self.assertEqual(rows["cold-a"]["superseded_by"], "compacted-1")
            self.assertEqual(rows["cold-b"]["superseded_by"], "compacted-1")
            self.assertEqual(
                store.fetch_compaction_sources("compacted-1"),
                ["cold-a", "cold-b"],
            )

    def test_decay_trigger_runs_once_within_twenty_four_hours_across_hooks(self):
        mem0 = FakeMem0()
        calls: list[str] = []

        def fake_cycle(**kwargs):
            del kwargs
            calls.append("run")
            return {"ran": True, "demoted": [], "compacted": []}

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            self.module._decay,
            "run_decay_cycle",
            side_effect=fake_cycle,
        ):
            first = self.module.MemoryProvider()
            first.initialize(
                "session-first",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: "",
            )
            for thread in list(first._maintenance_threads):
                thread.join(timeout=1)
            first.on_session_end([])
            for thread in list(first._consolidation_threads):
                thread.join(timeout=1)
            first.shutdown()

            second = self.module.MemoryProvider()
            second.initialize(
                "session-second",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: "",
            )
            for thread in list(second._maintenance_threads):
                thread.join(timeout=1)

            self.assertEqual(calls, ["run"])
            self.assertIsNotNone(second._store.get_maintenance_state("last_decay_run"))
            second.shutdown()

    def test_persistent_decay_claim_reopens_after_twenty_four_hours(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)

            self.assertTrue(store.claim_decay_cycle(now=self.now))
            self.assertFalse(store.claim_decay_cycle(now=self.now + timedelta(hours=23)))
            self.assertTrue(store.claim_decay_cycle(now=self.now + timedelta(hours=24)))

    def test_compaction_timeout_is_graceful_and_sources_remain_active(self):
        mem0 = FakeMem0()
        mem0.seed("cold-a", "Related cold memory one.")
        mem0.seed("cold-b", "Related cold memory two.")

        def slow_llm(**kwargs):
            del kwargs
            time.sleep(0.2)
            return json.dumps({"summary": "late", "importance_score": 1})

        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)
            self.add_shadow(store, "cold-a")
            self.add_shadow(store, "cold-b")
            store.demote_memories(["cold-a", "cold-b"], demoted_at=self.now)

            started = time.monotonic()
            result = self.module._decay.run_decay_cycle(
                shadow_store=store,
                mem0_client=mem0,
                llm_call=slow_llm,
                user_id="default",
                now=self.now,
                already_claimed=True,
                timeout_seconds=0.02,
            )
            elapsed = time.monotonic() - started
            rows = store.fetch_memory_index()

            self.assertLess(elapsed, 0.15)
            self.assertEqual(result["compacted"], [])
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["tier"] == "cold" for row in rows))
            self.assertTrue(all(row["t_invalid"] is None for row in rows))
            self.assertEqual(mem0.add_calls, [])

    def test_quarantined_compaction_does_not_invalidate_sources(self):
        mem0 = FakeMem0()
        mem0.seed("cold-a", "Related cold memory one.")
        mem0.seed("cold-b", "Related cold memory two.")
        decision = self.module._admission.AdmissionDecision(
            status="quarantined",
            flagged_reason="semantic_unsafe:compacted injection",
            pattern_findings=(),
            semantic_checked=True,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.module.HotSessionStore(tmpdir)
            self.add_shadow(store, "cold-a")
            self.add_shadow(store, "cold-b")
            store.demote_memories(["cold-a", "cold-b"], demoted_at=self.now)

            result = self.module._decay.run_decay_cycle(
                shadow_store=store,
                mem0_client=mem0,
                llm_call=lambda **_: json.dumps(
                    {"summary": "Unsafe compacted instruction.", "importance_score": 5}
                ),
                user_id="default",
                now=self.now,
                already_claimed=True,
                admission_check=lambda _: decision,
            )
            rows = {row["mem0_id"]: row for row in store.fetch_memory_index()}

            self.assertEqual(result["compacted"][0]["status"], "quarantined")
            self.assertEqual(rows["compacted-1"]["status"], "quarantined")
            self.assertTrue(all(rows[mem0_id]["t_invalid"] is None for mem0_id in ("cold-a", "cold-b")))
            self.assertTrue(all(rows[mem0_id]["superseded_by"] is None for mem0_id in ("cold-a", "cold-b")))
            self.assertEqual(store.fetch_compaction_sources("compacted-1"), [])


if __name__ == "__main__":
    unittest.main()
