import Foundation
import Testing
@testable import CleanMyCodeMac

@Suite("Log scanner safety")
struct LogsScannerTests {
    @Test("recognizes AI coding tool logs without matching generic application logs")
    func recognizesAICodingToolLogs() {
        let aiLogs = [
            "/Users/test/Library/Logs/codex-desktop-session.log",
            "/Users/test/Library/Logs/Claude/main.log",
            "/Users/test/Library/Logs/TRAe/renderer.log",
            "/Users/test/Library/Logs/com.tencent.CodeBuddy/app.log",
            "/Users/test/Library/Logs/GitHub Copilot/session.log",
            "/Users/test/Library/Logs/copilot.log",
            "/Users/test/Library/Logs/Qoder/main.log",
            "/Users/test/Library/Logs/trae-cn/main.log",
        ]
        let ordinaryLogs = [
            "/Users/test/Library/Logs/JetBrains/idea.log",
            "/Users/test/Library/Logs/scratch-claw-desktop.log",
            "/Users/test/Library/Logs/main.log",
            "/Users/test/Library/Logs/example-pipeline.log",
        ]

        for path in aiLogs {
            #expect(LogsScanner.isAIDeveloperToolLog(URL(fileURLWithPath: path)), "Should protect \(path)")
        }
        for path in ordinaryLogs {
            #expect(!LogsScanner.isAIDeveloperToolLog(URL(fileURLWithPath: path)), "Should not protect \(path)")
        }
    }

    @Test("AI coding tool logs are cautious and unselected while ordinary old logs remain selected")
    func appliesCautiousDefaults() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let codexLog = root.appendingPathComponent("codex-desktop-session.log")
        let ordinaryLog = root.appendingPathComponent("idea.log")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data(repeating: 1, count: 2048).write(to: codexLog)
        try Data(repeating: 1, count: 2048).write(to: ordinaryLog)
        let now = Date()
        let oldDate = now.addingTimeInterval(-10 * 86_400)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: codexLog.path)
        try FileManager.default.setAttributes([.modificationDate: oldDate], ofItemAtPath: ordinaryLog.path)
        defer { try? FileManager.default.removeItem(at: root) }

        let items = LogsScanner.scan(roots: [root], now: now, lang: "zh")
        let codexItem = items.first { $0.path.lastPathComponent == codexLog.lastPathComponent }
        let ordinaryItem = items.first { $0.path.lastPathComponent == ordinaryLog.lastPathComponent }

        #expect(codexItem?.isSafe == false)
        #expect(codexItem?.selected == false)
        #expect(codexItem?.description.contains("AI 编程工具") == true)
        #expect(ordinaryItem?.isSafe == true)
        #expect(ordinaryItem?.selected == true)
    }
}
