from __future__ import annotations

import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins" / "memory" / "hermes-dual-memory"


def load_provider_module():
    spec = importlib.util.spec_from_file_location("hermes_dual_memory_provider_test", PLUGIN_DIR / "__init__.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeMem0:
    def __init__(self):
        self.calls = []

    def add(self, content, **kwargs):
        self.calls.append((content, kwargs))
        return {"results": [{"id": f"fake-memory-{len(self.calls)}"}]}


class ConsolidationTest(unittest.TestCase):
    def setUp(self):
        self.module = load_provider_module()
        self.payload = (
            '{"summary":"Hermes uses a dual memory provider",'
            '"new_skills":[],"anomalies":[],"entities":[],'
            '"relations":[],"memory_type":"semantic","importance_score":8}'
        )

    def test_pre_compress_retries_and_writes_structured_mem0_without_inference(self):
        mem0 = FakeMem0()
        responses = iter(["not json", self.payload])
        consolidation_messages = []

        def llm_call(**kwargs):
            if kwargs["task"] == "memory_admission":
                return '{"safe":true,"reason":"ordinary durable fact"}'
            self.assertEqual(kwargs["task"], "memory_consolidation")
            consolidation_messages.append(kwargs["messages"])
            return next(responses)

        with tempfile.TemporaryDirectory() as tmp:
            provider = self.module.MemoryProvider()
            provider.initialize("session-1", hermes_home=tmp, mem0_client=mem0, llm_callable=llm_call)
            provider.sync_turn("user fact", "assistant acknowledgement", session_id="session-1")
            provider.shutdown()

            provider = self.module.MemoryProvider()
            provider.initialize("session-1", hermes_home=tmp, mem0_client=mem0, llm_callable=llm_call)
            summary = provider.on_pre_compress([])
            self.assertEqual(summary, "Hermes uses a dual memory provider")
            self.assertEqual(provider._store.pending_count("session-1"), 0)
            content, kwargs = mem0.calls[-1]
            self.assertEqual(content, summary)
            self.assertFalse(kwargs["infer"])
            self.assertEqual(kwargs["user_id"], "default")
            self.assertEqual(kwargs["metadata"]["session_id"], "session-1")
            self.assertEqual(kwargs["metadata"]["importance_score"], 8)
            self.assertEqual(kwargs["metadata"]["memory_type"], "semantic")
            self.assertEqual(kwargs["metadata"]["entities"], "[]")
            self.assertEqual(len(consolidation_messages), 2)
            self.assertIn("Respons sebelumnya invalid", consolidation_messages[1][-1]["content"])
            self.assertEqual(consolidation_messages[0], consolidation_messages[1][:-1])

    def test_session_end_hook_is_daemon_and_consolidates(self):
        mem0 = FakeMem0()

        def llm_call(**kwargs):
            if kwargs["task"] == "memory_admission":
                return '{"safe":true,"reason":"ordinary durable fact"}'
            return self.payload

        with tempfile.TemporaryDirectory() as tmp:
            provider = self.module.MemoryProvider()
            provider.initialize("session-2", hermes_home=tmp, mem0_client=mem0, llm_callable=llm_call)
            provider.sync_turn("user fact", "assistant acknowledgement")
            deadline = time.monotonic() + 2
            while provider._store.pending_count("session-2") < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            provider.on_session_end([])
            deadline = time.monotonic() + 2
            while provider._store.pending_count("session-2") and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(provider._store.pending_count("session-2"), 0)
            self.assertTrue(any(thread.daemon for thread in provider._consolidation_threads))

    def test_invalid_report_does_not_mark_hot_rows(self):
        mem0 = FakeMem0()
        calls = 0

        def llm_call(**kwargs):
            nonlocal calls
            calls += 1
            return "still not json"

        with tempfile.TemporaryDirectory() as tmp:
            provider = self.module.MemoryProvider()
            provider.initialize("session-3", hermes_home=tmp, mem0_client=mem0, llm_callable=llm_call)
            provider.sync_turn("user fact", "assistant acknowledgement")
            deadline = time.monotonic() + 2
            while provider._store.pending_count("session-3") < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(provider.on_pre_compress([]), "")
            self.assertEqual(calls, 2)
            self.assertEqual(provider._store.pending_count("session-3"), 2)
            self.assertEqual(mem0.calls, [])

    def test_long_session_is_consolidated_in_bounded_whole_turn_chunks(self):
        mem0 = FakeMem0()
        calls = []

        def llm_call(**kwargs):
            if kwargs["task"] == "memory_admission":
                return '{"safe":true,"reason":"ordinary durable fact"}'
            calls.append(kwargs["messages"])
            return self.payload

        with tempfile.TemporaryDirectory() as tmp:
            provider = self.module.MemoryProvider()
            provider.initialize("session-long", hermes_home=tmp, mem0_client=mem0, llm_callable=llm_call)
            for _ in range(4):
                provider._store.add_turn("session-long", "x" * 3_000, role="user")
            summary = provider.on_pre_compress([])
            self.assertEqual(summary, "Hermes uses a dual memory provider")
            self.assertEqual(provider._store.pending_count("session-long"), 0)
            self.assertEqual(len(calls), 2)
            self.assertTrue(all(len(messages[1]["content"]) <= 6_800 for messages in calls))

    def test_oversized_turn_remains_whole_in_its_own_chunk(self):
        consolidation = self.module._consolidation
        rows = [
            {"content": "x" * 5_000},
            {"content": "y" * 2_000},
            {"content": "z" * 2_000},
        ]
        self.assertEqual([len(chunk) for chunk in consolidation.chunk_rows(rows)], [1, 2])

    def test_failed_chunk_leaves_it_and_later_chunks_pending(self):
        mem0 = FakeMem0()
        calls = 0

        def llm_call(**kwargs):
            nonlocal calls
            if kwargs["task"] == "memory_admission":
                return '{"safe":true,"reason":"ordinary durable fact"}'
            calls += 1
            if calls <= 2:
                return self.payload
            raise TimeoutError("combo timeout")

        with tempfile.TemporaryDirectory() as tmp:
            provider = self.module.MemoryProvider()
            provider.initialize("session-partial", hermes_home=tmp, mem0_client=mem0, llm_callable=llm_call)
            for _ in range(7):
                provider._store.add_turn("session-partial", "x" * 8_000, role="user")
            self.assertEqual(provider.on_pre_compress([]), "")
            self.assertEqual(provider._store.pending_count("session-partial"), 5)

    def test_new_skill_output_limits_are_enforced(self):
        consolidation = self.module._consolidation
        base = {
            "summary": "Reusable procedure",
            "new_skills": [],
            "anomalies": [],
            "entities": [],
            "relations": [],
            "memory_type": "episodic",
            "importance_score": 5,
        }
        too_many = dict(base, new_skills=[{"title": f"Skill {index}", "detail": "Do it."} for index in range(4)])
        with self.assertRaisesRegex(ValueError, "cannot exceed 3 items"):
            consolidation.parse_report(json.dumps(too_many))

        oversized = dict(base, new_skills=[{"title": "Valid title", "detail": "x" * 1201}])
        with self.assertRaisesRegex(ValueError, "detail cannot exceed 1200"):
            consolidation.parse_report(json.dumps(oversized))


if __name__ == "__main__":
    unittest.main()
