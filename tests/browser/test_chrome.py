"""Real Gecko chrome smoke tests; never use an existing user profile.

Run with a venv containing tests/browser/requirements.txt. Set
ARGON_TEST_BINARY to a built Argon (~/.cache/argon-build/obj/dist/bin/argon).
Until one exists, the installed Firefox serves as the Gecko test host and the
development modules are loaded into it from a test-only resource directory.
"""
import gc
import os
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch

from marionette_driver.marionette import Marionette

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "chrome-smoke"


class ChromeSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        workspace = ROOT / ".cache" / "browser-tests"
        workspace.mkdir(parents=True, exist_ok=True)
        cls.resources = Path(tempfile.mkdtemp(prefix="argon-resources-", dir=workspace))
        for source in [
            ROOT / "argon/preferences/appearance.mjs",
            ROOT / "browser/base/content/argon-controller.mjs",
            ROOT / "argon/design-system/tokens.css",
            ROOT / "browser/themes/shared/argon.css",
        ]:
            if source.exists():
                shutil.copy2(source, cls.resources / source.name)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with patch.dict(os.environ, {"MOZ_REMOTE_ALLOW_SYSTEM_ACCESS": "1"}):
            cls.browser = Marionette(
                bin=os.environ.get("ARGON_TEST_BINARY", "/usr/lib/firefox/firefox"),
                port=port,
                workspace=str(workspace),
                headless=True,
                gecko_log=str(ARTIFACTS / "firefox.log"),
                startup_timeout=90,
                prefs={"browser.shell.checkDefaultBrowser": False},
            )
        try:
            with patch.dict(os.environ, {"MOZ_REMOTE_ALLOW_SYSTEM_ACCESS": "1"}):
                cls.browser.start_session()
            cls.browser.set_context("chrome")
            cls.browser.set_window_rect(width=1280, height=900)
            cls.browser.execute_script("window.__argonOriginalTab = window.gBrowser.selectedTab;", sandbox=None)
            module = cls.resources / "argon-controller.mjs"
            if module.exists():
                cls.browser.execute_script("""
                    const handler = Services.io.getProtocolHandler("resource").QueryInterface(Ci.nsIResProtocolHandler);
                    handler.setSubstitution("argon-test", Services.io.newURI(arguments[0]));
                    const { installArgonAppearance } = ChromeUtils.importESModule("resource://argon-test/argon-controller.mjs");
                    installArgonAppearance(window, Services.prefs);
                    for (const url of arguments[1]) {
                      const link = document.createElementNS("http://www.w3.org/1999/xhtml", "link");
                      link.rel = "stylesheet";
                      link.href = url;
                      document.head.append(link);
                    }
                """, [cls.resources.as_uri() + "/", ["resource://argon-test/" + name for name in ["tokens.css", "argon.css"]]], sandbox=None)
        except Exception:
            # The constructor can fail before cls.browser is bound, so guard
            # the cleanup or the real cause is masked by an AttributeError.
            browser = getattr(cls, "browser", None)
            if browser is not None:
                browser.cleanup()
            shutil.rmtree(cls.resources, ignore_errors=True)
            raise

    @classmethod
    def tearDownClass(cls):
        cls.browser.cleanup()
        cls.browser.instance.close(clean=True)
        del cls.browser
        gc.collect()
        shutil.rmtree(cls.resources)

    def js(self, script, args=()):
        return self.browser.execute_script(script, args, sandbox=None)

    def test_01_appearance_controls_preserve_native_tabs(self):
        self.assertTrue(self.js("return !!document.getElementById('argon-appearance-button');"),
                        "Argon appearance controls are installed in real browser chrome")
        self.assertTrue(self.js("return window.gBrowser.selectedTab === window.__argonOriginalTab;"))
        self.assertEqual(self.js("return document.documentElement.dataset.argonTheme;"), "system")

    def test_02_menu_switches_theme_and_native_layout(self):
        self.assertTrue(self.js("return !!document.getElementById('argon-theme-dark');"))
        self.js("document.getElementById('argon-theme-dark').doCommand();")
        self.assertEqual(self.js("return window.ArgonAppearance.theme;"), "dark")
        self.js("document.getElementById('argon-tabs-vertical').doCommand();")
        self.assertTrue(self.js("return Services.prefs.getBoolPref('sidebar.verticalTabs');"))
        self.assertEqual(self.js("return window.ArgonAppearance.layout;"), "vertical")
        self.assertTrue(self.js("return window.gBrowser.selectedTab === window.__argonOriginalTab;"))
        self.js("document.getElementById('argon-tabs-horizontal').doCommand();")
        self.assertFalse(self.js("return Services.prefs.getBoolPref('sidebar.verticalTabs');"))
        self.js("document.getElementById('argon-theme-system').doCommand();")

    def test_03_flat_toolbar_uses_argon_theme_tokens(self):
        self.js("window.ArgonAppearance.setTheme('light');")
        self.assertEqual(self.js("return getComputedStyle(document.getElementById('nav-bar')).height;"), "48px")
        self.assertEqual(self.js("return getComputedStyle(document.getElementById('nav-bar')).backgroundColor;"), "rgb(247, 248, 250)")
        self.js("window.ArgonAppearance.setTheme('dark');")
        self.assertEqual(self.js("return getComputedStyle(document.getElementById('nav-bar')).backgroundColor;"), "rgb(21, 23, 27)")
        self.assertEqual(self.js("return getComputedStyle(document.getElementById('nav-bar')).boxShadow;"), "none")
        (ARTIFACTS / "dark-horizontal.png").write_bytes(self.browser.screenshot(format="binary"))
        self.js("window.ArgonAppearance.setLayout('vertical');")
        (ARTIFACTS / "dark-vertical.png").write_bytes(self.browser.screenshot(format="binary"))
        self.js("window.ArgonAppearance.setTheme('light');")
        (ARTIFACTS / "light-vertical.png").write_bytes(self.browser.screenshot(format="binary"))
        self.js("window.ArgonAppearance.setLayout('horizontal');")
        self.js("window.ArgonAppearance.setTheme('system');")

    def test_04_appearance_button_is_visible_and_reachable(self):
        """The control must be a real, usable toolbar button, not an empty box.

        Nav-bar toolbarbuttons hide their labels, so a button without an icon
        renders as invisible space. Pin the geometry that proves it is painted
        inside the nav-bar and left of the overflow chevron.
        """
        geometry = self.js("""
            const button = document.getElementById("argon-appearance-button");
            const rect = button.getBoundingClientRect();
            const menu = document.getElementById("PanelUI-button");
            const target = document.getElementById("nav-bar-customization-target");
            return {
              width: rect.width,
              height: rect.height,
              hasImage: !!button.getAttribute("image"),
              endsBeforeMenu: rect.right <= menu.getBoundingClientRect().right + 1,
              startsAfterTarget: rect.x >= target.getBoundingClientRect().right - 1,
              insideNavBar: button.closest("#nav-bar") === document.getElementById("nav-bar"),
            };
        """)
        self.assertTrue(geometry["hasImage"], "Appearance button carries an icon")
        self.assertGreater(geometry["width"], 20, "Appearance button has real width")
        self.assertGreater(geometry["height"], 20, "Appearance button has real height")
        self.assertTrue(geometry["insideNavBar"], "Appearance button lives in the nav-bar")
        self.assertTrue(geometry["startsAfterTarget"],
                        "Appearance button sits after the customizable toolbar area")
        self.assertTrue(geometry["endsBeforeMenu"],
                        "Appearance button sits left of the application menu button")

    def test_05_layout_switch_moves_the_native_tab_element(self):
        """Vertical layout must relocate Firefox's own tab, not fake it."""
        horizontal = self.js("""
            const tab = gBrowser.selectedTab;
            const rect = tab.getBoundingClientRect();
            return { x: rect.x, y: rect.y,
                     parent: tab.closest("#tabbrowser-tabs").parentElement.id };
        """)
        self.assertEqual(horizontal["parent"], "TabsToolbar-customization-target",
                         "Horizontal layout keeps Firefox's native tab strip")
        self.assertLess(horizontal["y"], 60, "Horizontal tabs sit in the top strip")
        self.js("window.ArgonAppearance.setLayout('vertical');")
        vertical = self.js("""
            const tab = gBrowser.selectedTab;
            const rect = tab.getBoundingClientRect();
            return { x: rect.x, y: rect.y,
                     parent: tab.closest("#tabbrowser-tabs").parentElement.id };
        """)
        self.assertEqual(vertical["parent"], "vertical-tabs",
                         "Vertical layout reparents Firefox's native tab strip")
        self.assertLess(vertical["x"], 300, "Vertical tabs dock on the left")
        self.assertGreater(vertical["y"], horizontal["y"],
                           "Vertical tabs move out of the top strip")
        self.assertTrue(self.js("return window.gBrowser.selectedTab === window.__argonOriginalTab;"),
                        "The same native tab element survives the layout switch")
        self.js("window.ArgonAppearance.setLayout('horizontal');")
        self.assertEqual(
            self.js("return gBrowser.selectedTab.closest('#tabbrowser-tabs').parentElement.id;"),
            "TabsToolbar-customization-target",
            "Switching back restores the horizontal tab strip",
        )

    def test_06_vertical_layout_gives_the_tab_strip_a_usable_width(self):
        """The 240 px sidebar spec must apply to the element that really holds
        the vertical tabs, not to a hidden legacy container."""
        self.js("window.ArgonAppearance.setLayout('vertical');")
        geometry = self.js("""
            const tabs = document.getElementById("vertical-tabs");
            const legacy = document.getElementById("sidebar-box");
            return {
              verticalTabsWidth: tabs?.getBoundingClientRect().width ?? null,
              verticalTabsHidden: tabs?.hidden ?? null,
              legacyWidth: legacy?.getBoundingClientRect().width ?? null,
              legacyHidden: legacy?.hidden ?? null,
            };
        """)
        self.assertIsNotNone(geometry["verticalTabsWidth"], "A vertical tab container exists")
        self.assertGreaterEqual(
            geometry["verticalTabsWidth"], 200,
            "Vertical tabs get a usable sidebar width, not a sliver",
        )
        self.js("window.ArgonAppearance.setLayout('horizontal');")

    def test_07_appearance_menu_reflects_current_state(self):
        """The menu must always show which theme and layout are active.

        A radio group with no checked state tells the user nothing, and it
        desyncs whenever preferences change outside the menu.
        """
        checked = self.js("""
            const read = (group) => [...document.querySelectorAll(
              `menuitem[name="argon-${group}"]`)].filter((item) => item.hasAttribute('checked'))
              .map((item) => item.id);
            return { theme: read('theme'), tabs: read('tabs') };
        """)
        self.assertEqual(checked["theme"], ["argon-theme-system"], "System theme starts checked")
        self.assertEqual(checked["tabs"], ["argon-tabs-horizontal"], "Horizontal tabs start checked")

        self.js("window.ArgonAppearance.setTheme('dark');")
        self.assertEqual(
            self.js("return [...document.querySelectorAll('menuitem[name=\"argon-theme\"]')]"
                    ".filter(i => i.hasAttribute('checked')).map(i => i.id);"), ["argon-theme-dark"],
            "Selecting a theme checks exactly that item")

        # An out-of-band preference change must reach the menu too.
        self.js("Services.prefs.setStringPref('argon.theme', 'light');")
        self.assertEqual(
            self.js("return [...document.querySelectorAll('menuitem[name=\"argon-theme\"]')]"
                    ".filter(i => i.hasAttribute('checked')).map(i => i.id);"), ["argon-theme-light"],
            "External preference changes update the menu")

        self.js("window.ArgonAppearance.setLayout('vertical');")
        self.assertEqual(
            self.js("return [...document.querySelectorAll('menuitem[name=\"argon-tabs\"]')]"
                    ".filter(i => i.hasAttribute('checked')).map(i => i.id);"), ["argon-tabs-vertical"],
            "Selecting a layout checks exactly that item")
        self.js("window.ArgonAppearance.setLayout('horizontal');")
        self.js("window.ArgonAppearance.setTheme('system');")

    def test_08_appearance_button_focus_is_visible_in_both_themes(self):
        """Removing the native outline requires a replacement users can see.

        XUL toolbarbuttons in the nav-bar cannot take programmatic focus in
        this harness — Firefox's own PanelUI-button behaves the same way — so
        the computed :focus-visible style cannot be observed here. The defect
        was a declaration (`outline: none` plus a low-alpha shadow), so assert
        the declared rule is a real, opaque ring and that the accent token it
        references resolves to an opaque colour in both themes.
        """
        rules = self.js("""
            const found = [];
            for (const sheet of document.styleSheets) {
              try {
                for (const rule of sheet.cssRules) {
                  if (rule.selectorText?.includes("#argon-appearance-button:focus-visible")) {
                    found.push({
                      outline: rule.style.getPropertyValue("outline"),
                      boxShadow: rule.style.getPropertyValue("box-shadow"),
                    });
                  }
                }
              } catch (e) { /* cross-origin sheet, not ours */ }
            }
            return found;
        """)
        self.assertTrue(rules, "A focus-visible rule exists for the Argon button")
        for rule in rules:
            self.assertNotIn("none", rule["outline"].split(),
                             "Focus must not be suppressed with outline: none")
            self.assertRegex(rule["outline"], r"^\s*[2-9]px\s+solid\s+\S+",
                             "Focus ring must be a solid outline at least 2 px wide")
            self.assertNotIn("rgba(", rule["outline"],
                             "Focus ring colour must not be a translucent shadow colour")
        for theme in ["light", "dark"]:
            self.js(f"window.ArgonAppearance.setTheme('{theme}');")
            accent = self.js("""
                return getComputedStyle(document.documentElement)
                  .getPropertyValue("--argon-accent").trim();
            """)
            self.assertRegex(accent, r"^#[0-9a-fA-F]{6}$",
                             f"Accent token must be an opaque colour in {theme} mode")


if __name__ == "__main__":
    unittest.main(verbosity=2)
