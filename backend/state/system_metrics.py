from datetime import datetime


def get_disk_usage():
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        return {
            "total": total,
            "used": used,
            "free": free,
            "used_percent": round(used / total * 100, 2)
        }
    except Exception:
        return {"total": 0, "used": 0, "free": 0, "used_percent": 0}


def get_memory_usage():
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "used": mem.used,
            "free": mem.available,
            "used_percent": mem.percent
        }
    except Exception:
        return {"total": 0, "used": 0, "free": 0, "used_percent": 0}


def get_system_uptime():
    try:
        import psutil
        boot_time = psutil.boot_time()
        uptime = int(datetime.now().timestamp()) - boot_time
        return {
            "seconds": uptime,
            "hours": round(uptime / 3600, 2),
            "days": round(uptime / 86400, 2)
        }
    except Exception:
        return {"seconds": 0, "hours": 0, "days": 0}
