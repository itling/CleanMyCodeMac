import Testing
@testable import CleanMyCodeMac

@Suite("Disk information")
struct DiskInfoTests {
    @Test("separates unallocated and reclaimable capacity")
    func separatesAvailableCapacity() {
        let snapshot = DiskCapacitySnapshot(
            total: 245_110_000_000,
            free: 35_390_000_000,
            available: 38_230_000_000
        )

        #expect(snapshot.used == 209_720_000_000)
        #expect(snapshot.available == 38_230_000_000)
        #expect(snapshot.reclaimable == 2_840_000_000)
        #expect(abs(snapshot.percentUsed - 85.56158459467179) < 0.0001)
    }

    @Test("never reports less available capacity than free capacity")
    func normalizesAvailableCapacity() {
        let snapshot = DiskCapacitySnapshot(
            total: 100,
            free: 30,
            available: 20
        )

        #expect(snapshot.available == 30)
        #expect(snapshot.reclaimable == 0)
    }

    @Test("serializes all capacity values for the web UI")
    func payloadIncludesCapacityBreakdown() {
        let payload = DiskCapacitySnapshot(total: 100, free: 25, available: 35).payload()

        #expect(payload["total"] as? Int64 == 100)
        #expect(payload["free"] as? Int64 == 25)
        #expect(payload["available"] as? Int64 == 35)
        #expect(payload["reclaimable"] as? Int64 == 10)
        #expect(payload["used"] as? Int64 == 75)
        #expect(payload["percent_used"] as? Double == 75)
    }
}
