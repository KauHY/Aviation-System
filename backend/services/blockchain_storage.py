from typing import Dict

from .json_store import JsonStore


class BlockchainStorageService:
    def __init__(self, store: JsonStore):
        self.store = store

    def load_blockchain(self) -> Dict[str, dict]:
        data = self.store.load()
        return data if isinstance(data, dict) else {}

    def save_blockchain(self, data: Dict[str, dict]) -> None:
        self.store.save(data if isinstance(data, dict) else {})
