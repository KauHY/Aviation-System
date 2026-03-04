from typing import Dict

from .json_store import JsonStore


class ContractsStorageService:
    def __init__(self, store: JsonStore):
        self.store = store

    def load_contracts(self) -> Dict[str, dict]:
        data = self.store.load()
        return data if isinstance(data, dict) else {}

    def save_contracts(self, data: Dict[str, dict]) -> None:
        self.store.save(data if isinstance(data, dict) else {})
