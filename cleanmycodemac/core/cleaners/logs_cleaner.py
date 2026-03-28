from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime, timedelta
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import get_file_size
from utils.config import load_config
from utils.i18n import t

LOG_DIRS = [
    Path.home() / "Library/Logs",
    Path.home() / "Library/Logs/DiagnosticReports",
]

LOG_EXTENSIONS = {".log", ".ips", ".diag", ".crash", ".spin", ".hang"}
MIN_AGE_DAYS = 7


class LogsCleaner(BaseCleaner):
    CATEGORY = "log"
    @property
    def DISPLAY_NAME(self):
        return t("cat.log")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        items = []
        config = load_config()
        min_age_days = config.get("old_log_days", MIN_AGE_DAYS)
        auto_select_safe = config.get("auto_select_safe_items", True)
        cutoff = datetime.now() - timedelta(days=min_age_days)
        seen_paths = set()

        self._notify(progress_callback, t("scan.log"))

        for log_dir in LOG_DIRS:
            if not log_dir.exists():
                continue
            self._scan_dir(log_dir, cutoff, items, seen_paths)

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)

    def _scan_dir(self, directory: Path, cutoff: datetime, items: list, seen: set):
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if str(entry) in seen:
                continue
            seen.add(str(entry))

            if entry.is_dir():
                self._scan_dir(entry, cutoff, items, seen)
                continue

            if entry.suffix.lower() not in LOG_EXTENSIONS:
                continue

            try:
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
            except OSError:
                continue

            if mtime > cutoff:
                continue  # 7天内的日志不清理

            size = get_file_size(entry)
            if size < 1024:  # 跳过 <1KB
                continue

            # 从路径猜测应用名
            parts = entry.name.split("_")
            app_name = parts[0] if parts else entry.stem

            items.append(ScanItem(
                path=entry,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=app_name,
                is_safe=True,
                selected=auto_select_safe,
                last_modified=mtime,
                description=t("desc.log_date", date=mtime.strftime('%Y-%m-%d')),
                description_key="desc.log_date",
                description_args={"date": mtime.strftime('%Y-%m-%d')},
            ))
