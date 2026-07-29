from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.phase8_regression import (
    aggregate_report,
    answerability_summary,
    baseline_comparison,
    category_summary,
    distribution,
    extract_fixture_ids,
    load_corpus,
    nearest_rank,
    score_query,
    write_json_atomic,
)

CORPUS_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "phase8_corpus.json"


class Phase8EvaluationTest(unittest.TestCase):
    def test_corpus_has_hard_negative_abstention_set_and_all_categories(self):
        corpus = load_corpus(CORPUS_PATH)
        self.assertEqual(len(corpus["fixtures"]), 16)
        self.assertEqual(len(corpus["queries"]), 48)
        self.assertEqual(
            sum(item["category"] == "abstention" for item in corpus["queries"]),
            30,
        )
        self.assertEqual(
            len({item["id"] for item in corpus["queries"]}),
            len(corpus["queries"]),
        )
        security_fixtures = [
            item for item in corpus["fixtures"] if item.get("source_security_corpus_id")
        ]
        self.assertEqual(len(security_fixtures), 3)
        self.assertEqual(
            {item["category"] for item in corpus["queries"]},
            {
                "single_session_recall",
                "multi_session_aggregation",
                "knowledge_update",
                "temporal_reasoning",
                "abstention",
                "cross_tier_recall",
                "security_exclusion",
            },
        )

    def test_nearest_rank_distribution_is_deterministic(self):
        values = list(range(1, 21))
        self.assertEqual(nearest_rank(values, 50), 10.0)
        self.assertEqual(nearest_rank(values, 95), 19.0)
        self.assertEqual(
            distribution(values),
            {"count": 20, "min": 1.0, "max": 20.0, "mean": 10.5, "p50": 10.0, "p95": 19.0},
        )

    def test_fixture_extraction_preserves_context_order(self):
        fixtures = [
            {"id": "alpha", "content": "Alpha fact."},
            {"id": "beta", "content": "Beta fact."},
        ]
        context = "prefix Beta fact. middle Alpha fact. suffix"
        self.assertEqual(extract_fixture_ids(context, fixtures), ["beta", "alpha"])

    def test_answerable_scoring_uses_fixed_top_k(self):
        result = score_query(
            {
                "category": "multi_session_aggregation",
                "expected_fixture_ids": ["alpha", "beta"],
                "forbidden_fixture_ids": ["old"],
            },
            visible_fixture_ids=["alpha", "noise", "beta", "noise-2", "noise-3"],
            raw_fixture_ids=["alpha", "beta"],
            top_k=5,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["precision_at_k"], 0.4)

    def test_abstention_and_security_exclusion_are_explicit(self):
        abstention = score_query(
            {"category": "abstention", "expected_fixture_ids": []},
            visible_fixture_ids=["irrelevant"],
            raw_fixture_ids=["irrelevant"],
            top_k=5,
        )
        self.assertEqual(abstention["status"], "FAIL")
        abstention_summary = category_summary(
            "abstention",
            [{**abstention, "latency_ms": 100.0, "context_tokens": 20}],
            5,
        )
        self.assertIn(
            "answerability gate left at least one no-answer query with visible memory",
            abstention_summary["reasons"],
        )

        security = score_query(
            {
                "category": "security_exclusion",
                "expected_fixture_ids": [],
                "forbidden_fixture_ids": ["quarantined"],
                "require_forbidden_in_raw_results": True,
            },
            visible_fixture_ids=["safe"],
            raw_fixture_ids=["quarantined", "safe"],
            top_k=5,
        )
        self.assertEqual(security["status"], "PASS")
        self.assertEqual(security["forbidden_raw_fixture_ids"], ["quarantined"])

    def test_temporal_partial_summary_records_remaining_retrieval_gap(self):
        query_results = [
            {
                "status": "PARTIAL",
                "reason": "found 1 of 2 expected facts",
                "expected_count": 2,
                "recalled_count": 1,
                "latency_ms": 100.0,
                "context_tokens": 20,
            }
        ]
        result = category_summary("temporal_reasoning", query_results, 5)
        self.assertEqual(result["verdict"], "PARTIAL")
        self.assertIn(
            "historical intent mode ran but expected temporal facts remained incomplete",
            result["reasons"],
        )
        self.assertEqual(result["latency_ms"]["p50"], 100.0)
        self.assertEqual(result["context_tokens"]["p50"], 20.0)

    def test_aggregate_and_baseline_comparison_are_structured(self):
        query_results = [
            {
                "category": "single_session_recall",
                "status": "PASS",
                "expected_count": 1,
                "recalled_count": 1,
                "latency_ms": 100.0,
                "context_tokens": 20,
                "forbidden_visible_fixture_ids": [],
            },
            {
                "category": "abstention",
                "status": "PASS",
                "expected_count": 0,
                "recalled_count": 0,
                "latency_ms": 200.0,
                "context_tokens": 0,
                "forbidden_visible_fixture_ids": [],
            },
        ]
        aggregate = aggregate_report(query_results, 5)
        self.assertEqual(aggregate["memory_recall"], 1.0)
        self.assertEqual(aggregate["memory_precision_at_k"], 0.2)
        self.assertEqual(aggregate["token_efficiency"]["total_injected_tokens"], 20)

        current = {
            "generated_at": "current",
            "aggregate": aggregate,
            "categories": [{"category": "single_session_recall", "verdict": "PASS"}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            baseline_path = Path(tmpdir) / "baseline.json"
            write_json_atomic(
                baseline_path,
                {
                    "generated_at": "baseline",
                    "aggregate": aggregate,
                    "categories": [{"category": "single_session_recall", "verdict": "PASS"}],
                },
            )
            comparison = baseline_comparison(current, baseline_path)
            self.assertEqual(comparison["metric_deltas"]["memory_recall"]["delta"], 0.0)
            self.assertEqual(comparison["metric_deltas"]["memory_recall"]["status"], "compared")
            self.assertEqual(comparison["category_verdict_changes"], [])
            self.assertEqual(json.loads(baseline_path.read_text())["generated_at"], "baseline")

            current_without_tokens = json.loads(json.dumps(current))
            current_without_tokens["aggregate"]["token_efficiency"]["per_query"] = {"count": 0}
            unavailable = baseline_comparison(current_without_tokens, baseline_path)
            self.assertIsNone(unavailable["metric_deltas"]["mean_context_tokens"]["delta"])
            self.assertEqual(
                unavailable["metric_deltas"]["mean_context_tokens"]["status"],
                "unavailable",
            )

    def test_answerability_summary_counts_calls_retries_and_usage(self):
        summary = answerability_summary(
            [
                {
                    "answerability_events": [
                        {
                            "status": "verified",
                            "candidate_count": 2,
                            "accepted_count": 1,
                            "latency_ms": 120.0,
                            "prompt_tokens": 100,
                            "completion_tokens": 8,
                            "attempt_count": 1,
                        }
                    ]
                },
                {
                    "answerability_events": [
                        {
                            "status": "verified",
                            "candidate_count": 1,
                            "accepted_count": 0,
                            "latency_ms": 200.0,
                            "prompt_tokens": 210,
                            "completion_tokens": 15,
                            "attempt_count": 2,
                        }
                    ]
                },
                {
                    "answerability_events": [
                        {
                            "status": "not_needed",
                            "candidate_count": 0,
                            "accepted_count": 0,
                            "latency_ms": 0.0,
                            "prompt_tokens": None,
                            "completion_tokens": None,
                            "attempt_count": 0,
                        }
                    ]
                },
            ]
        )
        self.assertEqual(summary["query_count_with_verifier"], 2)
        self.assertEqual(summary["call_count"], 3)
        self.assertEqual(summary["candidate_count"], 3)
        self.assertEqual(summary["accepted_count"], 1)
        self.assertEqual(summary["prompt_tokens"]["total"], 310)
        self.assertEqual(summary["completion_tokens"]["total"], 23)


if __name__ == "__main__":
    unittest.main()
