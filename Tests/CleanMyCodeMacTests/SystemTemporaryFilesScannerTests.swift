import Foundation
import Testing
@testable import CleanMyCodeMac

@Suite("System temporary files scanner")
struct SystemTemporaryFilesScannerTests {
    @Test("shows recent and old regular items but excludes special entries")
    func showsAllOrdinaryTemporaryItems() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let now = Date(timeIntervalSince1970: 2_000_000_000)
        let recent = try makeFile(named: "recent.tmp", root: root, ageDays: 2, now: now)
        let cautious = try makeFile(named: "cautious.tmp", root: root, ageDays: 10, now: now)
        let recommended = try makeFile(named: "recommended.tmp", root: root, ageDays: 40, now: now)
        let active = try makeFile(named: "active.tmp", root: root, ageDays: 40, now: now)
        let lock = try makeFile(named: ".worker.lock", root: root, ageDays: 40, now: now)
        let alias = root.appendingPathComponent("alias.tmp")
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: recommended)

        let items = SystemTemporaryFilesScanner.scan(
            root: root,
            now: now,
            lang: "zh"
        )

        #expect(Set(items.map { $0.path.lastPathComponent }) == Set([
            recent.lastPathComponent, cautious.lastPathComponent,
            recommended.lastPathComponent, active.lastPathComponent, lock.lastPathComponent,
        ]))
        #expect(items.first(where: { $0.path.lastPathComponent == recent.lastPathComponent })?.isSafe == false)
        #expect(items.first(where: { $0.path.lastPathComponent == cautious.lastPathComponent })?.isSafe == false)
        #expect(items.first(where: { $0.path.lastPathComponent == recommended.lastPathComponent })?.isSafe == true)
        #expect(items.first(where: { $0.path.lastPathComponent == recent.lastPathComponent })?.selected == false)
        #expect(items.first(where: { $0.path.lastPathComponent == cautious.lastPathComponent })?.selected == true)
        #expect(items.first(where: { $0.path.lastPathComponent == recommended.lastPathComponent })?.selected == true)
        #expect(items.first(where: { $0.path.lastPathComponent == active.lastPathComponent })?.selected == true)
        #expect(!items.contains(where: { $0.pathString == alias.path }))
    }

    @Test("only immediate children of the configured root are eligible")
    func confinesCleanupToRootChildren() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let child = root.appendingPathComponent("old.tmp")
        let nested = root.appendingPathComponent("nested/old.tmp")
        try FileManager.default.createDirectory(at: nested.deletingLastPathComponent(), withIntermediateDirectories: true)
        try Data(repeating: 1, count: 2048).write(to: child)
        try Data(repeating: 1, count: 2048).write(to: nested)
        defer { try? FileManager.default.removeItem(at: root) }

        let now = Date(timeIntervalSince1970: 2_000_000_000)
        try setModifiedDate(now.addingTimeInterval(-40 * 86_400), for: child)
        try setModifiedDate(now.addingTimeInterval(-40 * 86_400), for: nested)

        #expect(SystemTemporaryFilesScanner.isEligible(child, root: root))
        #expect(!SystemTemporaryFilesScanner.isEligible(nested, root: root))
    }

    @Test("keeps the original private tmp path in presentation")
    func preservesOriginalPath() {
        let url = URL(fileURLWithPath: "/private/tmp/example.tmp")
        #expect(NativeFormat.shortPath(url) == "/private/tmp/example.tmp")
    }

    private func makeFile(named name: String, root: URL, ageDays: Int, now: Date) throws -> URL {
        let url = root.appendingPathComponent(name)
        try Data(repeating: 1, count: 2048).write(to: url)
        try setModifiedDate(now.addingTimeInterval(-Double(ageDays) * 86_400), for: url)
        return url
    }

    private func setModifiedDate(_ date: Date, for url: URL) throws {
        try FileManager.default.setAttributes([.modificationDate: date], ofItemAtPath: url.path)
    }
}
