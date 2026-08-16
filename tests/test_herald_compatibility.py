from __future__ import annotations

import hashlib
import importlib.util
import os
import tempfile
import time
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins" / "memory" / "hermes-dual-memory"


def _load_provider_module():
    spec = importlib.util.spec_from_file_location(
        "hermes_dual_memory_herald_test",
        PLUGIN_DIR / "__init__.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_storage_module():
    spec = importlib.util.spec_from_file_location(
        "hermes_dual_memory_herald_storage_test",
        PLUGIN_DIR / "storage.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HeraldCompatibilityTest(unittest.TestCase):
    def test_agent_context_subagent_skips_sync_write(self) -> None:
        provider_mod = _load_provider_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "hermes-home"
            provider = provider_mod.MemoryProvider()
            try:
                provider.initialize(
                    "session-subagent",
                    hermes_home=str(hermes_home),
                    platform="cli",
                    agent_context="subagent",
                )
                provider.sync_turn("user line", "assistant line", session_id="session-subagent")
                time.sleep(0.2)
                self.assertIsNotNone(provider._store)
                store = provider._store
                assert store is not None
                self.assertEqual(store.pending_count("session-subagent"), 0)
            finally:
                provider.shutdown()

    def test_agent_context_cron_skips_sync_write(self) -> None:
        provider_mod = _load_provider_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "hermes-home"
            provider = provider_mod.MemoryProvider()
            try:
                provider.initialize(
                    "session-cron",
                    hermes_home=str(hermes_home),
                    platform="cron",
                    agent_context="cron",
                )
                provider.sync_turn("cron user", "cron assistant", session_id="session-cron")
                time.sleep(0.2)
                self.assertIsNotNone(provider._store)
                store = provider._store
                assert store is not None
                self.assertEqual(store.pending_count("session-cron"), 0)
            finally:
                provider.shutdown()

    def test_agent_context_primary_writes(self) -> None:
        provider_mod = _load_provider_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "hermes-home"
            provider = provider_mod.MemoryProvider()
            try:
                provider.initialize(
                    "session-primary",
                    hermes_home=str(hermes_home),
                    platform="cli",
                    agent_context="primary",
                )
                provider.sync_turn("user line", "assistant line", session_id="session-primary")
                deadline = time.monotonic() + 3.0
                while time.monotonic() < deadline:
                    if provider._store is not None and provider._store.pending_count("session-primary") >= 2:
                        break
                    time.sleep(0.05)
                self.assertIsNotNone(provider._store)
                store = provider._store
                assert store is not None
                self.assertEqual(store.pending_count("session-primary"), 2)
            finally:
                provider.shutdown()

    def test_backup_paths_without_initialize(self) -> None:
        provider_mod = _load_provider_module()
        provider = provider_mod.MemoryProvider()
        old_home = os.environ.get("HERMES_HOME")
        try:
            os.environ["HERMES_HOME"] = "/tmp/herald-test-home"
            paths = provider.backup_paths()
            self.assertEqual(paths, ["/tmp/herald-test-home/hermes-dual-memory"])
        finally:
            if old_home is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = old_home

    def test_on_memory_write_creates_audit_trail_only(self) -> None:
        provider_mod = _load_provider_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "hermes-home"
            provider = provider_mod.MemoryProvider()
            try:
                provider.initialize("session-audit", hermes_home=str(hermes_home), platform="cli")
                self.assertIsNotNone(provider._store)
                store = provider._store
                assert store is not None
                before_mem = len(store.fetch_memory_index())

                provider.on_memory_write(
                    "add", "memory", "Farid suka kopi", {"write_origin": "test"}
                )
                entries = store.audit_entries(limit=10)
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["action"], "add")
                self.assertEqual(entries[0]["target"], "memory")
                expected_hash = hashlib.sha256("Farid suka kopi".encode("utf-8")).hexdigest()
                self.assertEqual(entries[0]["content_hash"], expected_hash)
                # No shadow / Mem0 write may result from a core-memory write.
                self.assertEqual(len(store.fetch_memory_index()), before_mem)
            finally:
                provider.shutdown()

    def test_on_session_switch_records_parent_lineage(self) -> None:
        provider_mod = _load_provider_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "hermes-home"
            provider = provider_mod.MemoryProvider()
            try:
                provider.initialize("session-old", hermes_home=str(hermes_home), platform="cli")
                provider.sync_turn("user a", "assistant a", session_id="session-old")
                deadline = time.monotonic() + 3.0
                while time.monotonic() < deadline:
                    if provider._store is not None and provider._store.pending_count("session-old") >= 1:
                        break
                    time.sleep(0.05)
                provider.on_session_switch(
                    "session-new", parent_session_id="session-old", reset=False
                )
                self.assertIsNotNone(provider._store)
                store = provider._store
                assert store is not None
                rows = store.fetch_turns("session-old")
                self.assertGreaterEqual(len(rows), 1)
                self.assertEqual(rows[0]["parent_session_id"], "session-old")
            finally:
                provider.shutdown()

    def test_schema_migration_is_idempotent(self) -> None:
        storage_mod = _load_storage_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "store"
            store = storage_mod.HotSessionStore(base)
            store._ensure_schema()  # second run must not fail
            store._ensure_schema()
            self.assertIsNotNone(store)


if __name__ == "__main__":
    unittest.main()
