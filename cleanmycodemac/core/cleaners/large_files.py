from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import mdfind_large_files, get_file_size
from utils.config import load_config

# 不扫描的目录前缀
EXCLUDED_PREFIXES = [
    "/System",
    "/Library",
    "/private",
    "/usr",
    "/bin",
    "/sbin",
    "/Applications",
]


class LargeFileScanner(BaseCleaner):
    CATEGORY = "large_file"
    DISPLAY_NAME = "大文件"

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        config = load_config()
        threshold_bytes = config.get("large_file_threshold_mb", 500) * 1024 * 1024

        self._notify(progress_callback, f"正在搜索大文件（>{config['large_file_threshold_mb']}MB）...")

        home = str(Path.home())
        file_paths = mdfind_large_files(
            min_bytes=threshold_bytes,
            root=home
        )

        items = []
        for p_str in file_paths:
            path = Path(p_str)

            # 排除系统目录
            if any(p_str.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
                continue

            if not path.is_file():
                continue

            try:
                size = path.stat().st_size
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                continue

            if size < threshold_bytes:
                continue

            items.append(ScanItem(
                path=path,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=path.suffix.upper().lstrip(".") or "文件",
                is_safe=False,      # 大文件需用户确认
                selected=False,     # 默认不勾选，需用户主动选择
                last_modified=mtime,
                description=f"大文件：{path.name}",
            ))

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)
