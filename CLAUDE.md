# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CleanMyCodeMac is a native macOS disk cleanup utility. The app is now implemented in **Swift + AppKit + WKWebView**. The frontend is a single-page app stored at `resources/ui/index.html`, and all bridge, scan, cleanup, and analysis logic lives under `source/`.

## Development Commands

```bash
# Build the app
swift build

# Run the app
swift run

# Or use the double-clickable launcher
./run.command
```

### Building

```bash
# Build DMG installer
./build_dmg.sh              # auto-detect arch
./build_dmg.sh arm64        # Apple Silicon
./build_dmg.sh x86_64       # Intel
./build_dmg.sh all          # both architectures

# Generate app icon from resources/app_icon.png
./build_icon.sh

# Sign and notarize (requires Apple Developer credentials)
DEVELOPER_ID_APP="..." APPLE_ID="..." TEAM_ID="..." APP_PASSWORD="..." ./sign_and_notarize.sh
```

No linting or test runner is configured in this project.

## Architecture

### Startup Flow

`swift run` → `AppMain.swift` → `WKWebView` window. `AppSupport.swift` injects a `window.pywebview.api` compatible bridge shim before the page loads, and `NativeBridge.swift` forwards JS calls into `NativeScanEngine.swift`.

### Key Components

- **`Package.swift`** — Swift Package definition for the executable target.
- **`source/AppMain.swift`** — AppKit startup, WKWebView configuration, window lifecycle.
- **`source/AppSupport.swift`** — Repository/resource lookup, bridge bootstrap JS, disk info, permission checks, text helpers.
- **`source/NativeBridge.swift`** — Bridge dispatcher that exposes `get_disk`, `start_scan`, `clean_paths`, and the rest of the JS API surface.
- **`source/NativeScanEngine.swift`** — Native scanning, deduped selection state, cleanup, and lightweight file analysis for all categories.
- **`resources/ui/index.html`** — The SPA that renders the current app UI.

### Adding a New Cleaner

1. Add a new scan path in `NativeScanEngine.swift`.
2. Register the category in `startScan`, `progressKey`, and serialization helpers.
3. Update `resources/ui/index.html` so the category appears in the scan scope and results UI.
4. Add any new labels or shared copy in `AppSupport.swift` if the browser UI needs native-provided text.

### File Operations

Unsafe items are moved to Trash when possible. Safe cleanup targets and Trash entries may be removed directly to reclaim space immediately.

### macOS-Specific Details

- **Full Disk Access (FDA):** Detected by attempting to read Safari's cache directory. The UI shows a permission card if FDA is missing.
- **Trash access:** Checked by probing the current user's Trash directory.
- **Window bridge:** The HTML expects a `pywebview`-style API; the Swift shell intentionally preserves that interface.
