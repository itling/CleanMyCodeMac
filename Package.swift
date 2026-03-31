// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "CleanMyCodeMac",
    platforms: [
        .macOS(.v13),
    ],
    products: [
        .executable(
            name: "CleanMyCodeMac",
            targets: ["CleanMyCodeMac"]
        ),
    ],
    targets: [
        .executableTarget(
            name: "CleanMyCodeMac",
            path: "source"
        ),
    ]
)
