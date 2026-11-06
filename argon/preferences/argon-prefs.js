/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

// Argon preference defaults, applied to every Argon profile.
//
// The build overlay appends this file to browser/app/profile/firefox.js inside
// a marked block so the change stays reviewable and reversible against
// upstream. Preference names use the argon. prefix to avoid collisions with
// Firefox preferences.

// Appearance: system, light, or dark. Matches the Milestone 0.1 default.
pref("argon.theme", "system");

// Tab layout: horizontal or vertical. Vertical reuses Firefox's native
// sidebar.verticalTabs implementation rather than a custom tab strip.
pref("argon.tabs.layout", "horizontal");

// Privacy by default: Argon ships no telemetry of its own.
pref("argon.telemetry.enabled", false);

// Argon is a separate product, so its users are not enrolled in Mozilla's
// studies, remote experiments, or Firefox data collection by default. These
// are opt-in services, not security features: the security preferences
// (add-on signing, sandboxing, Safe Browsing) stay at their upstream values.
pref("app.normandy.enabled", false);
pref("app.shield.optoutstudies.enabled", false);
pref("datareporting.healthreport.uploadEnabled", false);
pref("datareporting.policy.dataSubmissionEnabled", false);
pref("browser.discovery.enabled", false);
