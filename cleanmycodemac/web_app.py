"""CleanMyCodeMac - 本地原生窗口 UI，基于 pywebview + 内置 http.server"""

import json
import threading
import queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from core.scanner import Scanner, CATEGORY_NAMES
from core.disk_info import get_disk_info
from core.permissions import check_full_disk_access, request_full_disk_access
from core.analyzer import analyze_path
from core.cleaners import (
    SystemCacheCleaner, AppCacheCleaner, LogsCleaner,
    DownloadsAnalyzer, LargeFileScanner, TrashCleaner,
)
from models.scan_item import format_size
from models.scan_result import ScanResult
from utils.subprocess_utils import reveal_in_finder

CLEANER_MAP = {
    "system_cache": SystemCacheCleaner(),
    "app_cache":    AppCacheCleaner(),
    "log":          LogsCleaner(),
    "download":     DownloadsAnalyzer(),
    "large_file":   LargeFileScanner(),
    "trash":        TrashCleaner(),
}

# 全局状态
scan_result: ScanResult = None
scan_progress = {"status": "idle", "percent": 0, "label": "", "logs": []}
scan_queue = queue.Queue()
scanner = None
scan_options = {"categories": list(CLEANER_MAP.keys())}


def _serialize_scan_result(result: ScanResult | None):
    if not result:
        return None

    data = {}
    for cat, items in result.by_category().items():
        by_app = {}
        for item in items:
            by_app.setdefault(item.app_name, []).append(item)

        sub_groups = []
        for app_name, app_items in by_app.items():
            app_size = sum(x.size_bytes for x in app_items)
            app_selected = sum(x.size_bytes for x in app_items if x.selected)
            all_safe = all(x.is_safe for x in app_items)
            any_selected = any(x.selected for x in app_items)
            all_selected = all(x.selected for x in app_items)
            files = [{
                "path": str(x.path),
                "path_short": x.path_str,
                "size": x.size_bytes,
                "size_display": x.size_display,
                "selected": x.selected,
                "is_safe": x.is_safe,
                "can_analyze": x.category == "large_file",
            } for x in app_items]
            sub_groups.append({
                "app_name": app_name,
                "description": app_items[0].description,
                "size": app_size,
                "size_display": format_size(app_size),
                "selected_size": app_selected,
                "selected_display": format_size(app_selected),
                "is_safe": all_safe,
                "any_selected": any_selected,
                "all_selected": all_selected,
                "file_count": len(files),
                "primary_path": files[0]["path"] if files else "",
                "can_analyze": app_items[0].category == "large_file" and len(files) == 1,
                "files": files,
            })

        sub_groups.sort(key=lambda g: g["size"], reverse=True)
        cat_size = sum(i.size_bytes for i in items)
        cat_selected = sum(i.size_bytes for i in items if i.selected)
        data[cat] = {
            "name": CATEGORY_NAMES.get(cat, cat),
            "size": cat_size,
            "size_display": format_size(cat_size),
            "selected_size": cat_selected,
            "selected_display": format_size(cat_selected),
            "any_selected": any(i.selected for i in items),
            "all_selected": all(i.selected for i in items),
            "sub_groups": sub_groups,
        }

    total = sum(i.size_bytes for i in result.items)
    selected = sum(i.size_bytes for i in result.items if i.selected)
    return {
        "categories": data,
        "total_items": len(result.items),
        "total_size": format_size(total),
        "total_bytes": total,
        "selected_size": format_size(selected),
        "selected_bytes": selected,
    }


def _selected_size_payload():
    selected_size = sum(i.size_bytes for i in scan_result.items if i.selected) if scan_result else 0
    return {"selected_size": format_size(selected_size)}


def do_scan(categories=None):
    global scan_result, scanner, scan_queue, scan_options
    categories = [cat for cat in (categories or CLEANER_MAP.keys()) if cat in CLEANER_MAP]
    scan_options = {"categories": categories}
    scan_progress["status"] = "scanning"
    scan_progress["percent"] = 0
    scan_progress["label"] = "初始化..."
    scan_progress["logs"] = []
    scan_queue = queue.Queue()
    scanner = Scanner()

    def on_done(result):
        global scan_result
        scan_result = result
        scan_progress["status"] = "done"
        scan_progress["percent"] = 100
        scan_progress["label"] = "扫描完成！"

    scanner.scan_all(scan_queue, categories=categories, done_callback=on_done)

    # 后台线程消费队列更新进度
    def consume():
        while scan_progress["status"] == "scanning":
            try:
                msg = scan_queue.get(timeout=0.1)
                t = msg.get("type")
                if t == "progress":
                    scan_progress["percent"] = msg["value"]
                    scan_progress["label"] = msg.get("label", "")
                elif t == "log":
                    scan_progress["logs"].append(msg["msg"])
                elif t == "done":
                    pass  # done_callback 已处理
            except queue.Empty:
                pass
            except Exception:
                pass

    threading.Thread(target=consume, daemon=True).start()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._html()
        elif path == "/api/disk":
            self._json(get_disk_info())
        elif path == "/api/scan/progress":
            self._json(scan_progress)
        elif path == "/api/scan/result":
            self._json(_serialize_scan_result(scan_result))
        elif path == "/api/perm":
            self._json({"fda": check_full_disk_access()})
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path == "/api/scan/start":
            categories = body.get("categories") or list(CLEANER_MAP.keys())
            do_scan(categories)
            self._json({"ok": True, "categories": scan_options["categories"]})
        elif path == "/api/clean":
            paths_to_clean = set(body.get("paths", []))
            if not scan_result or not paths_to_clean:
                self._json({"error": "无选中项"})
                return
            by_cat = {}
            for item in scan_result.items:
                if str(item.path) in paths_to_clean:
                    by_cat.setdefault(item.category, []).append(item)
            freed, errors = 0, []
            for cat, items in by_cat.items():
                c = CLEANER_MAP.get(cat)
                if c:
                    r = c.clean(items)
                    freed += r.cleaned_bytes
                    errors.extend(r.failed)
            self._json({
                "freed": format_size(freed),
                "freed_bytes": freed,
                "errors": len(errors),
            })
        elif path == "/api/select":
            # 更新选中状态
            path_str = body.get("path")
            selected = body.get("selected")
            if scan_result and path_str is not None:
                for item in scan_result.items:
                    if str(item.path) == path_str:
                        item.selected = selected
                        break
            self._json(_selected_size_payload())
        elif path == "/api/select_category":
            cat = body.get("category")
            app_name = body.get("app_name")
            state = body.get("selected", True)
            if scan_result:
                for item in scan_result.items:
                    if item.category == cat:
                        if app_name is None or item.app_name == app_name:
                            item.selected = state
            self._json(_selected_size_payload())
        elif path == "/api/select_all":
            state = body.get("selected", True)
            if scan_result:
                for item in scan_result.items:
                    item.selected = state
            self._json(_selected_size_payload())
        elif path == "/api/reveal":
            target = body.get("path")
            if not target:
                self._json({"ok": False, "error": "缺少路径"})
                return
            self._json({"ok": reveal_in_finder(target)})
        elif path == "/api/analyze":
            target = body.get("path")
            if not target:
                self._json({"error": "缺少路径"})
                return
            self._json(analyze_path(target))
        elif path == "/api/perm/open":
            request_full_disk_access()
            self._json({"ok": True})
        else:
            self.send_error(404)

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _html(self):
        body = HTML_PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def start_server(port=9527):
    import webview

    server = HTTPServer(("127.0.0.1", port), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"CleanMyCodeMac 后端已启动: http://127.0.0.1:{port}")

    window = webview.create_window(
        "CleanMyCodeMac",
        f"http://127.0.0.1:{port}",
        width=1120,
        height=720,
        min_size=(800, 500),
    )
    webview.start()
    print("已退出")
    server.shutdown()


# ──────────────────────────────────────────────
#  HTML 单页应用
# ──────────────────────────────────────────────

HTML_PAGE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CleanMyCodeMac</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, "Helvetica Neue", sans-serif; background: #F5F5F5; color: #333; }

.app { display: flex; height: 100vh; }
.sidebar { width: 200px; background: #1E293B; color: #F1F5F9; padding: 20px 14px; display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
.sidebar h2 { font-size: 15px; margin-bottom: 16px; }
.main { flex: 1; overflow-y: auto; display: flex; flex-direction: column; }

.gauge { position: relative; width: 120px; height: 120px; margin-bottom: 6px; }
.gauge svg { width: 100%; height: 100%; }
.gauge-text { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
.gauge-pct { font-size: 22px; font-weight: 700; }
.gauge-label { font-size: 10px; color: #94A3B8; margin-top: 2px; }
.disk-info { font-size: 10px; color: #94A3B8; text-align: center; margin-bottom: 12px; }
.perm-status { font-size: 10px; color: #94A3B8; text-align: center; margin-top: 12px; border-top: 1px solid #2D3F55; padding-top: 12px; width: 100%; }
.perm-ok { color: #10B981; }
.perm-warn { color: #F59E0B; }
.perm-action { margin-top: 8px; border: 1px solid #475569; background: transparent; color: #E2E8F0; border-radius: 8px; padding: 7px 10px; font-size: 11px; cursor: pointer; }
.perm-action:hover { background: rgba(255,255,255,0.06); }
.version { margin-top: auto; font-size: 10px; color: #475569; text-align: center; line-height: 1.7; }
.version .about-label { color: #94A3B8; display: block; margin-bottom: 4px; }

.hero { background: linear-gradient(135deg, #1E293B 0%, #334155 100%); padding: 56px 32px; text-align: center; }
.hero h1 { font-size: 28px; color: #F1F5F9; margin-bottom: 8px; }
.hero p { color: #94A3B8; font-size: 14px; margin-bottom: 28px; }
.hero-actions { display: flex; justify-content: center; gap: 10px; }
.btn-scan { background: linear-gradient(135deg, #F97316, #FB923C); color: white; border: none; padding: 14px 36px; font-size: 16px; font-weight: 600; border-radius: 12px; cursor: pointer; transition: transform 0.15s, box-shadow 0.15s; box-shadow: 0 4px 14px rgba(249,115,22,0.4); }
.btn-scan:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(249,115,22,0.5); }
.btn-ghost { background: rgba(255,255,255,0.08); color: #F8FAFC; border: 1px solid rgba(255,255,255,0.16); padding: 14px 20px; font-size: 14px; font-weight: 600; border-radius: 12px; cursor: pointer; }
.scope-head { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px 0; }
.cards-title { font-size: 12px; font-weight: 600; color: #999; text-transform: uppercase; letter-spacing: 1px; }
.scope-summary { font-size: 12px; color: #666; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding: 20px 24px 24px; }
.scope-card { background: white; border-radius: 12px; padding: 16px; border: 1px solid #E8E8E8; position: relative; cursor: pointer; transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s; }
.scope-card:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06); }
.scope-card.selected { border-color: #3B82F6; box-shadow: 0 0 0 1px rgba(59,130,246,0.15); }
.scope-card input { position: absolute; right: 14px; top: 14px; width: 18px; height: 18px; accent-color: #3B82F6; pointer-events: none; }
.card-icon { display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: 700; margin-bottom: 8px; }
.card h3 { font-size: 13px; font-weight: 600; margin-bottom: 3px; }
.card p { font-size: 11px; color: #999; line-height: 1.4; }

.scan-view { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; padding: 60px; }
.spinner { width: 56px; height: 56px; border: 5px solid #E8E8E8; border-top-color: #F97316; border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 20px; }
@keyframes spin { to { transform: rotate(360deg); } }
.scan-title { font-size: 20px; font-weight: 700; margin-bottom: 6px; }
.scan-sub { color: #475569; margin-bottom: 14px; font-size: 13px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 999px; padding: 8px 14px; max-width: 420px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; box-shadow: 0 8px 20px rgba(15, 23, 42, 0.04); }
.scan-scope { width: 440px; max-width: 100%; margin-bottom: 14px; padding: 10px 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; display: flex; align-items: center; gap: 8px; overflow: hidden; }
.scan-scope-label { font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; flex-shrink: 0; }
.scan-scope-value { font-size: 12px; color: #334155; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.progress-bar { width: 400px; height: 6px; background: #E8E8E8; border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #F97316, #FB923C); border-radius: 3px; transition: width 0.3s; }
.scan-pct { font-size: 12px; color: #999; margin-bottom: 16px; }
.scan-log { width: 440px; max-height: 140px; overflow-y: auto; background: #FAFAFA; border: 1px solid #E8E8E8; border-radius: 8px; padding: 10px; font-size: 11px; font-family: "Menlo", monospace; color: #999; }

.result-top { background: white; padding: 20px 24px; display: flex; align-items: center; border-bottom: 1px solid #E8E8E8; position: sticky; top: 0; z-index: 10; }
.result-icon { width: 56px; height: 56px; margin-right: 16px; flex-shrink: 0; }
.result-icon svg { width: 100%; height: 100%; }
.result-info { flex: 1; }
.result-info h2 { font-size: 22px; font-weight: 700; }
.result-info h2 span { color: #F97316; }
.result-info .sel { font-size: 13px; color: #F97316; margin-top: 4px; }
.result-actions { display: flex; gap: 8px; align-items: center; }
.btn-back { padding: 8px 20px; border: 1px solid #DDD; border-radius: 8px; background: white; font-size: 13px; cursor: pointer; color: #666; }
.btn-back:hover { background: #F5F5F5; }
.btn-lite { padding: 8px 14px; border: 1px solid #DDD; border-radius: 8px; background: white; font-size: 12px; cursor: pointer; color: #444; }
.btn-clean { background: linear-gradient(135deg, #34D399, #10B981); color: white; border: none; padding: 12px 32px; font-size: 15px; font-weight: 600; border-radius: 10px; cursor: pointer; box-shadow: 0 4px 14px rgba(16,185,129,0.3); transition: transform 0.15s; }
.btn-clean:hover { transform: translateY(-1px); }
.btn-clean:disabled { background: #CCC; box-shadow: none; cursor: not-allowed; transform: none; }

.cat-list { padding: 16px 20px; flex: 1; }
.cat-group { background: white; border-radius: 12px; margin-bottom: 12px; border: 1px solid #E8E8E8; overflow: hidden; }
.cat-header { display: flex; align-items: center; padding: 14px 18px; cursor: pointer; user-select: none; }
.cat-header:hover { background: #FAFAFA; }
.cat-check { width: 18px; height: 18px; margin-right: 12px; accent-color: #3B82F6; cursor: pointer; flex-shrink: 0; }
.cat-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; margin-right: 12px; flex-shrink: 0; }
.cat-name { font-size: 15px; font-weight: 600; }
.cat-meta { font-size: 12px; color: #999; margin-left: 8px; }
.cat-meta .sel-size { color: #F97316; font-weight: 500; }
.cat-right { margin-left: auto; display: flex; align-items: center; gap: 6px; }
.cat-arrow { font-size: 10px; color: #CCC; transition: transform 0.2s; }
.cat-arrow.open { transform: rotate(180deg); }

.sub-item { display: flex; align-items: center; padding: 10px 18px 10px 62px; border-top: 1px solid #F0F0F0; }
.sub-item:hover { background: #FAFAFA; }
.sub-cb { margin-right: 12px; width: 18px; height: 18px; accent-color: #3B82F6; cursor: pointer; flex-shrink: 0; }
.sub-name { font-size: 13px; font-weight: 500; min-width: 120px; }
.sub-desc { font-size: 12px; color: #999; flex: 1; margin-left: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub-right { margin-left: auto; display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.sub-size { font-size: 12px; color: #666; min-width: 80px; text-align: right; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; white-space: nowrap; }
.badge-safe { color: #10B981; background: #ECFDF5; }
.badge-warn { color: #F59E0B; background: #FFFBEB; }
.badge-danger { color: #EF4444; background: #FEF2F2; }
.badge-clean { color: #10B981; }
.sub-toggle { font-size: 10px; color: #CCC; cursor: pointer; transition: transform 0.2s; padding: 4px; }
.sub-toggle.open { transform: rotate(180deg); }

.file-row { display: flex; align-items: center; padding: 8px 18px 8px 96px; border-top: 1px solid #F8F8F8; font-size: 12px; gap: 10px; }
.file-row:hover { background: #FAFAFA; }
.file-cb { margin-right: 10px; width: 15px; height: 15px; accent-color: #3B82F6; cursor: pointer; }
.file-path-wrap { flex: 1; min-width: 0; }
.file-path { font-family: "Menlo", monospace; font-size: 11px; color: #666; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-hint { font-size: 11px; color: #94A3B8; margin-top: 2px; }
.file-size { color: #999; font-size: 11px; margin-left: 12px; min-width: 70px; text-align: right; }
.file-actions { display: flex; align-items: center; gap: 6px; }
.btn-mini { border: 1px solid #D6DDE7; background: white; color: #475569; border-radius: 6px; padding: 5px 8px; font-size: 11px; cursor: pointer; }
.btn-mini:hover { background: #F8FAFC; }

.analysis-mask { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.42); display: none; align-items: center; justify-content: center; z-index: 30; }
.analysis-mask.show { display: flex; }
.analysis-panel { width: min(760px, calc(100vw - 32px)); max-height: calc(100vh - 40px); overflow-y: auto; background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(15, 23, 42, 0.28); }
.analysis-head { display: flex; justify-content: space-between; align-items: center; padding: 18px 20px; border-bottom: 1px solid #E5E7EB; position: sticky; top: 0; background: white; }
.analysis-head h3 { font-size: 18px; }
.analysis-close { border: none; background: #F1F5F9; color: #475569; width: 32px; height: 32px; border-radius: 8px; cursor: pointer; }
.analysis-body { padding: 18px 20px 24px; }
.analysis-section { margin-bottom: 18px; }
.analysis-section h4 { font-size: 13px; color: #0F172A; margin-bottom: 8px; }
.analysis-note { font-size: 12px; color: #475569; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; line-height: 1.6; }
.analysis-list { border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; }
.analysis-row { display: flex; justify-content: space-between; gap: 12px; padding: 10px 12px; border-top: 1px solid #F1F5F9; font-size: 12px; }
.analysis-row:first-child { border-top: none; }
.analysis-name { min-width: 0; flex: 1; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.analysis-size { color: #0F172A; white-space: nowrap; font-weight: 600; }
.analysis-pre { white-space: pre-wrap; font-family: "Menlo", monospace; font-size: 11px; color: #334155; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px; line-height: 1.5; }
.tree-root { border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; }
.tree-node { border-top: 1px solid #F1F5F9; }
.tree-node:first-child { border-top: none; }
.tree-head { display: flex; align-items: center; gap: 10px; padding: 10px 12px; }
.tree-depth-1 .tree-head { padding-left: 28px; }
.tree-depth-2 .tree-head { padding-left: 44px; }
.tree-depth-3 .tree-head { padding-left: 60px; }
.tree-toggle { width: 18px; color: #94A3B8; text-align: center; cursor: pointer; user-select: none; }
.tree-label { min-width: 0; flex: 1; }
.tree-name { font-size: 12px; color: #334155; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tree-meta { font-size: 11px; color: #64748B; margin-top: 2px; }
.tree-size { min-width: 120px; text-align: right; font-size: 12px; font-weight: 600; color: #0F172A; }
.tree-children.hidden { display: none; }
.analysis-chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.analysis-chip { border: 1px solid #D8E2EF; background: #F8FAFC; color: #334155; border-radius: 999px; padding: 6px 10px; font-size: 11px; }
.tree-actions { display: flex; gap: 6px; margin-left: 8px; }
.analysis-cmd { border: 1px solid #E5E7EB; border-radius: 12px; padding: 12px; margin-top: 10px; background: #FCFCFD; }
.analysis-cmd-title { font-size: 12px; font-weight: 600; color: #0F172A; margin-bottom: 4px; }
.analysis-cmd-desc { font-size: 12px; color: #475569; line-height: 1.6; margin-bottom: 8px; }
.analysis-cmd-code { font-family: "Menlo", monospace; font-size: 11px; color: #0F172A; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; white-space: pre-wrap; }
.analysis-cmd-actions { margin-top: 8px; }
.dialog-mask { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.44); display: none; align-items: center; justify-content: center; z-index: 40; }
.dialog-mask.show { display: flex; }
.dialog-panel { width: min(420px, calc(100vw - 32px)); background: white; border-radius: 18px; box-shadow: 0 24px 80px rgba(15, 23, 42, 0.30); overflow: hidden; }
.dialog-head { padding: 18px 20px 10px; }
.dialog-title { font-size: 18px; font-weight: 700; color: #0F172A; }
.dialog-body { padding: 0 20px 18px; font-size: 13px; color: #475569; line-height: 1.7; white-space: pre-wrap; }
.dialog-actions { padding: 14px 20px 20px; display: flex; justify-content: flex-end; gap: 10px; border-top: 1px solid #F1F5F9; }
.btn-dialog-secondary { padding: 10px 16px; border: 1px solid #D7DEE7; background: white; color: #475569; border-radius: 10px; font-size: 13px; cursor: pointer; }
.btn-dialog-primary { padding: 10px 18px; border: none; background: linear-gradient(135deg, #F97316, #FB923C); color: white; border-radius: 10px; font-size: 13px; font-weight: 600; cursor: pointer; }
.toast-wrap { position: fixed; top: 20px; right: 20px; z-index: 45; display: flex; flex-direction: column; gap: 10px; pointer-events: none; }
.toast { min-width: 280px; max-width: 360px; background: white; border: 1px solid #DDE7F1; border-radius: 14px; box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18); padding: 14px 16px; transform: translateY(-8px); opacity: 0; transition: opacity 0.22s ease, transform 0.22s ease; }
.toast.show { opacity: 1; transform: translateY(0); }
.toast-title { font-size: 13px; font-weight: 700; color: #0F172A; margin-bottom: 4px; }
.toast-body { font-size: 12px; color: #475569; line-height: 1.6; white-space: pre-wrap; }
.toast-success { border-color: #BBF7D0; }

.hidden { display: none; }
</style>
</head>
<body>
<div class="app">
  <div class="sidebar">
    <h2>CleanMyCodeMac</h2>
    <div class="gauge">
      <svg viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="50" fill="none" stroke="#2D3F55" stroke-width="10"
                stroke-dasharray="236" stroke-dashoffset="79" transform="rotate(135 60 60)" stroke-linecap="round"/>
        <circle id="gauge-arc" cx="60" cy="60" r="50" fill="none" stroke="#10B981" stroke-width="10"
                stroke-dasharray="236" stroke-dashoffset="236" transform="rotate(135 60 60)" stroke-linecap="round"/>
      </svg>
      <div class="gauge-text">
        <div class="gauge-pct" id="gauge-pct">--%</div>
        <div class="gauge-label">已使用</div>
      </div>
    </div>
    <div class="disk-info" id="disk-info">加载中...</div>
    <div class="perm-status" id="perm-status"></div>
    <div class="version">v1.0.0</div>
  </div>

  <div class="main">
    <!-- 首页 -->
    <div id="view-home">
      <div class="hero">
        <h1>CleanMyCodeMac</h1>
        <p>扫描并清理 Mac 上的垃圾文件，快速释放磁盘空间</p>
        <div class="hero-actions">
          <button class="btn-scan" onclick="startScan()">开始扫描</button>
          <button class="btn-ghost" onclick="selectAllScopes(true)">全选范围</button>
          <button class="btn-ghost" onclick="selectAllScopes(false)">清空范围</button>
        </div>
      </div>
      <div class="scope-head">
        <div class="cards-title">扫描范围</div>
        <div class="scope-summary" id="scope-summary">已选择 6 / 6 项</div>
      </div>
      <div class="cards" id="scope-cards"></div>
    </div>

    <div id="view-scan" class="hidden">
      <div class="scan-view">
        <div class="spinner"></div>
        <div class="scan-title">正在扫描...</div>
        <div class="scan-sub" id="scan-label">初始化中...</div>
        <div class="scan-scope"><span class="scan-scope-label">范围</span><span class="scan-scope-value" id="scan-scope"></span></div>
        <div class="progress-bar"><div class="progress-fill" id="scan-bar" style="width:0%"></div></div>
        <div class="scan-pct" id="scan-pct">0%</div>
        <div class="scan-log" id="scan-log"></div>
      </div>
    </div>

    <div id="view-result" class="hidden" style="display:none;flex-direction:column;flex:1;">
      <div class="result-top">
        <div class="result-icon">
          <svg viewBox="0 0 56 56"><circle cx="28" cy="28" r="26" fill="#FFF7ED" stroke="#F97316" stroke-width="2"/><text x="28" y="34" text-anchor="middle" font-size="24" fill="#F97316">!</text></svg>
        </div>
        <div class="result-info">
          <h2>共发现可清理文件 <span id="result-total">--</span></h2>
          <div class="sel">已选择垃圾 <strong id="result-selected">--</strong></div>
        </div>
        <div class="result-actions">
          <button class="btn-back" onclick="showView('home')">返回</button>
          <button class="btn-lite" onclick="toggleAllResultSelection(true)">全选结果</button>
          <button class="btn-lite" onclick="toggleAllResultSelection(false)">取消全选</button>
          <button class="btn-clean" id="btn-clean" onclick="doClean()">立即清理</button>
        </div>
      </div>
      <div class="cat-list" id="cat-list"></div>
    </div>
  </div>
</div>

<div id="analysis-mask" class="analysis-mask" onclick="closeAnalysis(event)">
  <div class="analysis-panel" onclick="event.stopPropagation()">
    <div class="analysis-head">
      <h3 id="analysis-title">占用分析</h3>
      <button class="analysis-close" onclick="closeAnalysis()">&times;</button>
    </div>
    <div class="analysis-body" id="analysis-body"></div>
  </div>
</div>

<div id="dialog-mask" class="dialog-mask" onclick="closeDialog(false)">
  <div class="dialog-panel" onclick="event.stopPropagation()">
    <div class="dialog-head"><div class="dialog-title" id="dialog-title">提示</div></div>
    <div class="dialog-body" id="dialog-body"></div>
    <div class="dialog-actions" id="dialog-actions"></div>
  </div>
</div>

<div id="toast-wrap" class="toast-wrap"></div>

<script>
const CAT_CFG = {
  system_cache: { icon: '&#9881;', color: '#F97316', bg: '#FFF7ED', name: '系统垃圾', desc: 'macOS 系统应用产生的临时缓存' },
  app_cache:    { icon: '&#9638;', color: '#3B82F6', bg: '#EFF6FF', name: '应用垃圾', desc: 'Chrome、VSCode 等 App 缓存' },
  log:          { icon: '&#9776;', color: '#8B5CF6', bg: '#F5F3FF', name: '日志文件', desc: '7 天以上的崩溃报告与运行日志' },
  download:     { icon: '&#8595;', color: '#10B981', bg: '#ECFDF5', name: '下载文件', desc: '下载文件夹旧文件分析' },
  large_file:   { icon: '&#9650;', color: '#EF4444', bg: '#FEF2F2', name: '大文件', desc: '搜索 500MB 以上的大文件并分析占用' },
  trash:        { icon: '&#9003;', color: '#6B7280', bg: '#F3F4F6', name: '废纸篓', desc: '立即清空废纸篓释放空间' },
};
const CAT_ORDER = ['system_cache', 'log', 'app_cache', 'download', 'large_file', 'trash'];

let resultData = null;
let scanSelections = {};
let dialogResolver = null;

function showView(name) {
  document.querySelectorAll('.main > div').forEach(v => { v.classList.add('hidden'); v.style.display = 'none'; });
  const el = document.getElementById('view-' + name);
  el.classList.remove('hidden');
  el.style.display = name === 'result' ? 'flex' : '';
}

function initScopes() {
  CAT_ORDER.forEach(cat => { scanSelections[cat] = true; });
  renderScopeCards();
}

function renderScopeCards() {
  const root = document.getElementById('scope-cards');
  root.innerHTML = '';
  CAT_ORDER.forEach(cat => {
    const cfg = CAT_CFG[cat];
    const card = document.createElement('div');
    card.className = 'scope-card card' + (scanSelections[cat] ? ' selected' : '');
    card.innerHTML =
      '<input type="checkbox"' + (scanSelections[cat] ? ' checked' : '') + '>' +
      '<span class="card-icon" style="color:' + cfg.color + ';background:' + cfg.bg + '">' + cfg.icon + '</span>' +
      '<h3>' + cfg.name + '</h3>' +
      '<p>' + cfg.desc + '</p>';
    card.onclick = () => {
      scanSelections[cat] = !scanSelections[cat];
      renderScopeCards();
    };
    root.appendChild(card);
  });
  updateScopeSummary();
}

function updateScopeSummary() {
  const selected = getSelectedScanCategories();
  document.getElementById('scope-summary').textContent = '已选择 ' + selected.length + ' / ' + CAT_ORDER.length + ' 项';
}

function selectAllScopes(state) {
  CAT_ORDER.forEach(cat => { scanSelections[cat] = state; });
  renderScopeCards();
}

function getSelectedScanCategories() {
  return CAT_ORDER.filter(cat => scanSelections[cat]);
}

async function loadDisk() {
  const r = await fetch('/api/disk').then(r => r.json());
  const pct = r.total > 0 ? (r.used / r.total * 100) : 0;
  document.getElementById('gauge-pct').textContent = Math.round(pct) + '%';
  const arc = document.getElementById('gauge-arc');
  arc.style.strokeDashoffset = 236 - 236 * (pct / 100);
  arc.style.stroke = pct < 60 ? '#10B981' : pct < 85 ? '#F59E0B' : '#EF4444';
  const usedG = (r.used / 1073741824).toFixed(1);
  const totalG = (r.total / 1073741824).toFixed(1);
  const freeG = (r.free / 1073741824).toFixed(1);
  document.getElementById('disk-info').textContent = usedG + 'G / ' + totalG + 'G (可用 ' + freeG + 'G)';
}

async function loadPerm() {
  const r = await fetch('/api/perm').then(r => r.json());
  const el = document.getElementById('perm-status');
  el.innerHTML = r.fda
    ? '<span class="perm-ok">&#10003; 完全磁盘访问已授权</span>'
    : '<span class="perm-warn">&#9888; 未授权完全磁盘访问</span><div><button class="perm-action" onclick="openPermissionSettings()">打开授权设置</button></div>';
}

async function openPermissionSettings() {
  await postJson('/api/perm/open', {});
}

async function postJson(url, body) {
  return fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body || {}),
  }).then(r => r.json());
}

async function startScan() {
  const categories = getSelectedScanCategories();
  if (categories.length === 0) {
    await showAlert('请至少勾选一个扫描范围', '扫描范围为空');
    return;
  }
  showView('scan');
  document.getElementById('scan-bar').style.width = '0%';
  document.getElementById('scan-pct').textContent = '0%';
  document.getElementById('scan-label').textContent = '初始化中...';
  document.getElementById('scan-log').textContent = '';
  document.getElementById('scan-scope').textContent = categories.map(cat => CAT_CFG[cat].name).join('、');
  await postJson('/api/scan/start', { categories });
  pollProgress();
}

async function pollProgress() {
  const r = await fetch('/api/scan/progress').then(r => r.json());
  document.getElementById('scan-bar').style.width = r.percent + '%';
  document.getElementById('scan-pct').textContent = r.percent + '%';
  document.getElementById('scan-label').textContent = r.label;
  const logEl = document.getElementById('scan-log');
  logEl.textContent = r.logs.map(l => '\u25b8 ' + l).join('\n');
  logEl.scrollTop = logEl.scrollHeight;
  if (r.status === 'done') { setTimeout(loadResult, 400); }
  else { setTimeout(pollProgress, 200); }
}

function safetyBadge(is_safe, size) {
  if (size === 0) return '<span class="badge-clean">很干净</span>';
  if (is_safe) return '<span class="badge badge-safe">建议清理</span>';
  return '<span class="badge badge-warn">谨慎清理</span>';
}

async function loadResult() {
  resultData = await fetch('/api/scan/result').then(r => r.json());
  if (!resultData) return;
  renderResult();
  showView('result');
  loadDisk();
}

function renderResult() {
  const r = resultData;
  document.getElementById('result-total').textContent = r.total_size;
  document.getElementById('result-selected').textContent = r.selected_size;

  const list = document.getElementById('cat-list');
  list.innerHTML = '';

  for (const cat of CAT_ORDER) {
    const data = r.categories[cat];
    if (!data) continue;
    const cfg = CAT_CFG[cat] || { icon: '?', color: '#999', bg: '#F5F5F5', name: cat };

    const group = document.createElement('div');
    group.className = 'cat-group';
    group.dataset.cat = cat;

    const header = document.createElement('div');
    header.className = 'cat-header';
    header.innerHTML =
      '<input type="checkbox" class="cat-check"' + (data.all_selected ? ' checked' : '') + '>' +
      '<div class="cat-icon" style="background:' + cfg.bg + ';color:' + cfg.color + '">' + cfg.icon + '</div>' +
      '<span class="cat-name" style="color:' + cfg.color + '">' + cfg.name + '</span>' +
      '<span class="cat-meta">&nbsp;&nbsp;共 ' + data.size_display + '，已选择 <span class="sel-size cat-sel-size">' + data.selected_display + '</span></span>' +
      '<span class="cat-right"><span class="cat-arrow open">&#9660;</span></span>';

    const body = document.createElement('div');
    body.className = 'cat-body';

    header.onclick = () => {
      body.classList.toggle('hidden');
      header.querySelector('.cat-arrow').classList.toggle('open');
    };

    const catCb = header.querySelector('.cat-check');
    catCb.indeterminate = data.any_selected && !data.all_selected;
    catCb.addEventListener('click', e => e.stopPropagation());
    catCb.addEventListener('change', async () => {
      await postJson('/api/select_category', { category: cat, selected: catCb.checked });
      await loadResult();
    });

    for (const sg of data.sub_groups) {
      const subRow = document.createElement('div');
      subRow.className = 'sub-item';
      subRow.innerHTML =
        '<input type="checkbox" class="sub-cb"' +
        (sg.all_selected ? ' checked' : '') +
        (sg.any_selected && !sg.all_selected ? ' data-indeterminate="1"' : '') +
        ' data-cat="' + cat + '" data-app="' + escapeHtml(sg.app_name) + '">' +
        '<span class="sub-name">' + escapeHtml(sg.app_name) + '</span>' +
        '<span class="sub-desc">' + escapeHtml(sg.description) + '</span>' +
        '<span class="sub-right">' +
          '<span class="sub-size">' + sg.size_display + '</span>' +
          safetyBadge(sg.is_safe, sg.size) +
          '<span class="sub-toggle" title="展开文件列表">&#9660;</span>' +
        '</span>';

      const cb = subRow.querySelector('.sub-cb');
      if (cb.dataset.indeterminate === '1') cb.indeterminate = true;
      cb.addEventListener('change', async (e) => {
        e.stopPropagation();
        await postJson('/api/select_category', { category: cat, app_name: sg.app_name, selected: cb.checked });
        await loadResult();
      });

      body.appendChild(subRow);

      const filesDiv = document.createElement('div');
      filesDiv.className = 'file-details hidden';
      for (const f of sg.files) {
        const frow = document.createElement('div');
        frow.className = 'file-row';
        frow.innerHTML =
          '<input type="checkbox" class="file-cb"' + (f.selected ? ' checked' : '') +
          ' data-path="' + escapeHtml(f.path) + '">' +
          '<div class="file-path-wrap">' +
            '<div class="file-path" title="' + escapeHtml(f.path) + '">' + escapeHtml(f.path_short) + '</div>' +
          '</div>' +
          '<span class="file-size">' + f.size_display + '</span>' +
          '<span class="file-actions">' +
            '<button class="btn-mini" data-action="reveal" data-path="' + escapeHtml(f.path) + '">打开</button>' +
            (f.can_analyze ? '<button class="btn-mini" data-action="analyze" data-path="' + escapeHtml(f.path) + '">分析</button>' : '') +
          '</span>';
        const fcb = frow.querySelector('.file-cb');
        fcb.addEventListener('change', async (e) => {
          e.stopPropagation();
          await postJson('/api/select', { path: f.path, selected: fcb.checked });
          await loadResult();
        });
        frow.querySelectorAll('.btn-mini').forEach(btn => {
          btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const targetPath = btn.dataset.path;
            if (btn.dataset.action === 'reveal') {
              await postJson('/api/reveal', { path: targetPath });
            } else if (btn.dataset.action === 'analyze') {
              await openAnalysis(targetPath);
            }
          });
        });
        filesDiv.appendChild(frow);
      }
      const toggle = subRow.querySelector('.sub-toggle');
      toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        filesDiv.classList.toggle('hidden');
        toggle.classList.toggle('open');
      });
      body.appendChild(filesDiv);
    }

    group.appendChild(header);
    group.appendChild(body);
    list.appendChild(group);
  }
}

async function toggleAllResultSelection(state) {
  await postJson('/api/select_all', { selected: state });
  await loadResult();
}

async function doClean() {
  // 从 resultData 收集所有服务端标记为 selected 的路径
  const paths = [];
  if (resultData) {
    for (const cat of CAT_ORDER) {
      const data = resultData.categories[cat];
      if (!data) continue;
      for (const sg of data.sub_groups) {
        for (const f of sg.files) {
          if (f.selected && !paths.includes(f.path)) paths.push(f.path);
        }
      }
    }
  }
  const uniquePaths = paths;

  if (uniquePaths.length === 0) {
    await showAlert('请先勾选要清理的项目', '未选择项目');
    return;
  }
  const confirmed = await showConfirm(
    '即将清理 ' + uniquePaths.length + ' 个项目。\n文件将移入废纸篓（可恢复），确认继续？',
    '确认清理'
  );
  if (!confirmed) return;

  const btn = document.getElementById('btn-clean');
  btn.disabled = true;
  btn.textContent = '清理中...';

  const r = await fetch('/api/clean', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({paths: uniquePaths})
  }).then(r => r.json());

  let msg = '清理完成，释放了 ' + r.freed;
  if (r.errors > 0) msg += '\n\n' + r.errors + ' 个项目失败';
  showToast(msg, '清理完成', 'success');
  btn.disabled = false;
  btn.textContent = '立即清理';
  startScan();
}

async function openAnalysis(path) {
  const mask = document.getElementById('analysis-mask');
  const title = document.getElementById('analysis-title');
  const body = document.getElementById('analysis-body');
  title.textContent = '占用分析';
  body.innerHTML = '<div class="analysis-note">正在分析，请稍候...</div>';
  mask.classList.add('show');

  const data = await postJson('/api/analyze', { path });
  if (data.error) {
    title.textContent = '占用分析';
    body.innerHTML = '<div class="analysis-note">' + escapeHtml(data.error) + '</div>';
    return;
  }

  title.textContent = data.name + ' · ' + data.size_display;

  const sections = [];
  if (data.highlights) {
    sections.push(
      '<div class="analysis-section"><h4>分析结论</h4>' +
      data.highlights.map(line => '<div class="analysis-note">' + escapeHtml(line) + '</div>').join('') +
      '</div>'
    );
  }

  if (data.same_level_items && data.same_level_items.length) {
    sections.push(renderAnalysisList('同级目录占用', data.same_level_items));
  }

  if (data.tree) {
    sections.push(renderAnalysisTree('树状占用视图', data.tree));
  }

  if (data.ancestor_levels && data.ancestor_levels.length) {
    data.ancestor_levels.forEach(level => {
      if (level.children && level.children.length) {
        sections.push(renderAnalysisList('上层目录：' + level.path, level.children));
      }
    });
  }

  if (data.special && data.special.kind === 'docker_raw') {
    sections.push(
      '<div class="analysis-section"><h4>' + escapeHtml(data.special.title) + '</h4>' +
      data.special.highlights.map(line => '<div class="analysis-note">' + escapeHtml(line) + '</div>').join('') +
      (data.special.docker_summary && data.special.docker_summary.length
        ? '<div class="analysis-chip-row">' + data.special.docker_summary.map(item =>
            '<div class="analysis-chip">' + escapeHtml(item.label) + '：' + escapeHtml(item.value) + '</div>'
          ).join('') + '</div>'
        : '') +
      (data.special.suggestions && data.special.suggestions.length
        ? '<div class="analysis-section"><h4>建议动作</h4>' +
          data.special.suggestions.map(item =>
            '<div class="analysis-cmd">' +
              '<div class="analysis-cmd-title">' + escapeHtml(item.label) + '</div>' +
              '<div class="analysis-cmd-desc">' + escapeHtml(item.description) + '</div>' +
              '<div class="analysis-cmd-code">' + escapeHtml(item.command) + '</div>' +
              '<div class="analysis-cmd-actions">' +
                '<button class="btn-mini" data-copy="' + escapeHtml(item.command) + '">复制命令</button>' +
              '</div>' +
            '</div>'
          ).join('') +
          '</div>'
        : '') +
      (data.special.docker_cli_available
        ? '<div class="analysis-pre">' + escapeHtml(data.special.docker_df_lines.join('\n')) + '</div>'
        : '<div class="analysis-note">未获取到 Docker CLI 结果，可能是 Docker 未启动或命令不可用。</div>') +
      '</div>'
    );
  }

  body.innerHTML = sections.join('') || '<div class="analysis-note">没有可展示的分析数据。</div>';
  bindTreeToggles();
  bindAnalysisActions();
}

function renderAnalysisList(title, items) {
  return '<div class="analysis-section"><h4>' + escapeHtml(title) + '</h4><div class="analysis-list">' +
    items.map(item =>
      '<div class="analysis-row">' +
        '<div class="analysis-name" title="' + escapeHtml(item.path || item.name) + '">' + escapeHtml(item.name) + '</div>' +
        '<div class="analysis-size">' + escapeHtml(item.size_display) + '</div>' +
      '</div>'
    ).join('') +
    '</div></div>';
}

function renderAnalysisTree(title, tree) {
  return '<div class="analysis-section"><h4>' + escapeHtml(title) + '</h4><div class="tree-root">' +
    renderTreeNode(tree, 0) +
    '</div></div>';
}

function renderTreeNode(node, depth) {
  const hasChildren = node.children && node.children.length > 0;
  return '<div class="tree-node tree-depth-' + depth + '">' +
    '<div class="tree-head">' +
      '<span class="tree-toggle"' + (hasChildren ? '' : ' style="visibility:hidden"') + '>' + (hasChildren ? '&#9660;' : '') + '</span>' +
      '<div class="tree-label">' +
        '<div class="tree-name" title="' + escapeHtml(node.path) + '">' + escapeHtml(node.name) + '</div>' +
        '<div class="tree-meta">' + escapeHtml(node.kind === 'dir' ? '目录' : '文件') + ' · 占比 ' + escapeHtml(node.percent) + '</div>' +
      '</div>' +
      '<div class="tree-actions">' +
        '<button class="btn-mini" data-reveal="' + escapeHtml(node.path) + '">Finder</button>' +
        (node.can_drill ? '<button class="btn-mini" data-drill="' + escapeHtml(node.path) + '">深入分析</button>' : '') +
      '</div>' +
      '<div class="tree-size">' + escapeHtml(node.size_display) + '</div>' +
    '</div>' +
    (hasChildren ? '<div class="tree-children">' + node.children.map(child => renderTreeNode(child, depth + 1)).join('') + '</div>' : '') +
    '</div>';
}

function bindTreeToggles() {
  document.querySelectorAll('.tree-node > .tree-head > .tree-toggle').forEach(toggle => {
    if (!toggle.textContent.trim()) return;
    toggle.addEventListener('click', () => {
      const node = toggle.closest('.tree-node');
      const children = node.querySelector(':scope > .tree-children');
      if (!children) return;
      children.classList.toggle('hidden');
      toggle.innerHTML = children.classList.contains('hidden') ? '&#9658;' : '&#9660;';
    });
  });
}

function bindAnalysisActions() {
  document.querySelectorAll('[data-drill]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await openAnalysis(btn.dataset.drill);
    });
  });

  document.querySelectorAll('[data-reveal]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await postJson('/api/reveal', { path: btn.dataset.reveal });
    });
  });

  document.querySelectorAll('[data-copy]').forEach(btn => {
    btn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(btn.dataset.copy);
        btn.textContent = '已复制';
        setTimeout(() => { btn.textContent = '复制命令'; }, 1200);
      } catch (_) {
        showAlert('复制失败，请手动复制命令', '复制失败');
      }
    });
  });
}

function showAlert(message, title = '提示') {
  return new Promise(resolve => {
    const mask = document.getElementById('dialog-mask');
    document.getElementById('dialog-title').textContent = title;
    document.getElementById('dialog-body').textContent = message;
    document.getElementById('dialog-actions').innerHTML =
      '<button class="btn-dialog-primary" onclick="closeDialog(true)">知道了</button>';
    dialogResolver = resolve;
    mask.classList.add('show');
  });
}

function showConfirm(message, title = '请确认') {
  return new Promise(resolve => {
    const mask = document.getElementById('dialog-mask');
    document.getElementById('dialog-title').textContent = title;
    document.getElementById('dialog-body').textContent = message;
    document.getElementById('dialog-actions').innerHTML =
      '<button class="btn-dialog-secondary" onclick="closeDialog(false)">取消</button>' +
      '<button class="btn-dialog-primary" onclick="closeDialog(true)">确认</button>';
    dialogResolver = resolve;
    mask.classList.add('show');
  });
}

function closeDialog(result) {
  const mask = document.getElementById('dialog-mask');
  mask.classList.remove('show');
  if (dialogResolver) {
    const resolver = dialogResolver;
    dialogResolver = null;
    resolver(Boolean(result));
  }
}

function showToast(message, title = '提示', type = 'success') {
  const wrap = document.getElementById('toast-wrap');
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  toast.innerHTML =
    '<div class="toast-title">' + escapeHtml(title) + '</div>' +
    '<div class="toast-body">' + escapeHtml(message) + '</div>';
  wrap.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 220);
  }, 3200);
}

function closeAnalysis(event) {
  if (event && event.target !== document.getElementById('analysis-mask')) return;
  document.getElementById('analysis-mask').classList.remove('show');
}

function escapeHtml(s) { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

initScopes();
loadDisk();
loadPerm();
</script>
</body>
</html>
'''
