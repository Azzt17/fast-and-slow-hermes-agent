from __future__ import annotations

import importlib.util
import tempfile
import time
import unittest
from pathlib import Path


def _load_provider_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "plugins"
        / "memory"
        / "hermes-dual-memory"
        / "__init__.py"
    )
    spec = importlib.util.spec_from_file_location("hermes_dual_memory_provider_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _wait_for_rows(store, session_id: str, expected_count: int, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    last_rows = []
    while time.monotonic() < deadline:
        rows = store.fetch_turns(session_id)
        last_rows = rows
        if len(rows) >= expected_count:
            return rows
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {expected_count} rows; last={last_rows!r}")


class MemoryProviderSyncTest(unittest.TestCase):
    def test_initialize_scopes_storage_and_sync_turn_writes_via_daemon_thread(self) -> None:
        provider_mod = _load_provider_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "hermes-home"
            provider = provider_mod.MemoryProvider()

            provider.initialize("session-sync-001", hermes_home=str(hermes_home), platform="cli")

            assert provider._store is not None
            self.assertEqual(
                provider._store.db_path,
                hermes_home / "hermes-dual-memory" / "hot_sessions.sqlite3",
            )

            provider.sync_turn(
                "user line for sync_turn",
                "assistant line for sync_turn",
                session_id="session-sync-001",
                messages=[
                    {"role": "user", "content": "user line for sync_turn"},
                    {"role": "assistant", "content": "assistant line for sync_turn"},
                ],
            )

            self.assertTrue(provider._sync_threads)
            self.assertTrue(provider._sync_threads[-1].daemon)

            rows = _wait_for_rows(provider._store, "session-sync-001", 2)
            self.assertEqual(len(rows), 2)
            self.assertEqual([row["role"] for row in rows], ["user", "assistant"])
            self.assertEqual(rows[0]["content"], "user line for sync_turn")
            self.assertEqual(rows[1]["content"], "assistant line for sync_turn")
            self.assertEqual(rows[0]["session_id"], "session-sync-001")
            self.assertEqual(rows[1]["session_id"], "session-sync-001")
            self.assertEqual(provider._store.pending_count("session-sync-001"), 2)


if __name__ == "__main__":
    unittest.main()
