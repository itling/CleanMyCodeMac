import Foundation
import Testing
@testable import CleanMyCodeMac

@Suite("Application update availability")
struct UpdateAvailabilityTests {
    @Test("starts the launch probe before the updater enters its startup cycle")
    func startsInitialProbeOnce() {
        var state = UpdateCheckState()
        let now = Date(timeIntervalSince1970: 1_000)

        let firstStart = state.beginInitialProbe()
        let secondStart = state.beginInitialProbe()
        let requestAction = state.requestAction(
            sessionInProgress: true,
            now: now,
            minimumInterval: UpdateCheckPolicy.refreshInterval
        )

        #expect(firstStart)
        #expect(!secondStart)
        #expect(requestAction == .waitForActiveProbe)
    }

    @Test("returns the cached launch result to the web UI")
    func returnsCachedProbeResult() {
        var state = UpdateCheckState()
        let completedAt = Date(timeIntervalSince1970: 1_000)

        let didStart = state.beginInitialProbe()
        state.completeProbe(at: completedAt)
        let requestAction = state.requestAction(
            sessionInProgress: false,
            now: completedAt.addingTimeInterval(UpdateCheckPolicy.refreshInterval - 1),
            minimumInterval: UpdateCheckPolicy.refreshInterval
        )

        #expect(didStart)
        #expect(requestAction == .returnCached)
    }

    @Test("starts another probe when the refresh interval elapses")
    func refreshesAfterInterval() {
        var state = UpdateCheckState()
        let completedAt = Date(timeIntervalSince1970: 1_000)

        let didStart = state.beginInitialProbe()
        state.completeProbe(at: completedAt)
        let requestAction = state.requestAction(
            sessionInProgress: false,
            now: completedAt.addingTimeInterval(UpdateCheckPolicy.refreshInterval),
            minimumInterval: UpdateCheckPolicy.refreshInterval
        )

        #expect(didStart)
        #expect(requestAction == .startProbe)
    }

    @Test("available update exposes its display version")
    func availableUpdatePayload() {
        let availability = UpdateAvailability.available(version: "1.0.4")

        #expect(availability.dictionary()["has_update"] as? Bool == true)
        #expect(availability.dictionary()["latest_version"] as? String == "1.0.4")
        #expect(availability.dictionary()["updater_available"] as? Bool == true)
    }

    @Test("up-to-date state hides the update action")
    func currentVersionPayload() {
        let availability = UpdateAvailability.current

        #expect(availability.dictionary()["has_update"] as? Bool == false)
        #expect(availability.dictionary()["latest_version"] as? String == "")
        #expect(availability.dictionary()["updater_available"] as? Bool == true)
    }

    @Test("unconfigured builds report updater unavailable")
    func unavailablePayload() {
        let availability = UpdateAvailability.unavailable(reason: "Missing update feed.")

        #expect(availability.dictionary()["has_update"] as? Bool == false)
        #expect(availability.dictionary()["updater_available"] as? Bool == false)
        #expect(availability.dictionary()["error"] as? String == "Missing update feed.")
    }
}
