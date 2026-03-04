from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt

import app_state
from permission_manager import permission_manager, permission_audit, Permission, Role
from services.task_workflow import TaskWorkflow

router = APIRouter()
task_workflow = TaskWorkflow()

def _get_current_user_from_request(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None

    try:
        payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
    except JWTError:
        return None

    username = payload.get("username")
    role_value = payload.get("role", "user")
    try:
        role = Role(role_value)
    except ValueError:
        role = role_value

    private_key = ""
    if username and username in app_state.users:
        private_key = app_state.users[username].get("private_key", "")

    return {
        "address": payload.get("sub"),
        "username": username,
        "role": role,
        "public_key": payload.get("public_key", ""),
        "private_key": private_key
    }


def _ensure_permission(request: Request, permission: Permission):
    current_user = _get_current_user_from_request(request)
    if not current_user:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "未登录"}
        )

    role = current_user.get("role", Role.USER)
    role_value = role.value if isinstance(role, Role) else str(role)
    user_id = current_user.get("username") or current_user.get("address") or "unknown"

    if not permission_manager.has_permission(role, permission):
        permission_audit.log_permission_check(
            user_id=user_id,
            user_role=role_value,
            resource=permission.split(":")[0],
            action=permission.split(":")[1],
            allowed=False,
            reason="权限不足",
            ip_address=request.client.host if request.client else "unknown"
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": f"权限不足，需要权限: {permission}"}
        )

    permission_audit.log_permission_check(
        user_id=user_id,
        user_role=role_value,
        resource=permission.split(":")[0],
        action=permission.split(":")[1],
        allowed=True,
        ip_address=request.client.host if request.client else "unknown"
    )

    return current_user

# 获取检测人员列表
@router.get("/api/inspectors")
async def get_inspectors(request: Request):
    """获取检测人员列表"""
    permission_check = _ensure_permission(request, Permission.TASK_VIEW)
    if isinstance(permission_check, JSONResponse):
        return permission_check

    # 从用户数据中筛选出角色为technician或user的用户
    technician_users = task_workflow.build_inspectors(app_state.users)
    for inspector in technician_users:
        inspector["position"] = "技术人员"

    # 更新全局inspectors列表
    app_state.inspectors.clear()
    app_state.inspectors.extend(technician_users)

    print(f"[DEBUG] 获取到 {len(technician_users)} 个技术人员")

    return JSONResponse(status_code=200, content={
        "success": True,
        "inspectors": technician_users
    })

# 获取检测任务列表
@router.get("/api/tasks")
async def get_tasks(request: Request):
    """获取检测任务列表"""
    permission_check = _ensure_permission(request, Permission.TASK_VIEW)
    if isinstance(permission_check, JSONResponse):
        return permission_check

    return JSONResponse(status_code=200, content={
        "success": True,
        "tasks": app_state.tasks
    })

# 分配检测任务
@router.post("/api/tasks/assign")
async def assign_task(request: Request):
    """分配检测任务"""
    try:
        permission_check = _ensure_permission(request, Permission.TASK_ASSIGN)
        if isinstance(permission_check, JSONResponse):
            return permission_check

        data = await request.json()
        task_id = data.get("task_id")
        inspector_id = data.get("inspector_id")

        task, error_code = task_workflow.assign_task(
            app_state.tasks,
            app_state.inspectors,
            task_id,
            inspector_id
        )
        if error_code == "task_not_found":
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })
        if error_code == "inspector_not_found":
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "检测人员不存在"
            })
        if error_code == "inspector_busy":
            return JSONResponse(status_code=400, content={
                "success": False,
                "message": "检测人员当前忙"
            })

        # 保存任务数据
        app_state.save_tasks()

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "任务分配成功",
            "task": task
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "分配任务失败: " + str(e)
        })

# 完成检测任务
@router.post("/api/tasks/complete")
async def complete_task(request: Request):
    """完成检测任务"""
    try:
        permission_check = _ensure_permission(request, Permission.TASK_EDIT)
        if isinstance(permission_check, JSONResponse):
            return permission_check

        current_user = permission_check
        data = await request.json()

        record_id, error_code, error_detail = task_workflow.complete_task(
            tasks=app_state.tasks,
            inspectors=app_state.inspectors,
            maintenance_records=app_state.maintenance_records,
            blockchain_events=app_state.blockchain_events,
            data=data,
            current_user=current_user,
            contract_engine=app_state.contract_engine,
            master_contract=app_state.master_contract,
            users=app_state.users,
            save_tasks=app_state.save_tasks,
            save_maintenance_records=app_state.save_maintenance_records,
            save_blockchain_events=app_state.save_blockchain_events,
            save_blockchain=app_state.save_blockchain,
            save_contracts=app_state.save_contracts,
            description_builder=lambda task: f"完成{task.get('flight_number', '')}航班的{task.get('task_type', '')}任务"
        )
        if error_code == "task_not_found":
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })
        if error_code == "blockchain_error":
            return JSONResponse(status_code=500, content={
                "success": False,
                "message": "创建维修记录失败: " + (error_detail or "区块链异常")
            })

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "维修记录创建成功",
            "record_id": record_id
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "创建维修记录失败: " + str(e)
        })
