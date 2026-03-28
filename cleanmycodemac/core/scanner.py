import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional
from models.scan_result import ScanResult
from .cleaners import (
    SystemCacheCleaner, AppCacheCleaner, LogsCleaner,
    DownloadsAnalyzer, LargeFileScanner, TrashCleaner
)

CLEANERS = [
    SystemCacheCleaner(),
    AppCacheCleaner(),
    LogsCleaner(),
    DownloadsAnalyzer(),
    LargeFileScanner(),
    TrashCleaner(),
]
CLEANERS_BY_CATEGORY = {cleaner.CATEGORY: cleaner for cleaner in CLEANERS}

CATEGORY_NAMES = {
    "system_cache": "系统缓存",
    "app_cache": "应用缓存",
    "log": "日志文件",
    "download": "下载文件",
    "large_file": "大文件",
    "trash": "废纸篓",
}


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
                    "msg": "未选择扫描范围，已跳过扫描。",
                })
                progress_queue.put({"type": "done", "result": result})
                if done_callback:
                    done_callback(result)
                return

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {}
                for cleaner in cleaners:
                    if self._stop_event.is_set():
                        break
                    future = executor.submit(
                        cleaner.scan,
                        lambda msg: progress_queue.put({"type": "log", "msg": msg})
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
                            "label": f"已完成：{cleaner.DISPLAY_NAME}",
                        })
                    except Exception as e:
                        progress_queue.put({
                            "type": "log",
                            "msg": f"{cleaner.DISPLAY_NAME} 扫描出错：{e}",
                        })

            progress_queue.put({"type": "done", "result": result})
            if done_callback:
                done_callback(result)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def stop(self):
        self._stop_event.set()
