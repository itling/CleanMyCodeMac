import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".cleanmycodemac_config.json"

DEFAULT_CONFIG = {
    "large_file_threshold_mb": 500,
    "old_download_days": 30,
    "old_log_days": 7,
    "default_scan_categories": [
        "system_cache",
        "app_cache",
        "log",
        "download",
        "large_file",
        "trash",
    ],
    "auto_select_safe_items": True,
    "whitelist_paths": [],
    "move_to_trash": True,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(data)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)
    with open(CONFIG_PATH, "w") as f:
        json.dump(merged, f, indent=2)
