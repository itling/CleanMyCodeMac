from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Optional


@dataclass
class ScanItem:
    path: Path
    size_bytes: int
    category: str          # "system_cache" | "app_cache" | "log" | "download" | "large_file" | "trash"
    app_name: str          # 所属应用名，如 "Google Chrome"
    is_safe: bool          # 是否在安全清理范围内
    selected: bool = True  # UI 勾选状态
    last_modified: Optional[datetime] = None
    description: str = ""

    @property
    def size_display(self) -> str:
        return format_size(self.size_bytes)

    @property
    def path_str(self) -> str:
        home = str(Path.home())
        p = str(self.path)
        if p.startswith(home):
            return "~" + p[len(home):]
        return p


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"
