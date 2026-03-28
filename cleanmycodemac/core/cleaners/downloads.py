from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime, timedelta
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import get_file_size
from utils.config import load_config

# 文件类型分类
TYPE_MAP = {
    "安装包": {".dmg", ".pkg", ".mpkg"},
    "压缩包": {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar"},
    "视频": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"},
    "镜像": {".iso", ".img"},
    "文档": {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"},
}


def categorize_file(path: Path) -> str:
    ext = path.suffix.lower()
    for category, exts in TYPE_MAP.items():
        if ext in exts:
            return category
    return "其他"


class DownloadsAnalyzer(BaseCleaner):
    CATEGORY = "download"
    DISPLAY_NAME = "下载文件"

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        config = load_config()
        old_days = config.get("old_download_days", 30)
        cutoff = datetime.now() - timedelta(days=old_days)

        downloads_dir = Path.home() / "Downloads"
        items = []

        self._notify(progress_callback, "正在分析下载文件夹...")

        if not downloads_dir.exists():
            return items

        for entry in downloads_dir.iterdir():
            if entry.name.startswith("."):
                continue

            try:
                size = get_file_size(entry) if entry.is_file() else 0
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
            except OSError:
                continue

            if size < 1024 * 100:  # 跳过 <100KB
                continue

            category_name = categorize_file(entry) if entry.is_file() else "文件夹"
            is_old = mtime < cutoff

            items.append(ScanItem(
                path=entry,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=category_name,
                is_safe=is_old,
                selected=False,     # 下载文件默认不勾选，让用户决定
                last_modified=mtime,
                description=f"{'旧文件 ' if is_old else ''}下载于 {mtime.strftime('%Y-%m-%d')}",
            ))

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)
