// swift-tools-version: 6.1
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
