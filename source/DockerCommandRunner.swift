import Foundation

struct DockerCommandSpecification: Equatable {
    let actionID: String
    let arguments: [String]
    let displayCommand: String
    let requiresConfirmation: Bool
}

enum DockerCommandRunner {
    static func specification(for actionID: String) -> DockerCommandSpecification? {
        switch actionID {
        case "system_df":
            return DockerCommandSpecification(
                actionID: actionID,
                arguments: ["system", "df"],
                displayCommand: "docker system df",
                requiresConfirmation: false
            )
        case "system_prune":
            return DockerCommandSpecification(
                actionID: actionID,
                arguments: ["system", "prune", "-a", "-f"],
                displayCommand: "docker system prune -af",
                requiresConfirmation: true
            )
        case "volume_prune":
            return DockerCommandSpecification(
                actionID: actionID,
                arguments: ["volume", "prune", "-f"],
                displayCommand: "docker volume prune",
                requiresConfirmation: true
            )
        default:
            return nil
        }
    }

    static func run(actionID: String) -> [String: Any] {
        guard let specification = specification(for: actionID) else {
            return [
                "success": false,
                "error": "Unsupported Docker action.",
            ]
        }
        guard let executableURL = dockerExecutableURL() else {
            return [
                "success": false,
                "command": specification.displayCommand,
                "error": "Docker CLI was not found.",
            ]
        }

        let process = Process()
        process.executableURL = executableURL
        process.arguments = specification.arguments
        let outputPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = outputPipe

        do {
            try process.run()
            let data = outputPipe.fileHandleForReading.readDataToEndOfFile()
            process.waitUntilExit()
            let output = (String(data: data, encoding: .utf8) ?? "")
                .trimmingCharacters(in: .whitespacesAndNewlines)
            return [
                "success": process.terminationStatus == 0,
                "command": specification.displayCommand,
                "output": output,
                "exit_code": Int(process.terminationStatus),
            ]
        } catch {
            return [
                "success": false,
                "command": specification.displayCommand,
                "error": error.localizedDescription,
            ]
        }
    }

    private static func dockerExecutableURL() -> URL? {
        [
            "/opt/homebrew/bin/docker",
            "/usr/local/bin/docker",
            "/Applications/Docker.app/Contents/Resources/bin/docker",
        ]
        .first(where: FileManager.default.isExecutableFile(atPath:))
        .map { URL(fileURLWithPath: $0) }
    }
}
