import Foundation
import Testing
@testable import CleanMyCodeMac

@Suite("Analysis tree deletion")
struct AnalysisDeletionTests {
    @Test("deletes a file exposed by the latest tree analysis")
    func deletesExposedFile() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let file = root.appendingPathComponent("cache.bin")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data("cache".utf8).write(to: file)
        defer { try? FileManager.default.removeItem(at: root) }

        let engine = NativeScanEngine()
        _ = engine.analysisPayload(for: root.path, lang: "en")

        let result = engine.deleteAnalyzedPath(file.path)

        #expect(result["success"] as? Bool == true)
        #expect(!FileManager.default.fileExists(atPath: file.path))
    }

    @Test("deletes a directory exposed by the latest tree analysis")
    func deletesExposedDirectory() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let directory = root.appendingPathComponent("node_modules", isDirectory: true)
        let nestedFile = directory.appendingPathComponent("package.bin")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try Data("package".utf8).write(to: nestedFile)
        defer { try? FileManager.default.removeItem(at: root) }

        let engine = NativeScanEngine()
        _ = engine.analysisPayload(for: root.path, lang: "en")

        let result = engine.deleteAnalyzedPath(directory.path)

        #expect(result["success"] as? Bool == true)
        #expect(!FileManager.default.fileExists(atPath: directory.path))
    }

    @Test("deletes a same-level item exposed by the latest analysis")
    func deletesExposedSameLevelItem() throws {
        let container = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let analyzedRoot = container.appendingPathComponent("analyzed", isDirectory: true)
        let analyzedFile = analyzedRoot.appendingPathComponent("cache.bin")
        let siblingFile = container.appendingPathComponent("old-build.zip")
        try FileManager.default.createDirectory(at: analyzedRoot, withIntermediateDirectories: true)
        try Data("cache".utf8).write(to: analyzedFile)
        try Data("archive".utf8).write(to: siblingFile)
        defer { try? FileManager.default.removeItem(at: container) }

        let engine = NativeScanEngine()
        _ = engine.analysisPayload(for: analyzedRoot.path, lang: "en")

        let result = engine.deleteAnalyzedPath(siblingFile.path)

        #expect(result["success"] as? Bool == true)
        #expect(!FileManager.default.fileExists(atPath: siblingFile.path))
    }

    @Test("rejects a path that was not exposed by the latest tree analysis")
    func rejectsUnexposedPath() throws {
        let container = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let unrelatedContainer = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString, isDirectory: true)
        let analyzedRoot = container.appendingPathComponent("analyzed", isDirectory: true)
        let analyzedFile = analyzedRoot.appendingPathComponent("cache.bin")
        let outsideFile = unrelatedContainer.appendingPathComponent("keep.txt")
        try FileManager.default.createDirectory(at: analyzedRoot, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: unrelatedContainer, withIntermediateDirectories: true)
        try Data("cache".utf8).write(to: analyzedFile)
        try Data("keep".utf8).write(to: outsideFile)
        defer { try? FileManager.default.removeItem(at: container) }
        defer { try? FileManager.default.removeItem(at: unrelatedContainer) }

        let engine = NativeScanEngine()
        _ = engine.analysisPayload(for: analyzedRoot.path, lang: "en")

        let result = engine.deleteAnalyzedPath(outsideFile.path)

        #expect(result["success"] as? Bool == false)
        #expect(FileManager.default.fileExists(atPath: outsideFile.path))
    }

    @Test("protects system roots and the user home directory")
    func protectsCriticalDirectories() {
        #expect(NativeScanEngine.isProtectedAnalysisDeletionPath("/"))
        #expect(NativeScanEngine.isProtectedAnalysisDeletionPath(FileManager.default.homeDirectoryForCurrentUser.path))
        #expect(NativeScanEngine.isProtectedAnalysisDeletionPath(
            FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library").path
        ))
        #expect(!NativeScanEngine.isProtectedAnalysisDeletionPath(FileManager.default.temporaryDirectory.path))
    }
}
