import Foundation
import Testing
@testable import CleanMyCodeMac

@Suite("Git repository scanner")
struct GitRepositoryScannerTests {
    @Test("finds directory and worktree repositories sorted by allocated size")
    func findsRepositoriesSortedByAllocatedSize() throws {
        let temporaryDirectory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: temporaryDirectory) }
        let small = try makeRepository(
            at: temporaryDirectory.appendingPathComponent("small"),
            gitMarkerIsFile: false,
            bytes: 4_096
        )
        let large = try makeRepository(
            at: temporaryDirectory.appendingPathComponent("large"),
            gitMarkerIsFile: true,
            bytes: 16_384
        )

        let repositories = GitRepositoryScanner.scan(roots: [temporaryDirectory])

        #expect(repositories.map(\.url.lastPathComponent) == [large.lastPathComponent, small.lastPathComponent])
        #expect(repositories[0].sizeBytes > repositories[1].sizeBytes)
    }

    @Test("finds nested repositories but ignores repositories inside Git metadata")
    func findsNestedRepositoriesWithoutScanningGitMetadata() throws {
        let temporaryDirectory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: temporaryDirectory) }
        let parent = try makeRepository(
            at: temporaryDirectory.appendingPathComponent("parent"),
            gitMarkerIsFile: false,
            bytes: 4_096
        )
        _ = try makeRepository(at: parent.appendingPathComponent("packages/child"), gitMarkerIsFile: false, bytes: 8_192)
        _ = try makeRepository(at: parent.appendingPathComponent(".git/modules/internal"), gitMarkerIsFile: false, bytes: 32_768)

        let repositories = GitRepositoryScanner.scan(roots: [temporaryDirectory])

        #expect(Set(repositories.map(\.url.lastPathComponent)) == Set(["parent", "child"]))
    }

    @Test("finds bare repositories")
    func findsBareRepositories() throws {
        let temporaryDirectory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: temporaryDirectory) }
        let bareRepository = temporaryDirectory.appendingPathComponent("archive.git")
        try FileManager.default.createDirectory(
            at: bareRepository.appendingPathComponent("objects"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: bareRepository.appendingPathComponent("refs"),
            withIntermediateDirectories: true
        )
        try Data("ref: refs/heads/main\n".utf8).write(to: bareRepository.appendingPathComponent("HEAD"))

        let repositories = GitRepositoryScanner.scan(roots: [temporaryDirectory])

        #expect(repositories.map(\.url.lastPathComponent) == ["archive.git"])
    }

    @Test("project artifact scan excludes Git metadata already covered by repository usage")
    func projectArtifactsExcludeGitMetadata() throws {
        let temporaryDirectory = try makeTemporaryDirectory()
        defer { try? FileManager.default.removeItem(at: temporaryDirectory) }
        let project = temporaryDirectory.appendingPathComponent("project")
        try FileManager.default.createDirectory(
            at: project.appendingPathComponent(".git/modules/dependency"),
            withIntermediateDirectories: true
        )
        try FileManager.default.createDirectory(
            at: project.appendingPathComponent("node_modules"),
            withIntermediateDirectories: true
        )

        let artifacts = DevCacheScanner.discoverProjectArtifacts(in: temporaryDirectory, lang: "en")

        #expect(artifacts.map(\.url.lastPathComponent) == ["node_modules"])
    }

    private func makeTemporaryDirectory() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        return url
    }

    private func makeRepository(at url: URL, gitMarkerIsFile: Bool, bytes: Int) throws -> URL {
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        let marker = url.appendingPathComponent(".git")
        if gitMarkerIsFile {
            try Data("gitdir: ../metadata".utf8).write(to: marker)
        } else {
            try FileManager.default.createDirectory(at: marker, withIntermediateDirectories: true)
        }
        try Data(repeating: 1, count: bytes).write(to: url.appendingPathComponent("payload.bin"))
        return url
    }
}
