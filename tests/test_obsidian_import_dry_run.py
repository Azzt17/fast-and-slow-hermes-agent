from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "obsidian_import_dry_run.py"


def load_importer():
    spec = importlib.util.spec_from_file_location("obsidian_import_dry_run", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ObsidianImportDryRunTest(unittest.TestCase):
    def test_manifest_is_metadata_only_and_classifies_sources(self):
        module = load_importer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            vault = root / "vault"
            output = root / "private" / "manifest.jsonl"
            (vault / "01-knowledge").mkdir(parents=True)
            (vault / "04-archive" / "journals" / "DailyJournal").mkdir(parents=True)
            (vault / "01-knowledge" / "profile.md").write_text(
                "---\ntags: [personal]\n---\n#private [[Context]]", encoding="utf-8"
            )
            (vault / "01-knowledge" / "api-token-notes.md").write_text(
                "do not expose", encoding="utf-8"
            )
            (vault / "04-archive" / "journals" / "DailyJournal" / "2026-01-01.md").write_text(
                "old journal", encoding="utf-8"
            )
            source_before = (vault / "01-knowledge" / "profile.md").read_bytes()

            report = module.build_manifest(vault, output)
            records = [json.loads(line) for line in output.read_text().splitlines()]

            self.assertEqual(report["records"], 3)
            self.assertFalse(report["memory_write"])
            self.assertFalse(report["semantic_analysis"])
            self.assertEqual(oct(output.stat().st_mode & 0o777), "0o600")
            self.assertEqual(source_before, (vault / "01-knowledge" / "profile.md").read_bytes())
            by_path = {record["source_path"]: record for record in records}
            self.assertEqual(by_path["01-knowledge/profile.md"]["classification"], "needs_review")
            self.assertNotIn("Context", json.dumps(by_path["01-knowledge/profile.md"]))
            self.assertEqual(by_path["01-knowledge/api-token-notes.md"]["classification"], "needs_review")
            self.assertEqual(
                by_path["04-archive/journals/DailyJournal/2026-01-01.md"]["classification"],
                "excluded",
            )

    def test_refuses_output_inside_vault(self):
        module = load_importer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            vault = Path(temporary_directory) / "vault"
            vault.mkdir()
            (vault / "note.md").write_text("note", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside the vault"):
                module.build_manifest(vault, vault / "manifest.jsonl")


if __name__ == "__main__":
    unittest.main()
