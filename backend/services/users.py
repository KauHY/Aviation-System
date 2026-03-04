from typing import Dict, Tuple

from .json_store import JsonStore


class UserService:
    def __init__(self, store: JsonStore):
        self.store = store

    def load_users(self) -> Tuple[Dict[str, dict], Dict[str, str]]:
        raw = self.store.load()
        if not isinstance(raw, dict):
            return {}, {}

        users = {}
        user_roles = {}
        for username, info in raw.items():
            if isinstance(info, dict):
                users[username] = info
                user_roles[username] = info.get("role", "user")
            else:
                role = user_roles.get(username, "user")
                users[username] = {
                    "password": info,
                    "role": role
                }
                user_roles[username] = role

        return users, user_roles

    def save_users(self, users: Dict[str, dict], user_roles: Dict[str, str]) -> None:
        data = {}
        for username, info in users.items():
            if isinstance(info, dict):
                data[username] = info
            else:
                data[username] = {
                    "password": info,
                    "role": user_roles.get(username, "user")
                }
        self.store.save(data)
