from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt


def create_access_token(
    data: dict,
    secret_key: str,
    algorithm: str,
    expires_delta: Optional[timedelta] = None
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def verify_token(token: str, secret_key: str, algorithm: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        address = payload.get("sub")
        if address is None:
            raise credentials_exception
        return address
    except JWTError:
        raise credentials_exception


async def get_current_user_from_token(
    request,
    secret_key: str,
    algorithm: str,
    auth_service,
    users: dict
) -> Optional[dict]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        address = payload.get("sub")
        username = payload.get("username")

        if address:
            user = auth_service.get_user_by_address(address)
            if user:
                if "is_admin" not in user:
                    user["is_admin"] = False
                return user

        if username:
            user_info = users.get(username)
            if user_info:
                return {
                    "address": user_info.get("address", address),
                    "name": user_info.get("name", username),
                    "employee_id": user_info.get("employee_id"),
                    "is_admin": user_info.get("role") == "admin",
                    "role": user_info.get("role", "user")
                }

        return None
    except Exception as exc:
        print("[DEBUG] get_current_user error: " + str(exc))
        return None
