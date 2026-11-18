# Magicblue CBE web integration

This branch is based on upstream CoolbarEmu `5be1e1ab90575509fbe970d508e0f7a5379cd854`.
The old `master` branch is left unchanged. No private game files or test save data are committed here.

## Changes kept outside the core

- `scripts/magicblue-input-bridge.py` exposes existing Emscripten keyboard callbacks and OpenAL audio resume. It also corrects pointer coordinates when the player viewport is rotated.
- `scripts/magicblue-package.py` repacks normal/WebGL1 runtime variants, preserves the WASM bytes, and emits unique build metadata plus a content-based core identity.
- `.github/workflows/magicblue-web.yml` runs core tests, builds the WASM core with `std,panic_abort`, packages both variants, verifies absence of exception instructions, and publishes a dedicated GitHub preview package.

Upstream already contains the old fork's important no-EH build and Emscripten logging fixes, so those patches are not blindly reapplied. The old built-in CBM fallback is replaced in the site by a separate companion ZIP containing the two verified `WpayKer42` names. The ZIP and site UI are maintained in the separate site deployment repository, not compiled into this core.

## Build and output

Pushes to `integration/magicblue-web` that change this workflow, scripts, or core sources trigger the workflow. Builds install tools only on the GitHub runner; no local Rust/emsdk installation is required.

Outputs:

- Actions artifact: `magicblue-coolbaremu`
- GitHub prerelease channel: `magicblue-web-preview`
- Package: `magicblue-coolbaremu.zip`
- Version/hash manifest: `core-build.json`

The package contains only:

```text
cores/coolbaremu-wasm.data
cores/coolbaremu-legacy-wasm.data
cores/reports/coolbaremu.json
core-build.json
```

Each inner archive retains upstream `license.txt`. Generated files under `out/` are excluded from Git.

## Site integration and validation scope

The site uses `coolbaremu`, the companion ZIP via `EJS_biosUrl`, and the public input bridge. Player UI, App return, screenshot tools, and local save UI are site-side changes. They are not deployed to Gitee by this workflow.

Local CBE samples tested: GodWar (the same game as magicblue.cn game 9031, not verified as the identical site variant), Three Kingdoms V101, and Zombie. The menu/scene transition save test in GodWar restored the original menu framebuffer. These tests do not establish complete game compatibility or real Android WebView behavior.

The local prototype used an official compiled bundle with the JS bridge added; the workflow performs a fresh build. WASM content hashes may differ from the prototype. State files are bound to the game and core identity, so compatibility of prototype state files with the fresh build is not promised. No old-state migration layer is included.
