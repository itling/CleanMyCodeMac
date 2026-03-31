import Darwin
import Foundation

private struct NativeScanItem {
    let path: URL
    let sizeBytes: Int64
    let category: String
    let appName: String
    let isSafe: Bool
    var selected: Bool
    let lastModified: Date?
    let description: String

    var pathString: String { path.path }
    var sizeDisplay: String { NativeFormat.size(sizeBytes) }
    var pathShort: String { NativeFormat.shortPath(path) }
    var canAnalyze: Bool { category == "large_file" }
}

private struct NativeScanProgress {
    var status: String
    var percent: Int
    var label: String
    var labelKey: String
    var labelArgs: [String: Any]
    var logs: [[String: Any]]

    static var idle: NativeScanProgress {
        NativeScanProgress(
            status: "idle",
            percent: 0,
            label: "",
            labelKey: "",
            labelArgs: [:],
            logs: []
        )
    }

    func payload() -> [String: Any] {
        [
            "status": status,
            "percent": percent,
            "label": label,
            "label_key": labelKey,
            "label_args": labelArgs,
            "logs": logs,
        ]
    }
}

private enum DownloadsScanner {
    static func scan(lang: String) -> [NativeScanItem] {
        let downloadsURL = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Downloads")
        let cutoff = Date().addingTimeInterval(-30 * 24 * 60 * 60)
        let minimumSize: Int64 = 100 * 1024

        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: downloadsURL,
            includingPropertiesForKeys: [.isDirectoryKey, .fileSizeKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        return entries.compactMap { entry in
            let values = try? entry.resourceValues(forKeys: [.isDirectoryKey, .fileSizeKey, .contentModificationDateKey])
            guard values?.isDirectory != true else { return nil }

            let size = Int64(values?.fileSize ?? 0)
            guard size >= minimumSize else { return nil }

            let modified = values?.contentModificationDate ?? Date.distantPast
            let isOld = modified < cutoff
            let descriptionDate = NativeFormat.date(modified)
            let ext = entry.pathExtension.lowercased()

            return NativeScanItem(
                path: entry,
                sizeBytes: size,
                category: "download",
                appName: NativeText.downloadGroupName(for: ext, lang: lang),
                isSafe: isOld,
                selected: false,
                lastModified: modified,
                description: isOld
                    ? NativeText.oldDownloadDescription(date: descriptionDate, lang: lang)
                    : NativeText.downloadDescription(date: descriptionDate, lang: lang)
            )
        }
        .sorted { $0.sizeBytes > $1.sizeBytes }
    }
}

private enum LargeFilesScanner {
    private static let excludedPrefixes = [
        "/System",
        "/Library",
        "/private",
        "/usr",
        "/bin",
        "/sbin",
        "/Applications",
    ]
    private static let packageExtensions: Set<String> = ["app", "photoslibrary", "musiclibrary", "fcpbundle"]
    private static let thresholdBytes: Int64 = 500 * 1024 * 1024

    static func scan(lang: String) -> [NativeScanItem] {
        let home = FileManager.default.homeDirectoryForCurrentUser
        guard let enumerator = FileManager.default.enumerator(
            at: home,
            includingPropertiesForKeys: [.isRegularFileKey, .isDirectoryKey, .fileSizeKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles, .skipsPackageDescendants]
        ) else {
            return []
        }

        var items: [NativeScanItem] = []

        while let url = enumerator.nextObject() as? URL {
            let path = url.path
            if excludedPrefixes.contains(where: { path.hasPrefix($0) }) {
                enumerator.skipDescendants()
                continue
            }

            if packageExtensions.contains(url.pathExtension.lowercased()) {
                enumerator.skipDescendants()
                continue
            }

            let values = try? url.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey, .contentModificationDateKey])
            guard values?.isRegularFile == true else { continue }

            let size = Int64(values?.fileSize ?? 0)
            guard size >= thresholdBytes else { continue }

            items.append(
                NativeScanItem(
                    path: url,
                    sizeBytes: size,
                    category: "large_file",
                    appName: url.pathExtension.isEmpty ? "FILE" : url.pathExtension.uppercased(),
                    isSafe: false,
                    selected: false,
                    lastModified: values?.contentModificationDate,
                    description: NativeText.largeFileDescription(name: url.lastPathComponent, lang: lang)
                )
            )
        }

        return items.sorted { $0.sizeBytes > $1.sizeBytes }
    }
}

private enum RecursiveHomeScanner {
    private static let baseSkipDirs: Set<String> = [
        "Applications", "Library", ".Trash",
        "node_modules", ".git", "__pycache__",
        ".orbstack",
    ]
    private static let packageExtensions: Set<String> = ["app", "photoslibrary", "musiclibrary", "fcpbundle"]

    static func scan(
        validExtensions: Set<String>,
        minimumSize: Int64,
        extraSkipDirs: Set<String>,
        category: String,
        groupName: (String) -> String,
        description: (String, String) -> String
    ) -> [NativeScanItem] {
        var items: [NativeScanItem] = []
        scanDirectory(
            FileManager.default.homeDirectoryForCurrentUser,
            items: &items,
            validExtensions: validExtensions,
            minimumSize: minimumSize,
            skipDirs: baseSkipDirs.union(extraSkipDirs),
            category: category,
            groupName: groupName,
            description: description
        )
        return items.sorted { $0.sizeBytes > $1.sizeBytes }
    }

    private static func scanDirectory(
        _ directory: URL,
        items: inout [NativeScanItem],
        validExtensions: Set<String>,
        minimumSize: Int64,
        skipDirs: Set<String>,
        category: String,
        groupName: (String) -> String,
        description: (String, String) -> String
    ) {
        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.isDirectoryKey, .fileSizeKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return
        }

        for entry in entries {
            let name = entry.lastPathComponent
            if name.hasPrefix(".") || skipDirs.contains(name) {
                continue
            }

            let values = try? entry.resourceValues(forKeys: [.isDirectoryKey, .fileSizeKey, .contentModificationDateKey])
            if values?.isDirectory == true {
                if packageExtensions.contains(entry.pathExtension.lowercased()) {
                    continue
                }
                scanDirectory(
                    entry,
                    items: &items,
                    validExtensions: validExtensions,
                    minimumSize: minimumSize,
                    skipDirs: skipDirs,
                    category: category,
                    groupName: groupName,
                    description: description
                )
                continue
            }

            let ext = entry.pathExtension.lowercased()
            guard validExtensions.contains(ext) else { continue }

            let size = Int64(values?.fileSize ?? 0)
            guard size >= minimumSize else { continue }

            let modified = values?.contentModificationDate ?? Date.distantPast
            let dateText = NativeFormat.date(modified)
            items.append(
                NativeScanItem(
                    path: entry,
                    sizeBytes: size,
                    category: category,
                    appName: groupName(ext),
                    isSafe: false,
                    selected: false,
                    lastModified: modified,
                    description: description(name, dateText)
                )
            )
        }
    }
}

private enum DocumentsScanner {
    private static let validExtensions: Set<String> = [
        "pdf", "doc", "docx", "xls", "xlsx", "csv", "ppt", "pptx",
        "md", "txt", "rtf", "pages", "numbers", "keynote",
    ]

    static func scan(lang: String) -> [NativeScanItem] {
        RecursiveHomeScanner.scan(
            validExtensions: validExtensions,
            minimumSize: 100 * 1024,
            extraSkipDirs: ["Downloads"],
            category: "document",
            groupName: { NativeText.documentGroupName(for: $0, lang: lang) },
            description: { NativeText.documentDescription(name: $0, date: $1, lang: lang) }
        )
    }
}

private enum MediaScanner {
    private static let validExtensions: Set<String> = [
        "jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "heic", "heif", "svg",
        "raw", "dng", "cr2", "cr3", "nef", "nrw", "arw", "srf", "sr2", "raf", "rw2", "orf",
        "pef", "ptx", "3fr", "rwl", "insp", "gpr",
        "mp3", "wav", "aac", "flac", "ogg", "m4a", "wma", "ape", "aiff", "aif", "opus", "amr",
        "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "3gp", "3g2", "ts", "mts", "m2ts",
        "insv", "lrv", "r3d", "braw", "mxf", "vob", "mpg", "mpeg", "m2v",
    ]

    static func scan(lang: String) -> [NativeScanItem] {
        RecursiveHomeScanner.scan(
            validExtensions: validExtensions,
            minimumSize: 1024 * 1024,
            extraSkipDirs: [],
            category: "media",
            groupName: { NativeText.mediaGroupName(for: $0, lang: lang) },
            description: { NativeText.mediaDescription(name: $0, date: $1, lang: lang) }
        )
    }
}

private enum SystemCacheScanner {
    static func scan(lang: String) -> [NativeScanItem] {
        let cacheRoot = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Caches")
        var items: [NativeScanItem] = []

        for bundleID in NativeText.safeSystemCaches {
            let cacheURL = cacheRoot.appendingPathComponent(bundleID)
            guard FileManager.default.fileExists(atPath: cacheURL.path) else { continue }
            let size = NativeFileMetrics.directorySize(cacheURL)
            guard size >= 100 * 1024 else { continue }
            items.append(
                NativeScanItem(
                    path: cacheURL,
                    sizeBytes: size,
                    category: "system_cache",
                    appName: NativeText.bundleDisplayName(bundleID),
                    isSafe: true,
                    selected: true,
                    lastModified: NativeFileMetrics.modifiedDate(cacheURL),
                    description: NativeText.systemCacheDescription(bundleID: bundleID, lang: lang)
                )
            )
        }

        return items.sorted { $0.sizeBytes > $1.sizeBytes }
    }
}

private enum AppCacheScanner {
    static func scan(lang: String) -> [NativeScanItem] {
        let cacheRoot = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Caches")
        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: cacheRoot,
            includingPropertiesForKeys: [.isDirectoryKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        var items: [NativeScanItem] = []
        for entry in entries {
            let bundleID = entry.lastPathComponent
            let values = try? entry.resourceValues(forKeys: [.isDirectoryKey, .contentModificationDateKey])
            guard values?.isDirectory == true else { continue }
            if NativeText.protectedAppCachePrefixes.contains(where: { bundleID.hasPrefix($0) }) {
                continue
            }

            let size = NativeFileMetrics.directorySize(entry)
            guard size >= 10 * 1024 else { continue }

            let isApple = bundleID.hasPrefix("com.apple.")
            let isSafe = !isApple
            items.append(
                NativeScanItem(
                    path: entry,
                    sizeBytes: size,
                    category: "app_cache",
                    appName: NativeText.bundleDisplayName(bundleID),
                    isSafe: isSafe,
                    selected: isSafe,
                    lastModified: values?.contentModificationDate,
                    description: NativeText.appCacheDescription(bundleID: bundleID, lang: lang)
                )
            )
        }

        return items.sorted { $0.sizeBytes > $1.sizeBytes }
    }
}

private enum LogsScanner {
    private static let logExtensions: Set<String> = ["log", "ips", "diag", "crash", "spin", "hang"]

    static func scan(lang: String) -> [NativeScanItem] {
        let roots = [
            FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs"),
            FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/DiagnosticReports"),
        ]
        let cutoff = Date().addingTimeInterval(-7 * 24 * 60 * 60)
        var seen: Set<String> = []
        var items: [NativeScanItem] = []

        for root in roots {
            scanDirectory(root, cutoff: cutoff, seen: &seen, items: &items, lang: lang)
        }

        return items.sorted { $0.sizeBytes > $1.sizeBytes }
    }

    private static func scanDirectory(
        _ directory: URL,
        cutoff: Date,
        seen: inout Set<String>,
        items: inout [NativeScanItem],
        lang: String
    ) {
        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [.isDirectoryKey, .fileSizeKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return
        }

        for entry in entries {
            let path = entry.path
            if seen.contains(path) {
                continue
            }
            seen.insert(path)

            let values = try? entry.resourceValues(forKeys: [.isDirectoryKey, .fileSizeKey, .contentModificationDateKey])
            if values?.isDirectory == true {
                scanDirectory(entry, cutoff: cutoff, seen: &seen, items: &items, lang: lang)
                continue
            }

            guard logExtensions.contains(entry.pathExtension.lowercased()) else { continue }
            let modified = values?.contentModificationDate ?? Date.distantFuture
            guard modified < cutoff else { continue }

            let size = Int64(values?.fileSize ?? 0)
            guard size >= 1024 else { continue }

            let appName = entry.lastPathComponent.split(separator: "_").first.map(String.init)
                ?? entry.deletingPathExtension().lastPathComponent
            items.append(
                NativeScanItem(
                    path: entry,
                    sizeBytes: size,
                    category: "log",
                    appName: appName,
                    isSafe: true,
                    selected: true,
                    lastModified: modified,
                    description: NativeText.logDescription(date: NativeFormat.date(modified), lang: lang)
                )
            )
        }
    }
}

private enum DevCacheScanner {
    private static let languageCaches: [(String, [String])] = [
        ("Node.js", ["~/.npm/_cacache", "~/.yarn/cache", "~/.pnpm-store", "~/.bun/install/cache", "~/.nvm/.cache", "~/.volta/cache"]),
        ("Python", ["~/Library/Caches/pip", "~/.cache/pip", "~/.conda/pkgs", "~/.pyenv/cache", "~/Library/Caches/pypoetry"]),
        ("Ruby", ["~/.gem", "~/.bundle/cache", "~/Library/Caches/CocoaPods", "~/.rbenv/cache"]),
        ("PHP", ["~/.composer/cache"]),
        ("Perl", ["~/.cpan/sources", "~/.cpan/build"]),
        ("Lua", ["~/.luarocks"]),
        ("Rust", ["~/.cargo/registry/cache", "~/.cargo/registry/src", "~/.cargo/git/db"]),
        ("Go", ["~/go/pkg/mod/cache", "~/.cache/go-build"]),
        ("Java", ["~/.m2/repository", "~/.gradle/caches", "~/.gradle/wrapper/dists"]),
        ("Kotlin", ["~/.kotlin/caches", "~/.konan/cache", "~/.konan/dependencies"]),
        ("Scala", ["~/.sbt/boot", "~/.ivy2/cache", "~/.cache/coursier"]),
        ("C/C++", ["~/.cache/ccache", "~/.conan/data", "~/.cache/vcpkg"]),
        ("Swift", ["~/Library/Caches/org.swift.swiftpm", "~/Library/org.swift.swiftpm"]),
        (".NET", ["~/.nuget/packages", "~/.dotnet/tools/.store"]),
        ("Zig", ["~/.cache/zig"]),
        ("V", ["~/.vmodules"]),
        ("Haskell", ["~/.cabal/packages", "~/.cabal/store", "~/.stack"]),
        ("Elixir", ["~/.mix", "~/.hex"]),
        ("Clojure", ["~/.lein", "~/.clojure/.cpcache"]),
        ("OCaml", ["~/.opam"]),
        ("Erlang", ["~/.cache/rebar3"]),
        ("Dart/Flutter", ["~/.pub-cache", "~/.flutter", "~/Library/Caches/com.google.dart.tools"]),
        ("R", ["~/Library/R", "~/.R/cache"]),
        ("Julia", ["~/.julia/packages", "~/.julia/compiled", "~/.julia/artifacts"]),
        ("MATLAB", ["~/Library/Caches/MathWorks"]),
    ]

    private static let electronCacheDirs = [
        "Cache", "CachedData", "CachedExtensionVSIXs", "CachedExtensions",
        "CachedProfilesData", "CachedConfigurations", "Code Cache", "GPUCache",
        "DawnCache", "Service Worker", "User/workspaceStorage", "logs",
    ]

    private static let electronEditors: [(String, String)] = [
        ("VS Code", "Code"),
        ("VS Code Insiders", "Code - Insiders"),
        ("Sublime Text", "Sublime Text"),
        ("Cursor", "Cursor"),
        ("Windsurf", "Windsurf"),
        ("Trae", "Trae"),
        ("Trae CN", "Trae CN"),
        ("Antigravity", "Antigravity"),
        ("Zed", "Zed"),
        ("Aide", "Aide"),
        ("Void", "Void"),
        ("HBuilderX", "HBuilder X"),
        ("HBuilderX", "HBuilderX"),
        ("Atom", "Atom"),
        ("Brackets", "Brackets"),
        ("Postman", "Postman"),
        ("Insomnia", "Insomnia"),
    ]

    private static let toolCaches: [(String, [String])] = [
        ("Xcode", ["~/Library/Developer/Xcode/DerivedData", "~/Library/Developer/Xcode/Archives", "~/Library/Developer/Xcode/iOS DeviceSupport", "~/Library/Developer/CoreSimulator/Caches", "~/Library/Developer/CoreSimulator/Devices"]),
        ("Android Studio", ["~/Library/Caches/Google/AndroidStudio*", "~/.android/cache", "~/.android/avd"]),
        ("Homebrew", ["~/Library/Caches/Homebrew"]),
        ("Eclipse", ["~/Library/Caches/Eclipse", "~/.eclipse"]),
        ("Unity", ["~/Library/Unity/cache", "~/Library/Caches/com.unity3d.*"]),
        ("Unreal Engine", ["~/Library/Caches/com.epicgames.*"]),
    ]

    private static let aiModelCaches: [(String, [String])] = [
        ("Ollama", ["~/.ollama/models"]),
        ("Hugging Face", ["~/.cache/huggingface/hub"]),
        ("LM Studio", ["~/.lmstudio/models", "~/Library/Application Support/LM Studio/models"]),
        ("Jan", ["~/Library/Application Support/Jan/models"]),
        ("GPT4All", ["~/Library/Application Support/nomic.ai/GPT4All"]),
        ("Msty", ["~/Library/Application Support/Msty/models"]),
        ("AnythingLLM", ["~/Library/Application Support/anythingllm-desktop/models"]),
        ("PyTorch Hub", ["~/.cache/torch/hub"]),
    ]

    private static let jetBrainsProducts = [
        "IntelliJIdea", "PyCharm", "WebStorm", "GoLand",
        "CLion", "PhpStorm", "RubyMine", "Rider", "DataGrip",
        "RustRover", "Aqua", "Fleet", "DataSpell",
    ]

    static func scan(lang: String) -> [NativeScanItem] {
        var items: [NativeScanItem] = []
        var seenPaths: Set<String> = []

        func addUnique(_ item: NativeScanItem) {
            let path = item.pathString
            guard !seenPaths.contains(path) else { return }
            if seenPaths.contains(where: { path.hasPrefix($0 + "/") || $0.hasPrefix(path + "/") }) {
                return
            }
            seenPaths.insert(path)
            items.append(item)
        }

        for (langName, patterns) in languageCaches {
            for pattern in patterns {
                for url in NativePaths.expand(pattern) {
                    let size = NativeFileMetrics.itemSize(url)
                    guard size >= 100 * 1024 else { continue }
                    addUnique(
                        NativeScanItem(
                            path: url,
                            sizeBytes: size,
                            category: "dev_cache",
                            appName: langName,
                            isSafe: true,
                            selected: true,
                            lastModified: NativeFileMetrics.modifiedDate(url),
                            description: NativeText.devLangCacheDescription(
                                langName: langName,
                                pathName: url.lastPathComponent,
                                lang: lang
                            )
                        )
                    )
                }
            }
        }

        let appSupport = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support")
        for (toolName, dirName) in electronEditors {
            let base = appSupport.appendingPathComponent(dirName)
            guard FileManager.default.fileExists(atPath: base.path) else { continue }
            for subdir in electronCacheDirs {
                let cacheURL = base.appendingPathComponent(subdir)
                guard FileManager.default.fileExists(atPath: cacheURL.path) else { continue }
                let size = NativeFileMetrics.itemSize(cacheURL)
                guard size >= 100 * 1024 else { continue }
                addUnique(
                    NativeScanItem(
                        path: cacheURL,
                        sizeBytes: size,
                        category: "dev_cache",
                        appName: toolName,
                        isSafe: true,
                        selected: true,
                        lastModified: NativeFileMetrics.modifiedDate(cacheURL),
                        description: NativeText.devToolCacheDescription(
                            tool: toolName,
                            pathName: cacheURL.lastPathComponent,
                            lang: lang
                        )
                    )
                )
            }
        }

        for (toolName, patterns) in toolCaches {
            for pattern in patterns {
                for url in NativePaths.expand(pattern) {
                    let size = NativeFileMetrics.itemSize(url)
                    guard size >= 100 * 1024 else { continue }
                    addUnique(
                        NativeScanItem(
                            path: url,
                            sizeBytes: size,
                            category: "dev_cache",
                            appName: toolName,
                            isSafe: true,
                            selected: true,
                            lastModified: NativeFileMetrics.modifiedDate(url),
                            description: NativeText.devToolCacheDescription(
                                tool: toolName,
                                pathName: url.lastPathComponent,
                                lang: lang
                            )
                        )
                    )
                }
            }
        }

        let jetBrainsRoot = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Caches/JetBrains")
        if let entries = try? FileManager.default.contentsOfDirectory(
            at: jetBrainsRoot,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) {
            for entry in entries {
                guard NativeFileMetrics.isDirectory(entry) else { continue }
                let size = NativeFileMetrics.directorySize(entry)
                guard size >= 100 * 1024 else { continue }
                let product = jetBrainsProducts.first(where: { entry.lastPathComponent.hasPrefix($0) })
                    ?? entry.lastPathComponent
                let toolName = "JetBrains \(product)"
                addUnique(
                    NativeScanItem(
                        path: entry,
                        sizeBytes: size,
                        category: "dev_cache",
                        appName: toolName,
                        isSafe: true,
                        selected: true,
                        lastModified: NativeFileMetrics.modifiedDate(entry),
                        description: NativeText.devToolCacheDescription(
                            tool: toolName,
                            pathName: entry.lastPathComponent,
                            lang: lang
                        )
                    )
                )
            }
        }

        for (cacheURL, size, toolName) in discoverPathCaches() {
            addUnique(
                NativeScanItem(
                    path: cacheURL,
                    sizeBytes: size,
                    category: "dev_cache",
                    appName: toolName,
                    isSafe: true,
                    selected: true,
                    lastModified: NativeFileMetrics.modifiedDate(cacheURL),
                    description: NativeText.devToolCacheDescription(
                        tool: toolName,
                        pathName: cacheURL.lastPathComponent,
                        lang: lang
                    )
                )
            )
        }

        for (toolName, patterns) in aiModelCaches {
            for pattern in patterns {
                for url in NativePaths.expand(pattern) {
                    let size = NativeFileMetrics.itemSize(url)
                    guard size >= 10 * 1024 * 1024 else { continue }
                    addUnique(
                        NativeScanItem(
                            path: url,
                            sizeBytes: size,
                            category: "dev_cache",
                            appName: toolName,
                            isSafe: false,
                            selected: false,
                            lastModified: NativeFileMetrics.modifiedDate(url),
                            description: NativeText.aiModelDescription(
                                tool: toolName,
                                name: url.lastPathComponent,
                                lang: lang
                            )
                        )
                    )
                }
            }
        }

        return items.sorted { $0.sizeBytes > $1.sizeBytes }
    }

    private static func discoverPathCaches() -> [(URL, Int64, String)] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let candidates = ["cache", "Cache", "caches", "Caches", "pkg", "tmp", "temp"]
        let pathValue = ProcessInfo.processInfo.environment["PATH"] ?? ""
        var seenParents: Set<String> = []
        var results: [(URL, Int64, String)] = []

        for rawPath in pathValue.split(separator: ":").map(String.init) {
            guard rawPath.hasPrefix(home), !rawPath.isEmpty else { continue }
            let binURL = URL(fileURLWithPath: rawPath)
            guard FileManager.default.fileExists(atPath: binURL.path) else { continue }

            let parent = binURL.deletingLastPathComponent()
            guard seenParents.insert(parent.path).inserted else { continue }

            for name in candidates {
                let cacheURL = parent.appendingPathComponent(name)
                guard FileManager.default.fileExists(atPath: cacheURL.path) else { continue }
                let size = NativeFileMetrics.itemSize(cacheURL)
                guard size >= 1024 * 1024 else { continue }
                results.append((cacheURL, size, parent.lastPathComponent))
            }
        }

        return results
    }
}

private enum TrashScanner {
    static func scan(lang: String) -> [NativeScanItem] {
        var items: [NativeScanItem] = []
        var permissionDenied = false

        for trashURL in NativePaths.trashLocations() {
            guard FileManager.default.fileExists(atPath: trashURL.path) else { continue }
            do {
                let entries = try FileManager.default.contentsOfDirectory(
                    at: trashURL,
                    includingPropertiesForKeys: [.isDirectoryKey, .contentModificationDateKey],
                    options: [.skipsHiddenFiles]
                )
                if entries.isEmpty {
                    continue
                }

                let isMainTrash = trashURL.path.hasSuffix("/.Trash")
                let volumeName = isMainTrash ? nil : trashURL.deletingLastPathComponent().deletingLastPathComponent().lastPathComponent

                for entry in entries {
                    items.append(
                        NativeScanItem(
                            path: entry,
                            sizeBytes: NativeFileMetrics.itemSize(entry),
                            category: "trash",
                            appName: entry.lastPathComponent,
                            isSafe: true,
                            selected: true,
                            lastModified: NativeFileMetrics.modifiedDate(entry),
                            description: NativeText.trashLabel(volume: volumeName, lang: lang)
                        )
                    )
                }
            } catch {
                permissionDenied = true
            }
        }

        if items.isEmpty && permissionDenied {
            let placeholder = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".Trash")
            items.append(
                NativeScanItem(
                    path: placeholder,
                    sizeBytes: 0,
                    category: "trash",
                    appName: NativeText.trashNoAccessLabel(lang: lang),
                    isSafe: false,
                    selected: false,
                    lastModified: nil,
                    description: NativeText.trashNoAccessDescription(lang: lang)
                )
            )
        }

        return items.sorted { $0.sizeBytes > $1.sizeBytes }
    }
}

final class NativeScanEngine: @unchecked Sendable {
    private let lock = NSLock()
    private let queue = DispatchQueue(label: "CleanMyCodeMac.native.scan", qos: .userInitiated)

    private var items: [NativeScanItem] = []
    private var progress: NativeScanProgress = .idle
    private var hasRunScan = false

    func startScan(categories: [String], lang: String) {
        let requested = categories.isEmpty
            ? ["system_cache", "app_cache", "log", "download", "large_file", "trash", "dev_cache", "document", "media"]
            : categories
        lock.lock()
        items = []
        hasRunScan = true
        progress = NativeScanProgress(
            status: "scanning",
            percent: 0,
            label: NativeText.migrationNotice(lang: lang),
            labelKey: "",
            labelArgs: [:],
            logs: []
        )
        lock.unlock()

        queue.async { [weak self] in
            self?.runScan(categories: requested, lang: lang)
        }
    }

    func progressPayload() -> [String: Any] {
        lock.lock()
        defer { lock.unlock() }
        return progress.payload()
    }

    func resultPayload(lang: String) -> [String: Any]? {
        lock.lock()
        let currentItems = items
        let didRun = hasRunScan
        lock.unlock()

        guard didRun else { return nil }
        return serialize(items: currentItems, lang: lang)
    }

    func selectPath(_ path: String, selected: Bool) -> [String: Any] {
        mutateSelection { item in
            if item.pathString == path {
                item.selected = selected
            }
        }
    }

    func selectCategory(_ category: String, appName: String?, selected: Bool) -> [String: Any] {
        lock.lock()
        let targetPaths = Set(items.compactMap { item -> String? in
            guard item.category == category else { return nil }
            if let appName, item.appName != appName {
                return nil
            }
            return item.pathString
        })
        for index in items.indices where targetPaths.contains(items[index].pathString) {
            items[index].selected = selected
        }
        let selectedBytes = dedupedSize(items: items, selectedOnly: true)
        lock.unlock()
        return [
            "selected_size": NativeFormat.size(selectedBytes),
        ]
    }

    func selectAll(_ selected: Bool) -> [String: Any] {
        mutateSelection { item in
            item.selected = selected
        }
    }

    func cleanPaths(_ paths: [String]) -> [String: Any] {
        let pathSet = Set(paths)
        guard !pathSet.isEmpty else {
            return [
                "freed": NativeFormat.size(0),
                "freed_bytes": 0,
                "errors": 1,
            ]
        }

        var freed: Int64 = 0
        var errors = 0

        lock.lock()
        let grouped = Dictionary(grouping: items.filter { pathSet.contains($0.pathString) }, by: { $0.pathString })
        lock.unlock()

        for (_, candidates) in grouped {
            guard let item = representativeItem(from: candidates) else { continue }
            do {
                if item.category == "trash" || item.isSafe {
                    try FileManager.default.removeItem(at: item.path)
                } else {
                    _ = try FileManager.default.trashItem(at: item.path, resultingItemURL: nil)
                }
                freed += item.sizeBytes
            } catch {
                do {
                    _ = try FileManager.default.trashItem(at: item.path, resultingItemURL: nil)
                    freed += item.sizeBytes
                } catch {
                    errors += 1
                }
            }
        }

        lock.lock()
        items.removeAll { pathSet.contains($0.pathString) }
        lock.unlock()

        return [
            "freed": NativeFormat.size(freed),
            "freed_bytes": freed,
            "errors": errors,
        ]
    }

    func analysisPayload(for target: String, lang: String) -> [String: Any] {
        let url = URL(fileURLWithPath: target)
        let attrs = try? FileManager.default.attributesOfItem(atPath: url.path)
        let size = (attrs?[.size] as? NSNumber)?.int64Value ?? 0

        let siblingRows: [[String: Any]]
        if let siblings = try? FileManager.default.contentsOfDirectory(
            at: url.deletingLastPathComponent(),
            includingPropertiesForKeys: [.fileSizeKey, .isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) {
            siblingRows = siblings.compactMap { sibling -> [String: Any]? in
                guard sibling.path != url.path else { return nil }
                let values = try? sibling.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey])
                let siblingSize = Int64(values?.fileSize ?? 0)
                guard siblingSize > 0 else { return nil }
                return [
                    "name": sibling.lastPathComponent,
                    "path": sibling.path,
                    "size": siblingSize,
                    "size_display": NativeFormat.size(siblingSize),
                ]
            }
            .sorted { lhs, rhs in
                (lhs["size"] as? Int64 ?? 0) > (rhs["size"] as? Int64 ?? 0)
            }
            .prefix(8)
            .map { row in
                var copy = row
                copy.removeValue(forKey: "size")
                return copy
            }
        } else {
            siblingRows = []
        }

        return [
            "name": url.lastPathComponent,
            "size_display": NativeFormat.size(size),
            "highlights": NativeText.analysisHighlights(url: url, size: NativeFormat.size(size), lang: lang),
            "same_level_items": siblingRows,
        ]
    }

    private func runScan(categories: [String], lang: String) {
        let supported = Set([
            "system_cache", "app_cache", "log", "download", "large_file",
            "trash", "dev_cache", "document", "media",
        ])
        let total = max(categories.count, 1)
        var completed = 0
        var scannedItems: [NativeScanItem] = []

        for category in categories {
            if supported.contains(category) {
                updateProgress(
                    percent: Int(Double(completed) / Double(total) * 100),
                    label: NativeText.scanLabel(for: category, lang: lang),
                    logKey: progressKey(for: category)
                )

                let result: [NativeScanItem]
                switch category {
                case "system_cache":
                    result = SystemCacheScanner.scan(lang: lang)
                case "app_cache":
                    result = AppCacheScanner.scan(lang: lang)
                case "log":
                    result = LogsScanner.scan(lang: lang)
                case "download":
                    result = DownloadsScanner.scan(lang: lang)
                case "large_file":
                    result = LargeFilesScanner.scan(lang: lang)
                case "trash":
                    result = TrashScanner.scan(lang: lang)
                case "dev_cache":
                    result = DevCacheScanner.scan(lang: lang)
                case "document":
                    result = DocumentsScanner.scan(lang: lang)
                case "media":
                    result = MediaScanner.scan(lang: lang)
                default:
                    result = []
                }
                scannedItems.append(contentsOf: result)
            }

            completed += 1
            updateProgress(
                percent: Int(Double(completed) / Double(total) * 100),
                label: supported.contains(category)
                    ? NativeText.scanDone(name: NativeText.categoryName(category, lang: lang), lang: lang)
                    : NativeText.migrationNotice(lang: lang),
                logKey: nil
            )
        }

        lock.lock()
        items = scannedItems
        progress = NativeScanProgress(
            status: "done",
            percent: 100,
            label: NativeText.scanComplete(lang: lang),
            labelKey: "",
            labelArgs: [:],
            logs: []
        )
        lock.unlock()
    }

    private func progressKey(for category: String) -> String {
        switch category {
        case "system_cache": return "scan.system_cache"
        case "app_cache": return "scan.app_cache"
        case "log": return "scan.log"
        case "download": return "scan.download"
        case "large_file": return "scan.large_file"
        case "trash": return "scan.trash"
        case "dev_cache": return "scan.dev_cache"
        case "document": return "scan.document"
        case "media": return "scan.media"
        default: return ""
        }
    }

    private func updateProgress(percent: Int, label: String, logKey: String?) {
        lock.lock()
        progress.percent = percent
        progress.label = label
        progress.labelKey = ""
        progress.labelArgs = [:]
        if let logKey, !logKey.isEmpty {
            progress.logs = [[
                "key": logKey,
                "args": [:],
            ]]
        }
        lock.unlock()
    }

    private func mutateSelection(mutation: (inout NativeScanItem) -> Void) -> [String: Any] {
        lock.lock()
        for index in items.indices {
            mutation(&items[index])
        }
        let selectedBytes = dedupedSize(items: items, selectedOnly: true)
        lock.unlock()
        return [
            "selected_size": NativeFormat.size(selectedBytes),
        ]
    }

    private func dedupedSize(items: [NativeScanItem], selectedOnly: Bool) -> Int64 {
        let filtered = selectedOnly ? items.filter(\.selected) : items
        let sortedItems = filtered.sorted {
            $0.pathString.components(separatedBy: "/").count < $1.pathString.components(separatedBy: "/").count
        }
        var counted: [String] = []
        var total: Int64 = 0

        for item in sortedItems {
            let path = item.pathString
            if counted.contains(path) { continue }
            if counted.contains(where: { path.hasPrefix($0 + "/") }) { continue }
            counted.append(path)
            total += item.sizeBytes
        }

        return total
    }

    private func representativeItem(from items: [NativeScanItem]) -> NativeScanItem? {
        items.first(where: { $0.category == "trash" }) ?? items.first(where: { !$0.isSafe }) ?? items.first
    }

    private func serialize(items: [NativeScanItem], lang: String) -> [String: Any] {
        var categories: [String: Any] = [:]
        let groupedByCategory = Dictionary(grouping: items, by: \.category)

        for (category, categoryItems) in groupedByCategory {
            let groupedByApp = Dictionary(grouping: categoryItems, by: \.appName)
            let subGroups: [[String: Any]] = groupedByApp
                .map { appName, appItems in
                    let groupSize = appItems.reduce(Int64(0)) { $0 + $1.sizeBytes }
                    let selectedSize = appItems.filter(\.selected).reduce(Int64(0)) { $0 + $1.sizeBytes }
                    let anySelected = appItems.contains(where: \.selected)
                    let allSelected = !appItems.isEmpty && appItems.allSatisfy(\.selected)
                    let allSafe = appItems.allSatisfy(\.isSafe)
                    let description = groupDescription(items: appItems, lang: lang)
                    let files: [[String: Any]] = appItems.map { item in
                        [
                            "path": item.pathString,
                            "path_short": item.pathShort,
                            "size": item.sizeBytes,
                            "size_display": item.sizeDisplay,
                            "selected": item.selected,
                            "is_safe": item.isSafe,
                            "can_analyze": item.canAnalyze,
                            "description": item.description,
                        ]
                    }

                    return [
                        "app_name": appName,
                        "description": description,
                        "size": groupSize,
                        "size_display": NativeFormat.size(groupSize),
                        "selected_size": selectedSize,
                        "selected_display": NativeFormat.size(selectedSize),
                        "is_safe": allSafe,
                        "any_selected": anySelected,
                        "all_selected": allSelected,
                        "file_count": files.count,
                        "primary_path": files.first?["path"] as? String ?? "",
                        "can_analyze": files.count == 1 && (files.first?["can_analyze"] as? Bool == true),
                        "files": files,
                    ]
                }
                .sorted { ($0["size"] as? Int64 ?? 0) > ($1["size"] as? Int64 ?? 0) }

            let categorySize = categoryItems.reduce(Int64(0)) { $0 + $1.sizeBytes }
            let categorySelected = categoryItems.filter(\.selected).reduce(Int64(0)) { $0 + $1.sizeBytes }
            categories[category] = [
                "name": NativeText.categoryName(category, lang: lang),
                "size": categorySize,
                "size_display": NativeFormat.size(categorySize),
                "selected_size": categorySelected,
                "selected_display": NativeFormat.size(categorySelected),
                "any_selected": categoryItems.contains(where: \.selected),
                "all_selected": !categoryItems.isEmpty && categoryItems.allSatisfy(\.selected),
                "sub_groups": subGroups,
            ]
        }

        let total = dedupedSize(items: items, selectedOnly: false)
        let selected = dedupedSize(items: items, selectedOnly: true)

        return [
            "categories": categories,
            "total_items": items.count,
            "total_size": NativeFormat.size(total),
            "total_bytes": total,
            "selected_size": NativeFormat.size(selected),
            "selected_bytes": selected,
        ]
    }

    private func groupDescription(items: [NativeScanItem], lang: String) -> String {
        guard items.count > 1 else {
            return items.first?.description ?? ""
        }

        let dates = items.compactMap(\.lastModified).map(NativeFormat.date).sorted()
        return NativeText.groupSummary(
            count: items.count,
            start: dates.first,
            end: dates.last,
            lang: lang
        )
    }
}
