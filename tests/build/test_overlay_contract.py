"""Consistency between the packaged chrome wiring and the overlay description.

The browser suite exercises the modules through a test-only resource:// mapped
directory, which cannot prove that a packaged build would find them. These
tests cover the wiring itself: every chrome:// URL referenced by the window
hooks must be copied into the tree and packaged by the jar manifest, and the
preferences the controller reads must exist in the defaults file.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERLAY = json.loads((ROOT / "config" / "overlay.json").read_text())
HOOKS = ROOT / "browser" / "base" / "content" / "argon-window-hooks.inc.xhtml"
PREFS = ROOT / "argon" / "preferences" / "argon-prefs.js"
CONTROLLER = ROOT / "browser" / "base" / "content" / "argon-controller.mjs"
APPEARANCE = ROOT / "argon" / "preferences" / "appearance.mjs"
MOZCONFIG = ROOT / "config" / "mozconfig"


class OverlayContractTests(unittest.TestCase):
    def setUp(self):
        self.hooks_text = HOOKS.read_text(encoding="utf-8")
        self.referenced = re.findall(r"chrome://browser/content/argon/([\w.-]+)", self.hooks_text)

    def test_window_hooks_reference_argon_resources(self):
        self.assertTrue(self.referenced, "window hooks must load Argon resources")
        self.assertIn("tokens.css", self.referenced)
        self.assertIn("argon.css", self.referenced)
        self.assertIn("argon-controller.mjs", self.referenced)

    def test_every_referenced_resource_is_copied_into_the_tree(self):
        copied = {Path(entry["to"]).name: entry for entry in OVERLAY["files"]}
        for name in self.referenced:
            self.assertIn(name, copied, f"{name} is referenced but never copied by the overlay")
            self.assertEqual(Path(copied[name]["to"]).parent.as_posix(),
                             "browser/base/content/argon",
                             f"{name} must land in the packaged argon directory")
            self.assertTrue((ROOT / copied[name]["from"]).is_file(),
                            f"{copied[name]['from']} is missing from the repository")

    def test_every_referenced_resource_is_packaged_by_the_jar_hook(self):
        jar_hook = next(hook for hook in OVERLAY["hooks"] if hook["path"] == "browser/base/jar.mn")
        packaged = {Path(entry["source"]).name for entry in jar_hook["entries"]}
        for name in self.referenced:
            self.assertIn(name, packaged, f"{name} is not listed in the jar.mn overlay entries")
        for entry in jar_hook["entries"]:
            self.assertTrue(entry["source"].startswith("content/argon/"),
                            "jar.mn entries must point inside the packaged argon directory")

    def test_the_preference_defaults_cover_every_preference_the_controller_reads(self):
        prefs_text = PREFS.read_text(encoding="utf-8")
        declared = set(re.findall(r'pref\("([\w.]+)"', prefs_text))
        used = set(re.findall(r'"argon\.[\w.]+"', APPEARANCE.read_text(encoding="utf-8")))
        used = {name.strip('"') for name in used}
        self.assertTrue(used, "the appearance controller must read argon.* preferences")
        for name in used:
            self.assertIn(name, declared, f"{name} is read by the controller but has no default")

    def test_the_controller_registers_only_on_browser_windows(self):
        source = CONTROLLER.read_text(encoding="utf-8")
        self.assertIn('getElementById("nav-bar")', source,
                      "auto-install must be gated on a browser chrome window")
        self.assertIn("ArgonAppearance", source, "double installation must be guarded")

    def test_the_overlay_does_not_disable_security_preferences(self):
        forbidden = re.compile(
            r"xpinstall\.signatures|security\.sandbox|browser\.safe_mode"
            r"|devtools\.selfxss\.count|privacy\.resistFingerprinting",
        )
        combined = PREFS.read_text(encoding="utf-8") + self.hooks_text
        self.assertIsNone(forbidden.search(combined),
                          "the overlay must not relax upstream security behaviour")

    def test_the_build_configuration_does_not_relax_add_on_signing(self):
        mozconfig = MOZCONFIG.read_text(encoding="utf-8")
        active = "\n".join(line for line in mozconfig.splitlines()
                           if not line.lstrip().startswith("#"))
        for flag in ("MOZ_REQUIRE_SIGNING", "--with-unsigned-addon-scopes",
                     "--allow-addon-sideload", "--enable-unverified-updates", "MOZILLA_OFFICIAL"):
            self.assertNotIn(flag, active, f"{flag} must not be set by the Argon build")

    def test_identity_hooks_only_touch_the_vendor_and_profile(self):
        hook = next(h for h in OVERLAY["hooks"] if h["path"] == "browser/moz.configure")
        self.assertEqual(hook["replace_line"], 'imply_option("MOZ_APP_VENDOR", "Mozilla")')
        self.assertEqual(
            hook["lines"],
            [
                'imply_option("MOZ_APP_VENDOR", "Argon")',
                'imply_option("MOZ_APP_PROFILE", "argon")',
            ],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
