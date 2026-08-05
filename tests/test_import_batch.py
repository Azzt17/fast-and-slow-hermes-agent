from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins/memory/hermes-dual-memory"
SCRIPT = ROOT / "plugins/memory/hermes-dual-memory/import_batch.py"


def load_module():
    spec = importlib.util.spec_from_file_location("import_batch", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ImportBatchTest(unittest.TestCase):
    def test_plan_only_includes_approved_and_preserves_temporal_gate(self):
        module = load_module()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "ledger.jsonl"
            records = [
                {"candidate_id": "stable", "fact": "pref", "source_path": "a.md", "source_sha256": "a" * 64, "review_status": "approved_stable"},
                {"candidate_id": "old", "fact": "idea", "source_path": "b.md", "source_sha256": "b" * 64, "review_status": "approved_historical_only"},
                {"candidate_id": "skip", "fact": "no", "source_path": "c.md", "source_sha256": "c" * 64, "review_status": "excluded_by_farid"},
            ]
            ledger.write_text("".join(json.dumps(row) + "\n" for row in records))
            plan = module.plan_import(module.load_approved_candidates(ledger), batch_id="batch-1")
        self.assertFalse(plan["memory_write"])
        self.assertTrue(plan["requires_explicit_write_approval"])
        self.assertEqual([item["candidate_id"] for item in plan["items"]], ["stable", "old"])
        self.assertEqual(plan["items"][0]["temporal_visibility"], "current")
        self.assertEqual(plan["items"][1]["temporal_visibility"], "historical")
        self.assertTrue(all(item["admission"] == "required_fail_closed" for item in plan["items"]))

    def test_rejects_duplicate_provenance(self):
        module = load_module()
        candidate = {
            "candidate_id": "same",
            "fact": "same fact",
            "source_path": "same.md",
            "source_sha256": "a" * 64,
            "review_status": "approved_stable",
        }
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.plan_import([candidate, candidate], batch_id="batch-1")

    def test_execution_requires_explicit_write_approval(self):
        class FakeMem0:
            def add(self, content, **kwargs):
                return {"results": [{"id": "unused"}]}

        with tempfile.TemporaryDirectory() as directory:
            storage_spec = importlib.util.spec_from_file_location("approval_storage", PLUGIN_DIR / "storage.py")
            assert storage_spec and storage_spec.loader
            storage_module = importlib.util.module_from_spec(storage_spec)
            storage_spec.loader.exec_module(storage_module)
            store = storage_module.HotSessionStore(Path(directory))
            candidate = {"candidate_id": "stable", "fact": "fact", "source_path": "a.md", "source_sha256": "a" * 64, "review_status": "approved_stable"}
            planner = load_module()
            plan = planner.plan_import([candidate], batch_id="batch-approval")
            with self.assertRaisesRegex(PermissionError, "explicit write approval"):
                planner.execute_import(
                    plan, mem0_client=FakeMem0(), shadow_store=store,
                    llm_call=lambda **kwargs: '{"safe": true}',
                    admission_timeout_seconds=1,
                )

    def test_production_prefetch_blocks_historical_and_rolled_back_imports(self):
        class FakeMem0:
            def __init__(self):
                self.items = []

            def add(self, content, **kwargs):
                memory_id = f"mem-{len(self.items) + 1}"
                self.items.append({"id": memory_id, "memory": content, "metadata": kwargs["metadata"]})
                return {"results": [{"id": memory_id}]}

            def search(self, query, **kwargs):
                return {"results": self.items}

        spec = importlib.util.spec_from_file_location("import_provider", PLUGIN_DIR / "__init__.py")
        assert spec and spec.loader
        provider_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(provider_module)
        with tempfile.TemporaryDirectory() as directory:
            mem0 = FakeMem0()
            provider = provider_module.MemoryProvider()
            provider.initialize("import-test", hermes_home=directory, mem0_client=mem0, llm_callable=lambda **kwargs: '{"safe": true}')
            candidates = [
                {"candidate_id": "stable", "fact": "Stable preference.", "source_path": "a.md", "source_sha256": "a" * 64, "review_status": "approved_stable"},
                {"candidate_id": "old", "fact": "Historical idea.", "source_path": "b.md", "source_sha256": "b" * 64, "review_status": "approved_historical_only"},
            ]
            planner = load_module()
            plan = planner.plan_import(candidates, batch_id="batch-visibility")
            def llm_call(**kwargs):
                if kwargs["task"] == "memory_admission":
                    return '{"safe": true, "reason": "test"}'
                payload = json.loads(kwargs["messages"][1]["content"])
                return json.dumps({candidate["id"]: True for candidate in payload["candidates"]})

            planner.execute_import(
                plan, mem0_client=mem0, shadow_store=provider._store,
                llm_call=llm_call, admission_timeout_seconds=1, write_approved=True,
            )
            self.assertIn("Stable preference.", provider.prefetch("What is the preference?"))
            self.assertNotIn("Historical idea.", provider.prefetch("What is the preference?"))
            self.assertIn("Historical idea.", provider.prefetch("What was the historical idea?"))
            provider._store.rollback_import_batch("batch-visibility")
            self.assertEqual(provider.prefetch("What was the historical idea?"), "")
            provider.shutdown()


if __name__ == "__main__":
    unittest.main()

class ImportBatchExecutionTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        storage_path = ROOT / "plugins/memory/hermes-dual-memory/storage.py"
        spec = importlib.util.spec_from_file_location("import_storage", storage_path)
        assert spec and spec.loader
        self.storage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.storage_module)

    def test_import_records_provenance_historical_and_rollback(self):
        class FakeMem0:
            def __init__(self):
                self.calls = []

            def add(self, content, **kwargs):
                self.calls.append((content, kwargs))
                return {"results": [{"id": f"mem-{len(self.calls)}"}]}

        with tempfile.TemporaryDirectory() as directory:
            store = self.storage_module.HotSessionStore(Path(directory))
            candidates = [
                {"candidate_id": "stable", "fact": "stable fact", "source_path": "a.md", "source_sha256": "a" * 64, "review_status": "approved_stable"},
                {"candidate_id": "old", "fact": "old idea", "source_path": "b.md", "source_sha256": "b" * 64, "review_status": "approved_historical_only"},
            ]
            plan = self.module.plan_import(candidates, batch_id="batch-1")
            mem0 = FakeMem0()
            results = self.module.execute_import(
                plan,
                mem0_client=mem0,
                shadow_store=store,
                llm_call=lambda **kwargs: '{"safe": true, "reason": "test"}', admission_timeout_seconds=1,
                write_approved=True,
            )
            self.assertEqual([result["status"] for result in results], ["trusted", "trusted"])
            self.assertTrue(all(call[1]["infer"] is False for call in mem0.calls))
            historical = store.import_provenance(plan["items"][1]["idempotency_key"])
            self.assertEqual(historical["temporal_visibility"], "historical")
            with store.connect() as connection:
                row = connection.execute(
                    "SELECT t_invalid FROM memory_index WHERE id = ?",
                    (historical["memory_index_id"],),
                ).fetchone()
            self.assertIsNotNone(row["t_invalid"])
            self.assertEqual(
                self.module.execute_import(plan, mem0_client=mem0, shadow_store=store, llm_call=lambda **kwargs: '{"safe": true, "reason": "test"}', admission_timeout_seconds=1, write_approved=True),
                [{"candidate_id": "stable", "status": "already_imported"}, {"candidate_id": "old", "status": "already_imported"}],
            )
            self.assertEqual(store.rollback_import_batch("batch-1"), 2)
            with store.connect() as connection:
                statuses = connection.execute(
                    "SELECT status FROM memory_index ORDER BY id"
                ).fetchall()
            self.assertEqual([row["status"] for row in statuses], ["quarantined", "quarantined"])

    def test_quarantined_import_stays_quarantined(self):
        class FakeMem0:
            def add(self, content, **kwargs):
                return {"results": [{"id": "mem-quarantine"}]}

        with tempfile.TemporaryDirectory() as directory:
            store = self.storage_module.HotSessionStore(Path(directory))
            candidate = {"candidate_id": "unsafe", "fact": "unsafe", "source_path": "a.md", "source_sha256": "a" * 64, "review_status": "approved_stable"}
            plan = self.module.plan_import([candidate], batch_id="batch-2")
            result = self.module.execute_import(
                plan,
                mem0_client=FakeMem0(),
                shadow_store=store,
                llm_call=None, admission_timeout_seconds=1, write_approved=True,
            )
            self.assertEqual(result[0]["status"], "quarantined")
            with store.connect() as connection:
                status = connection.execute("SELECT status FROM memory_index").fetchone()["status"]
            self.assertEqual(status, "quarantined")
