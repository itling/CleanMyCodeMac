import Testing
@testable import CleanMyCodeMac

@Suite("Native bridge scheduling")
struct NativeBridgeSchedulingTests {
    @Test("runs file-system intensive bridge methods in the background")
    func runsFileSystemWorkInBackground() {
        #expect(NativeBridge.requiresBackgroundExecution(method: "analyze_target"))
        #expect(NativeBridge.requiresBackgroundExecution(method: "delete_analyzed_path"))
        #expect(NativeBridge.requiresBackgroundExecution(method: "clean_paths"))
        #expect(NativeBridge.requiresBackgroundExecution(method: "run_docker_command"))
        #expect(!NativeBridge.requiresBackgroundExecution(method: "get_disk"))
    }

    @Test("routes Sparkle bridge methods through the main actor")
    func runsSparkleWorkOnMainActor() {
        #expect(NativeBridge.requiresMainActorExecution(method: "check_for_updates"))
        #expect(NativeBridge.requiresMainActorExecution(method: "install_update"))
        #expect(!NativeBridge.requiresMainActorExecution(method: "get_disk"))
    }
}
