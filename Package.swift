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
    dependencies: [
        .package(url: "https://github.com/sparkle-project/Sparkle", from: "2.9.4"),
    ],
    targets: [
        .executableTarget(
            name: "CleanMyCodeMac",
            dependencies: [
                .product(name: "Sparkle", package: "Sparkle"),
            ],
            path: "source",
            linkerSettings: [
                .unsafeFlags([
                    "-Xlinker", "-rpath",
                    "-Xlinker", "@loader_path/../Frameworks",
                ]),
            ]
        ),
        .testTarget(
            name: "CleanMyCodeMacTests",
            dependencies: ["CleanMyCodeMac"],
            path: "Tests/CleanMyCodeMacTests"
        ),
    ]
)
