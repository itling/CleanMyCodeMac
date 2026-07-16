import Foundation
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

@MainActor
final class UpdateCoordinator: NSObject, SPUUpdaterDelegate {
    private var controller: SPUStandardUpdaterController?
    private var availability: UpdateAvailability
    private var availabilityCompletions: [([String: Any]) -> Void] = []
    private var receivedAvailabilityResult = false

    override init() {
        let info = Bundle.main.infoDictionary ?? [:]
        let hasFeed = !(info["SUFeedURL"] as? String ?? "").isEmpty
        let hasPublicKey = !(info["SUPublicEDKey"] as? String ?? "").isEmpty

        if Bundle.main.bundleURL.pathExtension.lowercased() != "app" {
            controller = nil
            availability = .unavailable(reason: "Application updates are only available in the installed app.")
        } else if !hasFeed || !hasPublicKey {
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
        }
    }

    func checkAvailability(completion: @escaping ([String: Any]) -> Void) {
        guard let updater = controller?.updater else {
            completion(availability.dictionary())
            return
        }

        availabilityCompletions.append(completion)
        guard !updater.sessionInProgress else { return }
        receivedAvailabilityResult = false
        updater.checkForUpdateInformation()
    }

    func presentAvailableUpdate() -> Bool {
        guard let controller, controller.updater.canCheckForUpdates else { return false }
        controller.checkForUpdates(nil)
        return true
    }

    func updater(_ updater: SPUUpdater, didFindValidUpdate item: SUAppcastItem) {
        receivedAvailabilityResult = true
        availability = .available(version: item.displayVersionString)
    }

    func updaterDidNotFindUpdate(_ updater: SPUUpdater, error: any Error) {
        receivedAvailabilityResult = true
        availability = .current
    }

    func updater(
        _ updater: SPUUpdater,
        didFinishUpdateCycleFor updateCheck: SPUUpdateCheck,
        error: (any Error)?
    ) {
        if !receivedAvailabilityResult, let error {
            availability = .unavailable(reason: error.localizedDescription)
        }

        let payload = availability.dictionary()
        let completions = availabilityCompletions
        availabilityCompletions.removeAll()
        completions.forEach { $0(payload) }
    }
}
