from dataclasses import dataclass, field
from typing import List
from pathlib import Path
from .scan_item import format_size


@dataclass
class CleanReport:
    cleaned: List[Path] = field(default_factory=list)
    failed: List[tuple] = field(default_factory=list)   # (path, error_msg)
    skipped: List[Path] = field(default_factory=list)
    cleaned_bytes: int = 0

    def add_success(self, path: Path, size: int):
        self.cleaned.append(path)
        self.cleaned_bytes += size

    def add_failure(self, path: Path, error: str):
        self.failed.append((path, error))

    def add_skip(self, path: Path):
        self.skipped.append(path)

    @property
    def cleaned_display(self) -> str:
        return format_size(self.cleaned_bytes)

    @property
    def summary(self) -> str:
        lines = [
            f"清理完成：释放 {self.cleaned_display}",
            f"成功：{len(self.cleaned)} 项",
        ]
        if self.failed:
            lines.append(f"失败：{len(self.failed)} 项")
        if self.skipped:
            lines.append(f"跳过：{len(self.skipped)} 项")
        return "\n".join(lines)
