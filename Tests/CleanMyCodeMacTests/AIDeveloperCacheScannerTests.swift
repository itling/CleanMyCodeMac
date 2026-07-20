import Foundation
import Testing
@testable import CleanMyCodeMac

@Suite("AI developer tool cache scanner")
struct AIDeveloperCacheScannerTests {
    @Test("covers requested AI developer tools")
    func coversRequestedTools() {
        let cachePatterns = Dictionary(
            uniqueKeysWithValues: DevCacheScanner.aiDeveloperToolCaches.map {
                ($0.toolName, $0.patterns)
            }
        )

        let tokscaleTools: Set<String> = [
            "OpenCode", "Claude Code", "OpenClaw", "Codex", "GitHub Copilot CLI",
            "Hermes Agent", "Gemini CLI", "Cursor", "Amp", "Codebuff", "Factory Droid",
            "Pi", "Kimi CLI", "Qwen CLI", "Roo Code", "Kilo", "Kilo CLI", "Mux",
            "Crush", "Goose", "Antigravity", "Antigravity CLI", "Zed", "Kiro", "Trae",
            "Warp/Oz", "Cline", "Gajae-Code", "Grok Build", "Jcode", "MiMo Code",
            "Command Code", "Junie", "ZCode", "OpenCodeReview", "CodeBuddy", "WorkBuddy",
            "Devin CLI", "Devin Desktop", "Synthetic / Octofriend",
        ]

        #expect(Set(cachePatterns.keys).isSuperset(of: tokscaleTools))
        for tool in tokscaleTools.union(["Qoder", "Trae CN", "Windsurf"]) {
            #expect(cachePatterns[tool]?.isEmpty == false, "Missing cache paths for \(tool)")
        }

        #expect(cachePatterns["Codex"]?.contains("~/.codex/cache") == true)
        #expect(cachePatterns["Codex"]?.contains("~/.codex/Cache") == false)
        #expect(cachePatterns["Codex"]?.contains("~/.codex/.tmp") == false)
        #expect(cachePatterns["Claude Code"]?.contains("~/.claude/cache") == true)
        #expect(cachePatterns["Claude Code"]?.contains("~/Library/Caches/claude-cli-nodejs") == false)
        #expect(cachePatterns["CodeBuddy"]?.contains("~/.codebuddy/plugins/cache") == false)
        #expect(
            cachePatterns["CodeBuddy"]?.contains(
                "~/Library/Application Support/CodeBuddyExtension/Cache"
            ) == false
        )
        #expect(
            cachePatterns["Qoder"]?.contains(
                "~/Library/Application Support/Qoder/Cache"
            ) == true
        )
    }

    @Test("does not classify conversations, agent state, logs, configuration, or memory as cache")
    func protectsPersistentToolData() {
        let protectedComponents = [
            "/sessions", "/projects", "/config", "/settings", "/rules", "/skills",
            "/memory", "/workspaceStorage", "/Session Storage", "/Local Storage",
            "/IndexedDB", "/Backups", "/file-history", "/log", "/logs", "/telemetry",
            "/Crashpad", "/CrashReport", "/sentry", "/tmp", "/temp", "/.tmp",
        ]
        let patterns = DevCacheScanner.aiDeveloperToolCaches.flatMap(\.patterns)

        for pattern in patterns {
            #expect(
                !protectedComponents.contains(where: pattern.contains),
                "Persistent AI tool data must not be cleaned: \(pattern)"
            )
        }
    }

    @Test("all AI targets use an explicit safe cache class or a cautious policy")
    func usesExplicitCacheAllowlist() {
        let vettedHomeCaches = ["~/.claude/cache", "~/.codex/cache"]
        let cautiousTargets = ["~/.cache/codex-runtimes"]

        for spec in DevCacheScanner.aiDeveloperToolCaches {
            for target in spec.targets {
                let isElectronCache = target.pattern.contains("~/Library/Application Support/")
                    && DevCacheScanner.aiElectronCacheDirs.contains {
                        target.pattern.hasSuffix("/\($0)")
                    }
                let isMacOSCache = target.pattern.hasPrefix("~/Library/Caches/")
                let isVettedHomeCache = vettedHomeCaches.contains(target.pattern)

                if target.risk == .safe {
                    #expect(
                        isElectronCache || isMacOSCache || isVettedHomeCache,
                        "Unreviewed cache must not be selected by default: \(target.pattern)"
                    )
                } else {
                    #expect(
                        cautiousTargets.contains(target.pattern),
                        "Unexpected cautious target needs an explicit review: \(target.pattern)"
                    )
                }
            }
        }
    }

    @Test("tool data homes never become cache roots implicitly")
    func protectsEveryToolDataHome() {
        let vettedHomeCaches = Set(["~/.claude/cache", "~/.codex/cache"])

        for spec in DevCacheScanner.aiDeveloperToolCaches {
            for root in spec.protectedRoots {
                for pattern in spec.patterns where pattern.hasPrefix(root + "/") {
                    #expect(
                        vettedHomeCaches.contains(pattern),
                        "AI tool data root requires an exact reviewed exception: \(pattern)"
                    )
                }
            }
        }
    }

    @Test("known mixed-content caches are excluded")
    func excludesMixedContentCaches() {
        let patterns = Set(DevCacheScanner.aiDeveloperToolCaches.flatMap(\.patterns))
        let excluded = [
            "~/.cache/opencode",
            "~/.cache/devin",
            "~/.cache/claude",
            "~/Library/Caches/claude-cli-nodejs",
            "~/Library/Caches/com.tencent.codebuddy.ShipIt",
            "~/Library/Caches/com.tencent.codebuddycn.ShipIt",
            "~/Library/Caches/com.workbuddy.workbuddy.BundleMigration",
            "~/Library/Application Support/CodeBuddyExtension/Cache",
        ]

        for pattern in excluded {
            #expect(!patterns.contains(pattern), "Mixed-content cache must be excluded: \(pattern)")
        }
    }

    @Test("filesystem aliases share a scan identity")
    func deduplicatesFilesystemAliases() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let cache = root.appendingPathComponent("cache", isDirectory: true)
        let alias = root.appendingPathComponent("cache-alias", isDirectory: true)
        try FileManager.default.createDirectory(at: cache, withIntermediateDirectories: true)
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: cache)
        defer { try? FileManager.default.removeItem(at: root) }

        #expect(
            DevCacheScanner.fileIdentity(for: cache)
                == DevCacheScanner.fileIdentity(for: alias)
        )
    }

    @Test("Codex runtime dependencies are cautious and opt-in")
    func protectsCodexRuntimeDependencies() {
        let target = DevCacheScanner.aiDeveloperToolCaches
            .first(where: { $0.toolName == "Codex" })?
            .targets.first(where: { $0.pattern == "~/.cache/codex-runtimes" })

        #expect(target?.risk == .cautious)
    }

    @Test("generic editor cleanup excludes extension state and logs")
    func protectsEditorExtensionState() {
        let protectedDirectories = ["Service Worker", "User/workspaceStorage", "logs"]

        #expect(
            Set(DevCacheScanner.editorCacheDirs).isDisjoint(with: protectedDirectories),
            "Editor state may contain AI conversations and must not be cleaned"
        )
    }
}
