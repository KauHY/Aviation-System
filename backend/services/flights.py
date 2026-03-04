from typing import List

from .json_store import JsonStore


class FlightService:
    def __init__(self, store: JsonStore):
        self.store = store

    def load_flights(self) -> List[dict]:
        data = self.store.load()
        return data if isinstance(data, list) else []

    def save_flights(self, flights: List[dict]) -> None:
        self.store.save(flights if isinstance(flights, list) else [])
