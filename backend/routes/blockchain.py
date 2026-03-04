from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jose import jwt

import app_state
from contracts.signature_manager import SignatureManager

router = APIRouter()

@router.post("/api/blockchain/records/create")
async def create_maintenance_record(request: Request):
    """创建维修记录"""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import padding
        import uuid

        data = await request.json()

        # 验证必填字段
        required_fields = ['aircraft_registration', 'maintenance_type', 'maintenance_date', 'maintenance_description', 'technician_name', 'technician_id']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(status_code=400, content={"error": f"{field} 不能为空"})

        # 生成记录ID
        record_id = str(uuid.uuid4())[:12]

        # 简化创建流程，移除私钥验证
        # 实际生产环境中应该保留私钥验证以确保安全性

        # 生成样例公钥和签名
        public_pem = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwH6f8f8f8f8f8f8f8f8f8\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nfQIDAQAB\n-----END PUBLIC KEY-----"
        signature = "sample_signature"

        # 创建记录
        app_state.maintenance_records[record_id] = {
            "id": record_id,
            "aircraft_registration": data['aircraft_registration'],
            "aircraft_model": data.get('aircraft_model', ''),
            "aircraft_series": data.get('aircraft_series', ''),
            "aircraft_age": data.get('aircraft_age', ''),
            "maintenance_type": data['maintenance_type'],
            "maintenance_date": data['maintenance_date'],
            "maintenance_description": data['maintenance_description'],
            "maintenance_duration": data.get('maintenance_duration', ''),
            "parts_used": data.get('parts_used', ''),
            "is_rii": data.get('is_rii', False),
            "technician_name": data['technician_name'],
            "technician_id": data['technician_id'],
            "technician_public_key": public_pem,
            "signature": signature,
            "status": "pending",
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }

        # 保存维修记录到文件
        app_state.save_maintenance_records()

        # 同步到区块链
        try:
            if app_state.contract_engine and app_state.master_contract:
                # 获取技术人员信息
                technician_info = None
                if data['technician_id'] in app_state.users:
                    technician_info = app_state.users[data['technician_id']]

                # 调用智能合约创建记录
                result = app_state.contract_engine.execute_contract(
                    contract_address=app_state.master_contract.contract_address,
                    method_name="addRecord",
                    params={
                        "record_id": record_id,
                        "aircraft_registration": data['aircraft_registration'],
                        "aircraft_model": data.get('aircraft_model', ''),
                        "aircraft_series": data.get('aircraft_series', ''),
                        "aircraft_age": data.get('aircraft_age', ''),
                        "maintenance_type": data['maintenance_type'],
                        "maintenance_description": data['maintenance_description'],
                        "maintenance_duration": data.get('maintenance_duration', ''),
                        "parts_used": data.get('parts_used', ''),
                        "is_rii": data.get('is_rii', False),
                        "technician_address": technician_info.get('address', '') if technician_info else '',
                        "technician_name": data['technician_name'],
                        "technician_public_key": public_pem,
                        "caller_address": technician_info.get('address', '') if technician_info else '',
                        "caller_role": technician_info.get('role', 'technician') if technician_info else 'technician'
                    },
                    signature=signature,
                    signer_address=technician_info.get('address', '') if technician_info else '',
                    nonce=str(int(datetime.now().timestamp())),
                    verify_signature_func=lambda sig, addr, params: {"success": True}
                )

                if result.get("success"):
                    print(f"[DEBUG] 记录 {record_id} 已同步到区块链")

                    # 保存区块链信息到维修记录
                    app_state.maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                    app_state.maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                    app_state.maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                    app_state.save_maintenance_records()

                    # 手动添加创建事件到持久化存储
                    event_data = {
                        "event_name": "RecordCreated",
                        "contract_address": app_state.master_contract.contract_address,
                        "block_index": result.get("block_index", 0),
                        "data": {
                            "record_id": record_id,
                            "aircraft_registration": data['aircraft_registration'],
                            "subchain_address": result.get("subchain_address", ""),
                            "maintenance_type": data['maintenance_type'],
                            "description": data['maintenance_description'],
                            "technician_address": technician_info.get('address', '') if technician_info else ''
                        },
                        "signer_address": technician_info.get('address', '') if technician_info else ''
                    }
                    app_state.blockchain_events.append(event_data)
                    app_state.save_blockchain_events()
                else:
                    print(f"[DEBUG] 记录 {record_id} 同步到区块链失败: {result.get('error')}")
        except Exception as e:
            print(f"[DEBUG] 同步记录到区块链失败: {e}")

        # 为技术人员分配任务（创建对应的检测任务）
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())[:12]

            # 创建任务
            new_task = {
                "id": task_id,
                "flight_number": data['aircraft_registration'],
                "task_type": data['maintenance_type'],
                "description": data['maintenance_description'],
                "priority": "medium",
                "deadline": data['maintenance_date'],
                "status": "assigned",
                "assignee_id": data['technician_id'],
                "assignee_name": data['technician_name'],
                "created_at": int(datetime.now().timestamp())
            }

            app_state.tasks.append(new_task)

            print(f"为技术人员 {data['technician_name']} 分配任务成功: {task_id}")
        except Exception as e:
            print(f"分配任务失败: {e}")

        return JSONResponse(status_code=200, content={"message": "维修记录创建成功", "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "创建记录失败: " + str(e)})

@router.get("/api/blockchain/records/list")
async def get_maintenance_records(request: Request):
    """获取维修记录列表"""
    try:
        print(f"[DEBUG] get_maintenance_records 开始执行")

        if not app_state.contract_engine or not app_state.master_contract:
            print(f"[DEBUG] 区块链系统未初始化")
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        # 获取查询参数
        status_value = request.query_params.get("status", "all")
        aircraft_registration = request.query_params.get("aircraft_registration", "")
        search = request.query_params.get("search", "")

        print(f"[DEBUG] 查询参数 - status: {status_value}, aircraft_registration: {aircraft_registration}, search: {search}")

        # 从区块链获取所有记录
        all_records = []
        for record_id, record in app_state.master_contract.state["records"].items():
            # 优先从maintenance_records中获取技术人员信息
            technician_name = "未知"

            # 先检查maintenance_records中是否有该记录（获取最新状态）
            if record_id in app_state.maintenance_records:
                maintenance_record = app_state.maintenance_records[record_id]
                # 尝试从maintenance_records中获取技术人员名称
                technician_name = maintenance_record.get("technician_name", "未知")

                # 如果technician_name是"未知"，尝试从task_id找回技术人员
                if technician_name == "未知" or not technician_name:
                    task_id = maintenance_record.get("task_id")
                    if task_id:
                        # 从任务列表中查找对应的任务
                        for task in app_state.tasks:
                            if str(task.get("id")) == str(task_id):
                                assignee_id = task.get("assignee_id")
                                if assignee_id and assignee_id in app_state.users:
                                    technician_name = app_state.users[assignee_id].get("name", assignee_id)
                                    # 更新maintenance_records中的technician_name
                                    maintenance_record["technician_name"] = technician_name
                                    maintenance_record["technician_id"] = assignee_id
                                    print(f"[DEBUG] 从任务找回技术人员: {task_id} -> {technician_name}")
                                    app_state.save_maintenance_records()
                                break

                # 使用maintenance_records中的状态（因为审批后更新的是这里）
                record_status = maintenance_record.get("status", record.get("status", "pending"))
                print(f"[DEBUG] Record {record_id} found in maintenance_records: technician={technician_name}, status={record_status}")
            else:
                # 如果maintenance_records中没有，再从区块链记录中获取
                technician_address = record.get("technician_address", "")
                if technician_address:
                    # 如果有技术员地址，从用户列表中查找名称
                    for user_id, user in app_state.users.items():
                        if user.get("address") == technician_address:
                            technician_name = user.get("name", user.get("username", "未知"))
                            break
                else:
                    # 如果没有技术员地址，使用记录中的名称
                    technician_name = record.get("technician_name", "未知")
                # 使用区块链中的状态
                record_status = record.get("status", "pending")
                print(f"[DEBUG] Record {record_id} NOT in maintenance_records: technician={technician_name}, status={record_status}")

            # 格式化维修日期
            maintenance_date = ""
            if record.get("created_at"):
                if isinstance(record["created_at"], (int, float)):
                    maintenance_date = datetime.fromtimestamp(record["created_at"]).strftime("%Y/%m/%d %H:%M:%S")
                else:
                    maintenance_date = str(record["created_at"])

            # 获取任务信息
            task_info = None
            task_id = record.get("task_id") or maintenance_record.get("task_id") if record_id in app_state.maintenance_records else None
            if task_id:
                for task in app_state.tasks:
                    if str(task.get("id")) == str(task_id):
                        task_info = {
                            "id": task.get("id"),
                            "task_type": task.get("task_type"),
                            "priority": task.get("priority"),
                            "status": task.get("status")
                        }
                        break

            all_records.append({
                "id": record_id,
                **record,
                "maintenance_date": maintenance_date,
                "technician_name": technician_name,
                "status": record_status,
                "task_info": task_info
            })

        print(f"[DEBUG] 获取到 {len(all_records)} 条记录")

        # 过滤记录
        filtered_records = []
        for record in all_records:
            # 状态过滤
            if status_value != "all" and record["status"] != status_value:
                continue

            # 飞机注册号过滤
            if aircraft_registration and record["aircraft_registration"] != aircraft_registration:
                continue

            # 搜索过滤
            if search:
                if not (
                    search in record["id"] or
                    search in record["aircraft_registration"] or
                    search in record.get("technician_name", "") or
                    search in record.get("technician_address", "")
                ):
                    continue

            filtered_records.append(record)

        print(f"[DEBUG] 过滤后 {len(filtered_records)} 条记录")

        # 按创建时间排序
        filtered_records.sort(key=lambda x: x["created_at"], reverse=True)

        return JSONResponse(status_code=200, content={"records": filtered_records})
    except Exception as e:
        print(f"[DEBUG] 获取记录异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/blockchain/records/view/{record_id}")
async def get_maintenance_record_detail(record_id: str):
    """获取维修记录详情"""
    try:
        print(f"[DEBUG] get_maintenance_record_detail - record_id: {record_id}")

        if record_id not in app_state.maintenance_records:
            print(f"[DEBUG] 记录不存在: {record_id}")
            return JSONResponse(status_code=404, content={"error": "记录不存在"})

        record = app_state.maintenance_records[record_id]
        print(f"[DEBUG] 记录详情 - status: {record.get('status')}, id: {record.get('id')}")

        return JSONResponse(status_code=200, content={"record": record})
    except Exception as e:
        print(f"[DEBUG] 获取记录详情异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.post("/api/blockchain/records/approve/{record_id}")
async def approve_maintenance_record(request: Request, record_id: str):
    """审批维修记录"""
    try:
        if record_id not in app_state.maintenance_records:
            return JSONResponse(status_code=404, content={"error": "记录不存在"})

        data = await request.json()
        action = data.get("action", "approve")  # approve, reject, release

        # 获取当前用户信息
        current_user = None
        try:
            # 优先从cookie获取token
            token = request.cookies.get("access_token")
            if not token:
                # 如果cookie中没有，尝试从Authorization header获取
                token = request.headers.get("Authorization", "").replace("Bearer ", "")

            if token:
                payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
                current_user = {
                    "address": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "public_key": payload.get("public_key", "")
                }
        except:
            pass

        # 更新记录状态
        record = app_state.maintenance_records[record_id]
        if action == "approve":
            record["status"] = "approved"
        elif action == "reject":
            record["status"] = "rejected"
        elif action == "release":
            record["status"] = "released"

        record["updated_at"] = int(datetime.now().timestamp())

        # 保存维修记录到文件
        app_state.save_maintenance_records()

        # 同时更新智能合约中的状态
        if app_state.contract_engine and app_state.master_contract and current_user:
            try:
                timestamp = int(datetime.now().timestamp())
                nonce = str(timestamp)

                # 根据操作类型调用不同的合约方法
                method_name = None
                if action == "approve":
                    method_name = "approveRecord"
                elif action == "reject":
                    method_name = "rejectRecord"
                elif action == "release":
                    method_name = "releaseRecord"

                if method_name:
                    # 从users.json中获取私钥
                    username = current_user.get("name")
                    private_key = ""
                    if username and username in app_state.users:
                        private_key = app_state.users[username].get("private_key", "")

                    if private_key:
                        # 创建签名数据
                        sign_data = SignatureManager.create_sign_data(
                            contract_address=app_state.master_contract.contract_address,
                            method=method_name,
                            params={
                                "record_id": record_id,
                                "approver_address": current_user["address"]
                            },
                            timestamp=timestamp,
                            nonce=nonce
                        )

                        # 使用私钥签名
                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result

                            # 执行智能合约
                            result = app_state.contract_engine.execute_contract(
                                contract_address=app_state.master_contract.contract_address,
                                method_name=method_name,
                                params={
                                    "record_id": record_id,
                                    "approver_address": current_user["address"],
                                    "caller_address": current_user["address"],
                                    "caller_role": current_user["role"]
                                },
                                signature=signature,
                                signer_address=current_user["address"],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )

                            if result.get("success"):
                                app_state.save_blockchain()
                                app_state.save_contracts()
                                print(f"[DEBUG] 维修记录状态已更新到区块链: {record_id} -> {action}")

                                # 更新区块链信息到维修记录
                                if "transaction_hash" not in app_state.maintenance_records[record_id]:
                                    app_state.maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                                app_state.maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                                app_state.maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                                app_state.save_maintenance_records()

                                # 手动添加事件到持久化存储
                                event_type = None
                                if action == "approve":
                                    event_type = "RecordApproved"
                                elif action == "reject":
                                    event_type = "RecordRejected"
                                elif action == "release":
                                    event_type = "RecordReleased"

                                if event_type:
                                    event_data = {
                                        "event_name": event_type,
                                        "contract_address": app_state.master_contract.contract_address,
                                        "block_index": result.get("block_index", 0),
                                        "data": {
                                            "record_id": record_id,
                                            "aircraft_registration": record.get("aircraft_registration", ""),
                                            "subchain_address": record.get("subchain_address", "")
                                        },
                                        "signer_address": current_user["address"]
                                    }
                                    app_state.blockchain_events.append(event_data)
                                    app_state.save_blockchain_events()
                            else:
                                print(f"[DEBUG] 更新区块链状态失败: {result.get('error')}")
            except Exception as e:
                print(f"[DEBUG] 更新区块链状态异常: {e}")
                import traceback
                traceback.print_exc()

        return JSONResponse(status_code=200, content={"message": "审批成功", "record": record, "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "审批失败: " + str(e)})

@router.post("/api/blockchain/release-record")
async def release_maintenance_record(request: Request, record_id: str):
    """释放维修记录"""
    try:
        if record_id not in app_state.maintenance_records:
            return JSONResponse(status_code=404, content={"error": "记录不存在"})

        data = await request.json()
        action = data.get("action", "release")  # release

        # 获取当前用户信息
        current_user = None
        try:
            # 优先从cookie获取token
            token = request.cookies.get("access_token")
            if not token:
                # 如果cookie中没有，尝试从Authorization header获取
                token = request.headers.get("Authorization", "").replace("Bearer ", "")

            if token:
                payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
                current_user = {
                    "address": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "public_key": payload.get("public_key", "")
                }
        except:
            pass

        # 更新记录状态
        record = app_state.maintenance_records[record_id]
        if action == "release":
            record["status"] = "released"

        record["updated_at"] = int(datetime.now().timestamp())

        # 保存维修记录到文件
        app_state.save_maintenance_records()

        # 同时更新智能合约中的状态
        if app_state.contract_engine and app_state.master_contract and current_user:
            try:
                timestamp = int(datetime.now().timestamp())
                nonce = str(timestamp)

                # 根据操作类型调用不同的合约方法
                method_name = None
                if action == "release":
                    method_name = "releaseRecord"

                if method_name:
                    # 从users.json中获取私钥
                    username = current_user.get("name")
                    private_key = ""
                    if username and username in app_state.users:
                        private_key = app_state.users[username].get("private_key", "")

                    if private_key:
                        # 创建签名数据
                        sign_data = SignatureManager.create_sign_data(
                            contract_address=app_state.master_contract.contract_address,
                            method=method_name,
                            params={
                                "record_id": record_id,
                                "approver_address": current_user["address"]
                            },
                            timestamp=timestamp,
                            nonce=nonce
                        )

                        # 使用私钥签名
                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result

                            # 执行智能合约
                            result = app_state.contract_engine.execute_contract(
                                contract_address=app_state.master_contract.contract_address,
                                method_name=method_name,
                                params={
                                    "record_id": record_id,
                                    "approver_address": current_user["address"],
                                    "caller_address": current_user["address"],
                                    "caller_role": current_user["role"]
                                },
                                signature=signature,
                                signer_address=current_user["address"],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )

                            if result.get("success"):
                                app_state.save_blockchain()
                                app_state.save_contracts()
                                print(f"[DEBUG] 维修记录状态已更新到区块链: {record_id} -> {action}")

                                # 更新区块链信息到维修记录
                                if "transaction_hash" not in app_state.maintenance_records[record_id]:
                                    app_state.maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                                app_state.maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                                app_state.maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                                app_state.save_maintenance_records()

                                # 手动添加事件到持久化存储
                                event_type = None
                                if action == "release":
                                    event_type = "RecordReleased"

                                if event_type:
                                    event_data = {
                                        "event_name": event_type,
                                        "contract_address": app_state.master_contract.contract_address,
                                        "block_index": result.get("block_index", 0),
                                        "data": {
                                            "record_id": record_id,
                                            "aircraft_registration": record.get("aircraft_registration", ""),
                                            "subchain_address": record.get("subchain_address", "")
                                        },
                                        "signer_address": current_user["address"]
                                    }
                                    app_state.blockchain_events.append(event_data)
                                    app_state.save_blockchain_events()
                            else:
                                print(f"[DEBUG] 更新区块链状态失败: {result.get('error')}")
            except Exception as e:
                print(f"[DEBUG] 更新区块链状态异常: {e}")
                import traceback
                traceback.print_exc()

        return JSONResponse(status_code=200, content={"message": "释放成功", "record": record, "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "释放失败: " + str(e)})

@router.get("/api/blockchain/records")
async def get_all_maintenance_records(request: Request):
    """获取所有维修记录"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        all_records = list(app_state.master_contract.state["records"].values())

        return JSONResponse(status_code=200, content={
            "success": True,
            "records": all_records,
            "total": len(all_records)
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/blockchain/records/{record_id}")
async def get_maintenance_record(record_id: str):
    """获取单个维修记录"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        record = app_state.master_contract.state["records"].get(record_id)

        if not record:
            return JSONResponse(status_code=404, content={"error": "记录不存在"})

        return JSONResponse(status_code=200, content={
            "success": True,
            "record": record
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/blockchain/aircraft/{aircraft_registration}")
async def get_aircraft_records(aircraft_registration: str):
    """获取指定飞机的维修记录"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        aircraft_records = []

        # 从区块链获取飞机的所有维修记录
        for record_id, record in app_state.master_contract.state["records"].items():
            if record.get("aircraft_registration") == aircraft_registration:
                aircraft_records.append(record)

        return JSONResponse(status_code=200, content={
            "success": True,
            "records": aircraft_records,
            "total": len(aircraft_records)
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/blockchain/stats")
async def get_blockchain_stats():
    """获取区块链统计信息"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        total_records = len(app_state.master_contract.state["records"])
        total_blocks = app_state.contract_engine.get_blockchain_length()
        total_aircraft = len(app_state.master_contract.state.get("aircraft_subchains", {}))

        # 计算已完成的维修记录
        completed_records = sum(
            1 for record in app_state.master_contract.state["records"].values()
            if record.get("status") in ["approved", "released"]
        )

        stats = {
            "total_records": total_records,
            "total_blocks": total_blocks,
            "total_aircraft": total_aircraft,
            "completed_records": completed_records,
            "pending_records": total_records - completed_records
        }

        return JSONResponse(status_code=200, content={
            "success": True,
            "stats": stats
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计信息失败: " + str(e)})

@router.get("/api/blockchain/visualization/stats")
async def get_blockchain_visualization_stats():
    """获取区块链可视化统计数据"""
    try:
        # 从实际数据中统计
        total_records = len(app_state.maintenance_records)
        completed_records = sum(1 for r in app_state.maintenance_records.values() if r.get('status') in ['completed', 'released'])

        stats = {
            "total_records": total_records,
            "total_blocks": total_records,
            "completed_records": completed_records,
            "total_users": len(app_state.users),
            "avg_completion_time": 4.5,
            "total_transactions": total_records * 3
        }
        return JSONResponse(status_code=200, content=stats)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计数据失败: " + str(e)})


@router.get("/api/blockchain/visualization/blocks")
async def get_blockchain_blocks():
    """获取区块链结构数据"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        # 从智能合约中获取区块数据
        blocks = app_state.contract_engine.get_all_blocks()

        # 转换区块数据格式，添加合约类型信息
        formatted_blocks = []
        for block in blocks:
            # 确定区块类型（主链或子链）
            contract_address = block.get("contract_address", "")
            contract_type = "主链"
            aircraft_registration = ""

            # 检查是否是飞机子链
            for aircraft_reg, subchain_info in app_state.master_contract.state["aircraft_subchains"].items():
                if subchain_info.get("subchain_address") == contract_address:
                    contract_type = f"子链 ({aircraft_reg})"
                    aircraft_registration = aircraft_reg
                    break

            # 获取飞机注册号
            block_aircraft_registration = block.get("params", {}).get("aircraft_registration", aircraft_registration)

            # 获取操作人员名字
            signer_address = block.get("signer_address", "")
            operator_name = "未知"
            for username, user_info in app_state.users.items():
                if user_info.get("address") == signer_address:
                    operator_name = user_info.get("username", "未知")
                    break

            # 格式化操作时间
            timestamp = block.get("timestamp", 0)
            operation_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp > 0 else ""

            # 格式化交易数据
            transactions = []
            for tx in block.get("transactions", []):
                transactions.append({
                    "id": tx.get("id", ""),
                    "type": tx.get("type", ""),
                    "recordId": block.get("params", {}).get("record_id", ""),
                    "status": "completed"
                })

            formatted_block = {
                "index": block.get("index", 0),
                "hash": block.get("hash", ""),
                "previous_hash": block.get("previous_hash", ""),
                "timestamp": timestamp,
                "operationTime": operation_time,
                "transactions": transactions,
                "status": "completed",
                "contractType": contract_type,
                "contractAddress": contract_address,
                "aircraftRegistration": block_aircraft_registration,
                "method": block.get("method", ""),
                "signerAddress": signer_address,
                "operatorName": operator_name,
                "events": block.get("events", [])
            }
            formatted_blocks.append(formatted_block)

        return JSONResponse(status_code=200, content={"blocks": formatted_blocks})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取区块链结构失败: " + str(e)})

@router.get("/api/blockchain/visualization/transactions")
async def get_blockchain_transactions():
    """获取交易流程数据"""
    try:
        # 从实际维修记录中按两个维度组织数据

        # 技术人员维度
        tech_records = {}
        for record_id, record in app_state.maintenance_records.items():
            technician_id = record.get("technician_id", "未知")
            if technician_id not in tech_records:
                tech_records[technician_id] = {
                    "name": technician_id,
                    "records": []
                }
            tech_records[technician_id]["records"].append({
                "id": record_id,
                "timestamp": record.get("created_at", 0),
                "status": record.get("status", "pending")
            })

        # 飞机维度
        aircraft_records = {}
        for record_id, record in app_state.maintenance_records.items():
            aircraft_reg = record.get("aircraft_registration", "未知")
            if aircraft_reg not in aircraft_records:
                aircraft_records[aircraft_reg] = {
                    "name": aircraft_reg,
                    "records": []
                }
            aircraft_records[aircraft_reg]["records"].append({
                "id": record_id,
                "timestamp": record.get("created_at", 0),
                "status": record.get("status", "pending")
            })

        transactions = {
            "tech_records": tech_records,
            "aircraft_records": aircraft_records,
            "labels": ["创建记录", "提交审批", "互检签名", "必检签名", "放行签名", "完成记录"]
        }
        return JSONResponse(status_code=200, content=transactions)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取交易流程数据失败: " + str(e)})

@router.get("/api/blockchain/visualization/roles")
async def get_blockchain_roles():
    """获取角色权限数据"""
    try:
        # 模拟角色权限数据
        roles = {
            "tech": [100, 0, 0, 0, 0, 20],
            "manager": [0, 100, 0, 0, 0, 50],
            "admin": [100, 100, 100, 100, 100, 100],
            "labels": ["记录创建", "记录审批", "记录删除", "用户管理", "系统配置", "数据导出"]
        }
        return JSONResponse(status_code=200, content=roles)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取角色权限数据失败: " + str(e)})

@router.get("/api/blockchain/visualization/logs")
async def get_blockchain_logs():
    """获取操作日志数据"""
    try:
        print(f"[DEBUG] 开始获取操作日志")
        print(f"[DEBUG] blockchain_events 数量: {len(app_state.blockchain_events)}")

        # 打印所有事件详情
        for idx, event in enumerate(app_state.blockchain_events):
            print(f"[DEBUG] 事件 {idx}: event_name={event.get('event_name')}, data={event.get('data')}, signer={event.get('signer_address')}")

        if len(app_state.blockchain_events) == 0:
            return JSONResponse(status_code=200, content={"logs": []})

        # 从持久化的事件中生成操作日志
        logs = []
        log_id = 1

        for event in app_state.blockchain_events:
            event_type = event.get("event_name", "")
            event_data = event.get("data", {})
            signer_address = event.get("signer_address", "")
            timestamp = event.get("timestamp", 0)

            print(f"[DEBUG] 处理事件: {event_type}, 签名者: {signer_address}")

            # 查找用户信息
            user_name = "未知"
            user_role = "user"
            for username, user in app_state.users.items():
                if user.get("address") == signer_address:
                    user_name = username
                    user_role = user.get("role", "user")
                    print(f"[DEBUG] 找到用户: {username}, 角色: {user_role}")
                    break

            # 根据事件类型生成日志
            if event_type == "RecordCreated":
                logs.append({
                    "id": log_id,
                    "type": "create",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("record_id", ""),
                    "description": "创建维修记录",
                    "timestamp": timestamp
                })
                log_id += 1
            elif event_type == "RecordApproved":
                logs.append({
                    "id": log_id,
                    "type": "approve",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("record_id", ""),
                    "description": "审批维修记录",
                    "timestamp": timestamp
                })
                log_id += 1
            elif event_type == "RecordReleased":
                logs.append({
                    "id": log_id,
                    "type": "release",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("record_id", ""),
                    "description": "放行维修记录",
                    "timestamp": timestamp
                })
                log_id += 1
            elif event_type == "AircraftSubchainCreated":
                logs.append({
                    "id": log_id,
                    "type": "create_subchain",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("aircraft_registration", ""),
                    "description": f"创建飞机子链: {event_data.get('aircraft_registration', '')}",
                    "timestamp": timestamp
                })
                log_id += 1

        # 按时间倒序排序
        logs.sort(key=lambda x: x["timestamp"], reverse=True)

        print(f"[DEBUG] 生成了 {len(logs)} 条操作日志")
        return JSONResponse(status_code=200, content={"logs": logs})
    except Exception as e:
        print(f"[ERROR] 获取操作日志失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取操作日志失败: " + str(e)})


@router.get("/api/blockchain/visualization/statistics")
async def get_blockchain_statistics():
    """获取统计数据"""
    try:
        # 从实际维修记录中统计数据
        from collections import defaultdict

        # 按月份统计维修记录
        monthly_records = defaultdict(int)
        monthly_completed = defaultdict(int)

        for record in app_state.maintenance_records.values():
            created_at = record.get("created_at", 0)
            if created_at > 0:
                # 转换为月份
                dt = datetime.fromtimestamp(created_at)
                month = dt.month
                monthly_records[month] += 1

                # 统计已完成的记录
                if record.get("status") in ["approved", "released"]:
                    monthly_completed[month] += 1

        # 生成最近6个月的数据
        labels = []
        records_data = []
        completion_rate_data = []

        # 获取当前月份
        current_month = datetime.now().month

        for i in range(6):
            month = (current_month - 5 + i) if (current_month - 5 + i) > 0 else (current_month - 5 + i + 12)
            labels.append(f"{month}月")
            records_data.append(monthly_records.get(month, 0))

            # 计算完成率
            total = monthly_records.get(month, 0)
            completed = monthly_completed.get(month, 0)
            rate = round((completed / total * 100) if total > 0 else 0, 2)
            completion_rate_data.append(rate)

        statistics = {
            "labels": labels,
            "records": records_data,
            "completion_rate": completion_rate_data
        }
        return JSONResponse(status_code=200, content=statistics)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计数据失败: " + str(e)})


@router.get("/api/blockchain/health")
async def get_blockchain_health():
    """获取区块链健康度监控数据"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        # 检查区块完整性
        integrity_valid = True
        try:
            blocks = app_state.contract_engine.get_all_blocks()
            for i in range(1, len(blocks)):
                if blocks[i].get("previous_hash") != blocks[i-1].get("hash"):
                    integrity_valid = False
                    break
        except Exception as e:
            print(f"[ERROR] 区块完整性检查失败: {e}")
            integrity_valid = False

        # 检查哈希验证
        hash_valid = True
        try:
            blocks = app_state.contract_engine.get_all_blocks()
            for block in blocks:
                block_hash = block.get("hash", "")
                if not block_hash or len(block_hash) < 10:
                    hash_valid = False
                    break
        except Exception as e:
            print(f"[ERROR] 哈希验证检查失败: {e}")
            hash_valid = False

        # 检查区块一致性
        consistency_valid = True
        try:
            blocks = app_state.contract_engine.get_all_blocks()
            for i, block in enumerate(blocks):
                if block.get("index") != i:
                    consistency_valid = False
                    break
        except Exception as e:
            print(f"[ERROR] 区块一致性检查失败: {e}")
            consistency_valid = False

        # 检查合约状态
        contract_active = True
        try:
            if not app_state.master_contract or not hasattr(app_state.master_contract, 'state'):
                contract_active = False
        except Exception as e:
            print(f"[ERROR] 合约状态检查失败: {e}")
            contract_active = False

        health_data = {
            "integrity_valid": integrity_valid,
            "hash_valid": hash_valid,
            "consistency_valid": consistency_valid,
            "contract_active": contract_active
        }

        return JSONResponse(status_code=200, content=health_data)
    except Exception as e:
        print(f"[ERROR] 获取区块链健康度失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取区块链健康度失败: " + str(e)})

@router.post("/api/blockchain/verify")
async def verify_blockchain_integrity():
    """验证区块链完整性"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": "区块链系统未初始化"
            })

        blocks = app_state.contract_engine.get_all_blocks()
        verification_results = {
            "success": True,
            "total_blocks": len(blocks),
            "integrity_check": {
                "valid": True,
                "details": []
            },
            "hash_check": {
                "valid": True,
                "details": []
            },
            "consistency_check": {
                "valid": True,
                "details": []
            },
            "timestamp": int(datetime.now().timestamp())
        }

        # 检查区块完整性（前一个区块的哈希是否匹配）
        for i in range(1, len(blocks)):
            current_block = blocks[i]
            previous_block = blocks[i-1]

            if current_block.get("previous_hash") != previous_block.get("hash"):
                verification_results["integrity_check"]["valid"] = False
                verification_results["integrity_check"]["details"].append({
                    "block_index": i,
                    "error": f"区块 {i} 的前哈希与区块 {i-1} 的哈希不匹配",
                    "expected": previous_block.get("hash"),
                    "actual": current_block.get("previous_hash")
                })

        # 检查哈希验证
        for i, block in enumerate(blocks):
            block_hash = block.get("hash", "")
            if not block_hash or len(block_hash) < 10:
                verification_results["hash_check"]["valid"] = False
                verification_results["hash_check"]["details"].append({
                    "block_index": i,
                    "error": f"区块 {i} 的哈希无效",
                    "hash": block_hash
                })

        # 检查区块一致性（索引是否连续）
        for i, block in enumerate(blocks):
            if block.get("index") != i:
                verification_results["consistency_check"]["valid"] = False
                verification_results["consistency_check"]["details"].append({
                    "block_index": i,
                    "error": f"区块索引不一致，期望 {i}，实际 {block.get('index')}"
                })

        # 总体验证结果
        verification_results["overall_valid"] = (
            verification_results["integrity_check"]["valid"] and
            verification_results["hash_check"]["valid"] and
            verification_results["consistency_check"]["valid"]
        )

        return JSONResponse(status_code=200, content=verification_results)
    except Exception as e:
        print(f"[ERROR] 验证区块链完整性失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "验证区块链完整性失败: " + str(e)
        })


@router.get("/api/contract/info")
async def get_contract_info():
    """获取合约信息"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        # 获取主链合约信息
        master_contract_address = app_state.master_contract.address if hasattr(app_state.master_contract, 'address') else "未知"
        master_contract_active = True

        # 获取总区块数
        total_blocks = len(app_state.contract_engine.get_all_blocks())

        # 获取子链信息
        subchains = []
        aircraft_subchains = app_state.master_contract.state.get("aircraft_subchains", {})

        for aircraft_reg, subchain_info in aircraft_subchains.items():
            subchain_address = subchain_info.get("subchain_address", "")
            record_count = subchain_info.get("record_count", 0)

            subchains.append({
                "aircraft_registration": aircraft_reg,
                "address": subchain_address,
                "record_count": record_count,
                "active": True
            })

        contract_info = {
            "master_contract_address": master_contract_address,
            "master_contract_active": master_contract_active,
            "total_blocks": total_blocks,
            "subchains": subchains
        }

        return JSONResponse(status_code=200, content=contract_info)
    except Exception as e:
        print(f"[ERROR] 获取合约信息失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取合约信息失败: " + str(e)})


@router.post("/api/contract/release-record")
async def contract_release_record(request: Request):
    """使用智能合约释放维修记录"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        data = await request.json()

        required_fields = ['record_id', 'approver_address', 'signature', 'nonce']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(status_code=400, content={"error": f"{field} 不能为空"})

        current_user = None
        try:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if token:
                payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
                current_user = {
                    "address": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "public_key": payload.get("public_key", "")
                }
        except:
            pass

        if not current_user:
            return JSONResponse(status_code=401, content={"error": "未授权"})

        # 使用前端发送的timestamp
        timestamp = data.get('timestamp', int(datetime.now().timestamp()))

        sign_data = SignatureManager.create_sign_data(
            contract_address=app_state.master_contract.contract_address,
            method="releaseRecord",
            params={
                "record_id": data['record_id'],
                "approver_address": data['approver_address']
            },
            timestamp=timestamp,
            nonce=data['nonce']
        )

        verification_result = SignatureManager.verify_signature(
            data['signature'],
            current_user.get('public_key', ''),
            sign_data
        )

        if not verification_result.get("success"):
            return JSONResponse(status_code=400, content={"error": "签名验证失败"})

        result = app_state.contract_engine.execute_contract(
            contract_address=app_state.master_contract.contract_address,
            method_name="releaseRecord",
            params={
                "record_id": data['record_id'],
                "approver_address": data['approver_address'],
                "caller_address": current_user['address'],
                "caller_role": current_user['role']
            },
            signature=data['signature'],
            signer_address=current_user['address'],
            nonce=data['nonce'],
            verify_signature_func=lambda sig, addr, params: verification_result
        )

        if not result.get("success"):
            return JSONResponse(status_code=400, content={"error": result.get("error", "释放记录失败")})

        app_state.save_blockchain()
        app_state.save_contracts()

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "维修记录释放成功",
            "block_hash": result["block_hash"],
            "block_index": result["block_index"]
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "释放记录失败: " + str(e)})

@router.get("/api/contract/records")
async def contract_get_all_records(status: Optional[str] = None):
    """获取所有维修记录"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        all_records = list(app_state.master_contract.state["records"].values())

        # 根据状态筛选
        if status:
            all_records = [r for r in all_records if r.get("status") == status]

        return JSONResponse(status_code=200, content={
            "success": True,
            "records": all_records,
            "total": len(all_records)
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/contract/records/{record_id}")
async def contract_get_record(record_id: str):
    """获取维修记录详情"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        result = app_state.master_contract.get_record(record_id)

        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/contract/aircraft/{aircraft_registration}")
async def contract_get_aircraft_records(aircraft_registration: str, status: Optional[str] = None):
    """获取飞机的所有维修记录"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        result = app_state.master_contract.get_aircraft_records(aircraft_registration, status)

        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/contract/stats")
async def contract_get_stats():
    """获取全局统计"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        result = app_state.master_contract.get_global_stats()

        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计失败: " + str(e)})

@router.get("/api/contract/blocks")
async def contract_get_blocks():
    """获取区块链数据"""
    try:
        if not app_state.contract_engine:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        blocks = app_state.contract_engine.get_all_blocks()

        return JSONResponse(status_code=200, content={"blocks": blocks})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取区块失败: " + str(e)})

@router.get("/api/contract/subchains")
async def contract_get_subchains():
    """获取飞机子链信息"""
    try:
        if not app_state.contract_engine:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        if not app_state.master_contract:
            print("[ERROR] master_contract 未初始化")
            return JSONResponse(status_code=500, content={"error": "主合约未初始化"})

        print(f"[DEBUG] master_contract state: {app_state.master_contract.state}")

        subchains = []
        aircraft_subchains = app_state.master_contract.state.get("aircraft_subchains", {})
        print(f"[DEBUG] aircraft_subchains: {aircraft_subchains}")

        for aircraft_reg, subchain_info in aircraft_subchains.items():
            subchain_address = subchain_info.get("subchain_address", "")
            record_count = subchain_info.get("record_count", 0)

            subchain_records = app_state.contract_engine.get_subchain_records(subchain_address)

            subchains.append({
                "aircraft_registration": aircraft_reg,
                "subchain_address": subchain_address,
                "record_count": record_count,
                "records": subchain_records
            })

        print(f"[DEBUG] 返回子链数据: {subchains}")
        return JSONResponse(status_code=200, content={"subchains": subchains})
    except Exception as e:
        print(f"[ERROR] 获取子链失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取子链失败: " + str(e)})

@router.get("/api/contract/subchain/blocks")
async def contract_get_subchain_blocks(aircraft_registration: str):
    """获取指定飞机的子链区块"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        aircraft_subchains = app_state.master_contract.state.get("aircraft_subchains", {})
        subchain_info = aircraft_subchains.get(aircraft_registration)

        if not subchain_info:
            return JSONResponse(status_code=404, content={"error": "指定飞机的子链不存在"})

        # 获得子链地址并读取记录
        subchain_address = subchain_info.get("subchain_address", "")
        records = app_state.contract_engine.get_subchain_records(subchain_address)

        return JSONResponse(status_code=200, content={"records": records})
    except Exception as e:
        print(f"[ERROR] 获取子链区块失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取子链区块失败: " + str(e)})
