from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional

from app.models.user import User
from app.services.storage import storage_service

# 配置JWT
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        address: str = payload.get("sub")
        if address is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = storage_service.get_user_by_address(address)
    if user is None:
        raise credentials_exception
    return user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取管理员用户"""
    # 这里简化处理，实际项目中应该有管理员角色
    # 暂时假设第一个用户是管理员
    all_users = storage_service.get_all_users()
    if not all_users:
        raise HTTPException(status_code=404, detail="无用户存在")
    
    admin_address = all_users[0].address
    if current_user.address != admin_address:
        raise HTTPException(status_code=403, detail="无管理员权限")
    
    return current_user