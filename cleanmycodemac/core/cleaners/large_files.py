from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import mdfind_large_files, get_file_size
from utils.config import load_config
from utils.i18n import t

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
    @property
    def DISPLAY_NAME(self):
        return t("cat.large_file")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        config = load_config()
        threshold_bytes = config.get("large_file_threshold_mb", 500) * 1024 * 1024

        self._notify(progress_callback, "scan.large_file", threshold=config['large_file_threshold_mb'])

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
                stat = path.stat()
                # 使用实际占用块数而非逻辑大小，避免稀疏文件（如 Docker.raw）虚报
                size = stat.st_blocks * 512
                mtime = datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                continue

            if size < threshold_bytes:
                continue

            items.append(ScanItem(
                path=path,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=path.suffix.upper().lstrip(".") or t("desc.file_type.file"),
                is_safe=False,      # 大文件需用户确认
                selected=False,     # 默认不勾选，需用户主动选择
                last_modified=mtime,
                description=t("desc.large_file", name=path.name),
                description_key="desc.large_file",
                description_args={"name": path.name},
            ))

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)
