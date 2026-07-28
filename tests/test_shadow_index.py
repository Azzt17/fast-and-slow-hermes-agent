from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins" / "memory" / "hermes-dual-memory"


def load_provider_module():
    spec = importlib.util.spec_from_file_location(
        "hermes_dual_memory_shadow_test",
        PLUGIN_DIR / "__init__.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeMem0:
    def __init__(self):
        self.memories: list[dict[str, object]] = []

    def add(self, content, **kwargs):
        mem0_id = f"memory-{len(self.memories) + 1}"
        self.memories.append(
            {
                "id": mem0_id,
                "memory": content,
                "metadata": dict(kwargs["metadata"]),
                "created_at": f"2026-07-28T00:00:0{len(self.memories)}Z",
            }
        )
        return {"results": [{"id": mem0_id, "memory": content, "event": "ADD"}]}

    def search(self, query, **kwargs):
        del query, kwargs
        return {"results": list(reversed(self.memories))}

    def get(self, mem0_id):
        return next((item for item in self.memories if item["id"] == mem0_id), None)


def report(
    summary: str,
    *,
    memory_type: str = "semantic",
    target_id: str = "city-jakarta",
    target_label: str = "Jakarta",
    relation: str = "lives_in",
) -> str:
    return json.dumps(
        {
            "summary": summary,
            "new_skills": [],
            "anomalies": [],
            "entities": [
                {"id": "farid", "type": "person", "label": "Farid"},
                {"id": target_id, "type": "place", "label": target_label},
            ],
            "relations": [
                {"source": "farid", "target": target_id, "relation": relation},
            ],
            "memory_type": memory_type,
            "importance_score": 7,
        }
    )


class ShadowIndexTest(unittest.TestCase):
    def setUp(self):
        self.module = load_provider_module()

    def consolidate(
        self,
        *,
        tmpdir: str,
        mem0: FakeMem0,
        session_id: str,
        payload: str,
        contradiction: bool = False,
        contradiction_calls: list[dict[str, object]] | None = None,
    ):
        def llm_call(**kwargs):
            if kwargs["task"] == "memory_consolidation":
                return payload
            if contradiction_calls is not None:
                contradiction_calls.append(kwargs)
            return json.dumps({"contradiction": contradiction, "reason": "controlled test"})

        provider = self.module.MemoryProvider()
        provider.initialize(
            session_id,
            hermes_home=tmpdir,
            mem0_client=mem0,
            llm_callable=llm_call,
        )
        provider._store.add_turn(session_id, "controlled fact", role="user")
        self.assertTrue(provider.on_pre_compress([]))
        return provider

    def test_cross_session_contradiction_invalidates_old_and_filters_retrieval(self):
        mem0 = FakeMem0()
        with tempfile.TemporaryDirectory() as tmpdir:
            first = self.consolidate(
                tmpdir=tmpdir,
                mem0=mem0,
                session_id="session-a",
                payload=report("Farid lives in Jakarta."),
            )
            second = self.consolidate(
                tmpdir=tmpdir,
                mem0=mem0,
                session_id="session-b",
                payload=report(
                    "Farid lives in Bandung.",
                    target_id="city-bandung",
                    target_label="Bandung",
                ),
                contradiction=True,
            )

            rows = second._store.fetch_memory_index()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["mem0_id"], "memory-1")
            self.assertIsNotNone(rows[0]["t_invalid"])
            self.assertEqual(rows[0]["superseded_by"], "memory-2")
            self.assertEqual(rows[1]["mem0_id"], "memory-2")
            self.assertIsNone(rows[1]["t_invalid"])

            recalled = second.prefetch("Where does Farid live?")
            self.assertIn("Farid lives in Bandung.", recalled)
            self.assertNotIn("Farid lives in Jakarta.", recalled)
            first.shutdown()
            second.shutdown()

    def test_episodic_fact_does_not_invalidate_semantic_fact(self):
        mem0 = FakeMem0()
        contradiction_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            first = self.consolidate(
                tmpdir=tmpdir,
                mem0=mem0,
                session_id="session-semantic",
                payload=report("Farid lives in Jakarta."),
            )
            second = self.consolidate(
                tmpdir=tmpdir,
                mem0=mem0,
                session_id="session-episodic",
                payload=report(
                    "During this episode, Farid said he lived in Bandung.",
                    memory_type="episodic",
                    target_id="city-bandung",
                    target_label="Bandung",
                ),
                contradiction=True,
                contradiction_calls=contradiction_calls,
            )

            rows = second._store.fetch_memory_index()
            self.assertEqual([row["memory_type"] for row in rows], ["semantic", "episodic"])
            self.assertTrue(all(row["t_invalid"] is None for row in rows))
            self.assertEqual(contradiction_calls, [])
            first.shutdown()
            second.shutdown()

    def test_similar_multi_valued_claim_is_not_false_positive(self):
        mem0 = FakeMem0()
        contradiction_calls: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as tmpdir:
            first = self.consolidate(
                tmpdir=tmpdir,
                mem0=mem0,
                session_id="session-python",
                payload=report(
                    "Farid uses Python.",
                    target_id="python",
                    target_label="Python",
                    relation="uses",
                ),
            )
            second = self.consolidate(
                tmpdir=tmpdir,
                mem0=mem0,
                session_id="session-rust",
                payload=report(
                    "Farid also uses Rust.",
                    target_id="rust",
                    target_label="Rust",
                    relation="uses",
                ),
                contradiction=False,
                contradiction_calls=contradiction_calls,
            )

            rows = second._store.fetch_memory_index()
            self.assertTrue(all(row["t_invalid"] is None for row in rows))
            self.assertEqual(len(contradiction_calls), 1)
            recalled = second.prefetch("What does Farid use?")
            self.assertIn("Farid uses Python.", recalled)
            self.assertIn("Farid also uses Rust.", recalled)
            first.shutdown()
            second.shutdown()

    def test_legacy_mem0_result_without_shadow_remains_visible(self):
        mem0 = FakeMem0()
        mem0.memories.append(
            {
                "id": "legacy-memory",
                "memory": "Legacy Phase 3 fact.",
                "metadata": {"session_id": "legacy-session", "status": "trusted"},
                "created_at": "2026-07-27T00:00:00Z",
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self.module.MemoryProvider()
            provider.initialize(
                "session-new",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: "",
            )
            self.assertIn("Legacy Phase 3 fact.", provider.prefetch("legacy"))
            provider.shutdown()

    def test_non_trusted_shadow_is_hidden_by_existing_prefetch_path(self):
        mem0 = FakeMem0()
        mem0.memories.append(
            {
                "id": "candidate-memory",
                "memory": "Candidate fact must stay hidden.",
                "metadata": {"session_id": "candidate-session", "status": "trusted"},
                "created_at": "2026-07-28T00:00:00Z",
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self.module.MemoryProvider()
            provider.initialize(
                "session-new",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: "",
            )
            provider._store.record_memory(
                mem0_id="candidate-memory",
                session_id="candidate-session",
                memory_type="semantic",
                importance_score=5,
                entities=[],
                relations=[],
                status="candidate",
            )
            self.assertEqual(provider.prefetch("candidate"), "")
            provider.shutdown()

    def test_phase_4_mem0_orphan_without_shadow_is_hidden(self):
        mem0 = FakeMem0()
        mem0.memories.append(
            {
                "id": "orphan-memory",
                "memory": "Unindexed Phase 4 fact must stay hidden.",
                "metadata": {
                    "session_id": "orphan-session",
                    "status": "trusted",
                    "shadow_index_version": 1,
                },
                "created_at": "2026-07-28T00:00:00Z",
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self.module.MemoryProvider()
            provider.initialize(
                "session-new",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: "",
            )
            self.assertEqual(provider.prefetch("orphan"), "")
            provider.shutdown()

    def test_queued_prefetch_is_revalidated_after_shadow_invalidation(self):
        mem0 = FakeMem0()
        mem0.memories.append(
            {
                "id": "memory-old",
                "memory": "Farid lives in Jakarta.",
                "metadata": {"session_id": "session-old", "status": "trusted"},
                "created_at": "2026-07-28T00:00:00Z",
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self.module.MemoryProvider()
            provider.initialize(
                "session-new",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: "",
            )
            provider._store.record_memory(
                mem0_id="memory-old",
                session_id="session-old",
                memory_type="semantic",
                importance_score=5,
                entities=[],
                relations=[],
            )
            provider.queue_prefetch("Where does Farid live?")
            for thread in list(provider._prefetch_threads):
                thread.join(timeout=1)
            provider._store.record_memory(
                mem0_id="memory-new",
                session_id="session-new",
                memory_type="semantic",
                importance_score=5,
                entities=[],
                relations=[],
                supersedes=["memory-old"],
            )
            self.assertEqual(provider.prefetch("Where does Farid live?"), "")
            provider.shutdown()

    def test_missing_mem0_id_keeps_hot_rows_pending(self):
        class MissingIdMem0(FakeMem0):
            def add(self, content, **kwargs):
                del content, kwargs
                return {"results": []}

        mem0 = MissingIdMem0()
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = self.module.MemoryProvider()
            provider.initialize(
                "session-missing-id",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=lambda **_: report("Durable fact."),
            )
            provider._store.add_turn("session-missing-id", "durable fact", role="user")
            self.assertEqual(provider.on_pre_compress([]), "")
            self.assertEqual(provider._store.pending_count("session-missing-id"), 1)
            self.assertEqual(provider._store.fetch_memory_index(), [])
            provider.shutdown()


if __name__ == "__main__":
    unittest.main()
