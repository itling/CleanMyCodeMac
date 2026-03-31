import AppKit
import Foundation
import WebKit

final class NativeBridge: NSObject, WKScriptMessageHandler {
    private weak var webView: WKWebView?
    private let scanEngine = NativeScanEngine()

    init(webView: WKWebView) {
        self.webView = webView
    }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.name == BridgeKeys.messageHandler,
              let body = message.body as? [String: Any],
              let id = body["id"] as? Int,
              let method = body["method"] as? String
        else {
            return
        }

        let args = body["args"] as? [Any] ?? []

        if handleAsync(method: method, args: args, id: id) {
            return
        }

        do {
            let result = try handle(method: method, args: args)
            resolve(id: id, payload: result)
        } catch {
            reject(id: id, message: error.localizedDescription)
        }
    }

    private func handleAsync(method: String, args: [Any], id: Int) -> Bool {
        switch method {
        case "check_for_updates":
            UpdateService.checkForUpdates { [weak self] result in
                let resolvedPayload: [String: Any]?
                let message: String?
                switch result {
                case .success(let updatePayload):
                    resolvedPayload = updatePayload.dictionary()
                    message = nil
                case .failure(let error):
                    resolvedPayload = nil
                    message = error.localizedDescription
                }

                DispatchQueue.main.async {
                    if let resolvedPayload {
                        self?.resolve(id: id, payload: resolvedPayload)
                    } else {
                        self?.reject(id: id, message: message ?? "Unknown update error.")
                    }
                }
            }
            return true
        default:
            return false
        }
    }

    private func handle(method: String, args: [Any]) throws -> Any {
        let lang = LanguageStore.current()

        switch method {
        case "on_bootstrap_ready":
            return ["ok": true]
        case "get_disk":
            return DiskInfoService.payload()
        case "get_permissions":
            return PermissionService.payload()
        case "get_language":
            return LanguageStore.payload()
        case "get_app_meta":
            return AppMetadata.payload()
        case "open_external_url":
            guard let rawURL = args.first as? String,
                  let url = URL(string: rawURL),
                  !rawURL.isEmpty
            else {
                return ["ok": false, "error": "Missing URL."]
            }
            NSWorkspace.shared.open(url)
            return ["ok": true]
        case "set_language":
            if let lang = args.first as? String {
                LanguageStore.set(lang)
            }
            return LanguageStore.payload()
        case "open_permission_settings":
            if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles") {
                NSWorkspace.shared.open(url)
            }
            return ["ok": true]
        case "reveal_path":
            guard let path = args.first as? String, !path.isEmpty else {
                return ["ok": false, "error": "Missing path."]
            }
            NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
            return ["ok": true]
        case "start_scan":
            let categories = args.first as? [String] ?? []
            scanEngine.startScan(categories: categories, lang: lang)
            return ["ok": true, "categories": categories]
        case "get_scan_progress":
            return scanEngine.progressPayload()
        case "get_scan_result":
            return scanEngine.resultPayload(lang: lang) ?? NSNull()
        case "select_path":
            guard let path = args.first as? String,
                  let selected = args.dropFirst().first as? Bool
            else {
                return ["selected_size": NativeFormat.size(0)]
            }
            return scanEngine.selectPath(path, selected: selected)
        case "select_category":
            guard let category = args.first as? String else {
                return ["selected_size": NativeFormat.size(0)]
            }
            let appName = args.count > 1 ? args[1] as? String : nil
            let selected = args.count > 2 ? (args[2] as? Bool ?? true) : true
            return scanEngine.selectCategory(category, appName: appName, selected: selected)
        case "select_all":
            let selected = args.first as? Bool ?? true
            return scanEngine.selectAll(selected)
        case "clean_paths":
            let paths = args.first as? [String] ?? []
            return scanEngine.cleanPaths(paths)
        case "analyze_target":
            guard let target = args.first as? String, !target.isEmpty else {
                return ["error": "Missing path."]
            }
            return scanEngine.analysisPayload(for: target, lang: lang)
        default:
            throw NSError(
                domain: "CleanMyCodeMac",
                code: 4,
                userInfo: [NSLocalizedDescriptionKey: "Bridge method '\(method)' is not implemented yet."]
            )
        }
    }

    private func resolve(id: Int, payload: Any) {
        guard let script = javascriptCall(function: "__swiftBridgeResolve", id: id, payload: payload) else {
            return
        }
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(script, completionHandler: nil)
        }
    }

    private func reject(id: Int, message: String) {
        let payload = ["message": message]
        guard let script = javascriptCall(function: "__swiftBridgeReject", id: id, payload: payload) else {
            return
        }
        DispatchQueue.main.async { [weak self] in
            self?.webView?.evaluateJavaScript(script, completionHandler: nil)
        }
    }

    private func javascriptCall(function: String, id: Int, payload: Any) -> String? {
        guard JSONSerialization.isValidJSONObject([payload]),
              let payloadData = try? JSONSerialization.data(withJSONObject: payload, options: []),
              let payloadJSON = String(data: payloadData, encoding: .utf8)
        else {
            return nil
        }
        return "\(function)(\(id), \(payloadJSON));"
    }
}
