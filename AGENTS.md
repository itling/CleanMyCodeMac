# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

CleanMyCodeMac is a native macOS disk cleanup utility. It uses **pywebview** (WKWebView) for the native macOS window and a Python HTTP server (localhost:9527) as the backend. The UI is a single-page app embedded as an HTML string inside `web_app.py`.

## Development Commands

```bash
# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the app
cd cleanmycodemac
../venv/bin/python3 main.py

# Or use the double-clickable launcher
./run.command
```

### Building

```bash
# Package as .app (requires requirements-build.txt)
pip install -r requirements-build.txt
python3 -m PyInstaller --noconfirm CleanMyCodeMac.spec

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

`main.py` → `web_app.start_server(port=9527)` → HTTP server + pywebview window. The browser-side JS polls `/api/scan/progress` and makes POST requests to trigger scans and cleanups.

### Key Components

- **`cleanmycodemac/web_app.py`** — The central file (1400+ lines). Contains the HTTP request handler, all API endpoints, and the entire frontend UI as an embedded HTML string. This is where new API routes and UI changes go.
- **`cleanmycodemac/core/scanner.py`** — Orchestrates parallel scanning using `ThreadPoolExecutor`, invoking each cleaner's `scan()` method concurrently with progress callbacks.
- **`cleanmycodemac/core/cleaners/`** — Nine specialized cleaner modules. Each implements `BaseCleaner` with `scan()` (read-only, returns `ScanItem` list) and `clean()` (moves files to Trash, returns `CleanReport`).
- **`cleanmycodemac/models/`** — `ScanItem`, `ScanResult`, `CleanReport` dataclasses.
- **`cleanmycodemac/utils/i18n.py`** — All UI strings in Chinese and English. Use `t(key, **kwargs)` for lookups.
- **`cleanmycodemac/utils/config.py`** — Persists user config to `~/.cleanmycodemac_config.json`.

### Cleaner Modules (in `core/cleaners/`)

| File | Category key | What it scans |
|------|-------------|---------------|
| `system_cache.py` | `system_cache` | macOS system app caches (13 known paths) |
| `app_cache.py` | `app_cache` | Chrome, VSCode, JetBrains, Slack, Telegram caches |
| `logs_cleaner.py` | `log` | Crash reports and system logs older than N days |
| `downloads.py` | `download` | Old files in ~/Downloads (configurable age) |
| `large_files.py` | `large_file` | Files ≥500MB via `mdfind`; supports Docker image analysis |
| `trash.py` | `trash` | Trash bin summary and emptying |
| `dev_cache.py` | `dev_cache` | Node.js, Python, Ruby, Rust, Go, Java caches |
| `documents.py` | `document` | PDF, Word, Excel, Markdown, iWork files |
| `media.py` | `media` | Images, audio, video files |

### Adding a New Cleaner

1. Create `core/cleaners/my_cleaner.py` extending `BaseCleaner`.
2. Implement `CATEGORY`, `DISPLAY_NAME`, `scan()`, and `clean()`.
3. Register it in `core/scanner.py` and in the category list in `web_app.py`.
4. Add i18n strings to `utils/i18n.py`.

### File Operations

Files are moved to Trash via `osascript` (Finder AppleScript) — never permanently deleted. `shutil.rmtree()` is used only as a fallback. Directory sizes are measured with `du -sk` for performance.

### macOS-Specific Details

- **Full Disk Access (FDA):** Detected by attempting to read Safari's cache directory. The UI shows a permission card if FDA is missing.
- **Large file discovery:** Uses `mdfind` (Spotlight) rather than `os.walk`.
- **Disk usage:** `shutil.disk_usage("/")`.

### Runtime Config Defaults

```python
{
    "large_file_threshold_mb": 500,
    "old_download_days": 30,
    "old_log_days": 7,
    "default_scan_categories": ["system_cache", "app_cache", "log", "download", "large_file", "trash"],
    "auto_select_safe_items": True,
    "whitelist_paths": [],
    "move_to_trash": True,
}
```
