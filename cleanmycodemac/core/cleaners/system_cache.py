from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import get_dir_size
from utils.config import load_config
from utils.i18n import t

# 安全可清理的系统缓存（已验证无需 FDA）
SAFE_SYSTEM_CACHES = [
    "com.apple.appstore",
    "com.apple.commerce",
    "com.apple.Bird",
    "com.apple.helpd",
    "com.apple.Maps",
    "com.apple.Music",
    "com.apple.News",
    "com.apple.Photos.PhotosUIFramework",
    "com.apple.Podcasts",
    "com.apple.QuickLookDaemon",
    "com.apple.stocks",
    "com.apple.TV",
    "com.apple.findmy",
]


class SystemCacheCleaner(BaseCleaner):
    CATEGORY = "system_cache"
    @property
    def DISPLAY_NAME(self):
        return t("cat.system_cache")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        items = []
        config = load_config()
        auto_select_safe = config.get("auto_select_safe_items", True)
        cache_root = Path.home() / "Library/Caches"

        self._notify(progress_callback, "scan.system_cache")

        if not cache_root.exists():
            return items

        for name in SAFE_SYSTEM_CACHES:
            cache_dir = cache_root / name
            if not cache_dir.exists():
                continue

            size = get_dir_size(cache_dir)
            if size < 1024 * 100:  # 跳过 <100KB
                continue

            try:
                mtime = datetime.fromtimestamp(cache_dir.stat().st_mtime)
            except OSError:
                mtime = None

            items.append(ScanItem(
                path=cache_dir,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=name.replace("com.apple.", "Apple ").title(),
                is_safe=True,
                selected=auto_select_safe,
                last_modified=mtime,
                description=t("desc.system_cache_bundle", bundle_id=name),
                description_key="desc.system_cache_bundle",
                description_args={"bundle_id": name},
            ))

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)
