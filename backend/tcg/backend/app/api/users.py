from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from app.models.user import User
from app.services.storage import storage_service
from app.api.deps import get_current_user, get_admin_user

router = APIRouter()

# ================= 用户管理相关API =================

@router.get("/user/me", response_model=Dict[str, Any])
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {"success": True, "data": current_user.to_dict()}

@router.get("/admin/authorized-nodes", response_model=Dict[str, Any])
def get_authorized_users(current_user: User = Depends(get_admin_user)):
    """获取所有授权用户"""
    users = storage_service.get_authorized_users()
    return {
        "success": True,
        "data": [user.to_dict() for user in users]
    }

@router.post("/admin/authorize", response_model=Dict[str, Any])
def authorize_user(
    user_data: Dict[str, str],
    current_user: User = Depends(get_admin_user)
):
    """授权用户"""
    address = user_data.get("address", "")
    if not address:
        raise HTTPException(status_code=400, detail="地址不能为空")
    
    # 检查用户是否存在
    existing_user = storage_service.get_user_by_address(address)
    if existing_user:
        # 更新用户授权状态
        existing_user.is_authorized = True
        success = storage_service.update_user(existing_user)
    else:
        # 创建新用户
        new_user = User(
            address=address,
            name=user_data.get("name", ""),
            emp_id=user_data.get("empId", ""),
            is_authorized=True
        )
        success = storage_service.add_user(new_user)
    
    if not success:
        raise HTTPException(status_code=500, detail="授权失败")
    
    return {
        "success": True,
        "message": f"用户 {address} 授权成功"
    }

@router.post("/admin/revoke", response_model=Dict[str, Any])
def revoke_user(
    user_data: Dict[str, str],
    current_user: User = Depends(get_admin_user)
):
    """取消用户授权"""
    address = user_data.get("address", "")
    if not address:
        raise HTTPException(status_code=400, detail="地址不能为空")
    
    # 检查用户是否存在
    existing_user = storage_service.get_user_by_address(address)
    if not existing_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 更新用户授权状态
    existing_user.is_authorized = False
    success = storage_service.update_user(existing_user)
    
    if not success:
        raise HTTPException(status_code=500, detail="取消授权失败")
    
    return {
        "success": True,
        "message": f"用户 {address} 授权已取消"
    }

@router.post("/user/register", response_model=Dict[str, Any])
def register_user(user_data: Dict[str, str]):
    """注册新用户"""
    address = user_data.get("address", "")
    name = user_data.get("name", "")
    emp_id = user_data.get("empId", "")
    
    if not address:
        raise HTTPException(status_code=400, detail="地址不能为空")
    
    # 检查用户是否已存在
    existing_user = storage_service.get_user_by_address(address)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户已存在")
    
    # 创建新用户
    new_user = User(
        address=address,
        name=name,
        emp_id=emp_id,
        is_authorized=False  # 新用户默认未授权
    )
    
    success = storage_service.add_user(new_user)
    if not success:
        raise HTTPException(status_code=500, detail="注册失败")
    
    return {
        "success": True,
        "message": "注册成功",
        "data": new_user.to_dict()
    }

@router.get("/users", response_model=Dict[str, Any])
def get_all_users(current_user: User = Depends(get_admin_user)):
    """获取所有用户"""
    users = storage_service.get_all_users()
    return {
        "success": True,
        "data": [user.to_dict() for user in users]
    }