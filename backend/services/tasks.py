from typing import List

from .json_store import JsonStore


class TaskService:
    def __init__(self, store: JsonStore):
        self.store = store

    def load_tasks(self) -> List[dict]:
        data = self.store.load()
        return data if isinstance(data, list) else []

    def save_tasks(self, tasks: List[dict]) -> None:
        self.store.save(tasks if isinstance(tasks, list) else [])
