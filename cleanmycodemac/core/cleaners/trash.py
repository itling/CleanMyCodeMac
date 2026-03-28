import os
import shutil
from pathlib import Path
from typing import List, Callable, Optional
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from models.clean_report import CleanReport
from utils.subprocess_utils import get_dir_size, run
from utils.config import load_config


class TrashCleaner(BaseCleaner):
    CATEGORY = "trash"
    DISPLAY_NAME = "废纸篓"

    TRASH_PATH = Path.home() / ".Trash"

    def _trash_locations(self) -> list[Path]:
        locations = [self.TRASH_PATH]
        uid = str(os.getuid())
        volumes_root = Path("/Volumes")
        if volumes_root.exists():
            for volume in volumes_root.iterdir():
                locations.append(volume / ".Trashes" / uid)
        return locations

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        items = []
        auto_select_safe = load_config().get("auto_select_safe_items", True)
        self._notify(progress_callback, "正在检查废纸篓...")

        locations = [path for path in self._trash_locations() if path.exists()]
        if not locations:
            return items

        permission_denied = False
        for trash_path in locations:
            try:
                entries = list(trash_path.iterdir())
            except PermissionError:
                permission_denied = True
                continue

            total_size = get_dir_size(trash_path)
            if total_size <= 0 and not entries:
                continue

            label = "废纸篓" if trash_path == self.TRASH_PATH else f"{trash_path.parent.parent.name} 废纸篓"
            items.append(ScanItem(
                path=trash_path,
                size_bytes=total_size,
                category=self.CATEGORY,
                app_name=label,
                is_safe=True,
                selected=auto_select_safe,
                description=f"{label}中共 {len(entries)} 个项目",
            ))

        if not items and permission_denied:
            items.append(ScanItem(
                path=self.TRASH_PATH,
                size_bytes=0,
                category=self.CATEGORY,
                app_name="废纸篓（未授权）",
                is_safe=False,
                selected=False,
                description="当前运行的应用实例没有废纸篓访问权限，或 Finder 废纸篓位于其他受保护卷",
            ))

        return items

    def clean(self, items: List[ScanItem], dry_run: bool = False) -> CleanReport:
        report = CleanReport()
        if dry_run:
            return report

        # 使用 osascript 清空废纸篓（最安全的方式）
        script = 'tell application "Finder" to empty trash'
        result = run(["osascript", "-e", script], timeout=30)
        if result is not None:
            for item in items:
                report.add_success(item.path, item.size_bytes)
        else:
            # 降级：直接删除废纸篓内容
            try:
                for entry in self.TRASH_PATH.iterdir():
                    try:
                        if entry.is_dir():
                            shutil.rmtree(entry)
                        else:
                            entry.unlink()
                    except Exception as e:
                        report.add_failure(entry, str(e))
                for item in items:
                    report.add_success(item.path, item.size_bytes)
            except Exception as e:
                for item in items:
                    report.add_failure(item.path, str(e))

        return report
