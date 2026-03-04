from datetime import datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from jose import JWTError, jwt

import app_state
from contracts.signature_manager import SignatureManager
from permission_manager import permission_manager, permission_audit, Permission, Role

router = APIRouter()

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
    technician_users = []
    for username, user_info in app_state.users.items():
        user_role = user_info.get('role')
        # 同时筛选 technician 和 user 角色（两者都表示技术人员）
        if user_role in ['technician', 'user']:
            # 格式化用户数据为检测人员格式
            technician_users.append({
                "id": username,  # 使用用户名作为ID
                "name": user_info.get("name", username),  # 使用用户的name字段
                "position": "技术人员",
                "specialty": user_info.get("specialty", ""),  # 从用户数据中获取专长
                "status": "available",  # 默认状态为可用
                "current_task": None
            })

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

        # 查找任务
        task = next((t for t in app_state.tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })

        # 查找检测人员
        inspector = next((i for i in app_state.inspectors if i["id"] == inspector_id), None)
        if not inspector:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "检测人员不存在"
            })

        # 检查检测人员状态
        if inspector["status"] == "busy":
            return JSONResponse(status_code=400, content={
                "success": False,
                "message": "检测人员当前忙"
            })

        # 分配任务
        task["assignee_id"] = inspector_id
        task["status"] = "assigned"
        inspector["status"] = "busy"
        inspector["current_task"] = f"{task['aircraft_registration']}{task['task_type']}"

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
        task_id = data.get("task_id")

        # 查找任务
        task = next((t for t in app_state.tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })

        # 查找检测人员
        inspector_id = task.get("assignee_id")
        inspector_name = ""
        if inspector_id:
            inspector = next((i for i in app_state.inspectors if i["id"] == inspector_id), None)
            if inspector:
                inspector["status"] = "available"
                inspector["current_task"] = None
                inspector_name = inspector["name"]

        # 更新任务状态
        task["status"] = "completed"

        # 保存任务数据
        app_state.save_tasks()

        # 自动创建区块链存证记录
        try:
            import uuid
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.asymmetric import padding

            # 生成记录ID
            record_id = str(uuid.uuid4())[:12]

            # 生成样例公钥和签名
            public_pem = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwH6f8f8f8f8f8f8f8f8f8\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nfQIDAQAB\n-----END PUBLIC KEY-----"
            signature = "sample_signature"

            # 创建区块链存证记录
            app_state.maintenance_records[record_id] = {
                "id": record_id,
                "aircraft_registration": task["flight_number"],
                "aircraft_model": "",
                "aircraft_series": "",
                "aircraft_age": "",
                "maintenance_type": task["task_type"],
                "maintenance_date": datetime.now().strftime("%Y-%m-%d"),
                "maintenance_description": f"完成{task['flight_number']}航班的{task['task_type']}任务",
                "maintenance_duration": "",
                "parts_used": "",
                "is_rii": False,
                "technician_name": inspector_name or "未知",
                "technician_id": inspector_id or "",
                "technician_public_key": public_pem,
                "signature": signature,
                "status": "pending",
                "created_at": int(datetime.now().timestamp()),
                "updated_at": int(datetime.now().timestamp()),
                "task_id": task_id
            }

            # 保存维修记录到文件
            app_state.save_maintenance_records()

            # 同时保存到智能合约
            if app_state.contract_engine and app_state.master_contract and current_user:
                try:
                    technician_address = current_user.get("address", "")
                    timestamp = int(datetime.now().timestamp())
                    nonce = str(timestamp)

                    # 创建签名数据
                    sign_data = SignatureManager.create_sign_data(
                        contract_address=app_state.master_contract.contract_address,
                        method="createRecord",
                        params={
                            "aircraft_registration": data.get("aircraft_registration"),
                            "maintenance_type": data.get("maintenance_type"),
                            "description": data.get("fault_description"),
                            "technician_address": technician_address
                        },
                        timestamp=timestamp,
                        nonce=nonce
                    )

                    # 使用私钥签名
                    private_key = current_user.get("private_key", "")
                    if private_key:
                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result

                            # 执行智能合约
                            result = app_state.contract_engine.execute_contract(
                                contract_address=app_state.master_contract.contract_address,
                                method_name="createRecord",
                                params={
                                    "aircraft_registration": data.get("aircraft_registration"),
                                    "maintenance_type": data.get("maintenance_type"),
                                    "description": data.get("fault_description"),
                                    "technician_address": technician_address,
                                    "caller_address": technician_address,
                                    "caller_role": current_user.get("role", "technician")
                                },
                                signature=signature,
                                signer_address=current_user['address'],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )

                            # 检查合约方法执行结果
                            contract_result = result.get("result", {})
                            if contract_result.get("success"):
                                # 获取合约返回的record_id
                                contract_record_id = contract_result.get("record_id", record_id)
                                if contract_record_id:
                                    # 如果合约返回了新的record_id，更新maintenance_records
                                    if record_id in app_state.maintenance_records:
                                        old_record = app_state.maintenance_records.pop(record_id)
                                        old_record["id"] = contract_record_id
                                        app_state.maintenance_records[contract_record_id] = old_record
                                        print(f"[DEBUG] 更新记录ID: {record_id} -> {contract_record_id}")
                                        app_state.save_maintenance_records()

                            # 手动添加创建事件到持久化存储
                            event_data = {
                                "event_name": "RecordCreated",
                                "contract_address": app_state.master_contract.contract_address,
                                "block_index": len(app_state.blockchain_events),
                                "timestamp": timestamp,
                                "data": {
                                    "record_id": contract_record_id,
                                    "aircraft_registration": data.get("aircraft_registration"),
                                    "subchain_address": result.get("subchain_address", ""),
                                    "maintenance_type": data.get("maintenance_type"),
                                    "description": data.get("fault_description"),
                                    "technician_address": technician_address
                                },
                                "signer_address": technician_address
                            }
                            app_state.blockchain_events.append(event_data)
                            app_state.save_blockchain_events()

                            app_state.save_blockchain()
                            app_state.save_contracts()
                            print(f"[DEBUG] 维修记录已保存到区块链: {record_id}")
                        else:
                            print(f"[DEBUG] 签名失败: {signature_result.get('error')}")
                except Exception as e:
                    print(f"[DEBUG] 保存到区块链异常: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[DEBUG] 区块链系统未初始化，仅保存到文件")
        except Exception as e:
            print(f"[ERROR] 创建维修记录异常: {e}")
            import traceback
            traceback.print_exc()

        # 更新任务状态为已完成
        task["status"] = "completed"

        # 释放检测人员
        if task.get("assignee_id"):
            inspector_id = task["assignee_id"]
            inspector = next((i for i in app_state.inspectors if i["id"] == inspector_id), None)
            if inspector:
                inspector["status"] = "available"
                inspector["current_task"] = None

        # 保存任务数据
        app_state.save_tasks()

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
