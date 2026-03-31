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
                    source: AppBootstrapMetadata.script(),
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

    @objc
    private func showAboutPanel(_ sender: Any?) {
        NSApp.orderFrontStandardAboutPanel([
            "ApplicationName": "CleanMyCodeMac",
            "ApplicationVersion": AppMetadata.currentVersion(),
            "Version": AppMetadata.currentVersion(),
            "Copyright": "© killy"
        ])
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc
    private func showPreferencesPlaceholder(_ sender: Any?) {
        let alert = NSAlert()
        alert.messageText = "CleanMyCodeMac"
        alert.informativeText = "Settings are currently managed in the main window."
        alert.runModal()
    }

    func buildMainMenu() -> NSMenu {
        let mainMenu = NSMenu()

        let appMenuItem = NSMenuItem()
        mainMenu.addItem(appMenuItem)

        let appMenu = NSMenu()
        let appName = Bundle.main.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String ?? "CleanMyCodeMac"

        let aboutItem = NSMenuItem(
            title: "About \(appName)",
            action: #selector(showAboutPanel(_:)),
            keyEquivalent: ""
        )
        aboutItem.target = self
        appMenu.addItem(aboutItem)
        appMenu.addItem(NSMenuItem.separator())

        let settingsItem = NSMenuItem(
            title: "Settings…",
            action: #selector(showPreferencesPlaceholder(_:)),
            keyEquivalent: ","
        )
        settingsItem.target = self
        appMenu.addItem(settingsItem)
        appMenu.addItem(NSMenuItem.separator())

        appMenu.addItem(withTitle: "Hide \(appName)", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let hideOthers = NSMenuItem(
            title: "Hide Others",
            action: #selector(NSApplication.hideOtherApplications(_:)),
            keyEquivalent: "h"
        )
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(hideOthers)
        appMenu.addItem(withTitle: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")

        appMenuItem.submenu = appMenu

        let windowMenuItem = NSMenuItem()
        mainMenu.addItem(windowMenuItem)

        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        windowMenu.addItem(NSMenuItem.separator())
        windowMenu.addItem(withTitle: "Bring All to Front", action: #selector(NSApplication.arrangeInFront(_:)), keyEquivalent: "")
        windowMenuItem.submenu = windowMenu
        NSApp.windowsMenu = windowMenu

        return mainMenu
    }
}

@main
struct CleanMyCodeMacMain {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.mainMenu = delegate.buildMainMenu()
        app.run()
    }
}
