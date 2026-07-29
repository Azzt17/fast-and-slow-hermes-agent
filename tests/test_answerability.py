from __future__ import annotations

import importlib.util
import json
import time
import unittest
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "memory"
    / "hermes-dual-memory"
    / "answerability.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "hermes_dual_memory_answerability_test",
        MODULE_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AnswerabilityTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()
        self.candidates = [
            {"id": "c0", "content": "Farid prefers Toraja coffee."},
            {"id": "c1", "content": "Farid's favorite constellation is Orion."},
        ]

    def test_batch_keeps_only_direct_evidence_and_records_usage(self):
        calls = []

        def llm_call(**kwargs):
            calls.append(kwargs)
            return {
                "content": json.dumps({"c0": False, "c1": True}),
                "usage": {"prompt_tokens": 120, "completion_tokens": 30},
            }

        decision = self.module.verify_answerability(
            "What is Farid's favorite constellation?",
            self.candidates,
            llm_call=llm_call,
            timeout_seconds=0.5,
        )

        self.assertEqual(decision.status, "verified")
        self.assertEqual(decision.accepted_ids, ("c1",))
        self.assertEqual(decision.prompt_tokens, 120)
        self.assertEqual(decision.completion_tokens, 30)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["max_tokens"], 500)
        self.assertEqual(calls[0]["timeout"], 0.25)
        self.assertEqual(
            calls[0]["extra_body"],
            {"response_format": {"type": "json_object"}},
        )
        payload = json.loads(calls[0]["messages"][1]["content"])
        self.assertEqual([item["id"] for item in payload["candidates"]], ["c0", "c1"])

    def test_missing_or_duplicate_decisions_fail_closed(self):
        for payload in ({"c0": True}, {"c0": True, "c1": "false"}):
            with self.subTest(payload=payload):
                decision = self.module.verify_answerability(
                    "query",
                    self.candidates,
                    llm_call=lambda **_: json.dumps(payload),
                    timeout_seconds=0.5,
                )
                self.assertEqual(decision.status, "unavailable")
                self.assertEqual(decision.accepted_ids, ())
                self.assertEqual(decision.attempt_count, 2)

    def test_invalid_json_retries_once_then_accepts(self):
        responses = iter(("{", json.dumps({"c0": False, "c1": True})))
        decision = self.module.verify_answerability(
            "query",
            self.candidates,
            llm_call=lambda **_: next(responses),
            timeout_seconds=0.5,
        )
        self.assertEqual(decision.status, "verified")
        self.assertEqual(decision.accepted_ids, ("c1",))
        self.assertEqual(decision.attempt_count, 2)

    def test_timeout_and_missing_llm_fail_closed(self):
        def slow_llm(**_):
            time.sleep(0.2)
            return "{}"

        timeout = self.module.verify_answerability(
            "query",
            self.candidates,
            llm_call=slow_llm,
            timeout_seconds=0.02,
        )
        missing = self.module.verify_answerability(
            "query",
            self.candidates,
            llm_call=None,
            timeout_seconds=0.02,
        )
        self.assertTrue(timeout.reason.startswith("timeout_after_"))
        self.assertEqual(timeout.accepted_ids, ())
        self.assertEqual(missing.reason, "no_llm_callable")
        self.assertEqual(missing.accepted_ids, ())

    def test_no_candidates_needs_no_llm(self):
        decision = self.module.verify_answerability(
            "query",
            [],
            llm_call=None,
            timeout_seconds=0.02,
        )
        self.assertEqual(decision.status, "not_needed")
        self.assertEqual(decision.candidate_count, 0)


if __name__ == "__main__":
    unittest.main()
