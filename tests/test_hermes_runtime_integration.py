from __future__ import annotations

import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

EXPECTED_HERMES_PYTHON = Path("/home/wajdi/.hermes/hermes-agent/venv/bin/python").resolve()
HERMES_SOURCE_ROOT = Path("/home/wajdi/.hermes/hermes-agent").resolve()
REPO_PROVIDER_DIR = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "memory"
    / "hermes-dual-memory"
)


def _wait_for_rows(store, session_id: str, expected_count: int, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    last_rows = []
    while time.monotonic() < deadline:
        rows = store.fetch_turns(session_id)
        last_rows = rows
        if len(rows) >= expected_count:
            return rows
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {expected_count} hot-session rows; saw {last_rows!r}")


@unittest.skipUnless(Path(sys.executable).resolve() == EXPECTED_HERMES_PYTHON, "run with Hermes venv Python")
class HermesMemoryHookIntegrationTest(unittest.TestCase):
    def test_sync_all_routes_into_hot_sessions_via_loaded_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hermes_home = Path(tmpdir) / "hermes-home"
            provider_dir = hermes_home / "plugins" / "hermes-dual-memory"
            provider_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                REPO_PROVIDER_DIR,
                provider_dir,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )

            old_hermes_home = os.environ.get("HERMES_HOME")
            os.environ["HERMES_HOME"] = str(hermes_home)
            sys.path.insert(0, str(HERMES_SOURCE_ROOT))
            try:
                from agent.memory_manager import MemoryManager
                from plugins.memory import load_memory_provider

                provider = load_memory_provider("hermes-dual-memory")
                self.assertIsNotNone(provider)
                assert provider is not None

                provider.initialize("session-integration-001", hermes_home=str(hermes_home), platform="cli")

                manager = MemoryManager()
                manager.add_provider(provider)
                manager.sync_all(
                    "user turn for Hermes hook integration",
                    "assistant turn persisted by sync_turn",
                    session_id="session-integration-001",
                    messages=[
                        {"role": "user", "content": "user turn for Hermes hook integration"},
                        {"role": "assistant", "content": "assistant turn persisted by sync_turn"},
                    ],
                )

                self.assertTrue(manager.flush_pending(timeout=5.0))

                store = provider._store  # internal on purpose: we are verifying the hot-tier write path
                self.assertIsNotNone(store)
                rows = _wait_for_rows(store, "session-integration-001", 2)

                self.assertEqual([row["role"] for row in rows[:2]], ["user", "assistant"])
                self.assertEqual(rows[0]["content"], "user turn for Hermes hook integration")
                self.assertEqual(rows[1]["content"], "assistant turn persisted by sync_turn")
                self.assertEqual(rows[0]["consolidated"], 0)
                self.assertEqual(rows[1]["consolidated"], 0)
                self.assertEqual(store.pending_count("session-integration-001"), 2)
                self.assertEqual(
                    store.db_path,
                    hermes_home / "hermes-dual-memory" / "hot_sessions.sqlite3",
                )
            finally:
                try:
                    sys.path.remove(str(HERMES_SOURCE_ROOT))
                except ValueError:
                    pass
                if old_hermes_home is None:
                    os.environ.pop("HERMES_HOME", None)
                else:
                    os.environ["HERMES_HOME"] = old_hermes_home


if __name__ == "__main__":
    unittest.main()
