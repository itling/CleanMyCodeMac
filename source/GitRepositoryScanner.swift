import Foundation

struct GitRepositoryUsage: Equatable {
    let url: URL
    let sizeBytes: Int64
}

enum GitRepositoryScanner {
    private static let excludedSystemPaths: Set<String> = [
        "/System",
        "/Library",
        "/private",
        "/dev",
        "/bin",
        "/sbin",
        "/cores",
        "/Network",
        "/net",
        "/home",
    ]

    private static let excludedDirectoryNames: Set<String> = [
        ".Spotlight-V100",
        ".DocumentRevisions-V100",
        ".fseventsd",
        ".Trashes",
    ]

    static func scan(roots: [URL] = [URL(fileURLWithPath: "/", isDirectory: true)]) -> [GitRepositoryUsage] {
        var repositories: [GitRepositoryUsage] = []
        var visitedRoots: Set<String> = []

        for root in roots {
            let standardizedRoot = root.standardizedFileURL
            guard visitedRoots.insert(standardizedRoot.path).inserted else { continue }
            _ = scanDirectory(standardizedRoot, repositories: &repositories)
        }

        return repositories.sorted {
            if $0.sizeBytes == $1.sizeBytes {
                return $0.url.path.localizedStandardCompare($1.url.path) == .orderedAscending
            }
            return $0.sizeBytes > $1.sizeBytes
        }
    }

    @discardableResult
    private static func scanDirectory(_ directory: URL, repositories: inout [GitRepositoryUsage]) -> Int64 {
        guard !shouldExclude(directory) else { return 0 }
        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: directory,
            includingPropertiesForKeys: [
                .isDirectoryKey,
                .isRegularFileKey,
                .isSymbolicLinkKey,
                .totalFileAllocatedSizeKey,
                .fileAllocatedSizeKey,
                .fileSizeKey,
            ],
            options: []
        ) else {
            return 0
        }

        let isRepository = hasGitMarker(in: directory) || isBareRepository(directory)
        var total: Int64 = 0

        for entry in entries {
            let values = try? entry.resourceValues(forKeys: [
                .isDirectoryKey,
                .isRegularFileKey,
                .isSymbolicLinkKey,
                .totalFileAllocatedSizeKey,
                .fileAllocatedSizeKey,
                .fileSizeKey,
            ])
            if values?.isSymbolicLink == true { continue }

            if values?.isDirectory == true {
                if entry.lastPathComponent == ".git" {
                    total += allocatedSize(of: entry)
                } else {
                    total += scanDirectory(entry, repositories: &repositories)
                }
            } else if values?.isRegularFile == true {
                total += Int64(values?.totalFileAllocatedSize ?? values?.fileAllocatedSize ?? values?.fileSize ?? 0)
            }
        }

        if isRepository {
            repositories.append(GitRepositoryUsage(url: directory, sizeBytes: total))
        }
        return total
    }

    private static func hasGitMarker(in directory: URL) -> Bool {
        FileManager.default.fileExists(atPath: directory.appendingPathComponent(".git").path)
    }

    private static func isBareRepository(_ directory: URL) -> Bool {
        guard directory.pathExtension.lowercased() == "git" else { return false }
        return FileManager.default.fileExists(atPath: directory.appendingPathComponent("HEAD").path)
            && FileManager.default.fileExists(atPath: directory.appendingPathComponent("objects").path)
            && FileManager.default.fileExists(atPath: directory.appendingPathComponent("refs").path)
    }

    private static func shouldExclude(_ directory: URL) -> Bool {
        if excludedSystemPaths.contains(directory.path) { return true }
        if directory.deletingLastPathComponent().path == "/Volumes" {
            let values = try? directory.resourceValues(forKeys: [.volumeIsLocalKey])
            if values?.volumeIsLocal != true { return true }
        }
        return excludedDirectoryNames.contains(directory.lastPathComponent)
    }

    private static func allocatedSize(of directory: URL) -> Int64 {
        guard let enumerator = FileManager.default.enumerator(
            at: directory,
            includingPropertiesForKeys: [
                .isRegularFileKey,
                .isSymbolicLinkKey,
                .totalFileAllocatedSizeKey,
                .fileAllocatedSizeKey,
                .fileSizeKey,
            ],
            options: []
        ) else {
            return 0
        }

        var total: Int64 = 0
        while let entry = enumerator.nextObject() as? URL {
            let values = try? entry.resourceValues(forKeys: [
                .isRegularFileKey,
                .isSymbolicLinkKey,
                .totalFileAllocatedSizeKey,
                .fileAllocatedSizeKey,
                .fileSizeKey,
            ])
            if values?.isSymbolicLink == true {
                enumerator.skipDescendants()
                continue
            }
            guard values?.isRegularFile == true else { continue }
            total += Int64(values?.totalFileAllocatedSize ?? values?.fileAllocatedSize ?? values?.fileSize ?? 0)
        }
        return total
    }
}
