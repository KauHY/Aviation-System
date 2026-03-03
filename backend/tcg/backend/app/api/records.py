from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any
from datetime import datetime

from app.models.maintenance import MaintenanceRecord, PeerCheckSignature
from app.services.storage import storage_service
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

# ================= 记录查询相关API =================

@router.get("/record/{record_id}", response_model=Dict[str, Any])
def get_record(record_id: str):
    """根据记录ID获取记录详情"""
    record = storage_service.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"success": True, "data": record.to_dict()}

@router.get("/aircraft/{reg_no}", response_model=Dict[str, Any])
def get_records_by_aircraft(reg_no: str):
    """根据飞机注册号获取所有记录"""
    records = storage_service.get_records_by_aircraft(reg_no)
    return {
        "success": True,
        "data": [record.to_dict() for record in records]
    }

@router.get("/jobcard/{job_card_no}", response_model=Dict[str, Any])
def get_records_by_job_card(job_card_no: str):
    """根据工卡号获取所有记录"""
    records = storage_service.get_records_by_job_card(job_card_no)
    return {
        "success": True,
        "data": [record.to_dict() for record in records]
    }

@router.get("/mechanic/{mechanic_id}", response_model=Dict[str, Any])
def get_records_by_mechanic(mechanic_id: str):
    """根据机械师工号获取所有记录"""
    records = storage_service.get_records_by_mechanic(mechanic_id)
    return {
        "success": True,
        "data": [record.to_dict() for record in records]
    }

@router.get("/records", response_model=Dict[str, Any])
def get_all_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """分页获取所有记录"""
    records = storage_service.get_all_records(page, page_size)
    total = storage_service.get_record_count()
    
    return {
        "success": True,
        "data": [record.to_dict() for record in records],
        "total": total,
        "page": page,
        "pageSize": page_size
    }

# ================= 记录写入相关API =================

@router.post("/record", response_model=Dict[str, Any])
def add_record(
    record_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """添加检修记录"""
    if not current_user.is_authorized:
        raise HTTPException(status_code=403, detail="无权限添加记录")
    
    # 创建记录实例
    record = MaintenanceRecord()
    
    # 填充基本信息
    record.aircraft_reg_no = record_data.get("aircraftRegNo", "")
    record.aircraft_type = record_data.get("aircraftType", "")
    record.revision = record_data.get("revision", 0)
    record.ata_code = record_data.get("ataCode", "")
    record.work_type = record_data.get("workType", "")
    record.location = record_data.get("location", "")
    record.work_description = record_data.get("workDescription", "")
    record.reference_document = record_data.get("referenceDocument", "")
    record.is_rii = record_data.get("isRII", False)
    
    # 处理嵌套数据
    for part_data in record_data.get("usedParts", []):
        from app.models.maintenance import PartInfo
        part = PartInfo(
            part_number=part_data.get("partNumber", ""),
            serial_number=part_data.get("serialNumber", "")
        )
        record.used_parts.append(part)
    
    record.used_tools = record_data.get("usedTools", [])
    
    for test_data in record_data.get("testMeasureData", []):
        from app.models.maintenance import TestMeasureData
        test = TestMeasureData(
            test_item_name=test_data.get("testItemName", ""),
            measured_values=test_data.get("measuredValues", ""),
            is_pass=test_data.get("isPass", False)
        )
        record.test_measure_data.append(test)
    
    fault_data = record_data.get("faultInfo", {})
    from app.models.maintenance import FaultInfo
    record.fault_info = FaultInfo(
        fim_code=fault_data.get("fimCode", ""),
        fault_description=fault_data.get("faultDescription", "")
    )
    
    for replace_data in record_data.get("replaceInfo", []):
        from app.models.maintenance import ReplaceInfo
        replace = ReplaceInfo(
            removed_part_no=replace_data.get("removedPartNo", ""),
            removed_serial_no=replace_data.get("removedSerialNo", ""),
            removed_status=replace_data.get("removedStatus", ""),
            installed_part_no=replace_data.get("installedPartNo", ""),
            installed_serial_no=replace_data.get("installedSerialNo", ""),
            installed_source=replace_data.get("installedSource", ""),
            replacement_reason=replace_data.get("replacementReason", "")
        )
        record.replace_info.append(replace)
    
    # 处理签名信息
    sig_data = record_data.get("signatures", {})
    record.signatures.performed_by = current_user.address
    record.signatures.performed_by_name = sig_data.get("performedByName", current_user.name)
    record.signatures.performed_by_id = sig_data.get("performedById", current_user.emp_id)
    record.signatures.perform_time = int(datetime.now().timestamp())
    
    # 生成记录ID
    record.generate_record_id()
    
    # 设置记录人
    record.recorder = current_user.address
    record.timestamp = int(datetime.now().timestamp())
    
    # 保存记录
    success = storage_service.add_record(record)
    if not success:
        raise HTTPException(status_code=500, detail="添加记录失败")
    
    return {
        "success": True,
        "recordId": record.record_id,
        "jobCardNo": record.job_card_no,
        "message": "记录添加成功"
    }

@router.post("/record/{record_id}/peer-check", response_model=Dict[str, Any])
def sign_peer_check(
    record_id: str,
    signature_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """互检人员签名"""
    if not current_user.is_authorized:
        raise HTTPException(status_code=403, detail="无权限签名")
    
    record = storage_service.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # 检查是否已经是已发布状态
    if record.status.value == "Released":
        raise HTTPException(status_code=400, detail="记录已经发布")
    
    # 检查是否是工作者本人
    if record.signatures.performed_by == current_user.address:
        raise HTTPException(status_code=400, detail="互检人员不能是工作者本人")
    
    # 检查是否已经签过名
    for pc in record.signatures.peer_checks:
        if pc.inspector == current_user.address:
            raise HTTPException(status_code=400, detail="已经签过名")
    
    # 添加互检签名
    pc_signature = PeerCheckSignature(
        inspector=current_user.address,
        name=signature_data.get("name", current_user.name),
        emp_id=signature_data.get("empId", current_user.emp_id),
        time=int(datetime.now().timestamp())
    )
    record.signatures.peer_checks.append(pc_signature)
    
    # 更新记录
    success = storage_service.update_record(record)
    if not success:
        raise HTTPException(status_code=500, detail="签名失败")
    
    return {
        "success": True,
        "message": "互检签名成功"
    }

@router.post("/record/{record_id}/rii", response_model=Dict[str, Any])
def sign_rii(
    record_id: str,
    signature_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """必检人员签名"""
    if not current_user.is_authorized:
        raise HTTPException(status_code=403, detail="无权限签名")
    
    record = storage_service.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # 检查是否已经是已发布状态
    if record.status.value == "Released":
        raise HTTPException(status_code=400, detail="记录已经发布")
    
    # 检查是否是必检项目
    if not record.is_rii:
        raise HTTPException(status_code=400, detail="不是必检项目")
    
    # 检查是否是工作者本人
    if record.signatures.performed_by == current_user.address:
        raise HTTPException(status_code=400, detail="必检人员不能是工作者本人")
    
    # 添加必检签名
    record.signatures.rii_by = current_user.address
    record.signatures.rii_by_name = signature_data.get("name", current_user.name)
    record.signatures.rii_by_id = signature_data.get("empId", current_user.emp_id)
    
    # 更新记录
    success = storage_service.update_record(record)
    if not success:
        raise HTTPException(status_code=500, detail="签名失败")
    
    return {
        "success": True,
        "message": "必检签名成功"
    }

@router.post("/record/{record_id}/release", response_model=Dict[str, Any])
def sign_release(
    record_id: str,
    signature_data: Dict[str, str],
    current_user: User = Depends(get_current_user)
):
    """放行人员签名（最终放行）"""
    if not current_user.is_authorized:
        raise HTTPException(status_code=403, detail="无权限签名")
    
    record = storage_service.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # 检查是否已经是已发布状态
    if record.status.value == "Released":
        raise HTTPException(status_code=400, detail="记录已经发布")
    
    # 如果是必检项目，必须先有必检签名
    if record.is_rii and not record.signatures.rii_by:
        raise HTTPException(status_code=400, detail="必检项目需要先完成必检签名")
    
    # 添加放行签名
    record.signatures.release_by = current_user.address
    record.signatures.release_by_name = signature_data.get("name", current_user.name)
    record.signatures.release_by_id = signature_data.get("empId", current_user.emp_id)
    record.signatures.release_time = int(datetime.now().timestamp())
    
    # 更新记录状态为已发布
    from app.models.maintenance import RecordStatus
    record.status = RecordStatus.RELEASED
    
    # 更新记录
    success = storage_service.update_record(record)
    if not success:
        raise HTTPException(status_code=500, detail="签名失败")
    
    return {
        "success": True,
        "message": "放行签名成功，记录已发布"
    }