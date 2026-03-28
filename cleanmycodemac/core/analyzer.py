from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from models.scan_item import format_size
from utils.subprocess_utils import get_dir_size, run
from utils.i18n import t


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
            "label": t("analyzer.docker_prune_images"),
            "command": "docker image prune -a",
            "description": t("analyzer.docker_prune_images_desc"),
        },
        {
            "label": t("analyzer.docker_prune_containers"),
            "command": "docker container prune",
            "description": t("analyzer.docker_prune_containers_desc"),
        },
        {
            "label": t("analyzer.docker_prune_volumes"),
            "command": "docker volume prune",
            "description": t("analyzer.docker_prune_volumes_desc"),
        },
        {
            "label": t("analyzer.docker_force_remove_images"),
            "command": "ids=$(docker images -q); if [ -n \"$ids\" ]; then docker rmi -f $ids; else echo \"No images to remove\"; fi",
            "description": t("analyzer.docker_force_remove_images_desc"),
        },
        {
            "label": t("analyzer.docker_prune_all"),
            "command": "docker system prune -a -f",
            "description": t("analyzer.docker_prune_all_desc"),
        },
    ]

    return {
        "kind": "docker_raw",
        "title": t("analyzer.docker_title"),
        "highlights": [
            t("analyzer.docker_desc", size=format_size(path.stat().st_size)),
            t("analyzer.docker_hint"),
        ],
        "docker_cli_available": available,
        "docker_df_lines": summary_lines,
        "docker_summary": _parse_docker_summary(summary_lines),
        "suggestions": suggestions,
    }


def analyze_path(path_str: str) -> Dict:
    path = Path(path_str).expanduser()
    if not path.exists():
        return {"error": t("analyzer.file_not_found")}

    try:
        size = _path_size(path)
    except OSError:
        return {"error": t("analyzer.read_error")}

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
                t("analyzer.single_file", size=format_size(size)),
                t("analyzer.single_file_tree", dir=path.parent.name or str(path.parent)),
            ]
    else:
        result["highlights"] = [
            t("analyzer.dir_info", size=format_size(size)),
            t("analyzer.dir_tree"),
        ]

    return result
