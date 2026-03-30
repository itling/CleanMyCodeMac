from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime, timedelta
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import get_file_size
from utils.config import load_config
from utils.i18n import t

# 文件类型分类 (key is i18n key)
TYPE_MAP = {
    "dl.installer": {".dmg", ".pkg", ".mpkg"},
    "dl.archive": {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"},
    "dl.video": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"},
    "dl.image": {".iso", ".img"},
    "dl.document": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"},
}


def categorize_file(path: Path) -> str:
    ext = path.suffix.lower()
    for category, exts in TYPE_MAP.items():
        if ext in exts:
            return category
    return "dl.other"


class DownloadsAnalyzer(BaseCleaner):
    CATEGORY = "download"
    @property
    def DISPLAY_NAME(self):
        return t("cat.download")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        config = load_config()
        old_days = config.get("old_download_days", 30)
        cutoff = datetime.now() - timedelta(days=old_days)

        downloads_dir = Path.home() / "Downloads"
        items = []

        self._notify(progress_callback, "scan.download")

        if not downloads_dir.exists():
            return items

        for entry in downloads_dir.iterdir():
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                continue

            try:
                size = get_file_size(entry)
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
            except OSError:
                continue

            if size < 1024 * 100:  # 跳过 <100KB
                continue

            category_key = categorize_file(entry)
            is_old = mtime < cutoff

            desc_key = "desc.old_download" if is_old else "desc.download"
            desc_args = {"date": mtime.strftime('%Y-%m-%d')}
            items.append(ScanItem(
                path=entry,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=t(category_key),
                app_name_key=category_key,
                is_safe=is_old,
                selected=False,     # 下载文件默认不勾选，让用户决定
                last_modified=mtime,
                description=t(desc_key, **desc_args),
                description_key=desc_key,
                description_args=desc_args,
            ))

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)
