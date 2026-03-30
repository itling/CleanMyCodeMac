# Changelog

All notable changes to CleanMyCodeMac are documented here.

---

## [Unreleased]

### Fixed
- Download file descriptions ("Downloaded on …") now correctly switch language when toggling zh/en
- Documents and media item descriptions also re-translate on language switch (missing `description_key` filled in)
- Scan log entries now re-render in the current language immediately when language is toggled during scanning
- Scan card descriptions for Documents and Media no longer expose internal skip-directory details
- AI model scan log entry no longer includes parenthetical tool list "(Ollama / Hugging Face, etc.)"

### Changed
- README.md and BUILD.md converted to English; Chinese versions moved to README_ZH.md / BUILD_ZH.md
- All shell script output messages converted to English (build_dmg.sh, build_icon.sh, sign_and_notarize.sh)

---

## [0.3.0] - 2026-03-30

### Added
- **AI / LLM model file scanning** — Ollama (per-model with real blob size), Hugging Face (per-repo), LM Studio, Jan, GPT4All, Msty, AnythingLLM, PyTorch Hub
- **Expanded media formats** — Insta360 (`.insv`, `.insp`, `.lrv`), GoPro (`.gpr`), DJI (`.dng`), Canon RAW (`.cr3`), Sony (`.arw`), Fujifilm (`.raf`), Panasonic (`.rw2`), Olympus (`.orf`), RED (`.r3d`), Blackmagic (`.braw`), broadcast formats (`.mxf`, `.mts`, `.m2ts`)
- **Scan log i18n** — backend sends structured `{key, args}` per log entry; frontend translates locally so language switch takes effect instantly without re-scanning

### Fixed
- Total size showing ~1 TB on a 228 GB disk:
  - `Docker.raw` sparse file reported logical size instead of physical blocks — switched to `st_blocks * 512`
  - Documents / Media scanners were double-counting files already covered by DownloadsAnalyzer — added `"Downloads"` to `SKIP_DIRS`
  - Parent-dir + child-file double-counting in result serialization — added prefix-based dedup
- Disk gauge and used-space stats not updating after clean — safe items (cache / logs / dev cache) now deleted directly instead of moved to Trash, freeing space immediately
- `NameError: auto_select_safe` in `logs_cleaner._scan_dir()` — variable now passed as parameter
- Scan UI static texts and scope label not switching language during scanning
- Scan subtitle label not updating on language switch during active scan

### Changed
- `BaseCleaner.clean()` — safe items use `shutil.rmtree` / `unlink` for immediate disk space recovery; unsafe items (documents, media, large files) still go to Trash

---

## [0.2.0] - 2026-03-28

### Added
- **Dev Cache cleaner** — Node.js, Python, Ruby, Rust, Go, Java, Kotlin, Scala, C/C++, Swift, .NET, Zig, Haskell, Elixir, Clojure, OCaml, Erlang, Dart/Flutter, R, Julia, MATLAB language caches
- **Electron editor cache scanning** — VS Code, Cursor, Windsurf, Trae, JetBrains, Zed, and more
- **Document scanner** — PDF, Word, Excel, PPT, Markdown, iWork, plain text
- **Media scanner** — images, audio, video
- Configurable scan scope — users can select which categories to scan
- Per-category safety badges (Safe to clean / Use caution)
- Docker disk usage deep analysis with actionable cleanup commands
- Startup splash screen
- i18n support (Chinese / English), auto-detected from system language with manual toggle

### Fixed
- Language switch jumping from scan view to result view unexpectedly
- Trash permission handling for external volumes

### Changed
- Window size and sidebar layout adjusted
- Scan results grouped by category → app → file list with expandable drill-down

---

## [0.1.0] - 2026-03-20

### Added
- Initial release
- System cache cleaner (13 known macOS app cache paths)
- App cache cleaner (Chrome, VSCode, JetBrains, Slack, Telegram, etc.)
- Log files cleaner (crash reports and runtime logs older than 7 days)
- Downloads analyzer (grouped by file type, configurable age threshold)
- Large file scanner (≥500 MB via `mdfind` / Spotlight)
- Trash cleaner (summary + one-click empty)
- Native macOS window via pywebview + WKWebView
- Files moved to Trash by default (recoverable)
- Quick reveal in Finder
- PyInstaller `.app` packaging + DMG build script
- Code signing and notarization script
