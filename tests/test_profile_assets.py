from __future__ import annotations

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "deploy_profile_assets.py"


def load_deployer():
    spec = importlib.util.spec_from_file_location("profile_asset_deployer", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProfileAssetTest(unittest.TestCase):
    def test_assets_pass_native_validation(self):
        report = load_deployer().validate_static()
        profiles = report["profiles"]
        self.assertEqual(set(profiles), {"default", "research"})
        self.assertEqual(profiles["default"]["skills"], [])
        self.assertEqual(profiles["research"]["skills"], [])

    def test_deploy_is_profile_scoped_and_omits_secrets(self):
        module = load_deployer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            targets = {
                "default": root / "default",
                "research": root / "research",
            }
            workspace = root / "vault"
            with patch.object(module, "PROFILE_TARGETS", targets):
                report = module.deploy(["default", "research"], workspace)
                self.assertTrue((targets["default"] / "SOUL.md").is_file())
                self.assertTrue((targets["research"] / "SOUL.md").is_file())
                self.assertTrue((workspace / ".hermes.md").is_file())
                self.assertTrue((targets["research"] / "profile.yaml").is_file())
                self.assertEqual(report["removed"], [])
                self.assertFalse((targets["default"] / ".env").exists())
                self.assertFalse((targets["research"] / ".env").exists())
                self.assertNotEqual(
                    (targets["default"] / "SOUL.md").read_text(),
                    (targets["research"] / "SOUL.md").read_text(),
                )
                self.assertTrue(report["deployed"])
                verification = module.verify_deployment(
                    ["default", "research"], workspace
                )
                self.assertEqual(
                    len(verification["verified"]), len(report["deployed"])
                )
                self.assertEqual(
                    stat.S_IMODE((targets["default"] / "SOUL.md").stat().st_mode),
                    0o600,
                )

    def test_deploy_prunes_only_previously_managed_skills(self):
        module = load_deployer()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            target = root / "default"
            managed = target / "skills" / "asa-daily-checkin"
            unmanaged = target / "skills" / "native-skill"
            managed.mkdir(parents=True)
            unmanaged.mkdir(parents=True)
            (managed / "SKILL.md").write_text("managed")
            (unmanaged / "SKILL.md").write_text("native")
            with patch.object(module, "PROFILE_TARGETS", {"default": target}):
                report = module.deploy(["default"], None)
                self.assertIn(str(managed / "SKILL.md"), report["removed"])
                self.assertFalse(managed.exists())
                self.assertTrue((unmanaged / "SKILL.md").is_file())
                module.verify_deployment(["default"], None)


if __name__ == "__main__":
    unittest.main()
