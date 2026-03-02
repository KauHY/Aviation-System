import uuid
from typing import Dict, Any, Optional, List
from .base_contract import BaseContract


class MaintenanceRecordMasterContract(BaseContract):
    def __init__(self, contract_address: str):
        super().__init__(contract_address, "MaintenanceRecordMasterContract")
        self.state = {
            "records": {},
            "aircraft_subchains": {},
            "stats": {
                "total_records": 0,
                "total_aircraft": 0,
                "pending_count": 0,
                "approved_count": 0,
                "released_count": 0
            }
        }

    def get_state(self) -> Dict[str, Any]:
        return self.state

    def get_methods(self) -> Dict[str, callable]:
        return {
            "createAircraftSubchain": self.create_aircraft_subchain,
            "createRecord": self.create_record,
            "approveRecord": self.approve_record,
            "rejectRecord": self.reject_record,
            "releaseRecord": self.release_record,
            "getRecord": self.get_record,
            "getAircraftRecords": self.get_aircraft_records,
            "getAircraftSubchainInfo": self.get_aircraft_subchain_info,
            "getGlobalStats": self.get_global_stats
        }

    def create_aircraft_subchain(self, aircraft_registration: str, 
                                 aircraft_type: str, 
                                 caller_address: str, 
                                 caller_role: str) -> Dict[str, Any]:
        if caller_role != "admin":
            return {"success": False, "error": "权限不足"}
        
        if aircraft_registration in self.state["aircraft_subchains"]:
            return {"success": False, "error": "飞机子链已存在"}
        
        from .base_contract import BaseContract
        subchain_address = BaseContract.generate_address(
            "AircraftSubchainContract",
            {"aircraft_registration": aircraft_registration}
        )
        
        self.state["aircraft_subchains"][aircraft_registration] = {
            "aircraft_registration": aircraft_registration,
            "aircraft_type": aircraft_type,
            "subchain_address": subchain_address,
            "record_count": 0,
            "created_at": self.updated_at,
            "latest_block_hash": "0"
        }
        
        self.state["stats"]["total_aircraft"] += 1
        
        self.emit_event(
            "AircraftSubchainCreated",
            {
                "aircraft_registration": aircraft_registration,
                "aircraft_type": aircraft_type,
                "subchain_address": subchain_address,
                "creator_address": caller_address
            },
            caller_address
        )
        
        return {
            "success": True,
            "subchain_address": subchain_address,
            "message": "飞机子链创建成功"
        }

    def create_record(self, aircraft_registration: str, 
                     maintenance_type: str, 
                     description: str, 
                     technician_address: str, 
                     caller_address: str, 
                     caller_role: str) -> Dict[str, Any]:
        print(f"[DEBUG] create_record called: caller_role={caller_role}, caller_address={caller_address}, technician_address={technician_address}")
        
        if caller_role not in ["technician", "admin"]:
            print(f"[DEBUG] 权限不足: caller_role={caller_role}")
            return {"success": False, "error": "权限不足"}
        
        if caller_address != technician_address and caller_role != "admin":
            print(f"[DEBUG] 只能创建自己的记录: caller_address={caller_address}, technician_address={technician_address}")
            return {"success": False, "error": "只能创建自己的记录"}
        
        if aircraft_registration not in self.state["aircraft_subchains"]:
            subchain_result = self.create_aircraft_subchain(
                aircraft_registration,
                "未知",
                caller_address,
                "admin"
            )
            if not subchain_result["success"]:
                return {"success": False, "error": "创建飞机子链失败"}
        
        record_id = str(uuid.uuid4())[:12]
        subchain_address = self.state["aircraft_subchains"][aircraft_registration]["subchain_address"]
        
        self.state["records"][record_id] = {
            "id": record_id,
            "aircraft_registration": aircraft_registration,
            "subchain_address": subchain_address,
            "maintenance_type": maintenance_type,
            "description": description,
            "status": "pending",
            "technician_address": technician_address,
            "approver_address": "",
            "created_at": self.updated_at,
            "updated_at": self.updated_at,
            "block_index": self.block_index,
            "subchain_block_index": 0
        }
        
        self.state["stats"]["total_records"] += 1
        self.state["stats"]["pending_count"] += 1
        
        self.state["aircraft_subchains"][aircraft_registration]["record_count"] += 1
        
        self.emit_event(
            "RecordCreated",
            {
                "record_id": record_id,
                "aircraft_registration": aircraft_registration,
                "subchain_address": subchain_address,
                "maintenance_type": maintenance_type,
                "description": description,
                "technician_address": technician_address
            },
            caller_address
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "subchain_address": subchain_address,
            "message": "维修记录创建成功"
        }

    def approve_record(self, record_id: str, 
                      approver_address: str, 
                      caller_address: str, 
                      caller_role: str) -> Dict[str, Any]:
        if caller_role != "manager":
            return {"success": False, "error": "权限不足：只有管理人员可以审批记录"}
        
        if record_id not in self.state["records"]:
            return {"success": False, "error": "记录不存在"}
        
        record = self.state["records"][record_id]
        
        if record["status"] != "pending":
            return {"success": False, "error": "记录状态不正确"}
        
        record["status"] = "approved"
        record["approver_address"] = approver_address
        record["updated_at"] = self.updated_at
        
        self.state["stats"]["pending_count"] -= 1
        self.state["stats"]["approved_count"] += 1
        
        self.emit_event(
            "RecordApproved",
            {
                "record_id": record_id,
                "aircraft_registration": record["aircraft_registration"],
                "subchain_address": record["subchain_address"],
                "approver_address": approver_address
            },
            caller_address
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "维修记录审批成功"
        }

    def reject_record(self, record_id: str, 
                      approver_address: str, 
                      caller_address: str, 
                      caller_role: str) -> Dict[str, Any]:
        if caller_role != "manager":
            return {"success": False, "error": "权限不足：只有管理人员可以驳回记录"}
        
        if record_id not in self.state["records"]:
            return {"success": False, "error": "记录不存在"}
        
        record = self.state["records"][record_id]
        
        if record["status"] != "pending":
            return {"success": False, "error": "记录状态不正确"}
        
        record["status"] = "rejected"
        record["approver_address"] = approver_address
        record["updated_at"] = self.updated_at
        
        self.state["stats"]["pending_count"] -= 1
        
        self.emit_event(
            "RecordRejected",
            {
                "record_id": record_id,
                "aircraft_registration": record["aircraft_registration"],
                "subchain_address": record["subchain_address"],
                "approver_address": approver_address
            },
            caller_address
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "维修记录驳回成功"
        }

    def release_record(self, record_id: str, 
                       approver_address: str, 
                       caller_address: str, 
                       caller_role: str) -> Dict[str, Any]:
        if caller_role != "admin":
            return {"success": False, "error": "权限不足：只有总负责人可以放行记录"}
        
        if record_id not in self.state["records"]:
            return {"success": False, "error": "记录不存在"}
        
        record = self.state["records"][record_id]
        
        if record["status"] != "approved":
            return {"success": False, "error": "记录状态不正确：只有已批准的记录才能放行"}
        
        record["status"] = "released"
        record["approver_address"] = approver_address
        record["updated_at"] = self.updated_at
        
        self.state["stats"]["approved_count"] -= 1
        self.state["stats"]["released_count"] += 1
        
        self.emit_event(
            "RecordReleased",
            {
                "record_id": record_id,
                "aircraft_registration": record["aircraft_registration"],
                "subchain_address": record["subchain_address"],
                "approver_address": approver_address
            },
            caller_address
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "维修记录放行成功"
        }

    def get_record(self, record_id: str) -> Dict[str, Any]:
        if record_id not in self.state["records"]:
            return {"success": False, "error": "记录不存在"}
        
        return {
            "success": True,
            "record": self.state["records"][record_id]
        }

    def get_aircraft_records(self, aircraft_registration: str, 
                           status: Optional[str] = None) -> Dict[str, Any]:
        if aircraft_registration not in self.state["aircraft_subchains"]:
            return {"success": False, "error": "飞机子链不存在"}
        
        records = []
        for record in self.state["records"].values():
            if record["aircraft_registration"] == aircraft_registration:
                if status is None or record["status"] == status:
                    records.append(record)
        
        records.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "success": True,
            "records": records,
            "count": len(records)
        }

    def get_aircraft_subchain_info(self, aircraft_registration: str) -> Dict[str, Any]:
        if aircraft_registration not in self.state["aircraft_subchains"]:
            return {"success": False, "error": "飞机子链不存在"}
        
        return {
            "success": True,
            "info": self.state["aircraft_subchains"][aircraft_registration]
        }

    def get_global_stats(self) -> Dict[str, Any]:
        stats = self.state["stats"].copy()
        stats["master_contract_address"] = self.contract_address
        return {
            "success": True,
            "stats": stats
        }
