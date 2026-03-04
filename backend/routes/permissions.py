from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt

import app_state
from permission_manager import permission_manager, permission_audit, Role

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


@router.get("/api/permissions/audit")
async def get_permission_audit(request: Request):
    """获取权限审计日志（兼容旧接口）"""
    token = request.cookies.get('access_token')
    if not token:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return JSONResponse(status_code=401, content={"error": "未登录"})

    try:
        payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
        user_role = payload.get('role', 'user')
    except JWTError:
        return JSONResponse(status_code=401, content={"error": "令牌无效"})

    if user_role != Role.ADMIN and user_role != Role.ADMIN.value:
        return JSONResponse(status_code=403, content={"error": "您没有权限查看审计日志"})

    user_id_filter = request.query_params.get('user_id')
    limit = int(request.query_params.get('limit', 100))
    logs = permission_audit.get_audit_log(user_id=user_id_filter, limit=limit)

    return JSONResponse(status_code=200, content={
        "logs": logs,
        "total": len(logs)
    })
