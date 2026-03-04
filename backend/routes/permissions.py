from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt

import app_state
from permission_manager import permission_manager

router = APIRouter()

@router.get("/api/permissions/role")
async def get_role_permissions(request: Request):
    """获取指定角色的权限列表"""
    role = request.query_params.get('role', 'user')
    permissions = permission_manager.get_role_permissions(role)
    return JSONResponse(status_code=200, content={
        "role": role,
        "permissions": permissions
    })

@router.get("/api/permissions/check")
async def check_permission(request: Request):
    """检查用户是否有指定权限"""
    token = request.cookies.get('access_token')
    if not token:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
        user_role = payload.get('role', 'user')
        return JSONResponse(status_code=200, content={
            "role": user_role,
            "authorized": True
        })
    except JWTError:
        return JSONResponse(status_code=401, content={"error": "令牌无效"})
