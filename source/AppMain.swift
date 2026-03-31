import AppKit
import Foundation
import WebKit

private final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow?
    private var bridge: NativeBridge?

    func applicationDidFinishLaunching(_ notification: Notification) {
        do {
            let htmlURL = try HTMLLoader.resourceURL()
            let configuration = WKWebViewConfiguration()
            let controller = WKUserContentController()
            controller.addUserScript(
                WKUserScript(
                    source: BridgeBootstrap.script,
                    injectionTime: .atDocumentStart,
                    forMainFrameOnly: true
                )
            )
            controller.addUserScript(
                WKUserScript(
                    source: BridgeBootstrap.postLoadScript,
                    injectionTime: .atDocumentEnd,
                    forMainFrameOnly: true
                )
            )
            configuration.userContentController = controller

            let webView = WKWebView(frame: .zero, configuration: configuration)
            let bridge = NativeBridge(webView: webView)
            controller.add(bridge, name: BridgeKeys.messageHandler)
            self.bridge = bridge

            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 1120, height: 720),
                styleMask: [.titled, .closable, .miniaturizable, .resizable],
                backing: .buffered,
                defer: false
            )
            window.minSize = NSSize(width: 800, height: 500)
            window.title = "CleanMyCodeMac"
            window.center()
            window.contentView = webView
            window.makeKeyAndOrderFront(nil)

            self.window = window

            webView.loadFileURL(htmlURL, allowingReadAccessTo: htmlURL.deletingLastPathComponent())
            NSApp.activate(ignoringOtherApps: true)
        } catch {
            let alert = NSAlert()
            alert.messageText = "Failed to start Swift shell"
            alert.informativeText = error.localizedDescription
            alert.runModal()
            NSApp.terminate(nil)
        }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }
}

@main
struct CleanMyCodeMacMain {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
    }
}
