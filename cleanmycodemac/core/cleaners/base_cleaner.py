from abc import ABC, abstractmethod
from typing import List, Callable, Optional
from pathlib import Path
from models.scan_item import ScanItem
from models.clean_report import CleanReport
from utils.subprocess_utils import move_to_trash
import shutil


class BaseCleaner(ABC):
    CATEGORY = ""
    DISPLAY_NAME = ""

    @abstractmethod
    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        """只读扫描，返回可清理项目列表"""
        ...

    def clean(self, items: List[ScanItem], dry_run: bool = False) -> CleanReport:
        report = CleanReport()
        for item in items:
            if not item.path.exists():
                report.add_skip(item.path)
                continue
            if dry_run:
                continue
            if item.is_safe:
                # 安全项目（缓存/日志/开发缓存）直接删除，立即释放磁盘空间
                try:
                    if item.path.is_dir():
                        shutil.rmtree(item.path)
                    else:
                        item.path.unlink()
                    report.add_success(item.path, item.size_bytes)
                except Exception as e:
                    # 降级：移入废纸篓
                    if move_to_trash(item.path):
                        report.add_success(item.path, item.size_bytes)
                    else:
                        report.add_failure(item.path, str(e))
            else:
                # 非安全项目（文档/媒体/大文件）移入废纸篓，保留可恢复性
                success = move_to_trash(item.path)
                if success:
                    report.add_success(item.path, item.size_bytes)
                else:
                    try:
                        if item.path.is_dir():
                            shutil.rmtree(item.path)
                        else:
                            item.path.unlink()
                        report.add_success(item.path, item.size_bytes)
                    except Exception as e:
                        report.add_failure(item.path, str(e))
        return report

    def _notify(self, callback: Optional[Callable], key: str, **kwargs):
        if callback:
            callback({"key": key, "args": kwargs})
