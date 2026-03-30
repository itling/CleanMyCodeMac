import os
from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
from .base_cleaner import BaseCleaner
from models.scan_item import ScanItem
from utils.subprocess_utils import get_dir_size
from utils.config import load_config
from utils.i18n import t


# ── 编程语言缓存（Top 30 + 常用） ──

LANG_CACHES = {
    # --- Web / 脚本 ---
    "Node.js": [
        "~/.npm/_cacache",
        "~/.yarn/cache",
        "~/.pnpm-store",
        "~/.bun/install/cache",
        "~/.nvm/.cache",
        "~/.volta/cache",
    ],
    "Python": [
        "~/Library/Caches/pip",
        "~/.cache/pip",
        "~/.conda/pkgs",
        "~/.pyenv/cache",
        "~/Library/Caches/pypoetry",
    ],
    "Ruby": [
        "~/.gem",
        "~/.bundle/cache",
        "~/Library/Caches/CocoaPods",
        "~/.rbenv/cache",
    ],
    "PHP": [
        "~/.composer/cache",
    ],
    "Perl": [
        "~/.cpan/sources",
        "~/.cpan/build",
    ],
    "Lua": [
        "~/.luarocks",
    ],
    # --- 编译型 ---
    "Rust": [
        "~/.cargo/registry/cache",
        "~/.cargo/registry/src",
        "~/.cargo/git/db",
    ],
    "Go": [
        "~/go/pkg/mod/cache",
        "~/.cache/go-build",
    ],
    "Java": [
        "~/.m2/repository",
        "~/.gradle/caches",
        "~/.gradle/wrapper/dists",
    ],
    "Kotlin": [
        "~/.kotlin/caches",
        "~/.konan/cache",
        "~/.konan/dependencies",
    ],
    "Scala": [
        "~/.sbt/boot",
        "~/.ivy2/cache",
        "~/.cache/coursier",
    ],
    "C/C++": [
        "~/.cache/ccache",
        "~/.conan/data",
        "~/.cache/vcpkg",
    ],
    "Swift": [
        "~/Library/Caches/org.swift.swiftpm",
        "~/Library/org.swift.swiftpm",
    ],
    ".NET": [
        "~/.nuget/packages",
        "~/.dotnet/tools/.store",
    ],
    "Zig": [
        "~/.cache/zig",
    ],
    "V": [
        "~/.vmodules",
    ],
    # --- 函数式 ---
    "Haskell": [
        "~/.cabal/packages",
        "~/.cabal/store",
        "~/.stack",
    ],
    "Elixir": [
        "~/.mix",
        "~/.hex",
    ],
    "Clojure": [
        "~/.lein",
        "~/.clojure/.cpcache",
    ],
    "OCaml": [
        "~/.opam",
    ],
    "Erlang": [
        "~/.cache/rebar3",
    ],
    # --- 移动端 / 跨平台 ---
    "Dart/Flutter": [
        "~/.pub-cache",
        "~/.flutter",
        "~/Library/Caches/com.google.dart.tools",
    ],
    # --- 数据科学 ---
    "R": [
        "~/Library/R",
        "~/.R/cache",
    ],
    "Julia": [
        "~/.julia/packages",
        "~/.julia/compiled",
        "~/.julia/artifacts",
    ],
    "MATLAB": [
        "~/Library/Caches/MathWorks",
    ],
}

# ── 编程工具缓存 ──

# Electron 编辑器 / IDE 通用 cache 子目录
_ELECTRON_CACHE_DIRS = [
    "Cache", "CachedData", "CachedExtensionVSIXs", "CachedExtensions",
    "CachedProfilesData", "CachedConfigurations",
    "Code Cache", "GPUCache", "DawnCache",
    "Service Worker", "User/workspaceStorage",
    "logs",
]

# (显示名, Application Support 目录名)
ELECTRON_EDITORS = [
    # 传统编辑器
    ("VS Code", "Code"),
    ("VS Code Insiders", "Code - Insiders"),
    ("Sublime Text", "Sublime Text"),
    # AI 编程工具
    ("Cursor", "Cursor"),
    ("Windsurf", "Windsurf"),
    ("Trae", "Trae"),
    ("Trae CN", "Trae CN"),
    ("Antigravity", "Antigravity"),
    ("Zed", "Zed"),
    ("Aide", "Aide"),
    ("Void", "Void"),
    # 国产工具
    ("HBuilderX", "HBuilder X"),
    ("HBuilderX", "HBuilderX"),
    # 其他
    ("Atom", "Atom"),
    ("Brackets", "Brackets"),
    ("Postman", "Postman"),
    ("Insomnia", "Insomnia"),
]

TOOL_CACHES = {
    "Xcode": [
        "~/Library/Developer/Xcode/DerivedData",
        "~/Library/Developer/Xcode/Archives",
        "~/Library/Developer/Xcode/iOS DeviceSupport",
        "~/Library/Developer/CoreSimulator/Caches",
        "~/Library/Developer/CoreSimulator/Devices",
    ],
    "Android Studio": [
        "~/Library/Caches/Google/AndroidStudio*",
        "~/.android/cache",
        "~/.android/avd",
    ],
    "Homebrew": [
        "~/Library/Caches/Homebrew",
    ],
    "Eclipse": [
        "~/Library/Caches/Eclipse",
        "~/.eclipse",
    ],
    "Unity": [
        "~/Library/Unity/cache",
        "~/Library/Caches/com.unity3d.*",
    ],
    "Unreal Engine": [
        "~/Library/Caches/com.epicgames.*",
    ],
}

# ── 大模型文件 ──

AI_MODEL_CACHES = {
    "LM Studio":     ["~/.lmstudio/models",
                      "~/Library/Application Support/LM Studio/models"],
    "Jan":           ["~/Library/Application Support/Jan/models"],
    "GPT4All":       ["~/Library/Application Support/nomic.ai/GPT4All"],
    "Msty":          ["~/Library/Application Support/Msty/models"],
    "AnythingLLM":   ["~/Library/Application Support/anythingllm-desktop/models"],
    "PyTorch Hub":   ["~/.cache/torch/hub"],
}

# JetBrains 产品动态检测
JETBRAINS_PRODUCTS = [
    "IntelliJIdea", "PyCharm", "WebStorm", "GoLand",
    "CLion", "PhpStorm", "RubyMine", "Rider", "DataGrip",
    "RustRover", "Aqua", "Fleet", "DataSpell",
]


def _expand(pattern: str) -> list:
    """展开路径，支持 glob 通配符"""
    p = Path(pattern).expanduser()
    if "*" in pattern:
        return list(p.parent.glob(p.name))
    return [p] if p.exists() else []


def _discover_path_caches() -> list:
    """从 PATH 环境变量中发现编程工具的缓存目录"""
    found = []
    seen = set()
    home = str(Path.home())

    for p in os.environ.get("PATH", "").split(":"):
        p = p.strip()
        if not p or not p.startswith(home):
            continue
        bin_path = Path(p)
        if not bin_path.exists():
            continue

        parent = bin_path.parent
        parent_str = str(parent)
        if parent_str in seen:
            continue
        seen.add(parent_str)

        for cache_name in ["cache", "Cache", "caches", "Caches", "pkg", "tmp", "temp"]:
            cache_dir = parent / cache_name
            if cache_dir.exists() and cache_dir.is_dir():
                size = get_dir_size(cache_dir)
                if size >= 1024 * 1024:  # >= 1MB
                    found.append((cache_dir, size, parent.name))

    return found


def _scan_electron_editors() -> list:
    """扫描所有 Electron 编辑器 / AI 工具的缓存"""
    results = []
    app_support = Path.home() / "Library/Application Support"
    if not app_support.exists():
        return results

    for display_name, dir_name in ELECTRON_EDITORS:
        base = app_support / dir_name
        if not base.exists():
            continue
        for sub in _ELECTRON_CACHE_DIRS:
            cache_dir = base / sub
            if cache_dir.exists() and cache_dir.is_dir():
                size = get_dir_size(cache_dir)
                if size >= 1024 * 100:  # >= 100KB
                    results.append((cache_dir, size, display_name))

    return results


class DevCacheCleaner(BaseCleaner):
    CATEGORY = "dev_cache"

    @property
    def DISPLAY_NAME(self):
        return t("cat.dev_cache")

    def scan(self, progress_callback: Optional[Callable[[str], None]] = None) -> List[ScanItem]:
        items = []
        config = load_config()
        auto_select_safe = config.get("auto_select_safe_items", True)

        self._notify(progress_callback, "scan.dev_cache")

        # 1) 编程语言缓存
        for lang_name, paths in LANG_CACHES.items():
            lang_size = 0
            lang_paths = []
            for pattern in paths:
                for p in _expand(pattern):
                    if not p.exists():
                        continue
                    size = get_dir_size(p)
                    if size > 0:
                        lang_size += size
                        lang_paths.append((p, size))

            if lang_size < 1024 * 100:
                continue

            for p, size in lang_paths:
                try:
                    mtime = datetime.fromtimestamp(p.stat().st_mtime)
                except OSError:
                    mtime = None
                items.append(ScanItem(
                    path=p,
                    size_bytes=size,
                    category=self.CATEGORY,
                    app_name=lang_name,
                    is_safe=True,
                    selected=auto_select_safe,
                    last_modified=mtime,
                    description=t("desc.dev_lang_cache", lang=lang_name, path=p.name),
                    description_key="desc.dev_lang_cache",
                    description_args={"lang": lang_name, "path": p.name},
                ))

        # 2) Electron 编辑器 / AI 工具
        for cache_dir, size, tool_name in _scan_electron_editors():
            try:
                mtime = datetime.fromtimestamp(cache_dir.stat().st_mtime)
            except OSError:
                mtime = None
            items.append(ScanItem(
                path=cache_dir,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=tool_name,
                is_safe=True,
                selected=auto_select_safe,
                last_modified=mtime,
                description=t("desc.dev_tool_cache", tool=tool_name, path=cache_dir.name),
                description_key="desc.dev_tool_cache",
                description_args={"tool": tool_name, "path": cache_dir.name},
            ))

        # 3) 其他工具缓存
        for tool_name, paths in TOOL_CACHES.items():
            for pattern in paths:
                for p in _expand(pattern):
                    if not p.exists():
                        continue
                    size = get_dir_size(p)
                    if size < 1024 * 100:
                        continue
                    try:
                        mtime = datetime.fromtimestamp(p.stat().st_mtime)
                    except OSError:
                        mtime = None
                    items.append(ScanItem(
                        path=p,
                        size_bytes=size,
                        category=self.CATEGORY,
                        app_name=tool_name,
                        is_safe=True,
                        selected=auto_select_safe,
                        last_modified=mtime,
                        description=t("desc.dev_tool_cache", tool=tool_name, path=p.name),
                        description_key="desc.dev_tool_cache",
                        description_args={"tool": tool_name, "path": p.name},
                    ))

        # 4) JetBrains 动态检测
        jb_cache_root = Path.home() / "Library/Caches/JetBrains"
        if jb_cache_root.exists():
            try:
                entries = list(jb_cache_root.iterdir())
            except OSError:
                entries = []
            for entry in entries:
                if not entry.is_dir():
                    continue
                size = get_dir_size(entry)
                if size < 1024 * 100:
                    continue
                product = entry.name
                for name in JETBRAINS_PRODUCTS:
                    if entry.name.startswith(name):
                        product = name
                        break
                try:
                    mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                except OSError:
                    mtime = None
                items.append(ScanItem(
                    path=entry,
                    size_bytes=size,
                    category=self.CATEGORY,
                    app_name=f"JetBrains {product}",
                    is_safe=True,
                    selected=auto_select_safe,
                    last_modified=mtime,
                    description=t("desc.dev_tool_cache", tool=f"JetBrains {product}", path=entry.name),
                    description_key="desc.dev_tool_cache",
                    description_args={"tool": f"JetBrains {product}", "path": entry.name},
                ))

        # 5) PATH 环境变量发现的缓存（去重）
        seen_paths = {str(item.path) for item in items}
        for cache_dir, size, tool_name in _discover_path_caches():
            cache_str = str(cache_dir)
            if cache_str in seen_paths:
                continue
            if any(cache_str.startswith(s + "/") or s.startswith(cache_str + "/") for s in seen_paths):
                continue
            seen_paths.add(cache_str)
            try:
                mtime = datetime.fromtimestamp(cache_dir.stat().st_mtime)
            except OSError:
                mtime = None
            items.append(ScanItem(
                path=cache_dir,
                size_bytes=size,
                category=self.CATEGORY,
                app_name=tool_name,
                is_safe=True,
                selected=auto_select_safe,
                last_modified=mtime,
                description=t("desc.dev_tool_cache", tool=tool_name, path=cache_dir.name),
                description_key="desc.dev_tool_cache",
                description_args={"tool": tool_name, "path": cache_dir.name},
            ))

        # 6) 大模型文件（Ollama / HuggingFace / LM Studio 等）
        seen_paths = {str(item.path) for item in items}
        self._notify(progress_callback, "scan.ai_models")

        # Ollama：按单个模型列出（读 manifests 目录结构）
        # 目录层级：manifests/<registry>/<namespace>/<model_name>/<tag>
        ollama_manifests = Path.home() / ".ollama" / "models" / "manifests"
        ollama_blobs = Path.home() / ".ollama" / "models" / "blobs"
        if ollama_manifests.exists() and ollama_blobs.exists():
            try:
                import json as _json
                for registry in ollama_manifests.iterdir():
                    if not registry.is_dir():
                        continue
                    for namespace in registry.iterdir():
                        if not namespace.is_dir():
                            continue
                        for model_name in namespace.iterdir():
                            if not model_name.is_dir():
                                continue
                            for tag_file in model_name.iterdir():
                                if not tag_file.is_file():
                                    continue
                                try:
                                    manifest = _json.loads(tag_file.read_text())
                                    blob_size = 0
                                    for layer in manifest.get("layers", []) + [manifest.get("config", {})]:
                                        digest = (layer or {}).get("digest", "")
                                        if digest:
                                            blob = ollama_blobs / digest.replace(":", "-")
                                            if blob.exists():
                                                blob_size += blob.stat().st_blocks * 512
                                    if blob_size < 1024 * 1024 * 10:
                                        continue
                                    model_label = f"{model_name.name}:{tag_file.name}"
                                    try:
                                        mtime = datetime.fromtimestamp(tag_file.stat().st_mtime)
                                    except OSError:
                                        mtime = None
                                    if str(tag_file) not in seen_paths:
                                        seen_paths.add(str(tag_file))
                                        items.append(ScanItem(
                                            path=tag_file,
                                            size_bytes=blob_size,
                                            category=self.CATEGORY,
                                            app_name="Ollama",
                                            is_safe=False,
                                            selected=False,
                                            last_modified=mtime,
                                            description=t("desc.ai_model", tool="Ollama", name=model_label),
                                            description_key="desc.ai_model",
                                            description_args={"tool": "Ollama", "name": model_label},
                                        ))
                                except Exception:
                                    continue
            except OSError:
                pass

        # HuggingFace：按 repo 列出
        hf_hub = Path.home() / ".cache" / "huggingface" / "hub"
        if hf_hub.exists():
            try:
                for repo_dir in hf_hub.iterdir():
                    if not repo_dir.is_dir():
                        continue
                    size = get_dir_size(repo_dir)
                    if size < 1024 * 1024 * 10:
                        continue
                    repo_str = str(repo_dir)
                    if repo_str in seen_paths or any(repo_str.startswith(s + "/") for s in seen_paths):
                        continue
                    seen_paths.add(repo_str)
                    display_name = repo_dir.name.replace("models--", "").replace("--", "/")
                    try:
                        mtime = datetime.fromtimestamp(repo_dir.stat().st_mtime)
                    except OSError:
                        mtime = None
                    items.append(ScanItem(
                        path=repo_dir,
                        size_bytes=size,
                        category=self.CATEGORY,
                        app_name="Hugging Face",
                        is_safe=False,
                        selected=False,
                        last_modified=mtime,
                        description=t("desc.ai_model", tool="Hugging Face", name=display_name),
                        description_key="desc.ai_model",
                        description_args={"tool": "Hugging Face", "name": display_name},
                    ))
            except OSError:
                pass

        # 其他 AI 工具：整目录报告
        for tool_name, paths in AI_MODEL_CACHES.items():
            for pattern in paths:
                for p in _expand(pattern):
                    if not p.exists():
                        continue
                    size = get_dir_size(p)
                    if size < 1024 * 1024 * 10:
                        continue
                    p_str = str(p)
                    if p_str in seen_paths or any(p_str.startswith(s + "/") for s in seen_paths):
                        continue
                    seen_paths.add(p_str)
                    try:
                        mtime = datetime.fromtimestamp(p.stat().st_mtime)
                    except OSError:
                        mtime = None
                    items.append(ScanItem(
                        path=p,
                        size_bytes=size,
                        category=self.CATEGORY,
                        app_name=tool_name,
                        is_safe=False,
                        selected=False,
                        last_modified=mtime,
                        description=t("desc.ai_model", tool=tool_name, name=p.name),
                        description_key="desc.ai_model",
                        description_args={"tool": tool_name, "name": p.name},
                    ))

        return sorted(items, key=lambda x: x.size_bytes, reverse=True)
