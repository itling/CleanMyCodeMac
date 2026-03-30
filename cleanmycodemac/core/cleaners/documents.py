import os
from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.i18n import t


DOC_TYPES = {
    "doc.pdf":   {".pdf"},
    "doc.word":  {".doc", ".docx"},
    "doc.excel": {".xls", ".xlsx", ".csv"},
    "doc.ppt":   {".ppt", ".pptx"},
    "doc.markdown": {".md"},
    "doc.text":  {".txt"},
    "doc.rich_text": {".rtf"},
    "doc.iwork": {".pages", ".numbers", ".keynote"},
}

MIN_SIZE = 1024 * 100  # 100 KB

# 跳过不需要扫描文档的目录（系统/缓存/开发相关）
SKIP_DIRS = {
    "Applications", "Library", ".Trash",
    "node_modules", ".git", "__pycache__",
    ".orbstack",
    "Downloads",  # 由 DownloadsAnalyzer 负责扫描，避免重复计入
}
PACKAGE_SUFFIXES = {".app", ".photoslibrary", ".fcpbundle"}


def _categorize(path: Path) -> str:
    ext = path.suffix.lower()
    for key, exts in DOC_TYPES.items():
        if ext in exts:
            return key
    return "doc.other"


def _all_extensions() -> set:
    exts = set()
    for v in DOC_TYPES.values():
        exts.update(v)
    return exts


def _suffix(name: str) -> str:
    return Path(name).suffix.lower()


class DocumentScanner(BaseCleaner):
    CATEGORY = "document"

    @property
    def DISPLAY_NAME(self):
        return t("cat.document")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        items = []
        valid_exts = _all_extensions()

        self._notify(progress_callback, "scan.document")
        self._scan_dir(Path.home(), valid_exts, items)

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)

    def _scan_dir(self, directory: Path, valid_exts: set, items: list):
        try:
            entries = list(os.scandir(directory))
        except (PermissionError, OSError):
            return

        for entry in entries:
            name = entry.name
            if name.startswith(".") or name in SKIP_DIRS:
                continue
            try:
                is_dir = entry.is_dir(follow_symlinks=False)
            except OSError:
                continue

            if is_dir:
                # 跳过包文件
                if _suffix(name) in PACKAGE_SUFFIXES:
                    continue
                self._scan_dir(Path(entry.path), valid_exts, items)
                continue

            entry_suffix = _suffix(name)
            if entry_suffix not in valid_exts:
                continue

            try:
                stat = entry.stat(follow_symlinks=False)
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                continue

            if size < MIN_SIZE:
                continue

            entry_path = Path(entry.path)
            items.append(ScanItem(
                path=entry_path,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=t(_categorize(entry_path)),
                app_name_key=_categorize(entry_path),
                is_safe=False,
                selected=False,
                last_modified=mtime,
                description=t("desc.document", name=name, date=mtime.strftime("%Y-%m-%d")),
                description_key="desc.document",
                description_args={"name": name, "date": mtime.strftime("%Y-%m-%d")},
            ))
