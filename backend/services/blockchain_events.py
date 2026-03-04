from typing import List

from .json_store import JsonStore


class BlockchainEventService:
    def __init__(self, store: JsonStore):
        self.store = store

    def load_events(self) -> List[dict]:
        data = self.store.load()
        return data if isinstance(data, list) else []

    def save_events(self, events: List[dict]) -> None:
        self.store.save(events if isinstance(events, list) else [])
