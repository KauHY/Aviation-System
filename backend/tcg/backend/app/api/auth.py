from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.models.user import User
from app.services.storage import storage_service

router = APIRouter()

# 配置JWT
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_active_user(token: str = Depends(oauth2_scheme)):
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

@router.post("/auth/login", response_model=Dict[str, Any])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录"""
    # 这里使用address作为username
    user = storage_service.get_user_by_address(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 简化处理，实际项目中应该验证密码
    # 这里我们假设所有用户都可以登录，主要通过地址识别
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.address}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@router.post("/auth/guest", response_model=Dict[str, Any])
def guest_login():
    """访客登录（只读模式）"""
    return {
        "success": True,
        "message": "访客登录成功",
        "isGuest": True
    }

@router.get("/auth/me", response_model=Dict[str, Any])
async def get_me(current_user: User = Depends(get_current_active_user)):
    """获取当前登录用户信息"""
    return {
        "success": True,
        "data": current_user.to_dict()
    }