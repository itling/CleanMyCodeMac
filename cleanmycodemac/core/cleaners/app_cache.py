from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import get_dir_size
from utils.config import load_config
from core.app_detector import detect_installed_apps
from utils.i18n import t

# 不清理的 bundle ID 前缀（系统级）
PROTECTED_PREFIXES = [
    "com.apple.dt",        # Xcode 衍生数据
    "com.apple.security",
    "com.apple.keychain",
]


class AppCacheCleaner(BaseCleaner):
    CATEGORY = "app_cache"
    @property
    def DISPLAY_NAME(self):
        return t("cat.app_cache")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        items = []
        auto_select_safe = load_config().get("auto_select_safe_items", True)
        cache_root = Path.home() / "Library/Caches"
        installed_apps = detect_installed_apps()

        if not cache_root.exists():
            return items

        self._notify(progress_callback, "scan.app_cache")

        for cache_dir in sorted(cache_root.iterdir()):
            if not cache_dir.is_dir():
                continue

            bundle_id = cache_dir.name

            # 跳过受保护的缓存
            if any(bundle_id.startswith(p) for p in PROTECTED_PREFIXES):
                continue

            # 确定应用名
            app_name = installed_apps.get(bundle_id, bundle_id)

            size = get_dir_size(cache_dir)
            if size < 1024 * 10:  # 跳过 <10KB 的缓存
                continue

            try:
                mtime = datetime.fromtimestamp(cache_dir.stat().st_mtime)
            except OSError:
                mtime = None

            # com.apple.* 系统缓存标记为相对安全
            is_apple = bundle_id.startswith("com.apple.")
            is_safe = not is_apple  # 第三方应用缓存更安全清理

            items.append(ScanItem(
                path=cache_dir,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=app_name,
                is_safe=is_safe,
                selected=is_safe and auto_select_safe,
                last_modified=mtime,
                description=t("desc.app_cache_bundle", bundle_id=bundle_id),
                description_key="desc.app_cache_bundle",
                description_args={"bundle_id": bundle_id},
            ))

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)
