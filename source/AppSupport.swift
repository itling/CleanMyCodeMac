import AppKit
import Darwin
import Foundation
import WebKit

enum BridgeKeys {
    static let messageHandler = "bridge"
    static let lang = "cleanmycodemac.lang"
}

enum RepositoryLocator {
    static func rootURL() throws -> URL {
        var current = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .standardizedFileURL

        for _ in 0..<8 {
            let candidate = current.appendingPathComponent("resources/ui/index.html")
            if FileManager.default.fileExists(atPath: candidate.path) {
                return current
            }
            current.deleteLastPathComponent()
        }

        throw NSError(
            domain: "CleanMyCodeMac",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "Could not locate repository root from current working directory."]
        )
    }
}

enum HTMLLoader {
    static func resourceURL() throws -> URL {
        if let bundled = Bundle.main.resourceURL?.appendingPathComponent("ui/index.html"),
           FileManager.default.fileExists(atPath: bundled.path)
        {
            return bundled
        }

        if let repoRoot = try? RepositoryLocator.rootURL() {
            let repoHTML = repoRoot.appendingPathComponent("resources/ui/index.html")
            if FileManager.default.fileExists(atPath: repoHTML.path) {
                return repoHTML
            }
        }

        throw NSError(
            domain: "CleanMyCodeMac",
            code: 2,
            userInfo: [NSLocalizedDescriptionKey: "Could not locate resources/ui/index.html."]
        )
    }
}

enum BridgeBootstrap {
    static let script = """
    (function () {
      if (window.pywebview && window.pywebview.api) return;

      let seq = 0;
      const pending = new Map();

      function settle(kind, id, payload) {
        const entry = pending.get(id);
        if (!entry) return;
        pending.delete(id);
        if (kind === 'resolve') entry.resolve(payload);
        else entry.reject(new Error(payload && payload.message ? payload.message : String(payload || 'Bridge call failed')));
      }

      window.__swiftBridgeResolve = function (id, payload) {
        settle('resolve', id, payload);
      };

      window.__swiftBridgeReject = function (id, payload) {
        settle('reject', id, payload);
      };

      function call(method, ...args) {
        return new Promise((resolve, reject) => {
          const id = ++seq;
          pending.set(id, { resolve, reject });
          window.webkit.messageHandlers.bridge.postMessage({ id, method, args });
        });
      }

      window.__swiftNativeCall = call;

      window.pywebview = {
        api: new Proxy({}, {
          get(_target, prop) {
            return (...args) => call(String(prop), ...args);
          }
        })
      };

      window.dispatchEvent(new Event('pywebviewready'));
    })();
    """

    static let postLoadScript = """
    (function () {
      function remapBridgeApi() {
        if (typeof bridgeApi === 'undefined' || typeof window.__swiftNativeCall !== 'function') return;

        const map = {
          getDisk: 'get_disk',
          getPermissions: 'get_permissions',
          openPermissionSettings: 'open_permission_settings',
          startScan: 'start_scan',
          getScanProgress: 'get_scan_progress',
          getScanResult: 'get_scan_result',
          selectCategory: 'select_category',
          selectPath: 'select_path',
          selectAll: 'select_all',
          cleanPaths: 'clean_paths',
          analyzeTarget: 'analyze_target',
          deleteAnalyzedPath: 'delete_analyzed_path',
          runDockerCommand: 'run_docker_command',
          revealPath: 'reveal_path',
          getLanguage: 'get_language',
          getAppMeta: 'get_app_meta',
          checkForUpdates: 'check_for_updates',
          installUpdate: 'install_update',
          setLanguage: 'set_language',
          onBootstrapReady: 'on_bootstrap_ready'
        };

        Object.keys(map).forEach((name) => {
          bridgeApi[name] = (...args) => window.__swiftNativeCall(map[name], ...args);
        });

        if (typeof window.loadDisk === 'function') {
          setTimeout(() => {
            window.loadDisk();
            if (typeof window.loadPerm === 'function') {
              window.loadPerm();
            }
          }, 0);
        }
      }

      remapBridgeApi();
      window.addEventListener('load', remapBridgeApi);
      setTimeout(remapBridgeApi, 0);
      setTimeout(remapBridgeApi, 50);
    })();
    """
}

enum AppBootstrapMetadata {
    static func script() -> String {
        let payload = AppMetadata.payload()
        guard JSONSerialization.isValidJSONObject(payload),
              let data = try? JSONSerialization.data(withJSONObject: payload, options: []),
              let json = String(data: data, encoding: .utf8)
        else {
            return "window.__cleanMyCodeMacAppMeta = { version: '1.0.0', version_display: 'v1.0.0' };"
        }

        return "window.__cleanMyCodeMacAppMeta = \(json);"
    }
}

struct DiskCapacitySnapshot {
    let total: Int64
    let free: Int64
    let available: Int64

    init(total: Int64, free: Int64, available: Int64) {
        self.total = max(total, 0)
        self.free = min(max(free, 0), self.total)
        self.available = min(max(available, self.free), self.total)
    }

    var used: Int64 { max(total - free, 0) }
    var reclaimable: Int64 { max(available - free, 0) }
    var percentUsed: Double {
        total > 0 ? (Double(used) / Double(total)) * 100 : 0
    }

    func payload() -> [String: Any] {
        [
            "total": total,
            "free": free,
            "available": available,
            "reclaimable": reclaimable,
            "used": used,
            "percent_used": percentUsed,
        ]
    }
}

enum DiskInfoService {
    static func payload() -> [String: Any] {
        do {
            let attrs = try FileManager.default.attributesOfFileSystem(forPath: "/")
            let total = (attrs[.systemSize] as? NSNumber)?.int64Value ?? 0
            let free = (attrs[.systemFreeSize] as? NSNumber)?.int64Value ?? 0
            let values = try? URL(fileURLWithPath: "/").resourceValues(forKeys: [
                .volumeAvailableCapacityForImportantUsageKey,
            ])
            let available = values?.volumeAvailableCapacityForImportantUsage ?? free

            return DiskCapacitySnapshot(
                total: total,
                free: free,
                available: available
            ).payload()
        } catch {
            return DiskCapacitySnapshot(total: 0, free: 0, available: 0).payload()
        }
    }
}

enum PermissionService {
    private static let safariCache = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Caches/com.apple.Safari")
    static func payload() -> [String: Any] {
        [
            "fda": canReadDirectory(at: safariCache),
        ]
    }

    private static func canReadDirectory(at url: URL) -> Bool {
        do {
            _ = try FileManager.default.contentsOfDirectory(at: url, includingPropertiesForKeys: nil)
            return true
        } catch CocoaError.fileReadNoSuchFile {
            return true
        } catch {
            return false
        }
    }
}

enum LanguageStore {
    static func current() -> String {
        let stored = UserDefaults.standard.string(forKey: BridgeKeys.lang)
        return stored == "en" ? "en" : "zh"
    }

    static func set(_ lang: String) {
        UserDefaults.standard.set(lang == "en" ? "en" : "zh", forKey: BridgeKeys.lang)
    }

    static func payload() -> [String: Any] {
        [
            "lang": current(),
            "strings": [:],
        ]
    }
}

enum AppMetadata {
    private static let defaultVersion = "1.0.0"

    static func payload() -> [String: Any] {
        let version = currentVersion()
        return [
            "version": version,
            "version_display": "v\(version)",
        ]
    }

    static func currentVersion() -> String {
        if isRunningBundledApp(),
           let version = normalizedVersion(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String)
        {
            return version
        }
        if let version = normalizedVersion(ProcessInfo.processInfo.environment["APP_VERSION"]) {
            return version
        }
        if let version = normalizedVersion(ProcessInfo.processInfo.environment["VERSION"]) {
            return version
        }
        if let version = normalizedVersion(ProcessInfo.processInfo.environment["CLEANMYCODEMAC_VERSION"]) {
            return version
        }
        if let version = normalizedVersion(dotEnvValue(for: "APP_VERSION")) {
            return version
        }
        if let version = normalizedVersion(dotEnvValue(for: "VERSION")) {
            return version
        }
        if let version = normalizedVersion(dotEnvValue(for: "CLEANMYCODEMAC_VERSION")) {
            return version
        }
        if let version = normalizedVersion(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String) {
            return version
        }
        return defaultVersion
    }

    private static func isRunningBundledApp() -> Bool {
        Bundle.main.bundleURL.pathExtension.lowercased() == "app"
    }

    private static func normalizedVersion(_ raw: String?) -> String? {
        guard let raw else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if trimmed.hasPrefix("v") || trimmed.hasPrefix("V") {
            return String(trimmed.dropFirst())
        }
        return trimmed
    }

    private static func dotEnvValue(for key: String) -> String? {
        guard let rootURL = try? RepositoryLocator.rootURL() else { return nil }
        let envURL = rootURL.appendingPathComponent(".env")
        guard let content = try? String(contentsOf: envURL, encoding: .utf8) else { return nil }

        for rawLine in content.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
            if line.isEmpty || line.hasPrefix("#") { continue }
            guard let separator = line.firstIndex(of: "=") else { continue }

            let name = line[..<separator].trimmingCharacters(in: .whitespacesAndNewlines)
            guard name == key else { continue }

            var value = String(line[line.index(after: separator)...]).trimmingCharacters(in: .whitespacesAndNewlines)
            if value.hasPrefix("\""), value.hasSuffix("\""), value.count >= 2 {
                value = String(value.dropFirst().dropLast())
            } else if value.hasPrefix("'"), value.hasSuffix("'"), value.count >= 2 {
                value = String(value.dropFirst().dropLast())
            }
            return value
        }

        return nil
    }
}

enum NativeText {
    static let safeSystemCaches = [
        "com.apple.appstore",
        "com.apple.commerce",
        "com.apple.Bird",
        "com.apple.helpd",
        "com.apple.Maps",
        "com.apple.Music",
        "com.apple.News",
        "com.apple.Photos.PhotosUIFramework",
        "com.apple.Podcasts",
        "com.apple.QuickLookDaemon",
        "com.apple.stocks",
        "com.apple.TV",
        "com.apple.findmy",
    ]

    static let protectedAppCachePrefixes = [
        "com.apple.dt",
        "com.apple.security",
        "com.apple.keychain",
    ]

    static func categoryName(_ category: String, lang: String) -> String {
        switch (category, lang) {
        case ("download", "zh"): return "下载文件"
        case ("download", _): return "Downloads"
        case ("large_file", "zh"): return "大文件"
        case ("large_file", _): return "Large Files"
        case ("system_cache", "zh"): return "系统垃圾"
        case ("system_cache", _): return "System Junk"
        case ("app_cache", "zh"): return "应用垃圾"
        case ("app_cache", _): return "App Junk"
        case ("log", "zh"): return "日志文件"
        case ("log", _): return "Log Files"
        case ("system_temp", "zh"): return "系统临时文件"
        case ("system_temp", _): return "System Temporary Files"
        case ("dev_cache", "zh"): return "编程缓存"
        case ("dev_cache", _): return "Dev Cache"
        case ("document", "zh"): return "文档文件"
        case ("document", _): return "Documents"
        case ("media", "zh"): return "媒体文件"
        case ("media", _): return "Media"
        default: return category
        }
    }

    static func bundleDisplayName(_ bundleID: String) -> String {
        if bundleID.hasPrefix("com.apple.") {
            let suffix = bundleID.replacingOccurrences(of: "com.apple.", with: "")
            let parts = suffix
                .replacingOccurrences(of: ".", with: " ")
                .replacingOccurrences(of: "-", with: " ")
                .split(separator: " ")
                .map { String($0).capitalized }
            return "Apple " + parts.joined(separator: " ")
        }

        let suffix = bundleID.split(separator: ".").last.map(String.init) ?? bundleID
        return suffix
            .replacingOccurrences(of: "-", with: " ")
            .replacingOccurrences(of: "_", with: " ")
            .capitalized
    }

    static func downloadGroupName(for fileExtension: String, lang: String) -> String {
        switch fileExtension.lowercased() {
        case "dmg", "pkg", "mpkg":
            return lang == "zh" ? "安装包" : "Installers"
        case "zip", "tar", "gz", "bz2", "7z", "rar":
            return lang == "zh" ? "压缩包" : "Archives"
        case "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm":
            return lang == "zh" ? "视频" : "Videos"
        case "iso", "img":
            return lang == "zh" ? "镜像" : "Disk Images"
        case "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx":
            return lang == "zh" ? "文档" : "Documents"
        default:
            return lang == "zh" ? "其他" : "Others"
        }
    }

    static func oldDownloadDescription(date: String, lang: String) -> String {
        lang == "zh" ? "旧下载文件（\(date)）" : "Old download (\(date))"
    }

    static func downloadDescription(date: String, lang: String) -> String {
        lang == "zh" ? "下载文件（\(date)）" : "Download (\(date))"
    }

    static func largeFileDescription(name: String, lang: String) -> String {
        lang == "zh" ? "大文件：\(name)" : "Large file: \(name)"
    }

    static func documentGroupName(for fileExtension: String, lang: String) -> String {
        switch fileExtension.lowercased() {
        case "pdf":
            return "PDF"
        case "doc", "docx":
            return "Word"
        case "xls", "xlsx", "csv":
            return lang == "zh" ? "表格" : "Spreadsheets"
        case "ppt", "pptx":
            return lang == "zh" ? "演示文稿" : "Presentations"
        case "md":
            return "Markdown"
        case "txt":
            return lang == "zh" ? "文本" : "Text"
        case "rtf":
            return lang == "zh" ? "富文本" : "Rich Text"
        case "pages", "numbers", "keynote":
            return "iWork"
        default:
            return lang == "zh" ? "文档" : "Documents"
        }
    }

    static func mediaGroupName(for fileExtension: String, lang: String) -> String {
        switch fileExtension.lowercased() {
        case "jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "heic", "heif", "svg",
             "raw", "dng", "cr2", "cr3", "nef", "nrw", "arw", "srf", "sr2", "raf", "rw2", "orf",
             "pef", "ptx", "3fr", "rwl", "insp", "gpr":
            return lang == "zh" ? "图片" : "Images"
        case "mp3", "wav", "aac", "flac", "ogg", "m4a", "wma", "ape", "aiff", "aif", "opus", "amr":
            return lang == "zh" ? "音频" : "Audio"
        case "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "3gp", "3g2", "ts", "mts", "m2ts",
             "insv", "lrv", "r3d", "braw", "mxf", "vob", "mpg", "mpeg", "m2v":
            return lang == "zh" ? "视频" : "Videos"
        default:
            return lang == "zh" ? "媒体" : "Media"
        }
    }

    static func documentDescription(name: String, date: String, lang: String) -> String {
        lang == "zh" ? "文档文件：\(name)（\(date)）" : "Document: \(name) (\(date))"
    }

    static func mediaDescription(name: String, date: String, lang: String) -> String {
        lang == "zh" ? "媒体文件：\(name)（\(date)）" : "Media: \(name) (\(date))"
    }

    static func systemCacheDescription(bundleID: String, lang: String) -> String {
        lang == "zh" ? "系统缓存：\(bundleID)" : "System cache: \(bundleID)"
    }

    static func appCacheDescription(bundleID: String, lang: String) -> String {
        lang == "zh" ? "应用缓存：\(bundleID)" : "App cache: \(bundleID)"
    }

    static func logDescription(date: String, lang: String) -> String {
        lang == "zh" ? "旧日志（\(date)）" : "Old log (\(date))"
    }

    static func aiToolLogDescription(date: String, lang: String) -> String {
        lang == "zh"
            ? "AI 编程工具会话日志（\(date)），可能包含对话或排障信息"
            : "AI coding tool session log (\(date)); may contain conversation or diagnostic data"
    }

    static func systemTemporaryGroup(ageDays: Int, lang: String) -> String {
        if ageDays >= 30 {
            return lang == "zh" ? "30 天以上" : "30+ days old"
        }
        if ageDays >= 7 {
            return lang == "zh" ? "7 天以上" : "7+ days old"
        }
        return lang == "zh" ? "近期临时文件" : "Recent temporary files"
    }

    static func systemTemporaryDescription(date: String, ageDays: Int, lang: String) -> String {
        if lang == "zh" {
            return "系统临时项目，最后修改于 \(date)（约 \(ageDays) 天前）。请确认不再需要后清理。"
        }
        return "System temporary item, last modified \(date) (about \(ageDays) days ago). Clean it only if it is no longer needed."
    }

    static func devLangCacheDescription(langName: String, pathName: String, lang: String) -> String {
        lang == "zh" ? "\(langName) 缓存：\(pathName)" : "\(langName) cache: \(pathName)"
    }

    static func devToolCacheDescription(tool: String, pathName: String, lang: String) -> String {
        lang == "zh" ? "\(tool) 缓存：\(pathName)" : "\(tool) cache: \(pathName)"
    }

    static func aiRuntimeCacheDescription(tool: String, lang: String) -> String {
        lang == "zh"
            ? "\(tool) 运行依赖缓存；删除后需要重新下载，建议退出应用后手动选择。"
            : "\(tool) runtime dependencies; deleting requires a re-download. Quit the app and opt in manually."
    }

    static func aiModelDescription(tool: String, name: String, lang: String) -> String {
        lang == "zh" ? "\(tool) 模型：\(name)" : "\(tool) model: \(name)"
    }

    static func devCacheDescription(tool: String, pathName: String, lang: String) -> String {
        lang == "zh" ? "\(tool) 缓存：\(pathName)" : "\(tool) cache: \(pathName)"
    }

    static func projectArtifactDescription(tool: String, pathName: String, lang: String) -> String {
        return lang == "zh"
            ? "\(tool) 项目产物：\(pathName)，通常可由依赖安装或构建命令重新生成。"
            : "\(tool) project artifact: \(pathName). Usually rebuildable from install or build commands."
    }

    static func gitRepositoriesName(lang: String) -> String {
        lang == "zh" ? "Git 仓库" : "Git Repositories"
    }

    static func gitRepositoryDescription(path: String, lang: String) -> String {
        lang == "zh"
            ? "Git 仓库占用：\(path)，仅供分析，不会默认清理。"
            : "Git repository usage: \(path). Analysis only; never selected for cleanup by default."
    }

    static func dockerDataDescription(lang: String) -> String {
        lang == "zh"
            ? "Docker Desktop 数据目录。请用分析面板查看 Docker 可回收空间，不建议直接删除目录。"
            : "Docker Desktop data directory. Use the analysis panel for reclaimable Docker space; direct directory removal is not recommended."
    }

    static func dockerAnalysisTitle(lang: String) -> String {
        lang == "zh" ? "Docker 占用分析" : "Docker Usage Analysis"
    }

    static func dockerAnalysisHighlights(lang: String) -> [String] {
        if lang == "zh" {
            return [
                "Docker Desktop 会把镜像、容器、volume 和 build cache 放在本地 VM/数据目录里。",
                "建议优先使用 Docker CLI prune，而不是直接删除 Docker 数据目录。",
                "不带 --volumes 的 prune 通常更保守；volume 可能包含数据库等持久化数据。",
            ]
        }
        return [
            "Docker Desktop stores images, containers, volumes, and build cache in its local VM/data directory.",
            "Prefer Docker CLI prune commands instead of deleting the Docker data directory directly.",
            "Prune without --volumes is more conservative; volumes may contain persistent database data.",
        ]
    }

    static func dockerSuggestedActions(lang: String) -> [[String: Any]] {
        if lang == "zh" {
            return [
                [
                    "label": "保守清理",
                    "description": "删除未使用镜像、停止的容器、网络和 build cache；不删除 volume。",
                    "command": "docker system prune -af",
                    "action_id": "system_prune",
                    "requires_confirmation": true,
                ],
                [
                    "label": "查看占用",
                    "description": "先查看 Docker 自己报告的占用和可回收空间。",
                    "command": "docker system df",
                    "action_id": "system_df",
                    "requires_confirmation": false,
                ],
                [
                    "label": "清理未使用 volume",
                    "description": "会删除未挂载的数据卷，可能包含旧数据库数据，请确认后再执行。",
                    "command": "docker volume prune",
                    "action_id": "volume_prune",
                    "requires_confirmation": true,
                ],
            ]
        }
        return [
            [
                "label": "Conservative prune",
                "description": "Remove unused images, stopped containers, networks, and build cache; keep volumes.",
                "command": "docker system prune -af",
                "action_id": "system_prune",
                "requires_confirmation": true,
            ],
            [
                "label": "Inspect usage",
                "description": "Show Docker's own usage and reclaimable space report first.",
                "command": "docker system df",
                "action_id": "system_df",
                "requires_confirmation": false,
            ],
            [
                "label": "Prune unused volumes",
                "description": "Deletes unused volumes and may remove old database data. Confirm first.",
                "command": "docker volume prune",
                "action_id": "volume_prune",
                "requires_confirmation": true,
            ],
        ]
    }

    static func groupSummary(count: Int, start: String?, end: String?, lang: String) -> String {
        if let start, let end {
            if start == end {
                return lang == "zh" ? "共 \(count) 项，\(start)" : "\(count) items, \(start)"
            }
            return lang == "zh" ? "共 \(count) 项，\(start) ~ \(end)" : "\(count) items, \(start) ~ \(end)"
        }
        return lang == "zh" ? "共 \(count) 项" : "\(count) items"
    }

    static func migrationNotice(lang: String) -> String {
        if lang == "zh" {
            return "Swift 原生迁移已接通主扫描链路，当前版本会继续补齐与 Python 版的细节一致性。"
        }
        return "The Swift migration now drives the main scan flow natively, and parity polish with the Python build is continuing."
    }

    static func scanLabel(for category: String, lang: String) -> String {
        switch (category, lang) {
        case ("download", "zh"): return "正在分析下载文件夹..."
        case ("download", _): return "Analyzing downloads folder..."
        case ("large_file", "zh"): return "正在搜索大文件..."
        case ("large_file", _): return "Searching large files..."
        case ("system_cache", "zh"): return "正在扫描系统缓存..."
        case ("system_cache", _): return "Scanning system cache..."
        case ("app_cache", "zh"): return "正在扫描应用缓存..."
        case ("app_cache", _): return "Scanning app cache..."
        case ("log", "zh"): return "正在扫描日志文件..."
        case ("log", _): return "Scanning log files..."
        case ("system_temp", "zh"): return "正在扫描系统临时文件..."
        case ("system_temp", _): return "Scanning system temporary files..."
        case ("dev_cache", "zh"): return "正在扫描编程缓存..."
        case ("dev_cache", _): return "Scanning dev caches..."
        case ("document", "zh"): return "正在扫描文档文件..."
        case ("document", _): return "Scanning document files..."
        case ("media", "zh"): return "正在扫描媒体文件..."
        case ("media", _): return "Scanning media files..."
        default:
            return migrationNotice(lang: lang)
        }
    }

    static func scanDone(name: String, lang: String) -> String {
        lang == "zh" ? "已完成：\(name)" : "Done: \(name)"
    }

    static func scanComplete(lang: String) -> String {
        lang == "zh" ? "扫描完成" : "Scan complete"
    }

    static func analysisHighlights(url: URL, size: String, lang: String) -> [String] {
        if lang == "zh" {
            return [
                "文件位置：\(url.path)",
                "当前大小：\(size)",
            ]
        }
        return [
            "Location: \(url.path)",
            "Current size: \(size)",
        ]
    }
}

enum NativeFormat {
    static func size(_ sizeBytes: Int64) -> String {
        var value = Double(sizeBytes)
        let units = ["B", "KB", "MB", "GB", "TB", "PB"]
        for unit in units {
            if value < 1024 {
                return String(format: "%.1f %@", value, unit)
            }
            value /= 1024
        }
        return String(format: "%.1f PB", value)
    }

    static func shortPath(_ url: URL) -> String {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let path = url.path
        if path.hasPrefix(home) {
            return "~" + path.dropFirst(home.count)
        }
        return path
    }

    static func date(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }
}

enum NativePaths {
    static func expand(_ pattern: String) -> [URL] {
        let expanded = (pattern as NSString).expandingTildeInPath
        guard expanded.contains("*") || expanded.contains("?") else {
            let url = URL(fileURLWithPath: expanded)
            return FileManager.default.fileExists(atPath: url.path) ? [url] : []
        }

        let url = URL(fileURLWithPath: expanded)
        let parent = url.deletingLastPathComponent()
        let componentPattern = url.lastPathComponent

        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: parent,
            includingPropertiesForKeys: nil,
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        return entries.filter { wildcardMatch($0.lastPathComponent, pattern: componentPattern) }
    }

    static func wildcardMatch(_ value: String, pattern: String) -> Bool {
        let escaped = NSRegularExpression.escapedPattern(for: pattern)
            .replacingOccurrences(of: "\\*", with: ".*")
            .replacingOccurrences(of: "\\?", with: ".")
        let regex = "^\(escaped)$"
        return value.range(of: regex, options: .regularExpression) != nil
    }

}

enum NativeFileMetrics {
    static func modifiedDate(_ url: URL) -> Date? {
        (try? url.resourceValues(forKeys: [.contentModificationDateKey]))?.contentModificationDate
    }

    static func isDirectory(_ url: URL) -> Bool {
        (try? url.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory == true
    }

    static func fileSize(_ url: URL) -> Int64 {
        let values = try? url.resourceValues(
            forKeys: [.totalFileAllocatedSizeKey, .fileAllocatedSizeKey, .fileSizeKey]
        )
        return Int64(values?.totalFileAllocatedSize ?? values?.fileAllocatedSize ?? values?.fileSize ?? 0)
    }

    static func itemSize(_ url: URL) -> Int64 {
        isDirectory(url) ? directorySize(url) : fileSize(url)
    }

    static func directorySize(_ url: URL) -> Int64 {
        guard FileManager.default.fileExists(atPath: url.path) else { return 0 }
        guard let enumerator = FileManager.default.enumerator(
            at: url,
            includingPropertiesForKeys: [.isRegularFileKey, .totalFileAllocatedSizeKey, .fileAllocatedSizeKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else {
            return 0
        }

        var total: Int64 = 0
        while let item = enumerator.nextObject() as? URL {
            let values = try? item.resourceValues(
                forKeys: [.isRegularFileKey, .totalFileAllocatedSizeKey, .fileAllocatedSizeKey, .fileSizeKey]
            )
            guard values?.isRegularFile == true else { continue }
            total += Int64(values?.totalFileAllocatedSize ?? values?.fileAllocatedSize ?? values?.fileSize ?? 0)
        }
        return total
    }
}
