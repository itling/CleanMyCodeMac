from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from models.scan_item import format_size
from utils.subprocess_utils import get_dir_size, run


def _path_size(path: Path) -> int:
    return get_dir_size(path) if path.is_dir() else path.stat().st_size


def _safe_children(path: Path) -> List[Path]:
    if not path.exists() or not path.is_dir():
        return []
    try:
        return [child for child in path.iterdir() if not child.name.startswith(".")]
    except OSError:
        return []


def _format_percent(part: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{part / total * 100:.1f}%"


def _child_usage(path: Path, limit: int = 8) -> List[Dict]:
    children = []
    for child in _safe_children(path):
        try:
            size = _path_size(child)
        except OSError:
            continue
        children.append({
            "name": child.name,
            "path": str(child),
            "size_bytes": size,
            "size_display": format_size(size),
            "kind": "dir" if child.is_dir() else "file",
        })
    children.sort(key=lambda item: item["size_bytes"], reverse=True)
    return children[:limit]


def _build_tree(path: Path, total_size: int, depth: int = 0, max_depth: int = 2, limit: int = 6) -> Dict:
    try:
        size = _path_size(path)
    except OSError:
        size = 0

    node = {
        "name": path.name or str(path),
        "path": str(path),
        "size_bytes": size,
        "size_display": format_size(size),
        "kind": "dir" if path.is_dir() else "file",
        "percent": _format_percent(size, total_size),
        "can_drill": path.is_dir(),
        "children": [],
    }

    if not path.is_dir() or depth >= max_depth:
        return node

    children = []
    for child in _safe_children(path):
        try:
            child_size = _path_size(child)
        except OSError:
            continue
        children.append((child_size, child))

    children.sort(key=lambda item: item[0], reverse=True)
    for _, child in children[:limit]:
        node["children"].append(_build_tree(child, total_size, depth + 1, max_depth=max_depth, limit=limit))

    return node


def _ancestor_usage(path: Path, max_levels: int = 3) -> List[Dict]:
    levels = []
    current = path.parent
    home = Path.home()
    while current != current.parent and len(levels) < max_levels:
        if str(current).startswith(str(home)) or current == home:
            levels.append({
                "path": str(current),
                "name": current.name or str(current),
                "children": _child_usage(current, limit=6),
            })
        current = current.parent
    return levels


def _parse_docker_summary(lines: List[str]) -> List[Dict]:
    items = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("TYPE") or line.startswith("Images space usage:"):
            continue
        if line.startswith("Containers space usage:") or line.startswith("Local Volumes space usage:") or line.startswith("Build cache usage:"):
            continue
        parts = [part for part in line.split() if part]
        if len(parts) < 2:
            continue
        label = parts[0]
        maybe_size = next((part for part in reversed(parts) if part[-1:] in {"B"} or part.endswith(("kB", "MB", "GB", "TB"))), None)
        if maybe_size:
            items.append({"label": label, "value": maybe_size})
        if len(items) >= 6:
            break
    return items


def _docker_analysis(path: Path) -> Dict:
    output = run(["docker", "system", "df", "-v"], timeout=10)
    available = bool(output and output.strip())
    lines = [line.rstrip() for line in (output or "").splitlines() if line.strip()]
    summary_lines = lines[:120]

    suggestions = [
        {
            "label": "清理未使用镜像",
            "command": "docker image prune -a",
            "description": "删除未被容器使用的镜像，通常是 Docker.raw 膨胀的主要来源之一。",
        },
        {
            "label": "清理停止容器",
            "command": "docker container prune",
            "description": "删除已停止容器，释放容器层占用。",
        },
        {
            "label": "清理未使用卷",
            "command": "docker volume prune",
            "description": "删除未被容器使用的数据卷，适合卷占用过大的情况。",
        },
    ]

    return {
        "kind": "docker_raw",
        "title": "Docker 空间分析",
        "highlights": [
            f"Docker.raw 是 Docker Desktop 的虚拟磁盘文件，当前文件大小为 {format_size(path.stat().st_size)}。",
            "这个文件本身是容器、镜像和卷数据的聚合载体，建议按 Docker 资源类型清理，而不是直接删除该文件。",
        ],
        "docker_cli_available": available,
        "docker_df_lines": summary_lines,
        "docker_summary": _parse_docker_summary(summary_lines),
        "suggestions": suggestions,
    }


def analyze_path(path_str: str) -> Dict:
    path = Path(path_str).expanduser()
    if not path.exists():
        return {"error": "文件不存在"}

    try:
        size = _path_size(path)
    except OSError:
        return {"error": "无法读取文件信息"}

    tree_root = path if path.is_dir() else path.parent
    tree_total = size if path.is_dir() else _path_size(path.parent)

    result = {
        "path": str(path),
        "name": path.name,
        "size_bytes": size,
        "size_display": format_size(size),
        "kind": "directory" if path.is_dir() else "file",
        "parent_path": str(path.parent),
        "parent_name": path.parent.name or str(path.parent),
        "same_level_items": _child_usage(tree_root if tree_root.is_dir() else path.parent, limit=8),
        "ancestor_levels": _ancestor_usage(path, max_levels=3),
        "tree": _build_tree(tree_root, tree_total, max_depth=2, limit=6),
    }

    if path.is_file():
        suffix = path.suffix.lower()
        if path.name.lower() == "docker.raw" or ("docker" in str(path).lower() and suffix in {".raw", ".img", ".qcow2"}):
            result["special"] = _docker_analysis(path)
        else:
            result["highlights"] = [
                f"这是一个单文件占用项，文件大小为 {format_size(size)}。",
                f"下方树状视图展示的是它所在目录 {path.parent.name or path.parent} 的空间分布。",
            ]
    else:
        result["highlights"] = [
            f"这是一个目录，占用 {format_size(size)}。",
            "下方树状视图按占用大小展开到两层，便于继续定位真正的大头。",
        ]

    return result
