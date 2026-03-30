"""CleanMyCodeMac - 本地原生窗口 UI，基于 pywebview + 内置 http.server"""

import json
import threading
import queue
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from core.scanner import Scanner, get_category_names
from core.disk_info import get_disk_info
from core.permissions import check_full_disk_access, check_trash_access, request_full_disk_access
from core.analyzer import analyze_path
from core.cleaners import (
    SystemCacheCleaner, AppCacheCleaner, LogsCleaner,
    DownloadsAnalyzer, LargeFileScanner, TrashCleaner,
    DevCacheCleaner, DocumentScanner, MediaScanner,
)
from models.scan_item import format_size
from models.scan_result import ScanResult
from utils.subprocess_utils import reveal_in_finder
from utils.i18n import get_lang, set_lang, t, STRINGS

CLEANER_MAP = {
    "system_cache": SystemCacheCleaner(),
    "app_cache":    AppCacheCleaner(),
    "log":          LogsCleaner(),
    "download":     DownloadsAnalyzer(),
    "large_file":   LargeFileScanner(),
    "trash":        TrashCleaner(),
    "dev_cache":    DevCacheCleaner(),
    "document":     DocumentScanner(),
    "media":        MediaScanner(),
}

# 全局状态
scan_result: ScanResult = None
scan_progress = {"status": "idle", "percent": 0, "label": "", "logs": []}
scan_queue = queue.Queue()
scanner = None
scan_options = {"categories": list(CLEANER_MAP.keys())}


class AppBridge:
    def __init__(self):
        self.window = None
        self._shown = False

    def bind_window(self, window):
        self.window = window

    def on_bootstrap_ready(self):
        if self.window and not self._shown:
            self.window.show()
            self._shown = True
        return {"ok": True}


def _serialize_scan_result(result: ScanResult | None):
    if not result:
        return None

    data = {}
    for cat, items in result.by_category().items():
        by_app = {}
        for item in items:
            group_key = item.app_name_key or item.app_name
            by_app.setdefault(group_key, []).append(item)

        sub_groups = []
        for group_key, app_items in by_app.items():
            app_size = sum(x.size_bytes for x in app_items)
            app_selected = sum(x.size_bytes for x in app_items if x.selected)
            all_safe = all(x.is_safe for x in app_items)
            any_selected = any(x.selected for x in app_items)
            all_selected = all(x.selected for x in app_items)
            first_item = app_items[0]
            app_name = (
                t(first_item.app_name_key, **first_item.app_name_args)
                if first_item.app_name_key else first_item.app_name
            )
            description = (
                t(first_item.description_key, **first_item.description_args)
                if first_item.description_key else first_item.description
            )
            files = [{
                "path": str(x.path),
                "path_short": x.path_str,
                "size": x.size_bytes,
                "size_display": x.size_display,
                "selected": x.selected,
                "is_safe": x.is_safe,
                "can_analyze": x.category == "large_file",
                "description": t(x.description_key, **x.description_args) if x.description_key else x.description,
            } for x in app_items]
            sub_groups.append({
                "app_name": app_name,
                "description": description,
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
            "name": get_category_names().get(cat, cat),
            "size": cat_size,
            "size_display": format_size(cat_size),
            "selected_size": cat_selected,
            "selected_display": format_size(cat_selected),
            "any_selected": any(i.selected for i in items),
            "all_selected": all(i.selected for i in items),
            "sub_groups": sub_groups,
        }

    # 计算去重后的总大小：
    # 1. 相同路径只计一次（同一文件被多个扫描器发现）
    # 2. 若某路径是已统计目录的子路径，则跳过（目录大小已包含其下文件，不重复叠加）
    #    例：DevCacheCleaner 上报 DerivedData(50GB)，LargeFileScanner 又发现其内的 .a 文件(2GB)
    items_by_depth = sorted(result.items, key=lambda i: str(i.path).count('/'))
    counted: list[str] = []
    total = 0
    for i in items_by_depth:
        p = str(i.path)
        if p in counted:
            continue
        if any(p.startswith(parent + '/') for parent in counted):
            continue
        counted.append(p)
        total += i.size_bytes
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
    scan_progress["label"] = t("ui.init")
    scan_progress["label_key"] = "ui.init"
    scan_progress["label_args"] = {}
    scan_progress["logs"] = []
    scan_queue = queue.Queue()
    scanner = Scanner()

    def on_done(result):
        global scan_result
        scan_result = result
        scan_progress["status"] = "done"
        scan_progress["percent"] = 100
        scan_progress["label"] = t("ui.scan_done")

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
                    scan_progress["label_key"] = msg.get("label_key", "")
                    scan_progress["label_args"] = msg.get("label_args", {})
                elif t == "log":
                    scan_progress["logs"].append({"key": msg.get("key", ""), "args": msg.get("args", {})})
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
            self._json({"fda": check_full_disk_access(), "trash": check_trash_access()})
        elif path == "/api/lang":
            self._json({"lang": get_lang(), "strings": STRINGS.get(get_lang(), {})})
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
                self._json({"error": t("error.no_selection")})
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
                self._json({"ok": False, "error": t("error.missing_path")})
                return
            self._json({"ok": reveal_in_finder(target)})
        elif path == "/api/analyze":
            target = body.get("path")
            if not target:
                self._json({"error": t("error.missing_path")})
                return
            self._json(analyze_path(target))
        elif path == "/api/perm/open":
            request_full_disk_access()
            self._json({"ok": True})
        elif path == "/api/lang":
            lang = body.get("lang", "zh")
            set_lang(lang, save=True)
            self._json({"lang": get_lang(), "strings": STRINGS.get(get_lang(), {})})
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
    print(f"CleanMyCodeMac backend started: http://127.0.0.1:{port}")

    bridge = AppBridge()
    window = webview.create_window(
        "CleanMyCodeMac",
        f"http://127.0.0.1:{port}",
        js_api=bridge,
        width=1120,
        height=720,
        min_size=(800, 500),
        hidden=True,
        background_color="#0F172A",
    )
    bridge.bind_window(window)

    webview.start()
    print("Exited")
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
.lang-switch { margin-top: auto; margin-bottom: 8px; display: flex; gap: 4px; }
.lang-btn { flex: 1; padding: 5px 0; border: 1px solid #475569; background: transparent; color: #94A3B8; border-radius: 6px; font-size: 11px; cursor: pointer; transition: all 0.15s; }
.lang-btn:hover { background: rgba(255,255,255,0.06); }
.lang-btn.active { background: rgba(255,255,255,0.12); color: #F1F5F9; border-color: #64748B; }
.version { font-size: 10px; color: #475569; text-align: center; line-height: 1.7; }
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
.scan-log { width: 440px; background: #FAFAFA; border: 1px solid #E8E8E8; border-radius: 8px; padding: 10px 12px; font-size: 11px; font-family: "Menlo", monospace; color: #999; white-space: pre-wrap; line-height: 1.8; overflow: hidden; }

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
.startup-screen { position: fixed; inset: 0; z-index: 60; background:
  radial-gradient(circle at top, rgba(249,115,22,0.22), transparent 35%),
  linear-gradient(145deg, #0F172A 0%, #111827 45%, #1E293B 100%);
  color: #F8FAFC; display: flex; align-items: center; justify-content: center;
  transition: opacity 0.35s ease, visibility 0.35s ease; }
.startup-screen.hidden { opacity: 0; visibility: hidden; pointer-events: none; display: flex; }
.startup-card { width: min(420px, calc(100vw - 48px)); text-align: center; }
.startup-orb { width: 96px; height: 96px; margin: 0 auto 20px; border-radius: 28px;
  background: linear-gradient(145deg, rgba(249,115,22,0.95), rgba(251,146,60,0.82));
  box-shadow: 0 20px 50px rgba(249,115,22,0.28), inset 0 1px 0 rgba(255,255,255,0.25);
  position: relative; display: flex; align-items: center; justify-content: center; }
.startup-orb::after { content: ''; width: 54px; height: 54px; border-radius: 18px;
  border: 3px solid rgba(255,255,255,0.9); box-sizing: border-box; }
.startup-glow { position: absolute; inset: -14px; border-radius: 34px; border: 1px solid rgba(251,146,60,0.28);
  animation: startupPulse 1.8s ease-in-out infinite; }
.startup-title { font-size: 26px; font-weight: 700; letter-spacing: 0.01em; margin-bottom: 10px; }
.startup-subtitle { font-size: 14px; line-height: 1.7; color: #CBD5E1; margin-bottom: 20px; }
.startup-bar { width: 220px; max-width: 100%; height: 6px; margin: 0 auto 12px; border-radius: 999px;
  overflow: hidden; background: rgba(148,163,184,0.18); }
.startup-bar-fill { width: 38%; height: 100%;
  background: linear-gradient(90deg, rgba(249,115,22,0.1), #F97316, #FDBA74, rgba(249,115,22,0.1));
  animation: startupSweep 1.5s ease-in-out infinite; }
.startup-caption { font-size: 12px; color: #94A3B8; letter-spacing: 0.08em; text-transform: uppercase; }
@keyframes startupSweep {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(420%); }
}
@keyframes startupPulse {
  0%, 100% { transform: scale(0.98); opacity: 0.5; }
  50% { transform: scale(1.03); opacity: 1; }
}
</style>
</head>
<body>
<div id="startup-screen" class="startup-screen">
  <div class="startup-card">
    <div class="startup-orb">
      <div class="startup-glow"></div>
    </div>
    <div class="startup-title">CleanMyCodeMac</div>
    <div class="startup-subtitle">Inspecting local storage, preparing cleanup tools, and loading the desktop shell.</div>
    <div class="startup-bar"><div class="startup-bar-fill"></div></div>
    <div class="startup-caption">Starting Up</div>
  </div>
</div>
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
        <div class="gauge-label" id="gauge-label"></div>
      </div>
    </div>
    <div class="disk-info" id="disk-info"></div>
    <div class="perm-status" id="perm-status"></div>
    <div class="lang-switch" id="lang-switch"></div>
    <div class="version">
      <span class="about-label" id="about-label"></span>
      <div><span id="author-label"></span>: killy</div>
      <div><span id="email-label"></span>: 3168582@qq.com</div>
      <div><span id="version-label"></span>: v1.0.0</div>
    </div>
  </div>

  <div class="main">
    <!-- 首页 -->
    <div id="view-home">
      <div class="hero">
        <h1>CleanMyCodeMac</h1>
        <p id="hero-desc"></p>
        <div class="hero-actions">
          <button class="btn-scan" id="btn-start-scan" onclick="startScan()"></button>
          <button class="btn-ghost" id="btn-select-all" onclick="selectAllScopes(true)"></button>
          <button class="btn-ghost" id="btn-clear-all" onclick="selectAllScopes(false)"></button>
        </div>
      </div>
      <div class="scope-head">
        <div class="cards-title" id="scope-title"></div>
        <div class="scope-summary" id="scope-summary"></div>
      </div>
      <div class="cards" id="scope-cards"></div>
    </div>

    <div id="view-scan" class="hidden">
      <div class="scan-view">
        <div class="spinner"></div>
        <div class="scan-title" id="scan-title"></div>
        <div class="scan-sub" id="scan-label"></div>
        <div class="scan-scope"><span class="scan-scope-label" id="scan-scope-label"></span><span class="scan-scope-value" id="scan-scope"></span></div>
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
          <h2><span id="result-found-label"></span> <span id="result-total">--</span></h2>
          <div class="sel"><span id="result-selected-label"></span> <strong id="result-selected">--</strong></div>
        </div>
        <div class="result-actions">
          <button class="btn-back" id="btn-back" onclick="showView('home')"></button>
          <button class="btn-lite" id="btn-select-result" onclick="toggleAllResultSelection(true)"></button>
          <button class="btn-lite" id="btn-deselect-result" onclick="toggleAllResultSelection(false)"></button>
          <button class="btn-clean" id="btn-clean" onclick="doClean()"></button>
        </div>
      </div>
      <div class="cat-list" id="cat-list"></div>
    </div>
  </div>
</div>

<div id="analysis-mask" class="analysis-mask" onclick="closeAnalysis(event)">
  <div class="analysis-panel" onclick="event.stopPropagation()">
    <div class="analysis-head">
      <h3 id="analysis-title"></h3>
      <button class="analysis-close" onclick="closeAnalysis()">&times;</button>
    </div>
    <div class="analysis-body" id="analysis-body"></div>
  </div>
</div>

<div id="dialog-mask" class="dialog-mask" onclick="closeDialog(false)">
  <div class="dialog-panel" onclick="event.stopPropagation()">
    <div class="dialog-head"><div class="dialog-title" id="dialog-title"></div></div>
    <div class="dialog-body" id="dialog-body"></div>
    <div class="dialog-actions" id="dialog-actions"></div>
  </div>
</div>

<div id="toast-wrap" class="toast-wrap"></div>

<script>
/* ── i18n ── */
const UI = {
  zh: {
    used: '已使用', loading: '加载中...', heroDesc: '扫描并清理 Mac 上的垃圾文件，快速释放磁盘空间',
    startScan: '开始扫描', selectAll: '全选', clearAll: '清空',
    scopeTitle: '扫描范围', scopeSummary: '已选择 {n} / {t} 项',
    scanning: '正在扫描...', initializing: '初始化中...', scopeLabel: '范围',
    scanDone: '已完成：{name}', scanError: '{name} 扫描出错',
    scanKeys: {'ui.init':'初始化中...','scan.system_cache':'正在扫描系统缓存...','scan.app_cache':'正在扫描应用缓存...','scan.log':'正在扫描日志文件...','scan.download':'正在分析下载文件夹...','scan.large_file':'正在搜索大文件...','scan.trash':'正在检查废纸篓...','scan.dev_cache':'正在扫描编程工具与语言缓存...','scan.ai_models':'正在扫描大模型文件...','scan.document':'正在扫描文档文件...','scan.media':'正在扫描媒体文件...','scan.done':'已完成：{name}','scan.error':'{name} 扫描出错'},
    foundFiles: '共发现可清理文件', selectedJunk: '已选择垃圾',
    back: '返回', selectResult: '全选结果', deselectResult: '取消全选', cleanNow: '立即清理',
    cleaning: '清理中...', cleanDone: '清理完成', cleanFreed: '清理完成，释放了 {size}',
    cleanFailed: '{n} 个项目失败',
    permOk: '&#10003; 完全磁盘访问已授权', permWarn: '&#9888; 未授权完全磁盘访问',
    permTrashWarn: '废纸篓访问未授权', permPartialWarn: '部分受保护目录未授权',
    permOpen: '打开授权设置',
    diskFree: '可用',
    badgeClean: '很干净', badgeSafe: '建议清理', badgeWarn: '谨慎清理',
    expandFiles: '展开文件列表', open: '打开', analyze: '分析',
    catTotal: '共 {size}，已选择', analysisTitle: '占用分析', analyzing: '正在分析，请稍候...',
    analysisConclusion: '分析结论', sameLevelUsage: '同级目录占用', treeView: '树状占用视图',
    upperDir: '上层目录：', dirType: '目录', fileType: '文件', percent: '占比',
    finder: 'Finder', drillDown: '深入分析', copied: '已复制', copyCmd: '复制命令',
    copyFail: '复制失败，请手动复制命令', copyFailTitle: '复制失败',
    noAnalysis: '没有可展示的分析数据。', suggestedActions: '建议动作',
    dockerNoResult: '未获取到 Docker CLI 结果，可能是 Docker 未启动或命令不可用。',
    hint: '提示', gotIt: '知道了', confirm: '请确认', cancel: '取消', ok: '确认',
    about: '关于', author: '作者', email: '邮箱', version: '版本', langZh: '中文', langEn: 'EN',
    alertNoScope: '请至少勾选一个扫描范围', alertNoScopeTitle: '扫描范围为空',
    alertNoItem: '请先勾选要清理的项目', alertNoItemTitle: '未选择项目',
    confirmClean: '即将清理 {n} 个项目。\n缓存/日志等安全项目将直接删除并释放磁盘空间；文档/媒体等项目将移入废纸篓（可恢复）。确认继续？', confirmCleanTitle: '确认清理',
    confirmCleanTrash: '即将永久删除 {n} 个废纸篓项目。\n删除后不可恢复，确认继续？', confirmCleanTrashTitle: '确认永久删除',
    catName: {
      system_cache: '系统垃圾', app_cache: '应用垃圾', log: '日志文件',
      download: '下载文件', large_file: '大文件', trash: '废纸篓',
      dev_cache: '编程缓存', document: '文档文件', media: '媒体文件',
    },
    catDesc: {
      system_cache: 'macOS 系统应用产生的临时缓存', app_cache: 'Chrome、VSCode 等 App 缓存',
      log: '7 天以上的崩溃报告与运行日志', download: '下载文件夹旧文件分析',
      large_file: '搜索 500MB 以上的大文件并分析占用', trash: '立即清空废纸篓释放空间',
      dev_cache: 'Node、Rust、Java 等语言缓存与 IDE 缓存', document: '扫描主目录下的文档文件', media: '扫描主目录下的图片、音频、视频',
    },
  },
  en: {
    used: 'Used', loading: 'Loading...', heroDesc: 'Scan and clean junk files on your Mac to free up disk space',
    startScan: 'Start Scan', selectAll: 'Select All', clearAll: 'Clear',
    scopeTitle: 'Scan Scope', scopeSummary: '{n} / {t} selected',
    scanning: 'Scanning...', initializing: 'Initializing...', scopeLabel: 'Scope',
    scanDone: 'Done: {name}', scanError: '{name} scan error',
    scanKeys: {'ui.init':'Initializing...','scan.system_cache':'Scanning system cache...','scan.app_cache':'Scanning app cache...','scan.log':'Scanning log files...','scan.download':'Analyzing downloads folder...','scan.large_file':'Searching large files...','scan.trash':'Checking trash...','scan.dev_cache':'Scanning dev tools & language caches...','scan.ai_models':'Scanning AI model files...','scan.document':'Scanning document files...','scan.media':'Scanning media files...','scan.done':'Done: {name}','scan.error':'{name} scan error'},
    foundFiles: 'Cleanable files found', selectedJunk: 'Selected',
    back: 'Back', selectResult: 'Select All', deselectResult: 'Deselect All', cleanNow: 'Clean Now',
    cleaning: 'Cleaning...', cleanDone: 'Clean Complete', cleanFreed: 'Cleaned, freed {size}',
    cleanFailed: '{n} items failed',
    permOk: '&#10003; Full Disk Access granted', permWarn: '&#9888; Full Disk Access not granted',
    permTrashWarn: 'Trash access not granted', permPartialWarn: 'Protected folders partially not granted',
    permOpen: 'Open Settings',
    diskFree: 'free',
    badgeClean: 'Clean', badgeSafe: 'Safe to clean', badgeWarn: 'Use caution',
    expandFiles: 'Expand file list', open: 'Open', analyze: 'Analyze',
    catTotal: 'Total {size}, selected', analysisTitle: 'Usage Analysis', analyzing: 'Analyzing, please wait...',
    analysisConclusion: 'Analysis', sameLevelUsage: 'Same-level Usage', treeView: 'Tree View',
    upperDir: 'Parent dir: ', dirType: 'Directory', fileType: 'File', percent: 'Ratio',
    finder: 'Finder', drillDown: 'Drill Down', copied: 'Copied', copyCmd: 'Copy Command',
    copyFail: 'Copy failed, please copy manually', copyFailTitle: 'Copy Failed',
    noAnalysis: 'No analysis data available.', suggestedActions: 'Suggested Actions',
    dockerNoResult: 'Docker CLI result not available. Docker may not be running.',
    hint: 'Notice', gotIt: 'OK', confirm: 'Confirm', cancel: 'Cancel', ok: 'Confirm',
    about: 'About', author: 'Author', email: 'Email', version: 'Version', langZh: '中文', langEn: 'EN',
    alertNoScope: 'Please select at least one scan scope', alertNoScopeTitle: 'No Scope Selected',
    alertNoItem: 'Please select items to clean', alertNoItemTitle: 'No Items Selected',
    confirmClean: 'About to clean {n} items.\nSafe items (caches/logs) will be permanently deleted to free disk space. Documents/media will be moved to Trash (recoverable). Continue?', confirmCleanTitle: 'Confirm Clean',
    confirmCleanTrash: 'About to permanently delete {n} trash items.\nThis action cannot be undone. Continue?', confirmCleanTrashTitle: 'Confirm Permanent Delete',
    catName: {
      system_cache: 'System Junk', app_cache: 'App Junk', log: 'Log Files',
      download: 'Downloads', large_file: 'Large Files', trash: 'Trash',
      dev_cache: 'Dev Cache', document: 'Documents', media: 'Media',
    },
    catDesc: {
      system_cache: 'Temporary cache from macOS system apps', app_cache: 'Cache from Chrome, VSCode, etc.',
      log: 'Crash reports and logs older than 7 days', download: 'Old files in Downloads folder',
      large_file: 'Search for files larger than 500MB', trash: 'Empty Trash to free space',
      dev_cache: 'Node, Rust, Java language & IDE caches', document: 'Scan document files under Home', media: 'Scan images, audio and video under Home',
    },
  },
};
let currentLang = 'zh';
function T(key) { return (UI[currentLang] || UI.en)[key] || key; }
function catName(cat) { const d = (UI[currentLang] || UI.en).catName; return d[cat] || cat; }
function catDesc(cat) { const d = (UI[currentLang] || UI.en).catDesc; return d[cat] || ''; }

const CAT_CFG = {
  system_cache: { icon: '&#9881;', color: '#F97316', bg: '#FFF7ED' },
  app_cache:    { icon: '&#9638;', color: '#3B82F6', bg: '#EFF6FF' },
  log:          { icon: '&#9776;', color: '#8B5CF6', bg: '#F5F3FF' },
  download:     { icon: '&#8595;', color: '#10B981', bg: '#ECFDF5' },
  large_file:   { icon: '&#9650;', color: '#EF4444', bg: '#FEF2F2' },
  trash:        { icon: '&#9003;', color: '#6B7280', bg: '#F3F4F6' },
  dev_cache:    { icon: '&#128187;', color: '#0EA5E9', bg: '#F0F9FF' },
  document:     { icon: '&#128196;', color: '#D97706', bg: '#FFFBEB' },
  media:        { icon: '&#127912;', color: '#EC4899', bg: '#FDF2F8' },
};
const CAT_ORDER = ['system_cache', 'log', 'app_cache', 'dev_cache', 'download', 'document', 'media', 'large_file', 'trash'];

let resultData = null;
let scanSelections = {};
let currentScanCategories = [];
let dialogResolver = null;
let lastKnownLogs = [];
const startupStartedAt = Date.now();

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
      '<h3>' + catName(cat) + '</h3>' +
      '<p>' + catDesc(cat) + '</p>';
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
  document.getElementById('scope-summary').textContent = T('scopeSummary').replace('{n}', selected.length).replace('{t}', CAT_ORDER.length);
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
  arc.style.stroke = pct < 70 ? '#10B981' : pct <= 90 ? '#F59E0B' : '#EF4444';
  const usedG = (r.used / 1073741824).toFixed(1);
  const totalG = (r.total / 1073741824).toFixed(1);
  const freeG = (r.free / 1073741824).toFixed(1);
  document.getElementById('disk-info').textContent = usedG + 'G / ' + totalG + 'G (' + T('diskFree') + ' ' + freeG + 'G)';
}

async function loadPerm() {
  const r = await fetch('/api/perm').then(r => r.json());
  const el = document.getElementById('perm-status');
  if (r.fda && r.trash) {
    el.innerHTML = '<span class="perm-ok">' + T('permOk') + '</span>';
    return;
  }
  const warnText = !r.trash ? T('permTrashWarn') : T('permPartialWarn');
  el.innerHTML =
    '<span class="perm-warn">&#9888; ' + warnText + '</span>' +
    '<div><button class="perm-action" onclick="openPermissionSettings()">' + T('permOpen') + '</button></div>';
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
    await showAlert(T('alertNoScope'), T('alertNoScopeTitle'));
    return;
  }
  currentScanCategories = categories;
  showView('scan');
  document.getElementById('scan-title').textContent = T('scanning');
  document.getElementById('scan-bar').style.width = '0%';
  document.getElementById('scan-pct').textContent = '0%';
  document.getElementById('scan-label').textContent = T('initializing');
  lastKnownLogs = [];
  document.getElementById('scan-log').textContent = '';
  document.getElementById('scan-scope-label').textContent = T('scopeLabel');
  document.getElementById('scan-scope').textContent = currentScanCategories.map(cat => catName(cat)).join(currentLang === 'zh' ? '、' : ', ');
  await postJson('/api/scan/start', { categories });
  pollProgress();
}

async function pollProgress() {
  const r = await fetch('/api/scan/progress').then(r => r.json());
  document.getElementById('scan-bar').style.width = r.percent + '%';
  document.getElementById('scan-pct').textContent = r.percent + '%';
  // 优先用前端自己的 i18n 翻译，切换语言后立即生效
  const scanKeys = T('scanKeys') || {};
  let labelText = r.label;
  if (r.label_key && scanKeys[r.label_key]) {
    let tpl = scanKeys[r.label_key];
    const args = r.label_args || {};
    Object.keys(args).forEach(k => { tpl = tpl.replace('{' + k + '}', args[k]); });
    labelText = tpl;
  }
  document.getElementById('scan-label').textContent = labelText;
  lastKnownLogs = r.logs || [];
  renderScanLog();
  document.getElementById('scan-log').scrollTop = document.getElementById('scan-log').scrollHeight;
  if (r.status === 'done') { setTimeout(loadResult, 400); }
  else { setTimeout(pollProgress, 200); }
}

function renderScanLog() {
  const logScanKeys = T('scanKeys') || {};
  const logEl = document.getElementById('scan-log');
  if (!logEl) return;
  logEl.textContent = lastKnownLogs.map(l => {
    let text = l.key && logScanKeys[l.key] ? logScanKeys[l.key] : (l.key || '');
    const args = l.args || {};
    Object.keys(args).forEach(k => { text = text.replace('{' + k + '}', args[k]); });
    return '\u25b8 ' + text;
  }).join('\n');
}

function safetyBadge(is_safe, size) {
  if (size === 0) return '<span class="badge-clean">' + T('badgeClean') + '</span>';
  if (is_safe) return '<span class="badge badge-safe">' + T('badgeSafe') + '</span>';
  return '<span class="badge badge-warn">' + T('badgeWarn') + '</span>';
}

async function loadResult(showResultView = true) {
  resultData = await fetch('/api/scan/result').then(r => r.json());
  if (!resultData) return;
  renderResult();
  if (showResultView) showView('result');
  await loadDisk();
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
    const cfg = CAT_CFG[cat] || { icon: '?', color: '#999', bg: '#F5F5F5' };

    const group = document.createElement('div');
    group.className = 'cat-group';
    group.dataset.cat = cat;

    const header = document.createElement('div');
    header.className = 'cat-header';
    header.innerHTML =
      '<input type="checkbox" class="cat-check"' + (data.all_selected ? ' checked' : '') + '>' +
      '<div class="cat-icon" style="background:' + cfg.bg + ';color:' + cfg.color + '">' + cfg.icon + '</div>' +
      '<span class="cat-name" style="color:' + cfg.color + '">' + catName(cat) + '</span>' +
      '<span class="cat-meta">&nbsp;&nbsp;' + T('catTotal').replace('{size}', data.size_display) + ' <span class="sel-size cat-sel-size">' + data.selected_display + '</span></span>' +
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

    if (cat === 'trash') {
      for (const sg of data.sub_groups) {
        for (const f of sg.files) {
          const frow = document.createElement('div');
          frow.className = 'file-row';
          frow.innerHTML =
            '<input type="checkbox" class="file-cb"' + (f.selected ? ' checked' : '') +
            ' data-path="' + escapeHtml(f.path) + '">' +
            '<div class="file-path-wrap">' +
              '<div class="file-path" title="' + escapeHtml(f.path) + '">' + escapeHtml(f.path_short) + '</div>' +
              '<div class="file-hint">' + escapeHtml(f.description || '') + '</div>' +
            '</div>' +
            '<span class="file-size">' + f.size_display + '</span>' +
            '<span class="file-actions">' +
              '<button class="btn-mini" data-action="reveal" data-path="' + escapeHtml(f.path) + '">' + T('open') + '</button>' +
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
              await postJson('/api/reveal', { path: btn.dataset.path });
            });
          });
          body.appendChild(frow);
        }
      }
      group.appendChild(header);
      group.appendChild(body);
      list.appendChild(group);
      continue;
    }

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
          '<span class="sub-toggle" title="' + T('expandFiles') + '">&#9660;</span>' +
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
            '<button class="btn-mini" data-action="reveal" data-path="' + escapeHtml(f.path) + '">' + T('open') + '</button>' +
            (f.can_analyze ? '<button class="btn-mini" data-action="analyze" data-path="' + escapeHtml(f.path) + '">' + T('analyze') + '</button>' : '') +
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
  let hasTrashItems = false;
  if (resultData) {
    for (const cat of CAT_ORDER) {
      const data = resultData.categories[cat];
      if (!data) continue;
      for (const sg of data.sub_groups) {
        for (const f of sg.files) {
          if (f.selected && !paths.includes(f.path)) {
            paths.push(f.path);
            if (cat === 'trash') hasTrashItems = true;
          }
        }
      }
    }
  }
  const uniquePaths = paths;

  if (uniquePaths.length === 0) {
    await showAlert(T('alertNoItem'), T('alertNoItemTitle'));
    return;
  }
  const confirmed = await showConfirm(
    (hasTrashItems ? T('confirmCleanTrash') : T('confirmClean')).replace('{n}', uniquePaths.length),
    hasTrashItems ? T('confirmCleanTrashTitle') : T('confirmCleanTitle')
  );
  if (!confirmed) return;

  const btn = document.getElementById('btn-clean');
  btn.disabled = true;
  btn.textContent = T('cleaning');

  const r = await fetch('/api/clean', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({paths: uniquePaths})
  }).then(r => r.json());

  let msg = T('cleanFreed').replace('{size}', r.freed);
  if (r.errors > 0) msg += '\n\n' + T('cleanFailed').replace('{n}', r.errors);
  showToast(msg, T('cleanDone'), 'success');
  btn.disabled = false;
  btn.textContent = T('cleanNow');
  await new Promise(resolve => setTimeout(resolve, 600));
  await loadDisk();
  startScan();
}

async function openAnalysis(path) {
  const mask = document.getElementById('analysis-mask');
  const title = document.getElementById('analysis-title');
  const body = document.getElementById('analysis-body');
  title.textContent = T('analysisTitle');
  body.innerHTML = '<div class="analysis-note">' + T('analyzing') + '</div>';
  mask.classList.add('show');

  const data = await postJson('/api/analyze', { path });
  if (data.error) {
    title.textContent = T('analysisTitle');
    body.innerHTML = '<div class="analysis-note">' + escapeHtml(data.error) + '</div>';
    return;
  }

  title.textContent = data.name + ' · ' + data.size_display;

  const sections = [];
  if (data.highlights) {
    sections.push(
      '<div class="analysis-section"><h4>' + T('analysisConclusion') + '</h4>' +
      data.highlights.map(line => '<div class="analysis-note">' + escapeHtml(line) + '</div>').join('') +
      '</div>'
    );
  }

  if (data.same_level_items && data.same_level_items.length) {
    sections.push(renderAnalysisList(T('sameLevelUsage'), data.same_level_items));
  }

  if (data.tree) {
    sections.push(renderAnalysisTree(T('treeView'), data.tree));
  }

  if (data.ancestor_levels && data.ancestor_levels.length) {
    data.ancestor_levels.forEach(level => {
      if (level.children && level.children.length) {
        sections.push(renderAnalysisList(T('upperDir') + level.path, level.children));
      }
    });
  }

  if (data.special && data.special.kind === 'docker_raw') {
    sections.push(
      '<div class="analysis-section"><h4>' + escapeHtml(data.special.title) + '</h4>' +
      data.special.highlights.map(line => '<div class="analysis-note">' + escapeHtml(line) + '</div>').join('') +
      (data.special.docker_summary && data.special.docker_summary.length
        ? '<div class="analysis-chip-row">' + data.special.docker_summary.map(item =>
            '<div class="analysis-chip">' + escapeHtml(item.label) + ': ' + escapeHtml(item.value) + '</div>'
          ).join('') + '</div>'
        : '') +
      (data.special.suggestions && data.special.suggestions.length
        ? '<div class="analysis-section"><h4>' + T('suggestedActions') + '</h4>' +
          data.special.suggestions.map(item =>
            '<div class="analysis-cmd">' +
              '<div class="analysis-cmd-title">' + escapeHtml(item.label) + '</div>' +
              '<div class="analysis-cmd-desc">' + escapeHtml(item.description) + '</div>' +
              '<div class="analysis-cmd-code">' + escapeHtml(item.command) + '</div>' +
              '<div class="analysis-cmd-actions">' +
                '<button class="btn-mini" data-copy="' + escapeHtml(item.command) + '">' + T('copyCmd') + '</button>' +
              '</div>' +
            '</div>'
          ).join('') +
          '</div>'
        : '') +
      (data.special.docker_cli_available
        ? '<div class="analysis-pre">' + escapeHtml(data.special.docker_df_lines.join('\n')) + '</div>'
        : '<div class="analysis-note">' + T('dockerNoResult') + '</div>') +
      '</div>'
    );
  }

  body.innerHTML = sections.join('') || '<div class="analysis-note">' + T('noAnalysis') + '</div>';
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
        '<div class="tree-meta">' + escapeHtml(node.kind === 'dir' ? T('dirType') : T('fileType')) + ' · ' + T('percent') + ' ' + escapeHtml(node.percent) + '</div>' +
      '</div>' +
      '<div class="tree-actions">' +
        '<button class="btn-mini" data-reveal="' + escapeHtml(node.path) + '">' + T('finder') + '</button>' +
        (node.can_drill ? '<button class="btn-mini" data-drill="' + escapeHtml(node.path) + '">' + T('drillDown') + '</button>' : '') +
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
        btn.textContent = T('copied');
        setTimeout(() => { btn.textContent = T('copyCmd'); }, 1200);
      } catch (_) {
        showAlert(T('copyFail'), T('copyFailTitle'));
      }
    });
  });
}

function showAlert(message, title) {
  title = title || T('hint');
  return new Promise(resolve => {
    const mask = document.getElementById('dialog-mask');
    document.getElementById('dialog-title').textContent = title;
    document.getElementById('dialog-body').textContent = message;
    document.getElementById('dialog-actions').innerHTML =
      '<button class="btn-dialog-primary" onclick="closeDialog(true)">' + T('gotIt') + '</button>';
    dialogResolver = resolve;
    mask.classList.add('show');
  });
}

function showConfirm(message, title) {
  title = title || T('confirm');
  return new Promise(resolve => {
    const mask = document.getElementById('dialog-mask');
    document.getElementById('dialog-title').textContent = title;
    document.getElementById('dialog-body').textContent = message;
    document.getElementById('dialog-actions').innerHTML =
      '<button class="btn-dialog-secondary" onclick="closeDialog(false)">' + T('cancel') + '</button>' +
      '<button class="btn-dialog-primary" onclick="closeDialog(true)">' + T('ok') + '</button>';
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

function showToast(message, title, type) {
  title = title || T('hint');
  type = type || 'success';
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

async function notifyBootstrapReady() {
  const startedAt = Date.now();
  while (Date.now() - startedAt < 4000) {
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.on_bootstrap_ready) {
        await window.pywebview.api.on_bootstrap_ready();
        return;
      }
    } catch (_) {}
    await new Promise(resolve => setTimeout(resolve, 50));
  }
}

async function hideStartupScreen() {
  const minVisibleMs = 650;
  const elapsed = Date.now() - startupStartedAt;
  if (elapsed < minVisibleMs) {
    await new Promise(resolve => setTimeout(resolve, minVisibleMs - elapsed));
  }
  const startup = document.getElementById('startup-screen');
  startup.classList.add('hidden');
}

function renderLangSwitch() {
  const el = document.getElementById('lang-switch');
  el.innerHTML =
    '<button class="lang-btn' + (currentLang === 'zh' ? ' active' : '') + '" onclick="switchLang(\'zh\')">' + T('langZh') + '</button>' +
    '<button class="lang-btn' + (currentLang === 'en' ? ' active' : '') + '" onclick="switchLang(\'en\')">' + T('langEn') + '</button>';
}

function applyLang() {
  renderLangSwitch();
  document.getElementById('gauge-label').textContent = T('used');
  document.getElementById('disk-info').textContent = T('loading');
  document.getElementById('hero-desc').textContent = T('heroDesc');
  document.getElementById('btn-start-scan').textContent = T('startScan');
  document.getElementById('btn-select-all').textContent = T('selectAll');
  document.getElementById('btn-clear-all').textContent = T('clearAll');
  document.getElementById('scope-title').textContent = T('scopeTitle');
  document.getElementById('scan-title').textContent = T('scanning');
  document.getElementById('scan-scope-label').textContent = T('scopeLabel');
  if (currentScanCategories.length > 0) {
    document.getElementById('scan-scope').textContent = currentScanCategories.map(cat => catName(cat)).join(currentLang === 'zh' ? '、' : ', ');
  }
  const scanViewVisible = !document.getElementById('view-scan').classList.contains('hidden');
  if (scanViewVisible) {
    renderScanLog();
  }
  document.getElementById('result-found-label').textContent = T('foundFiles');
  document.getElementById('result-selected-label').textContent = T('selectedJunk');
  document.getElementById('btn-back').textContent = T('back');
  document.getElementById('btn-select-result').textContent = T('selectResult');
  document.getElementById('btn-deselect-result').textContent = T('deselectResult');
  document.getElementById('btn-clean').textContent = T('cleanNow');
  document.getElementById('about-label').textContent = T('about');
  document.getElementById('author-label').textContent = T('author');
  document.getElementById('email-label').textContent = T('email');
  document.getElementById('version-label').textContent = T('version');
  renderScopeCards();
  loadDisk();
  loadPerm();
  if (resultData) renderResult();
}

async function switchLang(lang) {
  currentLang = lang;
  await postJson('/api/lang', { lang: lang });
  applyLang();
  const resultViewVisible = !document.getElementById('view-result').classList.contains('hidden');
  if (resultData && resultViewVisible) {
    await loadResult(false);
  }
}

async function initLang() {
  const r = await fetch('/api/lang').then(r => r.json());
  currentLang = r.lang || 'zh';
}

initLang().then(() => {
  applyLang();
  initScopes();
  loadDisk();
  loadPerm();
  notifyBootstrapReady();
  hideStartupScreen();
});
</script>
</body>
</html>
'''
