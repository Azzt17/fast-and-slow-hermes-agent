from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


def _load_storage_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "plugins"
        / "memory"
        / "hermes-dual-memory"
        / "storage.py"
    )
    spec = importlib.util.spec_from_file_location("hermes_dual_memory_storage_test", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HotSessionStoreTest(unittest.TestCase):
    def test_hot_session_store_insert_and_fetch(self) -> None:
        storage = _load_storage_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            store = storage.HotSessionStore(Path(tmpdir) / "hermes_home")

            first_id = store.add_turn(
                "session-001",
                "user said hello",
                role="user",
                token_count=3,
            )
            second_id = store.add_turn(
                "session-001",
                "assistant replied",
                role="assistant",
                token_count=2,
            )

            rows = store.fetch_turns("session-001")

            self.assertEqual(len(rows), 2)
            self.assertEqual([row["id"] for row in rows], [first_id, second_id])
            self.assertEqual(rows[0]["session_id"], "session-001")
            self.assertEqual(rows[0]["role"], "user")
            self.assertEqual(rows[0]["content"], "user said hello")
            self.assertEqual(rows[0]["token_count"], 3)
            self.assertEqual(rows[0]["consolidated"], 0)
            self.assertEqual(rows[1]["role"], "assistant")
            self.assertEqual(rows[1]["content"], "assistant replied")
            self.assertEqual(rows[1]["token_count"], 2)
            self.assertEqual(rows[1]["consolidated"], 0)
            self.assertEqual(store.pending_count("session-001"), 2)


if __name__ == "__main__":
    unittest.main()
