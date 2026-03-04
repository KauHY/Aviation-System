import json
import os
from typing import Any, Callable


class JsonStore:
    def __init__(self, file_path: str, default_factory: Callable[[], Any]):
        self.file_path = file_path
        self.default_factory = default_factory

    def load(self) -> Any:
        if not os.path.exists(self.file_path):
            return self.default_factory()
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self.default_factory()

    def save(self, data: Any) -> None:
        base_dir = os.path.dirname(self.file_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
