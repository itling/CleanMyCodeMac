import plistlib
from pathlib import Path
from typing import Dict


def detect_installed_apps() -> Dict[str, str]:
    """返回 {bundle_id: app_name} 字典"""
    apps = {}
    for app_path in Path("/Applications").glob("*.app"):
        plist_path = app_path / "Contents/Info.plist"
        if not plist_path.exists():
            continue
        try:
            with open(plist_path, "rb") as f:
                plist = plistlib.load(f)
            bundle_id = plist.get("CFBundleIdentifier", "")
            name = plist.get("CFBundleName") or plist.get("CFBundleDisplayName") or app_path.stem
            if bundle_id:
                apps[bundle_id] = name
        except Exception:
            continue

    # 也检查用户 Applications
    user_apps = Path.home() / "Applications"
    if user_apps.exists():
        for app_path in user_apps.glob("*.app"):
            plist_path = app_path / "Contents/Info.plist"
            if not plist_path.exists():
                continue
            try:
                with open(plist_path, "rb") as f:
                    plist = plistlib.load(f)
                bundle_id = plist.get("CFBundleIdentifier", "")
                name = plist.get("CFBundleName") or app_path.stem
                if bundle_id:
                    apps[bundle_id] = name
            except Exception:
                continue

    return apps
