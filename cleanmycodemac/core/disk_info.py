import shutil


def get_disk_info() -> dict:
    """返回根磁盘的使用信息（字节）"""
    result = {
        "total": 0,
        "used": 0,
        "free": 0,
        "percent_used": 0.0,
    }
    try:
        usage = shutil.disk_usage("/")
        result["total"] = usage.total
        result["used"] = usage.used
        result["free"] = usage.free
        if usage.total > 0:
            result["percent_used"] = usage.used / usage.total * 100
    except Exception:
        pass
    return result
