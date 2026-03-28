import os
import subprocess
from pathlib import Path
from typing import List, Callable, Optional
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from models.clean_report import CleanReport
from utils.subprocess_utils import get_dir_size, get_file_size, permanently_delete
from utils.config import load_config
from utils.i18n import t


class TrashCleaner(BaseCleaner):
    CATEGORY = "trash"
    @property
    def DISPLAY_NAME(self):
        return t("cat.trash")

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
        self._notify(progress_callback, t("scan.trash"))

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

            if not entries:
                continue

            is_root_trash = trash_path == self.TRASH_PATH
            label_key = "trash.label" if is_root_trash else "trash.external"
            label_args = {} if is_root_trash else {"volume": trash_path.parent.parent.name}
            for entry in entries:
                try:
                    size = get_dir_size(entry) if entry.is_dir() else get_file_size(entry)
                except OSError:
                    size = 0
                items.append(ScanItem(
                    path=entry,
                    size_bytes=size,
                    category=self.CATEGORY,
                    app_name=entry.name,
                    is_safe=True,
                    selected=auto_select_safe,
                    description=t(label_key, **label_args),
                    description_key=label_key,
                    description_args=label_args,
                ))

        if not items and permission_denied:
            items.append(ScanItem(
                path=self.TRASH_PATH,
                size_bytes=0,
                category=self.CATEGORY,
                app_name=t("desc.trash_no_access_label"),
                app_name_key="desc.trash_no_access_label",
                is_safe=False,
                selected=False,
                description=t("desc.trash_no_access"),
                description_key="desc.trash_no_access",
            ))

        return items

    def clean(self, items: List[ScanItem], dry_run: bool = False) -> CleanReport:
        report = CleanReport()
        if dry_run:
            return report

        for item in items:
            try:
                if not permanently_delete(item.path):
                    subprocess.run(
                        ["rm", "-rf", str(item.path)],
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                report.add_success(item.path, item.size_bytes)
            except Exception as e:
                report.add_failure(item.path, str(e))

        return report
