import Foundation
import Testing
@testable import CleanMyCodeMac

@Suite("Scan result localization")
struct ResultLocalizationTests {
    @Test("developer cache results use the current display language")
    func localizesDeveloperCacheAfterLanguageSwitch() {
        let repository = NativeScanItem(
            path: URL(fileURLWithPath: "/Users/test/project"),
            sizeBytes: 1024,
            category: "dev_cache",
            appName: "Git 仓库",
            isSafe: false,
            selected: false,
            lastModified: nil,
            description: "Git 仓库占用：/Users/test/project，仅供分析，不会默认清理。",
            presentation: .gitRepository
        )
        let docker = NativeScanItem(
            path: URL(fileURLWithPath: "/Users/test/Library/Containers/com.docker.docker"),
            sizeBytes: 1024,
            category: "dev_cache",
            appName: "Docker",
            isSafe: false,
            selected: false,
            lastModified: nil,
            description: "Docker Desktop 数据目录。",
            presentation: .dockerData
        )
        let goCache = NativeScanItem(
            path: URL(fileURLWithPath: "/Users/test/go/pkg/mod"),
            sizeBytes: 1024,
            category: "dev_cache",
            appName: "Go",
            isSafe: true,
            selected: true,
            lastModified: nil,
            description: "Go 缓存：mod",
            presentation: .developerCache(tool: "Go")
        )
        let recentTemporaryFile = NativeScanItem(
            path: URL(fileURLWithPath: "/private/tmp/recent.tmp"),
            sizeBytes: 512,
            category: "system_temp",
            appName: "近期临时文件",
            isSafe: false,
            selected: false,
            lastModified: nil,
            description: "系统临时项目",
            presentation: .systemTemporary(ageDays: 1)
        )

        #expect(NativeScanEngine.localizedAppName(for: repository, lang: "en") == "Git Repositories")
        #expect(NativeScanEngine.localizedAppName(for: recentTemporaryFile, lang: "en") == "Recent temporary files")
        #expect(NativeScanEngine.localizedDescription(for: repository, lang: "en").hasPrefix("Git repository usage:"))
        #expect(NativeScanEngine.localizedDescription(for: docker, lang: "en").hasPrefix("Docker Desktop data directory."))
        #expect(NativeScanEngine.localizedDescription(for: goCache, lang: "en") == "Go cache: mod")
    }
}
