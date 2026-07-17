import Foundation
import OSLog
import Sparkle

enum UpdateAvailability: Equatable {
    case current
    case available(version: String)
    case unavailable(reason: String)

    func dictionary() -> [String: Any] {
        switch self {
        case .current:
            return [
                "has_update": false,
                "latest_version": "",
                "updater_available": true,
                "error": "",
            ]
        case .available(let version):
            return [
                "has_update": true,
                "latest_version": version,
                "updater_available": true,
                "error": "",
            ]
        case .unavailable(let reason):
            return [
                "has_update": false,
                "latest_version": "",
                "updater_available": false,
                "error": reason,
            ]
        }
    }
}

enum UpdateCheckRequestAction: Equatable {
    case returnCached
    case waitForActiveProbe
    case startProbe
}

enum UpdateCheckPolicy {
    static let refreshInterval: TimeInterval = 6 * 60 * 60
}

struct UpdateCheckState {
    private var probeStarted = false
    private var lastCompletedAt: Date?

    mutating func beginInitialProbe() -> Bool {
        guard !probeStarted, lastCompletedAt == nil else { return false }
        probeStarted = true
        return true
    }

    mutating func requestAction(
        sessionInProgress: Bool,
        now: Date,
        minimumInterval: TimeInterval
    ) -> UpdateCheckRequestAction {
        if probeStarted || sessionInProgress {
            return .waitForActiveProbe
        }
        if let lastCompletedAt,
           now.timeIntervalSince(lastCompletedAt) < minimumInterval
        {
            return .returnCached
        }

        probeStarted = true
        return .startProbe
    }

    mutating func completeProbe(at date: Date) {
        probeStarted = false
        lastCompletedAt = date
    }
}

@MainActor
final class UpdateCoordinator: NSObject, SPUUpdaterDelegate {
    private let logger = Logger(subsystem: "com.itling.cleanmycodemac", category: "updates")
    private var controller: SPUStandardUpdaterController?
    private var availability: UpdateAvailability
    private var availabilityCompletions: [([String: Any]) -> Void] = []
    private var receivedAvailabilityResult = false
    private var checkState = UpdateCheckState()

    override init() {
        let configLogger = Logger(subsystem: "com.itling.cleanmycodemac", category: "updates")
        let info = Bundle.main.infoDictionary ?? [:]
        let hasFeed = !(info["SUFeedURL"] as? String ?? "").isEmpty
        let hasPublicKey = !(info["SUPublicEDKey"] as? String ?? "").isEmpty
        configLogger.notice(
            "Configuring updater; feed=\(hasFeed), publicKey=\(hasPublicKey)"
        )

        if Bundle.main.bundleURL.pathExtension.lowercased() != "app" {
            configLogger.error("Updater unavailable because the process is not running from an app bundle")
            controller = nil
            availability = .unavailable(reason: "Application updates are only available in the installed app.")
        } else if !hasFeed || !hasPublicKey {
            configLogger.error("Updater unavailable because the feed or public key is missing")
            controller = nil
            availability = .unavailable(reason: "The update feed is not configured.")
        } else {
            controller = nil
            availability = .current
        }

        super.init()

        if case .current = availability {
            controller = SPUStandardUpdaterController(
                startingUpdater: true,
                updaterDelegate: self,
                userDriverDelegate: nil
            )

            // Sparkle explicitly supports starting a probe before the next runloop
            // cycle. Doing it here avoids colliding with Sparkle's launch-time
            // permission/scheduling cycle after the web UI has loaded.
            // Source: https://sparkle-project.org/documentation/api-reference/Classes/SPUUpdater.html#//api/name/startUpdater:
            if checkState.beginInitialProbe() {
                logger.notice("Starting launch-time update probe")
                controller?.updater.checkForUpdateInformation()
            }
        }
    }

    func checkAvailability(completion: @escaping ([String: Any]) -> Void) {
        guard let updater = controller?.updater else {
            completion(availability.dictionary())
            return
        }

        switch checkState.requestAction(
            sessionInProgress: updater.sessionInProgress,
            now: Date(),
            minimumInterval: UpdateCheckPolicy.refreshInterval
        ) {
        case .returnCached:
            logger.notice("Returning cached update availability to web UI")
            completion(availability.dictionary())
        case .waitForActiveProbe:
            logger.notice("Web UI is waiting for active update probe")
            availabilityCompletions.append(completion)
        case .startProbe:
            logger.notice("Starting update probe requested by web UI")
            availabilityCompletions.append(completion)
            receivedAvailabilityResult = false
            updater.checkForUpdateInformation()
        }
    }

    func presentAvailableUpdate() -> Bool {
        guard let controller, controller.updater.canCheckForUpdates else { return false }
        controller.checkForUpdates(nil)
        return true
    }

    func updater(_ updater: SPUUpdater, didFindValidUpdate item: SUAppcastItem) {
        logger.notice("Sparkle found update version \(item.displayVersionString, privacy: .public)")
        receivedAvailabilityResult = true
        availability = .available(version: item.displayVersionString)
    }

    func updaterDidNotFindUpdate(_ updater: SPUUpdater, error: any Error) {
        logger.notice("Sparkle found no update: \(error.localizedDescription)")
        receivedAvailabilityResult = true
        availability = .current
    }

    func updater(
        _ updater: SPUUpdater,
        didFinishUpdateCycleFor updateCheck: SPUUpdateCheck,
        error: (any Error)?
    ) {
        logger.notice("Sparkle finished update probe; pending web callbacks: \(self.availabilityCompletions.count)")
        if !receivedAvailabilityResult, let error {
            availability = .unavailable(reason: error.localizedDescription)
        }

        checkState.completeProbe(at: Date())
        let payload = availability.dictionary()
        let completions = availabilityCompletions
        availabilityCompletions.removeAll()
        completions.forEach { $0(payload) }
    }
}
