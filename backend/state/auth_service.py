from datetime import datetime
from typing import Callable


class AuthService:
    def __init__(self, user_provider: Callable[[], dict]):
        self.user_provider = user_provider
        self.use_passlib = False
        self.pwd_context = None
        try:
            from passlib.context import CryptContext
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            self.use_passlib = True
        except Exception as exc:
            print("Passlib import failed, using plain password validation: " + str(exc))

    def _find_user_by_address(self, address: str):
        users = self.user_provider() or {}
        for user_info in users.values():
            if user_info.get("address") == address:
                return user_info
        return None

    def get_user_by_address(self, address: str):
        return self._find_user_by_address(address)

    def authenticate(self, address: str, password: str):
        user = self._find_user_by_address(address)
        if not user:
            return None
        stored_password = user.get("password", "")
        if not self.verify_password(password, stored_password):
            return None
        return user

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        plain_password = (plain_password or "")[:72]
        if self.use_passlib and self.pwd_context:
            try:
                return self.pwd_context.verify(plain_password, hashed_password)
            except Exception as exc:
                print("Passlib verify failed, fallback to plain text: " + str(exc))
                return plain_password == hashed_password
        return plain_password == hashed_password

    def get_password_hash(self, password: str) -> str:
        password = (password or "")[:72]
        if self.use_passlib and self.pwd_context:
            try:
                return self.pwd_context.hash(password)
            except Exception as exc:
                print("Passlib hash failed, fallback to plain text: " + str(exc))
                return password
        return password

    def authorize_user(self, address: str, name: str, employee_id: str, password: str) -> bool:
        existing = self._find_user_by_address(address)
        if existing:
            return False
        users = self.user_provider() or {}
        username = name or address[-8:]
        if username in users:
            username = f"{username}_{address[-6:]}"
        users[username] = {
            "password": self.get_password_hash(password),
            "role": "user",
            "address": address,
            "name": name or username,
            "employee_id": employee_id,
            "created_at": int(datetime.now().timestamp())
        }
        return True

    def revoke_user(self, address: str) -> bool:
        users = self.user_provider() or {}
        for username, user_info in list(users.items()):
            if user_info.get("address") == address:
                del users[username]
                return True
        return False

    def get_authorized_users(self) -> list:
        users = self.user_provider() or {}
        return list(users.values())
