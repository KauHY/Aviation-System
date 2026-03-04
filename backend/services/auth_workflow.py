import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from jose import JWTError, jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class AuthWorkflow:
    def register_user(
        self,
        data: dict,
        users: Dict[str, dict],
        user_roles: Dict[str, str],
        auth,
        save_user_data
    ) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "user")

        if not username or not password:
            return None, "missing_fields", None

        if len(password) < 6:
            return None, "weak_password", None

        if username in users:
            return None, "username_exists", None

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        address = "0x" + hashlib.sha256(public_pem.encode()).hexdigest()[:40]

        if hasattr(auth, "get_password_hash"):
            hashed_password = auth.get_password_hash(password)
        else:
            hashed_password = password

        users[username] = {
            "password": hashed_password,
            "role": role,
            "address": address,
            "name": username,
            "employee_id": "EMP" + address[-8:],
            "public_key": public_pem,
            "private_key": private_pem,
            "created_at": int(datetime.now().timestamp())
        }
        user_roles[username] = role

        try:
            if hasattr(auth, "authorize_user"):
                auth.authorize_user(address, username, "EMP" + address[-8:], password)
        except Exception:
            pass

        save_user_data()

        result = {
            "message": "registered",
            "username": username,
            "role": role,
            "address": address,
            "employee_id": "EMP" + address[-8:],
            "public_key": public_pem,
            "private_key": private_pem,
            "info": "private_key_saved"
        }
        return result, None, None

    def login_user(
        self,
        data: dict,
        users: Dict[str, dict],
        user_roles: Dict[str, str],
        auth,
        create_access_token,
        access_token_minutes: int,
        save_user_data
    ) -> Tuple[Optional[dict], Optional[str], Optional[str]]:
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return None, "missing_fields", None

        if username not in users:
            return None, "invalid_credentials", None

        user_info = users[username]
        user_password = user_info.get("password", user_info)

        if hasattr(auth, "verify_password"):
            if not auth.verify_password(password, user_password):
                return None, "invalid_credentials", None
        else:
            if user_password != password:
                return None, "invalid_credentials", None

        role = user_info.get("role", user_roles.get(username, "user"))
        address = user_info.get("address", "0x" + hashlib.sha256(username.encode()).hexdigest()[:40])

        private_key_obj = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        private_pem = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        public_key_obj = private_key_obj.public_key()
        public_pem = public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        address = "0x" + hashlib.sha256(public_pem.encode()).hexdigest()[:40]

        user_info["public_key"] = public_pem
        user_info["address"] = address
        if "employee_id" not in user_info:
            user_info["employee_id"] = "EMP" + address[-8:]

        save_user_data()

        access_token_expires = timedelta(minutes=access_token_minutes)
        access_token = create_access_token(
            data={
                "sub": address,
                "username": username,
                "public_key": public_pem,
                "role": role
            },
            expires_delta=access_token_expires
        )

        result = {
            "message": "login_success",
            "username": username,
            "role": role,
            "address": address,
            "public_key": public_pem,
            "private_key": private_pem,
            "employee_id": user_info.get("employee_id", "EMP" + address[-8:]),
            "access_token": access_token
        }

        return result, None, None

    def get_payload_from_request(
        self,
        request,
        secret_key: str,
        algorithm: str
    ) -> Tuple[Optional[dict], Optional[str]]:
        token = request.cookies.get("access_token")
        if not token:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not token:
            return None, "no_token"

        try:
            payload = jwt.decode(token, secret_key, algorithms=[algorithm])
            return payload, None
        except JWTError:
            return None, "invalid_token"

    def update_profile(
        self,
        current_username: str,
        data: dict,
        users: Dict[str, dict],
        save_user_data
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        if current_username not in users:
            return False, "user_not_found", None

        if data.get("new_password"):
            current_password = data.get("current_password")
            if not current_password:
                return False, "missing_current_password", None

            if users[current_username].get("password") != current_password:
                return False, "invalid_password", None

        users[current_username].update({
            "name": data.get("name", users[current_username].get("name", current_username)),
            "employee_id": data.get("employee_id", users[current_username].get("employee_id")),
            "email": data.get("email", users[current_username].get("email")),
            "phone": data.get("phone", users[current_username].get("phone")),
            "specialty": data.get("specialty", users[current_username].get("specialty")),
            "bio": data.get("bio", users[current_username].get("bio"))
        })

        if data.get("new_password"):
            users[current_username]["password"] = data["new_password"]

        save_user_data()
        return True, None, None

    def get_current_user_data(self, username: str, users: Dict[str, dict]) -> Optional[dict]:
        if username not in users:
            return None

        user_data = users[username]
        return {
            "username": username,
            "name": user_data.get("name", username),
            "employee_id": user_data.get("employee_id"),
            "email": user_data.get("email"),
            "phone": user_data.get("phone"),
            "specialty": user_data.get("specialty"),
            "bio": user_data.get("bio"),
            "role": user_data.get("role"),
            "address": user_data.get("address"),
            "public_key": user_data.get("public_key")
        }

    def get_user_keys(self, username: str, users: Dict[str, dict]) -> Optional[dict]:
        if username not in users:
            return None

        user_data = users[username]
        return {
            "username": username,
            "public_key": user_data.get("public_key", ""),
            "private_key": user_data.get("private_key", "")
        }
