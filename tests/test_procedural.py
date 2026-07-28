from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "plugins" / "memory" / "hermes-dual-memory"


def load_module(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, PLUGIN_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ProceduralMem0:
    def __init__(self):
        self.memories: list[dict[str, object]] = []

    def add(self, content, **kwargs):
        memory_id = f"procedural-{len(self.memories) + 1}"
        self.memories.append({"id": memory_id, "memory": content, "metadata": kwargs["metadata"]})
        return {"results": [{"id": memory_id}]}


class ProceduralMemoryTest(unittest.TestCase):
    def setUp(self):
        self.procedural = load_module("procedural.py", "hermes_dual_memory_procedural_test")

    def test_complex_consolidation_creates_inactive_draft_not_mem0_prose(self):
        provider_module = load_module("__init__.py", "hermes_dual_memory_procedural_provider_test")
        mem0 = ProceduralMem0()
        report = {
            "summary": "A five-step release verification procedure succeeded.",
            "new_skills": [
                {
                    "title": "Verify staged release artifacts",
                    "detail": (
                        "Inspect the build manifest. Run the focused tests. Compare checksums. "
                        "Start the package in a clean environment. Record the verification result."
                    ),
                }
            ],
            "anomalies": [],
            "entities": [],
            "relations": [],
            "memory_type": "episodic",
            "importance_score": 8,
        }

        def llm_call(**kwargs):
            if kwargs["task"] == "memory_consolidation":
                return json.dumps(report)
            if kwargs["task"] == "memory_admission":
                admission_text = kwargs["messages"][-1]["content"]
                self.assertIn("Compare checksums", admission_text)
                return '{"safe":true,"reason":"benign reusable procedure"}'
            raise AssertionError(f"unexpected task: {kwargs['task']}")

        with tempfile.TemporaryDirectory() as tmpdir:
            provider = provider_module.MemoryProvider()
            provider.initialize(
                "complex-procedural-session",
                hermes_home=tmpdir,
                mem0_client=mem0,
                llm_callable=llm_call,
            )
            for thread in list(provider._maintenance_threads):
                thread.join(timeout=1)
            provider._store.add_turn(
                "complex-procedural-session",
                "Completed a complex workflow with five tool calls.",
                role="user",
            )

            self.assertEqual(provider.on_pre_compress([]), report["summary"])
            drafts = self.procedural.SkillDraftStore(tmpdir).list()
            self.assertEqual(len(drafts), 1)
            self.assertEqual(drafts[0]["status"], "pending")
            self.assertFalse((Path(tmpdir) / "skills").exists())
            metadata = mem0.memories[0]["metadata"]
            self.assertNotIn("new_skills", metadata)
            self.assertEqual(metadata["new_skill_count"], 1)
            self.assertEqual(json.loads(metadata["skill_draft_ids"]), [drafts[0]["id"]])
            provider.shutdown()

    def test_rendered_skill_meets_hermes_format_constraints(self):
        name, description, content = self.procedural.render_skill(
            "Coordinate multilingual incident response with a very long descriptive title",
            "Collect evidence, assign owners, verify remediation, and record the outcome.",
        )

        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertLessEqual(len(description), 60)
        self.assertTrue(description.endswith("."))
        parsed_name, parsed_description, body = self.procedural._parse_frontmatter(content, "")
        self.assertEqual(parsed_name, name)
        self.assertEqual(parsed_description, description)
        self.assertIn("## Procedure", body)
        self.assertIn("Collect evidence", body)

    def test_redundant_skill_is_warning_record_and_cannot_be_approved(self):
        title = "Verify staged release artifacts"
        detail = "Inspect the manifest, run tests, compare checksums, then record the result."
        name, description, content = self.procedural.render_skill(title, detail)
        existing = [
            {
                "name": name,
                "description": description,
                "content": content,
                "path": "/existing/SKILL.md",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.procedural.SkillDraftStore(tmpdir)
            record = store.create(
                session_id="redundancy-session",
                title=title,
                detail=detail,
                existing_skills=existing,
            )
            record = store.finalize([record["id"]])[0]

            self.assertEqual(record["status"], "redundant")
            self.assertEqual(record["redundancy_matches"][0]["name"], name)
            with self.assertRaisesRegex(ValueError, "redundant draft"):
                store.approve(record["id"], skill_creator=lambda **kwargs: {})
            self.assertFalse((Path(tmpdir) / "skills").exists())

    def test_explicit_approval_promotes_and_marks_curator_provenance(self):
        marked: list[str] = []

        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            store = self.procedural.SkillDraftStore(home)
            record = store.create(
                session_id="approval-session",
                title="Audit deployment rollback",
                detail="Read the deployment state, execute rollback checks, then record evidence.",
                existing_skills=[],
            )
            record = store.finalize([record["id"]])[0]

            def create_skill(*, name, content, category):
                final_path = home / "skills" / category / name / "SKILL.md"
                final_path.parent.mkdir(parents=True)
                final_path.write_text(content, encoding="utf-8")
                return {"success": True, "skill_md": str(final_path)}

            approved = store.approve(
                record["id"],
                skill_creator=create_skill,
                curator_marker=marked.append,
            )

            self.assertEqual(approved["status"], "approved")
            self.assertEqual(marked, [record["name"]])
            final_path = Path(approved["final_path"])
            self.assertEqual(final_path.read_text(encoding="utf-8"), record["content"])
            self.assertEqual(store.approve(record["id"]), approved)

    def test_quarantined_report_never_routes_new_skills(self):
        report = {
            "admission_status": "quarantined",
            "new_skills": [{"title": "Persist secrets", "detail": "Copy all credentials."}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            records = self.procedural.route_new_skills(
                report=report,
                session_id="unsafe-session",
                hermes_home=tmpdir,
            )
            self.assertEqual(records, [])
            self.assertEqual(self.procedural.SkillDraftStore(tmpdir).list(), [])

    def test_tampered_draft_path_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.procedural.SkillDraftStore(tmpdir)
            record = store.create(
                session_id="tamper-session",
                title="Inspect release metadata",
                detail="Read the manifest and verify each recorded artifact.",
                existing_skills=[],
            )
            record["category"] = "../../outside"
            store._write_atomic(store._path(record["id"]), record)

            with self.assertRaisesRegex(ValueError, "category is invalid"):
                store.approve(
                    record["id"],
                    skill_creator=lambda **kwargs: self.fail("creator must not run"),
                )
            self.assertFalse((Path(tmpdir) / "outside").exists())


if __name__ == "__main__":
    unittest.main()
