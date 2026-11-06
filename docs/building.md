# Building Argon

Status: fork tooling implemented and tested offline. No full Argon build has
been completed yet; see "Verified versus unverified".

Argon is a fork of Firefox Desktop. It does not restyle an installed Firefox:
it takes one pinned upstream source revision, applies Argon's changes to it,
and compiles a separate browser with its own binary, profile directory,
remoting name, vendor, and branding. A running Firefox and a running Argon do
not share profiles, windows, or URL hand-off.

## How the fork is organised

Argon uses the "patch set on a pinned upstream" model (the same model Zen and
LibreWolf use) instead of carrying a full copy of mozilla-central in this
repository:

| Piece | File | Role |
| :-- | :-- | :-- |
| Upstream pin | `config/firefox.lock.json` | Exact Firefox revision, archive SHA-256, artifact task, and the SHA-256 of every upstream file Argon patches |
| Change set | `config/overlay.json` | Every file Argon adds and every upstream file it patches, as data |
| Identity | `config/mozconfig` | Build options that make the product Argon |
| Tool | `scripts/argon.py` | fetch, apply, bootstrap, build, run, package |
| Argon sources | `browser/`, `argon/` | Chrome, branding, preferences, and Argon modules |

Updating to a newer Firefox means changing the lock, re-running `apply`, and
fixing whatever hooks report drift. That keeps the diff against upstream small
and reviewable.

## Application identity

| What | Value | Where it is set |
| :-- | :-- | :-- |
| Binary | `argon` (`dist/bin/argon`) | `--with-app-name=argon` |
| application.ini Name | `Argon` | `--with-app-basename=Argon` |
| Display name, icons, brand strings | Argon | `--with-branding=browser/branding/argon` |
| Profile directory | `argon` (own profile root, never Firefox's) | overlay hook on `browser/moz.configure` |
| Remoting name, WM_CLASS | `argon` | `MOZ_APP_REMOTINGNAME=argon` |
| Vendor | `Argon` | overlay hook on `browser/moz.configure` |
| Distribution id | `org.argon.browser` | `--with-distribution-id` |
| Updater, crash reporter | disabled | no Argon update or crash server exists yet |

Two values intentionally stay upstream:

- **`MOZ_APP_ID`** stays Firefox's id. WebExtensions on addons.mozilla.org
  declare compatibility against it; keeping it is what lets Argon install AMO
  add-ons natively.
- **The User-Agent** keeps Firefox's product token (`MOZ_APP_UA_NAME` is
  empty), so sites that sniff the UA do not treat Argon as an unknown browser.

`MOZ_APP_VENDOR` and `MOZ_APP_PROFILE` are patched in `browser/moz.configure`
instead of `config/mozconfig` because `toolkit/moz.configure` declares both
with `project_flag()`, which restricts `possible_origins` to `("implied",)`;
setting them from the environment or mozconfig would make configure fail.

## Commands

```bash
# Toolchain, RAM, disk, and identity report. Changes nothing.
python3 scripts/argon.py doctor

# Download the pinned archive, verify its SHA-256, extract it to the workspace.
python3 scripts/argon.py fetch

# Apply the Argon change set. All-or-nothing: every hook is checked for
# upstream drift before any file is written.
python3 scripts/argon.py apply

# Let mach install clang, rustc, cbindgen, and node into ~/.mozbuild.
python3 scripts/argon.py bootstrap

# Full source build with the Argon identity (two jobs by default).
python3 scripts/argon.py --jobs 2 build

# Launch dist/bin/argon with a development profile kept in the workspace.
python3 scripts/argon.py run

# Produce the distributable archive (refuses artifact builds).
python3 scripts/argon.py package
```

The same commands are available as `npm run doctor|fetch|apply|bootstrap|build|start|package`.

The workspace defaults to `~/.cache/argon-build` (or `$XDG_CACHE_HOME/argon-build`);
override it with `ARGON_WORKSPACE` or `--workspace`. It must be an ASCII path
without spaces, which is also why it lives outside this repository. The tool
refuses the filesystem root, the home directory, the repository, a repository
ancestor, and paths with shell metacharacters.

### Front-end loop: `--artifact`

```bash
python3 scripts/argon.py --artifact build
```

Artifact builds download Mozilla's pre-built C++ and Rust components, so CSS,
JavaScript, XHTML, and FTL changes need no compiler. The downloaded binaries
carry Firefox's native identity (`dist/bin/firefox`, Firefox's profile root
and remoting name), so an artifact build is only a development loop, never an
Argon release. `package` refuses to package one.

Artifact resolution also needs an hg or git checkout to map the tree to a
Mozilla task (`ValueError: Must provide path to exactly one of hg and git`),
and git artifact builds need a **git-cinnabar** clone. The GitHub tarball that
`fetch` downloads has no VCS metadata; `doctor --artifact` reports this.

## The change set

| Target | Change |
| :-- | :-- |
| `browser/base/content/argon/` | `tokens.css`, `argon.css`, `argon-controller.mjs` added |
| `browser/base/jar.mn` | three `content/browser/argon/*` entries |
| `browser/base/content/browser.xhtml` | `#include argon-window-hooks.inc.xhtml` after `browser-main.js` |
| `browser/app/profile/firefox.js` | `argon.*` defaults; Mozilla studies, Normandy, and data submission off by default |
| `browser/moz.configure` | `MOZ_APP_VENDOR` (`Argon`) and `MOZ_APP_PROFILE` (`argon`) implied |
| `browser/branding/argon/` | branding package added |

Every insertion is wrapped in `BEGIN Argon overlay` / `END Argon overlay`
markers; a replaced line keeps the upstream original as a comment. Re-running
`apply` replaces the blocks instead of stacking duplicates.

Security behaviour stays upstream: add-on signing, sandboxing, Safe Browsing,
and the self-XSS paste guard are not relaxed, and `tests/build` fails if the
prefs or the mozconfig try to.

## Verified versus unverified

**Verified:**

- `fetch` against the real pinned archive: the SHA-256 matched the lock.
- `apply` against the real upstream hook files (`config/source-reference/`
  holds byte-identical copies, checked against the lock). The patched
  `browser/moz.configure` still parses as Python and carries exactly one
  `MOZ_APP_VENDOR` implication.
- Every option in `config/mozconfig` was checked against the `moz.configure`
  files of the pinned revision.
- Offline tests for idempotency, drift detection, all-or-nothing apply, the
  generated mozconfig in both modes, `run`, and `package` guards.

**Not verified yet:**

- **A completed full build.** It needs the toolchains from `bootstrap`, about
  40 GB of disk, and realistically 8 GB of RAM or more. The development machine
  has 3.6 GiB, so the first full build should run on a larger workstation or a
  CI runner with `--jobs` sized to its memory.
- **A launched `dist/bin/argon`**, and therefore the profile path and window
  class on a real desktop.
- **Packaged binaries, code signing, and updates.** Phase 5.

## GitHub Actions full build

`.github/workflows/build.yml` runs the end-to-end Linux x86_64 source build on
GitHub Actions (`push` to `main`/`v*` tags or `workflow_dispatch`):

1. Frees ~55 GB of pre-installed runner bloat and provisions an 8 GB swapfile
   so Rust LTO and `libxul.so` linking do not run out of disk or memory.
2. Runs the Node and Python contract suites (`npm test && npm run test:python`).
3. Restores/saves cached Mozilla toolchains (`~/.mozbuild`), Rust (`~/.cargo`,
   `~/.rustup`), and the verified upstream tarball.
4. Runs `fetch`, `apply`, `bootstrap`, and `build` (`dist/bin/argon`).
5. Verifies `dist/bin/application.ini` (`Name=Argon`, `Vendor=Argon`,
   `Profile=argon`, `RemotingName=argon`) and `dist/bin/argon --version`.
6. Runs `tests/browser/test_chrome.py` with `ARGON_TEST_BINARY` pointed at the
   newly compiled `dist/bin/argon`.
7. Runs `package` (`./mach package`) and uploads `argon-*.tar.xz`,
   `SHA256SUMS`, `application.ini`, and the chrome smoke screenshots as the
   `argon-linux-x86_64` workflow artifact.

## Requirements

From Mozilla's Linux build documentation: 4 GB RAM minimum, 8 GB or more
recommended, and at least 30 GB of free disk space (an optimised objdir plus
the source tree is closer to 40 GB). Any change to C++, Rust, or native
platform APIs requires a full build.

## Tests

```bash
python3 -m unittest discover -s tests/build -v
```
