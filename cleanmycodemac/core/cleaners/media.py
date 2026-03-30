from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.i18n import t


MEDIA_TYPES = {
    "media.image": {
        # 通用
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".heic", ".heif", ".svg",
        # 相机 RAW
        ".raw", ".dng",          # Adobe DNG / 大疆 DJI RAW
        ".cr2", ".cr3",          # Canon
        ".nef", ".nrw",          # Nikon
        ".arw", ".srf", ".sr2",  # Sony
        ".raf",                  # Fujifilm
        ".rw2",                  # Panasonic / Lumix
        ".orf",                  # Olympus
        ".pef", ".ptx",          # Pentax
        ".3fr",                  # Hasselblad
        ".rwl",                  # Leica
        # 运动相机
        ".insp",                 # Insta360 照片
        ".gpr",                  # GoPro RAW
    },
    "media.audio": {
        ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma",
        ".ape", ".aiff", ".aif", ".opus", ".amr",
    },
    "media.video": {
        # 通用
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
        ".3gp", ".3g2", ".ts", ".mts", ".m2ts",
        # 运动相机 / 无人机
        ".insv",                 # Insta360 视频
        ".lrv",                  # Insta360 / GoPro 低码率预览
        ".r3d",                  # RED 摄影机
        ".braw",                 # Blackmagic RAW
        ".mxf",                  # 专业广播格式
        ".vob", ".mpg", ".mpeg", ".m2v",
    },
}

MIN_SIZE = 1024 * 1024  # 1 MB

# 跳过不需要扫描媒体的目录
SKIP_DIRS = {
    "Applications", "Library", ".Trash",
    "node_modules", ".git", "__pycache__",
    ".orbstack",
    "Downloads",  # 由 DownloadsAnalyzer 负责扫描，避免重复计入
}


def _categorize(path: Path) -> str:
    ext = path.suffix.lower()
    for key, exts in MEDIA_TYPES.items():
        if ext in exts:
            return key
    return "media.other"


def _all_extensions() -> set:
    exts = set()
    for v in MEDIA_TYPES.values():
        exts.update(v)
    return exts


class MediaScanner(BaseCleaner):
    CATEGORY = "media"

    @property
    def DISPLAY_NAME(self):
        return t("cat.media")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        items = []
        valid_exts = _all_extensions()

        self._notify(progress_callback, t("scan.media"))
        self._scan_dir(Path.home(), valid_exts, items)

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)

    def _scan_dir(self, directory: Path, valid_exts: set, items: list):
        try:
            entries = list(directory.iterdir())
        except (PermissionError, OSError):
            return

        for entry in entries:
            name = entry.name
            if name.startswith(".") or name in SKIP_DIRS:
                continue
            if entry.is_dir():
                # 跳过包文件
                if entry.suffix.lower() in {".app", ".photoslibrary", ".musiclibrary", ".fcpbundle"}:
                    continue
                self._scan_dir(entry, valid_exts, items)
                continue
            if entry.suffix.lower() not in valid_exts:
                continue

            try:
                stat = entry.stat()
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                continue

            if size < MIN_SIZE:
                continue

            items.append(ScanItem(
                path=entry,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=t(_categorize(entry)),
                app_name_key=_categorize(entry),
                is_safe=False,
                selected=False,
                last_modified=mtime,
                description=t("desc.media", name=entry.name, date=mtime.strftime("%Y-%m-%d")),
            ))
