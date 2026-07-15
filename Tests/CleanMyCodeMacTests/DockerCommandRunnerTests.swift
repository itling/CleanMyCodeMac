import Testing
@testable import CleanMyCodeMac

@Suite("Docker command runner")
struct DockerCommandRunnerTests {
    @Test("allows only predefined Docker actions")
    func allowsOnlyPredefinedActions() {
        #expect(DockerCommandRunner.specification(for: "system_df")?.arguments == ["system", "df"])
        #expect(DockerCommandRunner.specification(for: "system_prune")?.arguments == ["system", "prune", "-a", "-f"])
        #expect(DockerCommandRunner.specification(for: "volume_prune")?.arguments == ["volume", "prune", "-f"])
        #expect(DockerCommandRunner.specification(for: "docker system df; rm -rf /") == nil)
    }

    @Test("marks destructive Docker actions for confirmation")
    func marksDestructiveActions() {
        #expect(DockerCommandRunner.specification(for: "system_df")?.requiresConfirmation == false)
        #expect(DockerCommandRunner.specification(for: "system_prune")?.requiresConfirmation == true)
        #expect(DockerCommandRunner.specification(for: "volume_prune")?.requiresConfirmation == true)
    }
}
