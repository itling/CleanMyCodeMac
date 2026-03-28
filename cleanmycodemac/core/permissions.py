import os
from pathlib import Path
from utils.subprocess_utils import open_privacy_settings


SAFARI_CACHE = Path.home() / "Library/Caches/com.apple.Safari"
TRASH_PATH = Path.home() / ".Trash"


def check_full_disk_access() -> bool:
    """通过尝试列出 Safari 缓存目录来检测完全磁盘访问权限"""
    try:
        list(SAFARI_CACHE.iterdir())
        return True
    except PermissionError:
        return False
    except FileNotFoundError:
        return True  # 目录不存在，说明没被阻止访问


def check_trash_access() -> bool:
    try:
        list(TRASH_PATH.iterdir())
        return True
    except PermissionError:
        return False
    except FileNotFoundError:
        return True


def request_full_disk_access():
    open_privacy_settings()
