import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class SystemWorkflow:
    def create_backup(self, backup_dir: str, files: List[Tuple[str, str]]) -> Tuple[Optional[str], Optional[str]]:
        try:
            import zipfile

            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"backup_{timestamp}.zip")

            with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                for source, target in files:
                    if source and os.path.exists(source):
                        zipf.write(source, target)

            return backup_file, None
        except Exception as exc:
            return None, str(exc)

    def get_latest_backup(self, backup_dir: str) -> Optional[str]:
        if not os.path.exists(backup_dir):
            return None

        backup_files = [name for name in os.listdir(backup_dir) if name.endswith(".zip")]
        if not backup_files:
            return None

        backup_files.sort(reverse=True)
        return os.path.join(backup_dir, backup_files[0])

    def restore_backup(self, backup_file, restore_files: Dict[str, str]) -> Optional[str]:
        try:
            import zipfile
            import shutil

            temp_dir = f"temp_restore_{int(datetime.now().timestamp())}"
            os.makedirs(temp_dir, exist_ok=True)

            with zipfile.ZipFile(backup_file, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            for source, target in restore_files.items():
                source_path = os.path.join(temp_dir, source)
                if os.path.exists(source_path):
                    shutil.copy2(source_path, target)

            shutil.rmtree(temp_dir)
            return None
        except Exception as exc:
            return str(exc)

    def clear_cache(self, temp_dirs: List[str]) -> bool:
        cleared = False
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                cleared = True
        return cleared

    def clear_logs(self, log_dir: str = ".") -> bool:
        cleared = False
        log_files = [name for name in os.listdir(log_dir) if name.endswith(".log") or name.startswith("log_")]
        for log_file in log_files:
            os.remove(os.path.join(log_dir, log_file))
            cleared = True
        return cleared
