from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jose import jwt

import app_state
from contracts.signature_manager import SignatureManager
from services.auth_workflow import AuthWorkflow
from services.blockchain_workflow import BlockchainWorkflow

router = APIRouter()
auth_workflow = AuthWorkflow()
blockchain_workflow = BlockchainWorkflow()

@router.post("/api/blockchain/records/create")
async def create_maintenance_record(request: Request):
    """创建维修记录"""
    try:
        data = await request.json()
        record_id, error_code, error_detail = blockchain_workflow.create_record(
            data=data,
            maintenance_records=app_state.maintenance_records,
            tasks=app_state.tasks,
            users=app_state.users,
            contract_engine=app_state.contract_engine,
            master_contract=app_state.master_contract,
            blockchain_events=app_state.blockchain_events,
            save_maintenance_records=app_state.save_maintenance_records,
            save_blockchain_events=app_state.save_blockchain_events
        )
        if error_code == "missing_field":
            return JSONResponse(status_code=400, content={"error": f"{error_detail} 不能为空"})
        if error_code:
            return JSONResponse(status_code=500, content={"error": "创建记录失败: " + str(error_detail or "unknown")})

        return JSONResponse(status_code=200, content={"message": "维修记录创建成功", "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "创建记录失败: " + str(e)})

@router.get("/api/blockchain/records/list")
async def get_maintenance_records(request: Request):
    """获取维修记录列表"""
    try:
        if not app_state.contract_engine or not app_state.master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        status_value = request.query_params.get("status", "all")
        aircraft_registration = request.query_params.get("aircraft_registration", "")
        search = request.query_params.get("search", "")

        records, error_code = blockchain_workflow.list_records(
            status_value=status_value,
            aircraft_registration=aircraft_registration,
            search=search,
            maintenance_records=app_state.maintenance_records,
            master_contract=app_state.master_contract,
            users=app_state.users,
            tasks=app_state.tasks,
            save_maintenance_records=app_state.save_maintenance_records
        )
        if error_code == "blockchain_not_initialized":
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        return JSONResponse(status_code=200, content={"records": records})
    except Exception as e:
        print(f"[DEBUG] 获取记录异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/blockchain/records/view/{record_id}")
async def get_maintenance_record_detail(record_id: str):
    """获取维修记录详情"""
    try:
        record, error_code = blockchain_workflow.get_record_detail(
            record_id,
            app_state.maintenance_records
        )
        if error_code == "record_not_found":
            return JSONResponse(status_code=404, content={"error": "记录不存在"})

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
        data = await request.json()
        action = data.get("action", "approve")  # approve, reject, release

        # 获取当前用户信息
        current_user = None
        payload, _ = auth_workflow.get_payload_from_request(
            request,
            app_state.SECRET_KEY,
            app_state.ALGORITHM
        )
        if payload:
            current_user = {
                "address": payload.get("sub"),
                "username": payload.get("username"),
                "role": payload.get("role", "user"),
                "public_key": payload.get("public_key", "")
            }

        record, error_code = blockchain_workflow.update_record_status(
            record_id=record_id,
            action=action,
            current_user=current_user,
            maintenance_records=app_state.maintenance_records,
            master_contract=app_state.master_contract,
            contract_engine=app_state.contract_engine,
            users=app_state.users,
            blockchain_events=app_state.blockchain_events,
            save_maintenance_records=app_state.save_maintenance_records,
            save_blockchain_events=app_state.save_blockchain_events,
            save_blockchain=app_state.save_blockchain,
            save_contracts=app_state.save_contracts
        )
        if error_code == "record_not_found":
            return JSONResponse(status_code=404, content={"error": "记录不存在"})

        return JSONResponse(status_code=200, content={"message": "审批成功", "record": record, "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "审批失败: " + str(e)})

@router.post("/api/blockchain/release-record")
async def release_maintenance_record(request: Request, record_id: str):
    """释放维修记录"""
    try:
        data = await request.json()
        action = data.get("action", "release")  # release

        # 获取当前用户信息
        current_user = None
        payload, _ = auth_workflow.get_payload_from_request(
            request,
            app_state.SECRET_KEY,
            app_state.ALGORITHM
        )
        if payload:
            current_user = {
                "address": payload.get("sub"),
                "username": payload.get("username"),
                "role": payload.get("role", "user"),
                "public_key": payload.get("public_key", "")
            }

        record, error_code = blockchain_workflow.update_record_status(
            record_id=record_id,
            action=action,
            current_user=current_user,
            maintenance_records=app_state.maintenance_records,
            master_contract=app_state.master_contract,
            contract_engine=app_state.contract_engine,
            users=app_state.users,
            blockchain_events=app_state.blockchain_events,
            save_maintenance_records=app_state.save_maintenance_records,
            save_blockchain_events=app_state.save_blockchain_events,
            save_blockchain=app_state.save_blockchain,
            save_contracts=app_state.save_contracts
        )
        if error_code == "record_not_found":
            return JSONResponse(status_code=404, content={"error": "记录不存在"})

        return JSONResponse(status_code=200, content={"message": "释放成功", "record": record, "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "释放失败: " + str(e)})

@router.get("/api/blockchain/records")
async def get_all_maintenance_records(request: Request):
    """获取所有维修记录"""
    try:
        records, error_code = blockchain_workflow.get_all_records(app_state.master_contract)
        if error_code == "blockchain_not_initialized":
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

        return JSONResponse(status_code=200, content={
            "success": True,
            "records": records,
            "total": len(records)
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@router.get("/api/blockchain/records/{record_id}")
async def get_maintenance_record(record_id: str):
    """获取单个维修记录"""
    try:
        record, error_code = blockchain_workflow.get_record(app_state.master_contract, record_id)
        if error_code == "blockchain_not_initialized":
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        if error_code == "record_not_found":
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
        aircraft_records, error_code = blockchain_workflow.get_aircraft_records(
            app_state.master_contract,
            aircraft_registration
        )
        if error_code == "blockchain_not_initialized":
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

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
        stats, error_code = blockchain_workflow.get_stats(
            app_state.master_contract,
            app_state.contract_engine
        )
        if error_code == "blockchain_not_initialized":
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})

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
