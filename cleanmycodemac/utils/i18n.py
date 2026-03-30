"""Internationalization support — auto-detect system language, support zh/en."""

import subprocess

_current_lang = "zh"

STRINGS = {
    "zh": {
        # Category names
        "cat.system_cache": "系统缓存",
        "cat.app_cache": "应用缓存",
        "cat.log": "日志文件",
        "cat.download": "下载文件",
        "cat.large_file": "大文件",
        "cat.trash": "废纸篓",
        # Scanner progress
        "scan.system_cache": "正在扫描系统缓存...",
        "scan.app_cache": "正在扫描应用缓存...",
        "scan.log": "正在扫描日志文件...",
        "scan.download": "正在分析下载文件夹...",
        "scan.large_file": "正在搜索大文件（>{threshold}MB）...",
        "scan.trash": "正在检查废纸篓...",
        "scan.done": "已完成：{name}",
        "scan.error": "{name} 扫描出错：{error}",
        "scan.no_scope": "未选择扫描范围，已跳过扫描。",
        # Cleaner descriptions
        "desc.old_download": "旧文件 下载于 {date}",
        "desc.download": "下载于 {date}",
        "desc.large_file": "大文件：{name}",
        "desc.trash_items": "{label}中共 {count} 个项目",
        "desc.trash_items_root": "废纸篓中共 {count} 个项目",
        "desc.trash_items_external": "{volume} 废纸篓中共 {count} 个项目",
        "desc.trash_no_access": "当前运行的应用实例没有废纸篓访问权限，或 Finder 废纸篓位于其他受保护卷",
        "desc.trash_no_access_label": "废纸篓（未授权）",
        "desc.cache": "系统应用产生的缓存",
        "desc.file_type.folder": "文件夹",
        "desc.file_type.file": "文件",
        "desc.app_cache_bundle": "应用缓存: {bundle_id}",
        "desc.system_cache_bundle": "系统缓存: {bundle_id}",
        "desc.log_date": "日志文件 ({date})",
        # Trash labels
        "trash.label": "废纸篓",
        "trash.external": "{volume} 废纸篓",
        # New categories
        "cat.dev_cache": "编程缓存",
        "cat.document": "文档文件",
        "cat.media": "媒体文件",
        "scan.dev_cache": "正在扫描编程工具与语言缓存...",
        "scan.ai_models": "正在扫描大模型文件...",
        "scan.document": "正在扫描文档文件...",
        "scan.media": "正在扫描媒体文件...",
        "desc.dev_lang_cache": "{lang} 缓存：{path}",
        "desc.dev_tool_cache": "{tool} 缓存：{path}",
        "desc.ai_model": "{tool} 模型：{name}",
        "desc.document": "{name}（{date}）",
        "desc.media": "{name}（{date}）",
        "doc.pdf": "PDF",
        "doc.word": "Word",
        "doc.excel": "Excel",
        "doc.ppt": "PPT",
        "doc.markdown": "Markdown",
        "doc.text": "文本",
        "doc.rich_text": "富文本",
        "doc.iwork": "iWork",
        "doc.other": "其他文档",
        "media.image": "图片",
        "media.audio": "音频",
        "media.video": "视频",
        "media.other": "其他媒体",
        # Download file types
        "dl.installer": "安装包",
        "dl.archive": "压缩包",
        "dl.video": "视频",
        "dl.image": "镜像",
        "dl.document": "文档",
        "dl.other": "其他",
        # Backend UI strings
        "ui.init": "初始化...",
        "ui.scan_done": "扫描完成！",
        "ui.about": "关于",
        "ui.author": "作者",
        "ui.email": "邮箱",
        "ui.version": "版本",
        "ui.lang_zh": "中文",
        "ui.lang_en": "EN",
        "perm.trash_warn": "废纸篓访问未授权",
        "perm.partial_warn": "部分受保护目录未授权",
        "confirmCleanTrash": "即将永久删除 {n} 个废纸篓项目。\n删除后不可恢复，确认继续？",
        "confirmCleanTrashTitle": "确认永久删除",
        "error.no_selection": "无选中项",
        "error.missing_path": "缺少路径",
        # Analyzer
        "analyzer.file_not_found": "文件不存在",
        "analyzer.read_error": "无法读取文件信息",
        "analyzer.docker_title": "Docker 空间分析",
        "analyzer.docker_desc": "Docker.raw 是 Docker Desktop 的虚拟磁盘文件，当前文件大小为 {size}。",
        "analyzer.docker_hint": "这个文件本身是容器、镜像和卷数据的聚合载体，建议按 Docker 资源类型清理，而不是直接删除该文件。",
        "analyzer.docker_prune_images": "清理未使用镜像",
        "analyzer.docker_prune_images_desc": "删除未被容器使用的镜像，通常是 Docker.raw 膨胀的主要来源之一。",
        "analyzer.docker_prune_containers": "清理停止容器",
        "analyzer.docker_prune_containers_desc": "删除已停止容器，释放容器层占用。",
        "analyzer.docker_prune_volumes": "清理未使用卷",
        "analyzer.docker_prune_volumes_desc": "删除未被容器使用的数据卷，适合卷占用过大的情况。",
        "analyzer.docker_force_remove_images": "强力移除所有镜像",
        "analyzer.docker_force_remove_images_desc": "-f 为强制删除，即使镜像被容器引用。",
        "analyzer.docker_prune_all": "彻底清理所有环境",
        "analyzer.docker_prune_all_desc": "包含镜像、容器、卷的整体清理，适合需要快速回收 Docker 空间的情况。",
        "analyzer.single_file": "这是一个单文件占用项，文件大小为 {size}。",
        "analyzer.single_file_tree": "下方树状视图展示的是它所在目录 {dir} 的空间分布。",
        "analyzer.dir_info": "这是一个目录，占用 {size}。",
        "analyzer.dir_tree": "下方树状视图按占用大小展开到两层，便于继续定位真正的大头。",
    },
    "en": {
        "cat.system_cache": "System Cache",
        "cat.app_cache": "App Cache",
        "cat.log": "Log Files",
        "cat.download": "Downloads",
        "cat.large_file": "Large Files",
        "cat.trash": "Trash",
        "scan.system_cache": "Scanning system cache...",
        "scan.app_cache": "Scanning app cache...",
        "scan.log": "Scanning log files...",
        "scan.download": "Analyzing downloads folder...",
        "scan.large_file": "Searching large files (>{threshold}MB)...",
        "scan.trash": "Checking trash...",
        "scan.done": "Done: {name}",
        "scan.error": "{name} scan error: {error}",
        "scan.no_scope": "No scan scope selected, skipped.",
        "desc.old_download": "Old file, downloaded {date}",
        "desc.download": "Downloaded {date}",
        "desc.large_file": "Large file: {name}",
        "desc.trash_items": "{count} items in {label}",
        "desc.trash_items_root": "{count} items in Trash",
        "desc.trash_items_external": "{count} items in {volume} Trash",
        "desc.trash_no_access": "No trash access permission, or Finder trash is on a protected volume",
        "desc.trash_no_access_label": "Trash (no access)",
        "desc.cache": "Cache from system apps",
        "desc.file_type.folder": "Folder",
        "desc.file_type.file": "File",
        "desc.app_cache_bundle": "App Cache: {bundle_id}",
        "desc.system_cache_bundle": "System Cache: {bundle_id}",
        "desc.log_date": "Log Files ({date})",
        "trash.label": "Trash",
        "trash.external": "{volume} Trash",
        "cat.dev_cache": "Dev Cache",
        "cat.document": "Documents",
        "cat.media": "Media",
        "scan.dev_cache": "Scanning dev tools & language caches...",
        "scan.ai_models": "Scanning AI model files...",
        "scan.document": "Scanning document files...",
        "scan.media": "Scanning media files...",
        "desc.dev_lang_cache": "{lang} cache: {path}",
        "desc.dev_tool_cache": "{tool} cache: {path}",
        "desc.ai_model": "{tool} model: {name}",
        "desc.document": "{name} ({date})",
        "desc.media": "{name} ({date})",
        "doc.pdf": "PDF",
        "doc.word": "Word",
        "doc.excel": "Excel",
        "doc.ppt": "PPT",
        "doc.markdown": "Markdown",
        "doc.text": "Text",
        "doc.rich_text": "Rich Text",
        "doc.iwork": "iWork",
        "doc.other": "Other Docs",
        "media.image": "Images",
        "media.audio": "Audio",
        "media.video": "Video",
        "media.other": "Other Media",
        "dl.installer": "Installer",
        "dl.archive": "Archive",
        "dl.video": "Video",
        "dl.image": "Disk Image",
        "dl.document": "Document",
        "dl.other": "Other",
        "ui.init": "Initializing...",
        "ui.scan_done": "Scan complete!",
        "ui.about": "About",
        "ui.author": "Author",
        "ui.email": "Email",
        "ui.version": "Version",
        "ui.lang_zh": "中文",
        "ui.lang_en": "EN",
        "perm.trash_warn": "Trash access not granted",
        "perm.partial_warn": "Protected folders partially not granted",
        "confirmCleanTrash": "About to permanently delete {n} trash items.\nThis action cannot be undone. Continue?",
        "confirmCleanTrashTitle": "Confirm Permanent Delete",
        "error.no_selection": "No items selected",
        "error.missing_path": "Missing path",
        "analyzer.file_not_found": "File not found",
        "analyzer.read_error": "Unable to read file info",
        "analyzer.docker_title": "Docker Space Analysis",
        "analyzer.docker_desc": "Docker.raw is a Docker Desktop virtual disk file, current size is {size}.",
        "analyzer.docker_hint": "This file aggregates containers, images and volume data. Clean by Docker resource type instead of deleting this file directly.",
        "analyzer.docker_prune_images": "Prune Unused Images",
        "analyzer.docker_prune_images_desc": "Remove images not used by any container — usually the main cause of Docker.raw bloat.",
        "analyzer.docker_prune_containers": "Prune Stopped Containers",
        "analyzer.docker_prune_containers_desc": "Remove stopped containers to free container layer space.",
        "analyzer.docker_prune_volumes": "Prune Unused Volumes",
        "analyzer.docker_prune_volumes_desc": "Remove volumes not used by any container, useful when volumes are too large.",
        "analyzer.docker_force_remove_images": "Force Remove All Images",
        "analyzer.docker_force_remove_images_desc": "-f forces deletion even when images are referenced by containers.",
        "analyzer.docker_prune_all": "Deep Clean Entire Docker Environment",
        "analyzer.docker_prune_all_desc": "Cleans images, containers, and volumes together for maximum Docker space recovery.",
        "analyzer.single_file": "This is a single file, size is {size}.",
        "analyzer.single_file_tree": "The tree view below shows the space distribution of its parent directory {dir}.",
        "analyzer.dir_info": "This is a directory, using {size}.",
        "analyzer.dir_tree": "The tree view below expands up to two levels by size, helping you locate the biggest items.",
    },
}


def detect_language() -> str:
    """Detect system language via macOS defaults, return 'zh' or 'en'."""
    try:
        r = subprocess.run(
            ["defaults", "read", "-g", "AppleLanguages"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and "zh" in r.stdout:
            return "zh"
    except Exception:
        pass
    return "en"


def get_lang() -> str:
    return _current_lang


def set_lang(lang: str, save: bool = False):
    global _current_lang
    _current_lang = lang if lang in STRINGS else "en"
    if save:
        try:
            from utils.config import load_config, save_config
            cfg = load_config()
            cfg["lang"] = _current_lang
            save_config(cfg)
        except Exception:
            pass


def t(key: str, **kwargs) -> str:
    """Translate a key with optional format arguments."""
    text = STRINGS.get(_current_lang, STRINGS["en"]).get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# Auto-detect on import: saved preference > OS language
def _init_lang():
    try:
        from utils.config import load_config
        saved = load_config().get("lang")
        if saved and saved in STRINGS:
            set_lang(saved)
            return
    except Exception:
        pass
    set_lang(detect_language())

_init_lang()
