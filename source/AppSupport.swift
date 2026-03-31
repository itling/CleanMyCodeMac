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
          revealPath: 'reveal_path',
          getLanguage: 'get_language',
          getAppMeta: 'get_app_meta',
          checkForUpdates: 'check_for_updates',
          openExternalUrl: 'open_external_url',
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

enum DiskInfoService {
    static func payload() -> [String: Any] {
        do {
            let attrs = try FileManager.default.attributesOfFileSystem(forPath: "/")
            let total = (attrs[.systemSize] as? NSNumber)?.int64Value ?? 0
            let free = (attrs[.systemFreeSize] as? NSNumber)?.int64Value ?? 0
            let used = max(total - free, 0)
            let percent = total > 0 ? (Double(used) / Double(total)) * 100 : 0
            return [
                "total": total,
                "free": free,
                "used": used,
                "percent_used": percent,
            ]
        } catch {
            return [
                "total": 0,
                "free": 0,
                "used": 0,
                "percent_used": 0,
            ]
        }
    }
}

enum PermissionService {
    private static let safariCache = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent("Library/Caches/com.apple.Safari")
    private static let trashPath = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".Trash")

    static func payload() -> [String: Any] {
        [
            "fda": canReadDirectory(at: safariCache),
            "trash": canReadDirectory(at: trashPath),
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

private struct GitHubReleaseAsset: Decodable {
    let name: String
    let browserDownloadURL: String

    enum CodingKeys: String, CodingKey {
        case name
        case browserDownloadURL = "browser_download_url"
    }
}

private struct GitHubLatestRelease: Decodable {
    let tagName: String
    let htmlURL: String
    let assets: [GitHubReleaseAsset]

    enum CodingKeys: String, CodingKey {
        case tagName = "tag_name"
        case htmlURL = "html_url"
        case assets
    }
}

enum UpdateService {
    private static let owner = "itling"
    private static let repo = "CleanMyCodeMac"
    private static let releasePageURL = "https://github.com/\(owner)/\(repo)/releases/latest"
    private static let latestReleaseAPIURL = URL(string: "https://api.github.com/repos/\(owner)/\(repo)/releases/latest")!
    private static let releasesAPIURL = URL(string: "https://api.github.com/repos/\(owner)/\(repo)/releases")!

    struct Payload: Sendable {
        let currentVersion: String
        let latestVersion: String
        let currentArch: String
        let hasUpdate: Bool
        let manualOnly: Bool
        let downloadURL: String
        let releaseURL: String
        let assetName: String
        let buttonLabel: String
        let checkedAt: String
        let fallbackReleaseURL: String

        func dictionary() -> [String: Any] {
            [
                "current_version": currentVersion,
                "latest_version": latestVersion,
                "current_arch": currentArch,
                "has_update": hasUpdate,
                "manual_only": manualOnly,
                "download_url": downloadURL,
                "release_url": releaseURL,
                "asset_name": assetName,
                "button_label": buttonLabel,
                "checked_at": checkedAt,
                "fallback_release_url": fallbackReleaseURL,
            ]
        }
    }

    static func checkForUpdates(completion: @Sendable @escaping (Result<Payload, Error>) -> Void) {
        fetchRelease(url: latestReleaseAPIURL) { result in
            switch result {
            case .success(let release):
                completion(.success(payload(for: release)))
            case .failure(let error as NSError) where error.code == 404:
                fetchReleaseList { fallback in
                    switch fallback {
                    case .success(let release):
                        completion(.success(payload(for: release)))
                    case .failure(let fallbackError as NSError) where fallbackError.code == 404:
                        completion(.success(emptyPayload()))
                    case .failure:
                        completion(.success(manualPayload()))
                    }
                }
            case .failure:
                completion(.success(manualPayload()))
            }
        }
    }

    private static func fetchRelease(url: URL, completion: @Sendable @escaping (Result<GitHubLatestRelease, Error>) -> Void) {
        var request = URLRequest(url: url)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("CleanMyCodeMac", forHTTPHeaderField: "User-Agent")
        request.timeoutInterval = 8

        updateSession().dataTask(with: request) { data, response, error in
            if let error {
                completion(.failure(error))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion(.failure(NSError(
                    domain: "CleanMyCodeMac",
                    code: 20,
                    userInfo: [NSLocalizedDescriptionKey: "Invalid update response."]
                )))
                return
            }

            guard (200..<300).contains(http.statusCode), let data else {
                completion(.failure(NSError(
                    domain: "CleanMyCodeMac",
                    code: http.statusCode,
                    userInfo: [NSLocalizedDescriptionKey: "Update request failed with status \(http.statusCode)."]
                )))
                return
            }

            do {
                let release = try JSONDecoder().decode(GitHubLatestRelease.self, from: data)
                completion(.success(release))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    private static func fetchReleaseList(completion: @Sendable @escaping (Result<GitHubLatestRelease, Error>) -> Void) {
        fetchReleaseList(url: releasesAPIURL, completion: completion)
    }

    private static func fetchReleaseList(url: URL, completion: @Sendable @escaping (Result<GitHubLatestRelease, Error>) -> Void) {
        var request = URLRequest(url: url)
        request.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        request.setValue("CleanMyCodeMac", forHTTPHeaderField: "User-Agent")
        request.timeoutInterval = 8

        updateSession().dataTask(with: request) { data, response, error in
            if let error {
                completion(.failure(error))
                return
            }

            guard let http = response as? HTTPURLResponse else {
                completion(.failure(NSError(
                    domain: "CleanMyCodeMac",
                    code: 21,
                    userInfo: [NSLocalizedDescriptionKey: "Invalid releases list response."]
                )))
                return
            }

            guard (200..<300).contains(http.statusCode), let data else {
                completion(.failure(NSError(
                    domain: "CleanMyCodeMac",
                    code: http.statusCode,
                    userInfo: [NSLocalizedDescriptionKey: "Releases list request failed with status \(http.statusCode)."]
                )))
                return
            }

            do {
                let releases = try JSONDecoder().decode([GitHubLatestRelease].self, from: data)
                if let release = releases.first {
                    completion(.success(release))
                } else {
                    completion(.failure(NSError(
                        domain: "CleanMyCodeMac",
                        code: 404,
                        userInfo: [NSLocalizedDescriptionKey: "No published releases found."]
                    )))
                }
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }

    private static func payload(for release: GitHubLatestRelease) -> Payload {
        let currentVersion = AppMetadata.currentVersion()
        let latestVersion = normalizeVersion(release.tagName)
        let currentArch = currentArchitecture()
        let preferredAssetName = "CleanMyCodeMac-\(currentArch).dmg"
        let matchedAsset = release.assets.first { $0.name == preferredAssetName }
            ?? release.assets.first { $0.name.contains(currentArch) && $0.name.hasSuffix(".dmg") }
            ?? release.assets.first { $0.name.hasSuffix(".dmg") }

        let downloadURL = matchedAsset?.browserDownloadURL ?? release.htmlURL
        let hasUpdate = isVersion(latestVersion, newerThan: currentVersion)

        return Payload(
            currentVersion: currentVersion,
            latestVersion: latestVersion,
            currentArch: currentArch,
            hasUpdate: hasUpdate,
            manualOnly: false,
            downloadURL: downloadURL,
            releaseURL: release.htmlURL,
            assetName: matchedAsset?.name ?? "",
            buttonLabel: hasUpdate ? "v\(latestVersion)" : "",
            checkedAt: ISO8601DateFormatter().string(from: Date()),
            fallbackReleaseURL: releasePageURL
        )
    }

    private static func emptyPayload() -> Payload {
        Payload(
            currentVersion: AppMetadata.currentVersion(),
            latestVersion: AppMetadata.currentVersion(),
            currentArch: currentArchitecture(),
            hasUpdate: false,
            manualOnly: false,
            downloadURL: "",
            releaseURL: releasePageURL,
            assetName: "",
            buttonLabel: "",
            checkedAt: ISO8601DateFormatter().string(from: Date()),
            fallbackReleaseURL: releasePageURL
        )
    }

    private static func manualPayload() -> Payload {
        Payload(
            currentVersion: AppMetadata.currentVersion(),
            latestVersion: AppMetadata.currentVersion(),
            currentArch: currentArchitecture(),
            hasUpdate: false,
            manualOnly: true,
            downloadURL: "",
            releaseURL: releasePageURL,
            assetName: "",
            buttonLabel: "",
            checkedAt: ISO8601DateFormatter().string(from: Date()),
            fallbackReleaseURL: releasePageURL
        )
    }

    private static func updateSession() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.timeoutIntervalForRequest = 8
        configuration.timeoutIntervalForResource = 8
        configuration.connectionProxyDictionary = [:]
        return URLSession(configuration: configuration)
    }

    private static func currentArchitecture() -> String {
        #if arch(arm64)
        return "arm64"
        #elseif arch(x86_64)
        return "x86_64"
        #else
        return Host.current().localizedName ?? "unknown"
        #endif
    }

    private static func normalizeVersion(_ raw: String) -> String {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return AppMetadata.currentVersion() }
        if trimmed.hasPrefix("v") || trimmed.hasPrefix("V") {
            return String(trimmed.dropFirst())
        }
        return trimmed
    }

    private static func isVersion(_ lhs: String, newerThan rhs: String) -> Bool {
        let lhsParts = lhs.split(separator: ".").map { Int($0) ?? 0 }
        let rhsParts = rhs.split(separator: ".").map { Int($0) ?? 0 }
        let maxCount = max(lhsParts.count, rhsParts.count)

        for index in 0..<maxCount {
            let left = index < lhsParts.count ? lhsParts[index] : 0
            let right = index < rhsParts.count ? rhsParts[index] : 0
            if left != right {
                return left > right
            }
        }

        return false
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
        case ("trash", "zh"): return "废纸篓"
        case ("trash", _): return "Trash"
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

    static func devLangCacheDescription(langName: String, pathName: String, lang: String) -> String {
        lang == "zh" ? "\(langName) 缓存：\(pathName)" : "\(langName) cache: \(pathName)"
    }

    static func devToolCacheDescription(tool: String, pathName: String, lang: String) -> String {
        lang == "zh" ? "\(tool) 缓存：\(pathName)" : "\(tool) cache: \(pathName)"
    }

    static func aiModelDescription(tool: String, name: String, lang: String) -> String {
        lang == "zh" ? "\(tool) 模型：\(name)" : "\(tool) model: \(name)"
    }

    static func devCacheDescription(tool: String, pathName: String, lang: String) -> String {
        lang == "zh" ? "\(tool) 缓存：\(pathName)" : "\(tool) cache: \(pathName)"
    }

    static func trashLabel(volume: String?, lang: String) -> String {
        if let volume, !volume.isEmpty {
            return lang == "zh" ? "外置磁盘废纸篓（\(volume)）" : "External Trash (\(volume))"
        }
        return lang == "zh" ? "废纸篓项目" : "Trash item"
    }

    static func trashNoAccessLabel(lang: String) -> String {
        lang == "zh" ? "无法读取废纸篓" : "Trash access unavailable"
    }

    static func trashNoAccessDescription(lang: String) -> String {
        lang == "zh"
            ? "当前没有读取废纸篓的权限，请先授予相关访问权限。"
            : "Trash contents could not be read. Grant the required access permissions first."
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
        case ("trash", "zh"): return "正在检查废纸篓..."
        case ("trash", _): return "Checking trash..."
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

    static func trashLocations() -> [URL] {
        var results = [FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".Trash")]
        let uid = String(getuid())
        let volumes = URL(fileURLWithPath: "/Volumes")
        if let entries = try? FileManager.default.contentsOfDirectory(
            at: volumes,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) {
            for entry in entries {
                results.append(entry.appendingPathComponent(".Trashes/\(uid)"))
            }
        }
        return results
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
