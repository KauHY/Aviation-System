"""
权限管理模块
实现基于角色的访问控制（RBAC）
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from functools import wraps
from fastapi import Request, HTTPException, status
import time


class Permission(str, Enum):
    """权限枚举"""
    # 维修记录权限
    MAINTENANCE_VIEW = "maintenance:view"
    MAINTENANCE_CREATE = "maintenance:create"
    MAINTENANCE_EDIT = "maintenance:edit"
    MAINTENANCE_DELETE = "maintenance:delete"
    MAINTENANCE_APPROVE = "maintenance:approve"
    MAINTENANCE_UPLOAD = "maintenance:upload"
    
    # 任务管理权限
    TASK_VIEW = "task:view"
    TASK_CREATE = "task:create"
    TASK_EDIT = "task:edit"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    
    # 航班信息权限
    FLIGHT_VIEW = "flight:view"
    
    # 航空器信息权限
    AIRCRAFT_VIEW = "aircraft:view"
    
    # 用户管理权限
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"
    
    # 角色管理权限
    ROLE_VIEW = "role:view"
    ROLE_CREATE = "role:create"
    ROLE_EDIT = "role:edit"
    ROLE_DELETE = "role:delete"
    
    # 权限分配权限
    PERMISSION_ASSIGN = "permission:assign"
    
    # 系统设置权限
    SYSTEM_SETTINGS = "system:settings"
    
    # 系统监控权限
    SYSTEM_MONITOR = "system:monitor"
    
    # 数据备份权限
    DATA_BACKUP = "data:backup"
    DATA_RESTORE = "data:restore"
    
    # 日志查看权限
    LOG_VIEW = "log:view"
    
    # 区块链管理权限
    BLOCKCHAIN_VIEW = "blockchain:view"
    BLOCKCHAIN_MANAGE = "blockchain:manage"
    
    # 报表生成权限
    REPORT_GENERATE = "report:generate"
    REPORT_EXPORT = "report:export"


class Role(str, Enum):
    """角色枚举"""
    ADMIN = "admin"
    MANAGER = "manager"
    TECHNICIAN = "technician"
    USER = "user"


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.permissions = self._init_permissions()
    
    def _init_permissions(self) -> Dict[str, Dict[str, List[str]]]:
        """初始化权限配置"""
        return {
            # 技术人员权限
            Role.TECHNICIAN: {
                "maintenance_records": [
                    Permission.MAINTENANCE_VIEW,
                    Permission.MAINTENANCE_CREATE,
                    Permission.MAINTENANCE_EDIT,
                    Permission.MAINTENANCE_UPLOAD
                ],
                "tasks": [
                    Permission.TASK_VIEW
                ],
                "flights": [
                    Permission.FLIGHT_VIEW
                ],
                "aircraft": [
                    Permission.AIRCRAFT_VIEW
                ]
            },
            # 管理人员权限
            Role.MANAGER: {
                "maintenance_records": [
                    Permission.MAINTENANCE_VIEW,
                    Permission.MAINTENANCE_CREATE,
                    Permission.MAINTENANCE_EDIT,
                    Permission.MAINTENANCE_DELETE,
                    Permission.MAINTENANCE_APPROVE
                ],
                "tasks": [
                    Permission.TASK_VIEW,
                    Permission.TASK_CREATE,
                    Permission.TASK_EDIT,
                    Permission.TASK_DELETE,
                    Permission.TASK_ASSIGN
                ],
                "flights": [
                    Permission.FLIGHT_VIEW
                ],
                "aircraft": [
                    Permission.AIRCRAFT_VIEW
                ],
                "system": [
                    Permission.SYSTEM_MONITOR,
                    Permission.REPORT_GENERATE,
                    Permission.REPORT_EXPORT
                ]
            },
            # 总负责人权限
            Role.ADMIN: {
                "maintenance_records": [
                    Permission.MAINTENANCE_VIEW,
                    Permission.MAINTENANCE_CREATE,
                    Permission.MAINTENANCE_EDIT,
                    Permission.MAINTENANCE_DELETE,
                    Permission.MAINTENANCE_APPROVE
                ],
                "tasks": [
                    Permission.TASK_VIEW,
                    Permission.TASK_CREATE,
                    Permission.TASK_EDIT,
                    Permission.TASK_DELETE,
                    Permission.TASK_ASSIGN
                ],
                "flights": [
                    Permission.FLIGHT_VIEW
                ],
                "aircraft": [
                    Permission.AIRCRAFT_VIEW
                ],
                "users": [
                    Permission.USER_VIEW,
                    Permission.USER_CREATE,
                    Permission.USER_EDIT,
                    Permission.USER_DELETE
                ],
                "roles": [
                    Permission.ROLE_VIEW,
                    Permission.ROLE_CREATE,
                    Permission.ROLE_EDIT,
                    Permission.ROLE_DELETE
                ],
                "permissions": [
                    Permission.PERMISSION_ASSIGN
                ],
                "system": [
                    Permission.SYSTEM_SETTINGS,
                    Permission.SYSTEM_MONITOR,
                    Permission.DATA_BACKUP,
                    Permission.DATA_RESTORE,
                    Permission.LOG_VIEW,
                    Permission.BLOCKCHAIN_VIEW,
                    Permission.BLOCKCHAIN_MANAGE,
                    Permission.REPORT_GENERATE,
                    Permission.REPORT_EXPORT
                ]
            },
            # 普通用户权限
            Role.USER: {
                "maintenance_records": [
                    Permission.MAINTENANCE_VIEW
                ],
                "tasks": [],
                "flights": [
                    Permission.FLIGHT_VIEW
                ],
                "aircraft": [
                    Permission.AIRCRAFT_VIEW
                ]
            }
        }
    
    def get_role_permissions(self, role: str) -> List[str]:
        """获取角色的所有权限"""
        role_permissions = self.permissions.get(role, {})
        all_permissions = []
        for resource_perms in role_permissions.values():
            all_permissions.extend(resource_perms)
        return list(set(all_permissions))
    
    def has_permission(self, role: str, permission: str) -> bool:
        """检查角色是否有指定权限"""
        role_permissions = self.get_role_permissions(role)
        return permission in role_permissions
    
    def check_data_access(self, role: str, resource: str, 
                       data_owner: str = None, current_user: str = None) -> bool:
        """检查数据访问权限（数据隔离）"""
        
        # 技术人员只能访问自己创建的数据
        if role == Role.TECHNICIAN:
            if resource == "maintenance_record":
                return data_owner == current_user
            elif resource == "task":
                return data_owner == current_user
            return True
        
        # 管理人员可以访问所有数据
        if role == Role.MANAGER:
            return True
        
        # 总负责人可以访问所有数据
        if role == Role.ADMIN:
            return True
        
        # 普通用户只能查看数据
        if role == Role.USER:
            return resource in ["maintenance_record", "task", "flight", "aircraft"]
        
        return False


class PermissionAudit:
    """权限审计日志"""
    
    def __init__(self):
        self.audit_log = []
    
    def log_permission_check(self, user_id: str, user_role: str, resource: str, 
                          action: str, allowed: bool, reason: str = "",
                          ip_address: str = "unknown", data_id: str = None):
        """记录权限检查"""
        audit_entry = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "user_role": user_role,
            "resource": resource,
            "action": action,
            "allowed": allowed,
            "reason": reason,
            "ip_address": ip_address,
            "data_id": data_id
        }
        self.audit_log.append(audit_entry)
    
    def get_audit_log(self, user_id: str = None, 
                     start_time: float = None, end_time: float = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志"""
        filtered_log = self.audit_log
        
        if user_id:
            filtered_log = [log for log in filtered_log if log.get("user_id") == user_id]
        
        if start_time:
            filtered_log = [log for log in filtered_log if log.get("timestamp") >= start_time]
        
        if end_time:
            filtered_log = [log for log in filtered_log if log.get("timestamp") <= end_time]
        
        return filtered_log[-limit:]


# 全局权限管理器实例
permission_manager = PermissionManager()
permission_audit = PermissionAudit()


def require_permission(permission: str):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            
            # 从参数中获取request
            if args and hasattr(args[0], 'headers'):
                request = args[0]
            elif 'request' in kwargs:
                request = kwargs['request']
            
            if not request:
                return await func(*args, **kwargs)
            
            # 从请求中获取用户信息
            token = request.cookies.get('access_token')
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未登录"
                )
            
            # 解析token获取用户角色（这里简化处理，实际应该从token解析）
            user_role = request.headers.get('X-User-Role', 'user')
            user_id = request.headers.get('X-User-Id', 'unknown')
            
            # 检查权限
            if not permission_manager.has_permission(user_role, permission):
                permission_audit.log_permission_check(
                    user_id=user_id,
                    user_role=user_role,
                    resource=permission.split(':')[0],
                    action=permission.split(':')[1],
                    allowed=False,
                    reason="权限不足"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"您没有权限执行此操作，需要权限: {permission}"
                )
            
            # 记录权限检查通过
            permission_audit.log_permission_check(
                user_id=user_id,
                user_role=user_role,
                resource=permission.split(':')[0],
                action=permission.split(':')[1],
                allowed=True
            )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_data_access(resource: str):
    """数据访问权限装饰器（数据隔离）"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = None
            
            # 从参数中获取request
            if args and hasattr(args[0], 'headers'):
                request = args[0]
            elif 'request' in kwargs:
                request = kwargs['request']
            
            if not request:
                return await func(*args, **kwargs)
            
            # 从请求中获取用户信息
            token = request.cookies.get('access_token')
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未登录"
                )
            
            user_role = request.headers.get('X-User-Role', 'user')
            user_id = request.headers.get('X-User-Id', 'unknown')
            data_owner = kwargs.get('data_owner')
            
            # 检查数据访问权限
            if not permission_manager.check_data_access(user_role, resource, data_owner, user_id):
                permission_audit.log_permission_check(
                    user_id=user_id,
                    user_role=user_role,
                    resource=resource,
                    action="access",
                    allowed=False,
                    reason="数据隔离限制"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"您没有权限访问此数据"
                )
            
            # 记录权限检查通过
            permission_audit.log_permission_check(
                user_id=user_id,
                user_role=user_role,
                resource=resource,
                action="access",
                allowed=True,
                data_id=data_owner
            )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator
