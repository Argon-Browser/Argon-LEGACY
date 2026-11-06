# Argon Browser

Status: Phase 1, Foundation and prototyping (pre-alpha, planning and bootstrap stage)  
Base engine: [Firefox / Gecko](https://firefox-source-docs.mozilla.org/) · Target platforms: Linux, Windows, macOS

Argon is an open-source desktop web browser built on the [Firefox (Gecko)](https://firefox-source-docs.mozilla.org/) engine. It pairs a layout and workflow inspired by Arc and Zen Browser with native Firefox WebExtensions support and a compatibility bridge for Chromium extensions (Manifest V2 and V3).

## Current project status

The project is in the planning and repository bootstrap stage, preparing to start Milestone 0.1 (`Argon 0.1: Visual Foundation`).

| Area or deliverable | Current state | Target phase |
| :--- | :--- | :--- |
| Architecture and implementation plan | Completed ([`Argon Browser — Implementation Plan.md`](./Argon%20Browser%20%E2%80%94%20Implementation%20Plan.md)) | Phase 1 |
| Repository and version control setup | Initialized | Phase 1 |
| Firefox Artifact Build and isolated profile | Pending bootstrap | Phase 1 (Milestone 0.1) |
| Argon design system and flat toolbar (48 px) | Planned | Phase 1 (Milestone 0.1) |
| Adaptive horizontal and vertical tab strip | Planned | Phases 1 to 2 (Milestone 0.1) |
| Light, Dark, and System Auto theme switcher | Planned | Phases 1 to 2 (Milestone 0.1) |
| Smart sidebar, command palette, and New Tab | Planned | Phase 2 |
| Workspaces, tab suspension, and `about:argon` | Planned | Phase 3 |
| Argon Extension Bridge (Chromium MV2/MV3) | Planned (parallel R&D track) | Phase 4 |
| Cross-platform packaging and public beta | Planned | Phase 5 |

## Core design and features

### Appearance

Argon uses a flat interface without 3D bevels or heavy drop shadows, built on a `4 px` and `8 px` spatial grid with `8 to 12 px` corner radii. The top toolbar is `48 px` tall, and the sidebar collapses from `240 px` to `52 px`. Users can adjust accent colors (default `#6478F5`), UI density, corner radii, and themes (`#F7F8FA` Light, `#15171B` Dark, or System Auto) in real time without restarting. Transitions run for `120 to 200 ms` and respect `prefers-reduced-motion`.

### Usability and navigation

Tabs can switch between horizontal and vertical layouts at runtime. A vertical sidebar holds open tabs, pinned tabs, bookmarks, and workspace switchers in one dock, while a compact mode hides secondary chrome to give more room to web content. Workspaces isolate browsing sessions and pair with automatic tab unloading to save memory. Keyboard shortcuts follow operating system conventions and remain user-configurable, including `Ctrl+L` (`Cmd+L` on macOS) for the unified address bar and `Ctrl+Shift+P` (`Cmd+Shift+P` on macOS) for the command palette.

### Extensions

Standard Firefox add-ons from Mozilla Add-ons (AMO) run natively. For Chromium packages, the Argon Extension Bridge provides a multi-stage pipeline: a static `manifest.json` analyzer that generates an English compatibility report before installation, a manifest and API shim adapter, a background runtime that bridges Manifest V3 service workers to Gecko's background page model, and a local CRX/ZIP package installer. All extensions run inside Gecko's existing WebExtensions sandbox and permission model.

## Architecture overview

Argon is an incremental fork of Firefox Desktop. Gecko handles rendering, SpiderMonkey runs JavaScript, Necko manages networking, WebRender handles GPU compositing, and NSS provides cryptography. Argon modifies the front-end layer (HTML, CSS, JavaScript, XUL, and Web Components) and the extension subsystem so that site permissions, password management, private browsing isolation, and screen-reader accessibility stay intact across upstream updates.

### Planned repository layout

```text
argon/
├── browser/                 # Modified Firefox Desktop components
│   ├── base/content/        # Main browser window (browser.xhtml) and navigation logic
│   ├── components/          # Core browser features and services
│   ├── themes/              # Platform theme integration and CSS overrides
│   └── branding/argon/      # Argon logos, wordmarks, and branding assets
│
├── argon/                   # Argon-exclusive modules (100% English codebase)
│   ├── design-system/       # CSS design tokens and reusable Web Components
│   ├── workspaces/          # Workspace isolation and session management
│   ├── commands/            # Command Palette UI and action registry
│   ├── extensions/          # Argon Extension Bridge (Analyzer, Adapter, Runtime)
│   ├── preferences/         # Custom Argon settings UI and preference handlers
│   └── onboarding/          # First-run welcome flow and profile migration
│
├── tests/                   # Argon-specific Mochitest, xpcshell, and Playwright suites
├── scripts/                 # Build automation, patching, and packaging scripts
└── .github/workflows/       # GitHub Actions CI/CD pipelines
```

## Development roadmap

The 28-week schedule below is estimated for a team of 3 to 4 developers working in parallel.

| Phase | Timeline | Deliverables | Target milestone |
| :--- | :--- | :--- | :--- |
| 1. Foundation and prototyping *(current)* | Weeks 1 to 4 | Visual identity and CSS design tokens, Git and build script setup, Firefox Artifact Build with an isolated profile, initial flat toolbar. | Compilable Argon prototype (`v0.1`) |
| 2. Interface and navigation | Weeks 5 to 10 | Navigation toolbar, horizontal and vertical tab strip, smart sidebar, Light/Dark/Compact modes, New Tab page, command palette, keyboard and ARIA support. | Argon Alpha (functional UI) |
| 3. Productivity and settings | Weeks 11 to 15 | Isolated workspaces, persistent pinned tabs, automatic tab unloading, `about:argon` preferences UI, onboarding flow, browser data importer. | Complete core experience |
| 4. Extension compatibility | Weeks 16 to 23 | Native WebExtensions verification, Chrome `manifest.json` analyzer, Chromium API adapters, MV2/MV3 background runtime bridge, local CRX/ZIP importer, 50-extension test suite. | Experimental Extension Bridge |
| 5. Quality and distribution | Weeks 24 to 28 | Stability, performance, security, and regression testing; Linux and Windows packaged builds (macOS follow-up); GitHub Actions CI/CD and signed updates. | Argon Public Beta |

## Local development setup

Local front-end work uses Firefox Artifact Builds, which download pre-compiled C++ and Rust binaries from Mozilla instead of compiling the engine from source. Building on Linux requires at least 4 GB of RAM (8 GB or more recommended) and 30 GB of free disk space. Full C++ or Rust builds run on GitHub Actions CI or remote build machines.

```bash
# 1. Download the official Mozilla bootstrap script
curl -LO https://raw.githubusercontent.com/mozilla-firefox/firefox/refs/heads/main/python/mozboot/bin/bootstrap.py

# 2. Prepare system dependencies and clone the Firefox source repository
#    (Select "Firefox for Desktop Artifact Mode" when prompted)
python3 bootstrap.py

# 3. Enter the source directory and run the initial build
cd firefox
./mach build
./mach run

# 4. Fast iterative rebuilds for UI (HTML/XUL, CSS, JS) modifications
./mach build faster
./mach run
```

## Development standards and governance

All project artifacts, including documentation, source code, identifiers, comments, commit messages, pull requests, issue tracking, CI/CD configurations, and default UI strings, are written in English.

Argon uses dedicated user profile directories (`~/.argon` on Linux, `AppData` on Windows) so it never conflicts with an existing Firefox installation. Custom telemetry is disabled by default, and extension code never runs in privileged parent processes.

Repository code is currently covered by the root [`LICENSE`](./LICENSE). Upstream Firefox and Gecko components remain under the [Mozilla Public License 2.0 (MPL 2.0)](https://www.mozilla.org/en-US/MPL/2.0/), and distributed binaries follow the [Mozilla Trademark Distribution Policy](https://www.mozilla.org/en-US/foundation/trademarks/distribution-policy/) with independent Argon branding. Full specifications and the 12-point beta release checklist are in [`Argon Browser — Implementation Plan.md`](./Argon%20Browser%20%E2%80%94%20Implementation%20Plan.md).
