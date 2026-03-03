from enum import Enum
from typing import List, Optional
from datetime import datetime
import hashlib

class RecordStatus(Enum):
    PENDING = "Pending"
    RELEASED = "Released"

class PartInfo:
    def __init__(self, part_number: str, serial_number: str):
        self.part_number = part_number
        self.serial_number = serial_number
    
    def to_dict(self):
        return {
            "partNumber": self.part_number,
            "serialNumber": self.serial_number
        }

class TestMeasureData:
    def __init__(self, test_item_name: str, measured_values: str, is_pass: bool):
        self.test_item_name = test_item_name
        self.measured_values = measured_values
        self.is_pass = is_pass
    
    def to_dict(self):
        return {
            "testItemName": self.test_item_name,
            "measuredValues": self.measured_values,
            "isPass": self.is_pass
        }

class FaultInfo:
    def __init__(self, fim_code: str, fault_description: str):
        self.fim_code = fim_code
        self.fault_description = fault_description
    
    def to_dict(self):
        return {
            "fimCode": self.fim_code,
            "faultDescription": self.fault_description
        }

class PeerCheckSignature:
    def __init__(self, inspector: str, name: str, emp_id: str, time: int):
        self.inspector = inspector
        self.name = name
        self.emp_id = emp_id
        self.time = time
    
    def to_dict(self):
        return {
            "inspector": self.inspector,
            "name": self.name,
            "id": self.emp_id,
            "time": self.time
        }

class Signatures:
    def __init__(self):
        self.performed_by = ""
        self.performed_by_name = ""
        self.performed_by_id = ""
        self.perform_time = 0
        self.peer_checks: List[PeerCheckSignature] = []
        self.rii_by = ""
        self.rii_by_name = ""
        self.rii_by_id = ""
        self.release_by = ""
        self.release_by_name = ""
        self.release_by_id = ""
        self.release_time = 0
    
    def to_dict(self):
        return {
            "performedBy": self.performed_by,
            "performedByName": self.performed_by_name,
            "performedById": self.performed_by_id,
            "performTime": self.perform_time,
            "peerChecks": [pc.to_dict() for pc in self.peer_checks],
            "riiBy": self.rii_by,
            "riiByName": self.rii_by_name,
            "riiById": self.rii_by_id,
            "releaseBy": self.release_by,
            "releaseByName": self.release_by_name,
            "releaseById": self.release_by_id,
            "releaseTime": self.release_time
        }

class ReplaceInfo:
    def __init__(self, removed_part_no: str, removed_serial_no: str, removed_status: str,
                 installed_part_no: str, installed_serial_no: str, installed_source: str,
                 replacement_reason: str):
        self.removed_part_no = removed_part_no
        self.removed_serial_no = removed_serial_no
        self.removed_status = removed_status
        self.installed_part_no = installed_part_no
        self.installed_serial_no = installed_serial_no
        self.installed_source = installed_source
        self.replacement_reason = replacement_reason
    
    def to_dict(self):
        return {
            "removedPartNo": self.removed_part_no,
            "removedSerialNo": self.removed_serial_no,
            "removedStatus": self.removed_status,
            "installedPartNo": self.installed_part_no,
            "installedSerialNo": self.installed_serial_no,
            "installedSource": self.installed_source,
            "replacementReason": self.replacement_reason
        }

class MaintenanceRecord:
    def __init__(self):
        self.record_id = ""
        self.aircraft_reg_no = ""
        self.aircraft_type = ""
        self.job_card_no = ""
        self.revision = 0
        self.ata_code = ""
        self.work_type = ""
        self.location = ""
        self.work_description = ""
        self.reference_document = ""
        self.is_rii = False
        self.used_parts: List[PartInfo] = []
        self.used_tools: List[str] = []
        self.test_measure_data: List[TestMeasureData] = []
        self.fault_info = FaultInfo("", "")
        self.signatures = Signatures()
        self.replace_info: List[ReplaceInfo] = []
        self.recorder = ""
        self.timestamp = 0
        self.status = RecordStatus.PENDING
    
    def generate_record_id(self):
        """生成唯一的记录ID（基于哈希）"""
        unique_string = f"{self.aircraft_reg_no}-{datetime.now().timestamp()}-{hash(self)}"
        self.record_id = hashlib.sha256(unique_string.encode()).hexdigest()
        self.job_card_no = self.record_id
    
    def to_dict(self):
        return {
            "recordId": self.record_id,
            "aircraftRegNo": self.aircraft_reg_no,
            "aircraftType": self.aircraft_type,
            "jobCardNo": self.job_card_no,
            "revision": self.revision,
            "ataCode": self.ata_code,
            "workType": self.work_type,
            "location": self.location,
            "workDescription": self.work_description,
            "referenceDocument": self.reference_document,
            "isRII": self.is_rii,
            "usedParts": [part.to_dict() for part in self.used_parts],
            "usedTools": self.used_tools,
            "testMeasureData": [test.to_dict() for test in self.test_measure_data],
            "faultInfo": self.fault_info.to_dict(),
            "signatures": self.signatures.to_dict(),
            "replaceInfo": [replace.to_dict() for replace in self.replace_info],
            "recorder": self.recorder,
            "timestamp": self.timestamp,
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建记录实例"""
        record = cls()
        record.record_id = data.get("recordId", "")
        record.aircraft_reg_no = data.get("aircraftRegNo", "")
        record.aircraft_type = data.get("aircraftType", "")
        record.job_card_no = data.get("jobCardNo", "")
        record.revision = data.get("revision", 0)
        record.ata_code = data.get("ataCode", "")
        record.work_type = data.get("workType", "")
        record.location = data.get("location", "")
        record.work_description = data.get("workDescription", "")
        record.reference_document = data.get("referenceDocument", "")
        record.is_rii = data.get("isRII", False)
        
        # 处理嵌套数据
        for part_data in data.get("usedParts", []):
            part = PartInfo(
                part_data.get("partNumber", ""),
                part_data.get("serialNumber", "")
            )
            record.used_parts.append(part)
        
        record.used_tools = data.get("usedTools", [])
        
        for test_data in data.get("testMeasureData", []):
            test = TestMeasureData(
                test_data.get("testItemName", ""),
                test_data.get("measuredValues", ""),
                test_data.get("isPass", False)
            )
            record.test_measure_data.append(test)
        
        fault_data = data.get("faultInfo", {})
        record.fault_info = FaultInfo(
            fault_data.get("fimCode", ""),
            fault_data.get("faultDescription", "")
        )
        
        # 处理签名数据
        sig_data = data.get("signatures", {})
        record.signatures.performed_by = sig_data.get("performedBy", "")
        record.signatures.performed_by_name = sig_data.get("performedByName", "")
        record.signatures.performed_by_id = sig_data.get("performedById", "")
        record.signatures.perform_time = sig_data.get("performTime", 0)
        
        for pc_data in sig_data.get("peerChecks", []):
            pc = PeerCheckSignature(
                pc_data.get("inspector", ""),
                pc_data.get("name", ""),
                pc_data.get("id", ""),
                pc_data.get("time", 0)
            )
            record.signatures.peer_checks.append(pc)
        
        record.signatures.rii_by = sig_data.get("riiBy", "")
        record.signatures.rii_by_name = sig_data.get("riiByName", "")
        record.signatures.rii_by_id = sig_data.get("riiById", "")
        record.signatures.release_by = sig_data.get("releaseBy", "")
        record.signatures.release_by_name = sig_data.get("releaseByName", "")
        record.signatures.release_by_id = sig_data.get("releaseById", "")
        record.signatures.release_time = sig_data.get("releaseTime", 0)
        
        for replace_data in data.get("replaceInfo", []):
            replace = ReplaceInfo(
                replace_data.get("removedPartNo", ""),
                replace_data.get("removedSerialNo", ""),
                replace_data.get("removedStatus", ""),
                replace_data.get("installedPartNo", ""),
                replace_data.get("installedSerialNo", ""),
                replace_data.get("installedSource", ""),
                replace_data.get("replacementReason", "")
            )
            record.replace_info.append(replace)
        
        record.recorder = data.get("recorder", "")
        record.timestamp = data.get("timestamp", 0)
        record.status = RecordStatus(data.get("status", "Pending"))
        
        return record