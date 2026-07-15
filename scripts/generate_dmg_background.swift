import AppKit
import Foundation

guard CommandLine.arguments.count == 2 else {
    fputs("Usage: generate_dmg_background.swift <output.png>\n", stderr)
    exit(2)
}

let outputURL = URL(fileURLWithPath: CommandLine.arguments[1])
let canvasSize = NSSize(width: 660, height: 420)
let image = NSImage(size: canvasSize)

func color(_ red: CGFloat, _ green: CGFloat, _ blue: CGFloat, alpha: CGFloat = 1) -> NSColor {
    NSColor(srgbRed: red / 255, green: green / 255, blue: blue / 255, alpha: alpha)
}

func drawCenteredText(_ text: String, y: CGFloat, font: NSFont, textColor: NSColor) {
    let style = NSMutableParagraphStyle()
    style.alignment = .center
    let attributes: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: textColor,
        .paragraphStyle: style,
    ]
    (text as NSString).draw(
        in: NSRect(x: 30, y: y, width: canvasSize.width - 60, height: 36),
        withAttributes: attributes
    )
}

image.lockFocus()

color(248, 250, 252).setFill()
NSRect(origin: .zero, size: canvasSize).fill()

let cardColor = NSColor.white
for x in [70.0, 410.0] {
    let shadow = NSShadow()
    shadow.shadowColor = color(15, 23, 42, alpha: 0.08)
    shadow.shadowBlurRadius = 14
    shadow.shadowOffset = NSSize(width: 0, height: -3)
    NSGraphicsContext.saveGraphicsState()
    shadow.set()
    cardColor.setFill()
    NSBezierPath(roundedRect: NSRect(x: x, y: 92, width: 180, height: 205), xRadius: 20, yRadius: 20).fill()
    NSGraphicsContext.restoreGraphicsState()
}

drawCenteredText(
    "拖动到 Applications 完成安装",
    y: 350,
    font: .systemFont(ofSize: 24, weight: .semibold),
    textColor: color(15, 23, 42)
)
drawCenteredText(
    "Drag CleanMyCodeMac to the Applications folder",
    y: 318,
    font: .systemFont(ofSize: 13, weight: .regular),
    textColor: color(100, 116, 139)
)

let accent = color(249, 115, 22)
color(255, 237, 213).setFill()
NSBezierPath(ovalIn: NSRect(x: 292, y: 167, width: 76, height: 76)).fill()

let symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 44, weight: .medium)
    .applying(NSImage.SymbolConfiguration(paletteColors: [accent]))
if let arrow = NSImage(systemSymbolName: "arrow.right", accessibilityDescription: nil)?
    .withSymbolConfiguration(symbolConfiguration) {
    arrow.draw(in: NSRect(x: 304, y: 179, width: 52, height: 52))
}

drawCenteredText(
    "安装完成后，可从 Applications 或 Launchpad 启动",
    y: 30,
    font: .systemFont(ofSize: 12, weight: .regular),
    textColor: color(100, 116, 139)
)

image.unlockFocus()

guard let tiffData = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiffData),
      let pngData = bitmap.representation(using: .png, properties: [:])
else {
    fputs("Unable to render DMG background.\n", stderr)
    exit(1)
}

do {
    try FileManager.default.createDirectory(
        at: outputURL.deletingLastPathComponent(),
        withIntermediateDirectories: true
    )
    try pngData.write(to: outputURL, options: .atomic)
} catch {
    fputs("Unable to write DMG background: \(error.localizedDescription)\n", stderr)
    exit(1)
}
