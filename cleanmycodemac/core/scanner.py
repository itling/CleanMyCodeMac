import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional
from models.scan_result import ScanResult
from utils.i18n import t
from .cleaners import (
    SystemCacheCleaner, AppCacheCleaner, LogsCleaner,
    DownloadsAnalyzer, LargeFileScanner, TrashCleaner,
    DevCacheCleaner, DocumentScanner, MediaScanner,
)

CLEANERS = [
    SystemCacheCleaner(),
    AppCacheCleaner(),
    LogsCleaner(),
    DownloadsAnalyzer(),
    LargeFileScanner(),
    TrashCleaner(),
    DevCacheCleaner(),
    DocumentScanner(),
    MediaScanner(),
]
CLEANERS_BY_CATEGORY = {cleaner.CATEGORY: cleaner for cleaner in CLEANERS}
HEAVY_SCAN_CATEGORIES = {"dev_cache", "document", "media"}

def get_category_names():
    return {c.CATEGORY: c.DISPLAY_NAME for c in CLEANERS}


def _max_workers_for(selected_categories: list[str]) -> int:
    total = len(selected_categories)
    if total <= 1:
        return 1

    heavy_count = sum(1 for category in selected_categories if category in HEAVY_SCAN_CATEGORIES)
    if heavy_count >= 2:
        return 1
    if heavy_count == 1:
        return min(2, total)
    return min(3, total)


class Scanner:
    def __init__(self):
        self._stop_event = threading.Event()

    def scan_all(
        self,
        progress_queue: queue.Queue,
        categories: Optional[list[str]] = None,
        done_callback: Optional[Callable[[ScanResult], None]] = None,
    ):
        """在后台线程中运行所有扫描器，通过 queue 推送进度"""
        def _run():
            result = ScanResult()
            selected_categories = categories or list(CLEANERS_BY_CATEGORY.keys())
            cleaners = [
                CLEANERS_BY_CATEGORY[category]
                for category in selected_categories
                if category in CLEANERS_BY_CATEGORY
            ]
            total = len(cleaners)

            if total == 0:
                progress_queue.put({
                    "type": "log",
                    "msg": t("scan.no_scope"),
                })
                progress_queue.put({"type": "done", "result": result})
                if done_callback:
                    done_callback(result)
                return

            max_workers = _max_workers_for(selected_categories)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for cleaner in cleaners:
                    if self._stop_event.is_set():
                        break
                    future = executor.submit(
                        cleaner.scan,
                        lambda d: progress_queue.put({"type": "log", "key": d["key"], "args": d.get("args", {})})
                    )
                    futures[future] = cleaner

                completed = 0
                for future in as_completed(futures):
                    if self._stop_event.is_set():
                        break
                    cleaner = futures[future]
                    completed += 1
                    try:
                        items = future.result()
                        result.extend(items)
                        progress_queue.put({
                            "type": "progress",
                            "value": int(completed / total * 100),
                            "label": t("scan.done", name=cleaner.DISPLAY_NAME),
                            "label_key": "scan.done",
                            "label_args": {"name": cleaner.DISPLAY_NAME},
                        })
                    except Exception as e:
                        progress_queue.put({
                            "type": "log",
                            "msg": t("scan.error", name=cleaner.DISPLAY_NAME, error=str(e)),
                        })

            progress_queue.put({"type": "done", "result": result})
            if done_callback:
                done_callback(result)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def stop(self):
        self._stop_event.set()
