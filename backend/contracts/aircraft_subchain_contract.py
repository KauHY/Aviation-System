from typing import Dict, Any, Optional, List
from .base_contract import BaseContract


class AircraftSubchainContract(BaseContract):
    def __init__(self, contract_address: str, aircraft_registration: str, 
                 aircraft_type: str, master_contract_address: str):
        super().__init__(contract_address, "AircraftSubchainContract")
        self.aircraft_registration = aircraft_registration
        self.aircraft_type = aircraft_type
        self.master_contract_address = master_contract_address
        
        self.state = {
            "aircraft_info": {
                "aircraft_registration": aircraft_registration,
                "aircraft_type": aircraft_type,
                "master_contract_address": master_contract_address,
                "created_at": self.created_at
            },
            "records": {},
            "stats": {
                "total_records": 0,
                "pending_count": 0,
                "approved_count": 0,
                "released_count": 0,
                "last_maintenance_date": 0
            }
        }

    def get_state(self) -> Dict[str, Any]:
        return self.state

    def get_methods(self) -> Dict[str, callable]:
        return {
            "addRecord": self.add_record,
            "updateRecordStatus": self.update_record_status,
            "getRecord": self.get_record,
            "getAllRecords": self.get_all_records,
            "getMaintenanceHistory": self.get_maintenance_history,
            "getStats": self.get_stats
        }

    def add_record(self, record_id: str, maintenance_type: str, 
                   description: str, technician_address: str, 
                   master_record_id: str, caller_address: str, 
                   caller_role: str) -> Dict[str, Any]:
        if caller_role != "master_contract":
            return {"success": False, "error": "权限不足"}
        
        if record_id in self.state["records"]:
            return {"success": False, "error": "记录已存在"}
        
        self.state["records"][record_id] = {
            "id": record_id,
            "maintenance_type": maintenance_type,
            "description": description,
            "status": "pending",
            "technician_address": technician_address,
            "approver_address": "",
            "created_at": self.updated_at,
            "updated_at": self.updated_at,
            "block_index": self.block_index,
            "master_record_id": master_record_id
        }
        
        self.state["stats"]["total_records"] += 1
        self.state["stats"]["pending_count"] += 1
        self.state["stats"]["last_maintenance_date"] = self.updated_at
        
        self.emit_event(
            "RecordAdded",
            {
                "record_id": record_id,
                "maintenance_type": maintenance_type,
                "description": description,
                "technician_address": technician_address,
                "master_record_id": master_record_id
            },
            caller_address
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "记录添加成功"
        }

    def update_record_status(self, record_id: str, new_status: str, 
                            approver_address: str, caller_address: str, 
                            caller_role: str) -> Dict[str, Any]:
        if caller_role != "master_contract":
            return {"success": False, "error": "权限不足"}
        
        if record_id not in self.state["records"]:
            return {"success": False, "error": "记录不存在"}
        
        record = self.state["records"][record_id]
        old_status = record["status"]
        
        valid_transitions = {
            "pending": ["approved"],
            "approved": ["released"],
            "released": []
        }
        
        if new_status not in valid_transitions.get(old_status, []):
            return {"success": False, "error": "状态转换不合法"}
        
        record["status"] = new_status
        record["approver_address"] = approver_address
        record["updated_at"] = self.updated_at
        
        self.state["stats"][f"{old_status}_count"] -= 1
        self.state["stats"][f"{new_status}_count"] += 1
        
        self.emit_event(
            "RecordStatusUpdated",
            {
                "record_id": record_id,
                "old_status": old_status,
                "new_status": new_status,
                "approver_address": approver_address
            },
            caller_address
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "message": "记录状态更新成功"
        }

    def get_record(self, record_id: str) -> Dict[str, Any]:
        if record_id not in self.state["records"]:
            return {"success": False, "error": "记录不存在"}
        
        return {
            "success": True,
            "record": self.state["records"][record_id]
        }

    def get_all_records(self, status: Optional[str] = None) -> Dict[str, Any]:
        records = []
        for record in self.state["records"].values():
            if status is None or record["status"] == status:
                records.append(record)
        
        records.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "success": True,
            "records": records,
            "count": len(records)
        }

    def get_maintenance_history(self, start_date: int, 
                               end_date: int) -> Dict[str, Any]:
        records = []
        for record in self.state["records"].values():
            if start_date <= record["created_at"] <= end_date:
                records.append(record)
        
        records.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "success": True,
            "records": records,
            "count": len(records)
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "success": True,
            "stats": self.state["stats"]
        }
