import subprocess
from pathlib import Path
from typing import Optional


def run(cmd: list, timeout: int = 30) -> Optional[str]:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_dir_size(path: Path) -> int:
    """使用 du 获取目录大小（字节），比 Python 递归快 10 倍"""
    out = run(["du", "-sk", str(path)])
    if out:
        try:
            return int(out.split("\t")[0]) * 1024
        except (ValueError, IndexError):
            pass
    return 0


def get_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def move_to_trash(path: Path) -> bool:
    """通过 osascript 调用 Finder 将文件移入废纸篓"""
    escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "Finder" to delete POSIX file "{escaped}"'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=15
    )
    return result.returncode == 0


def permanently_delete(path: Path) -> bool:
    """通过 Finder 永久删除废纸篓中的条目"""
    escaped = str(path).replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "Finder" to delete POSIX file "{escaped}"'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.returncode == 0


def mdfind_large_files(min_bytes: int = 524288000, root: str = None) -> list:
    """使用 mdfind 搜索大文件（默认 >500MB），超时 15 秒自动跳过"""
    cmd = ["mdfind"]
    if root:
        cmd += ["-onlyin", root]
    cmd.append(f"kMDItemFSSize > {min_bytes}")
    out = run(cmd, timeout=15)
    if not out:
        return []
    return [p for p in out.strip().split("\n") if p]


def open_privacy_settings():
    subprocess.Popen([
        "open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
    ])


def reveal_in_finder(path) -> bool:
    """在 Finder 中显示文件，接受 str 或 Path"""
    result = subprocess.run(
        ["open", "-R", str(path)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.returncode == 0
