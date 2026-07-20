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
        #expect(cachePatterns["Claude Code"]?.contains("~/.claude/cache") == true)
        #expect(cachePatterns["CodeBuddy"]?.contains("~/.codebuddy/plugins/cache") == true)
        #expect(cachePatterns["Qoder"]?.contains("~/.qoder/cache") == true)
    }

    @Test("does not classify conversations, projects, configuration, or memory as cache")
    func protectsPersistentToolData() {
        let protectedComponents = [
            "/sessions", "/projects", "/config", "/settings", "/rules", "/skills",
            "/memory", "/workspaceStorage", "/Session Storage", "/Local Storage",
            "/IndexedDB", "/Backups", "/file-history",
        ]
        let patterns = DevCacheScanner.aiDeveloperToolCaches.flatMap(\.patterns)

        for pattern in patterns {
            #expect(
                !protectedComponents.contains(where: pattern.contains),
                "Persistent AI tool data must not be cleaned: \(pattern)"
            )
        }
    }
}
