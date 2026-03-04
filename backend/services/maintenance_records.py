from typing import Dict

from .json_store import JsonStore


class MaintenanceRecordService:
    def __init__(self, store: JsonStore):
        self.store = store

    def load_records(self) -> Dict[str, dict]:
        data = self.store.load()
        return data if isinstance(data, dict) else {}

    def save_records(self, records: Dict[str, dict]) -> None:
        self.store.save(records if isinstance(records, dict) else {})
