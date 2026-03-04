import uuid
from datetime import datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt

import app_state
from permission_manager import permission_manager, permission_audit, Permission, Role
from services.blockchain_workflow import BlockchainWorkflow
from services.task_workflow import TaskWorkflow

router = APIRouter()
task_workflow = TaskWorkflow()
blockchain_workflow = BlockchainWorkflow()

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


@router.post("/api/tasks")
async def create_task(request: Request):
    """创建检测任务"""
    try:
        permission_check = _ensure_permission(request, Permission.TASK_CREATE)
        if isinstance(permission_check, JSONResponse):
            return permission_check

        data = await request.json()
        required_fields = ["aircraft_registration", "task_type", "priority", "deadline"]
        for field in required_fields:
            if field not in data:
                return JSONResponse(status_code=400, content={
                    "success": False,
                    "message": f"缺少必填字段: {field}"
                })

        new_task = {
            "id": str(uuid.uuid4())[:12],
            "aircraft_registration": data.get("aircraft_registration", ""),
            "flight_number": data.get("aircraft_registration", ""),
            "task_type": data.get("task_type", ""),
            "priority": data.get("priority", "medium"),
            "status": "pending",
            "assignee_id": data.get("assignee_id") or None,
            "deadline": data.get("deadline", "")
        }

        app_state.tasks.append(new_task)
        app_state.save_tasks()

        return JSONResponse(status_code=201, content={
            "success": True,
            "message": "任务创建成功",
            "task": new_task
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "创建任务失败: " + str(e)
        })


@router.get("/api/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    """获取单个任务详情"""
    permission_check = _ensure_permission(request, Permission.TASK_VIEW)
    if isinstance(permission_check, JSONResponse):
        return permission_check

    task = next((item for item in app_state.tasks if str(item.get("id")) == str(task_id)), None)
    if not task:
        return JSONResponse(status_code=404, content={
            "success": False,
            "message": "任务不存在"
        })

    return JSONResponse(status_code=200, content={
        "success": True,
        "task": task
    })


@router.put("/api/tasks/{task_id}")
async def update_task(task_id: str, request: Request):
    """更新任务"""
    try:
        permission_check = _ensure_permission(request, Permission.TASK_EDIT)
        if isinstance(permission_check, JSONResponse):
            return permission_check

        data = await request.json()
        task = next((item for item in app_state.tasks if str(item.get("id")) == str(task_id)), None)
        if not task:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })

        if "aircraft_registration" in data:
            task["aircraft_registration"] = data["aircraft_registration"]
            task["flight_number"] = data["aircraft_registration"]
        if "task_type" in data:
            task["task_type"] = data["task_type"]
        if "priority" in data:
            task["priority"] = data["priority"]
        if "deadline" in data:
            task["deadline"] = data["deadline"]

        if "status" in data:
            if data["status"] == "completed" and task.get("assignee_id"):
                inspector = next(
                    (item for item in app_state.inspectors if item.get("id") == task.get("assignee_id")),
                    None
                )
                if inspector:
                    inspector["status"] = "available"
                    inspector["current_task"] = None
            task["status"] = data["status"]

        if "assignee_id" in data:
            task["assignee_id"] = data["assignee_id"]

        task["updated_at"] = int(datetime.now().timestamp())
        app_state.save_tasks()

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "任务更新成功",
            "task": task
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "更新任务失败: " + str(e)
        })


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    """删除任务"""
    try:
        permission_check = _ensure_permission(request, Permission.TASK_DELETE)
        if isinstance(permission_check, JSONResponse):
            return permission_check

        task_index = next(
            (index for index, item in enumerate(app_state.tasks) if str(item.get("id")) == str(task_id)),
            None
        )
        if task_index is None:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })

        task = app_state.tasks[task_index]
        if task.get("assignee_id"):
            inspector = next(
                (item for item in app_state.inspectors if item.get("id") == task.get("assignee_id")),
                None
            )
            if inspector:
                inspector["status"] = "available"
                inspector["current_task"] = None

        app_state.tasks.pop(task_index)
        app_state.save_tasks()

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "任务删除成功"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "删除任务失败: " + str(e)
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


@router.post("/api/maintenance")
async def create_maintenance_record_from_task(request: Request):
    """兼容旧版接口：从任务创建维修记录"""
    try:
        data = await request.json()

        required_fields = [
            "aircraft_registration",
            "task_type",
            "maintenance_type",
            "fault_description",
            "maintenance_measures",
            "task_id"
        ]
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(status_code=400, content={
                    "success": False,
                    "message": f"缺少必填字段: {field}"
                })

        task_id = str(data.get("task_id"))
        task = next((item for item in app_state.tasks if str(item.get("id")) == task_id), None)
        if not task:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })

        current_user = _get_current_user_from_request(request)
        if not current_user:
            return JSONResponse(status_code=401, content={
                "success": False,
                "message": "未授权"
            })

        username = current_user.get("username") or ""
        user_info = app_state.users.get(username, {}) if username else {}
        technician_name = user_info.get("name") or username or "未知"

        description_parts = [
            str(data.get("fault_description", "")).strip(),
            str(data.get("maintenance_measures", "")).strip()
        ]
        maintenance_description = "\n".join([item for item in description_parts if item])

        workflow_data = {
            "aircraft_registration": data.get("aircraft_registration", ""),
            "maintenance_type": data.get("maintenance_type", ""),
            "maintenance_date": datetime.now().strftime("%Y-%m-%d"),
            "maintenance_description": maintenance_description,
            "maintenance_duration": data.get("maintenance_duration", ""),
            "parts_used": data.get("parts_used", ""),
            "technician_name": technician_name,
            "technician_id": username or technician_name
        }

        record_id, error_code, error_detail = blockchain_workflow.create_record(
            data=workflow_data,
            maintenance_records=app_state.maintenance_records,
            tasks=app_state.tasks,
            users=app_state.users,
            contract_engine=app_state.contract_engine,
            master_contract=app_state.master_contract,
            blockchain_events=app_state.blockchain_events,
            save_maintenance_records=app_state.save_maintenance_records,
            save_blockchain_events=app_state.save_blockchain_events,
            save_blockchain=app_state.save_blockchain,
            save_contracts=app_state.save_contracts
        )
        if error_code == "missing_field":
            return JSONResponse(status_code=400, content={
                "success": False,
                "message": f"缺少必填字段: {error_detail}"
            })
        if error_code:
            return JSONResponse(status_code=500, content={
                "success": False,
                "message": "创建维修记录失败"
            })

        task["status"] = "completed"
        task["updated_at"] = int(datetime.now().timestamp())
        app_state.save_tasks()

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "任务完成成功，维修记录已创建",
            "record_id": record_id
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "创建维修记录失败: " + str(e)
        })


@router.get("/api/aircraft-inspection/{registration}")
async def get_aircraft_inspection_records(registration: str):
    """兼容旧版接口：按飞机注册号查询检修记录"""
    try:
        aircraft_records = []
        for record in app_state.maintenance_records.values():
            if str(record.get("aircraft_registration", "")) != str(registration):
                continue

            aircraft_records.append({
                "id": record.get("id", ""),
                "title": record.get("maintenance_type", ""),
                "description": record.get("maintenance_description", ""),
                "date": record.get("maintenance_date", ""),
                "status": "完成" if record.get("status") == "released" else "进行中",
                "technician": record.get("technician_name", "未知")
            })

        return JSONResponse(status_code=200, content={
            "success": True,
            "records": aircraft_records
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "获取检修记录失败: " + str(e)
        })


@router.get("/api/maintenance/records")
async def get_maintenance_records(aircraft_type: str = None):
    """兼容旧版接口：获取维修记录（支持机型筛选）"""
    try:
        records = []
        query = (aircraft_type or "").strip().lower()

        for record in app_state.maintenance_records.values():
            record_aircraft_type = str(record.get("aircraft_type") or record.get("aircraft_model") or "")
            record_registration = str(record.get("aircraft_registration") or "")

            if query:
                type_match = query in record_aircraft_type.lower()
                registration_match = query in record_registration.lower()
                if not type_match and not registration_match:
                    continue

            records.append({
                "id": record.get("id", ""),
                "maintenance_type": record.get("maintenance_type", ""),
                "maintenance_description": record.get("maintenance_description", ""),
                "maintenance_date": record.get("maintenance_date", ""),
                "status": record.get("status", "pending"),
                "technician_name": record.get("technician_name", "未知"),
                "aircraft_registration": record_registration,
                "aircraft_type": record_aircraft_type
            })

        records.sort(key=lambda item: item.get("maintenance_date") or "", reverse=True)

        return JSONResponse(status_code=200, content={
            "success": True,
            "records": records
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "获取维修记录失败: " + str(e)
        })
