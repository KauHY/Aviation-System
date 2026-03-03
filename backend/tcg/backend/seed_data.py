#!/usr/bin/env python3
"""
种子数据脚本
用于向系统中添加测试数据
"""
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.storage import storage_service
from app.models.maintenance import MaintenanceRecord, PartInfo, TestMeasureData, FaultInfo, ReplaceInfo

def seed_data():
    """添加测试数据"""
    print("开始添加测试数据...")
    
    # 检查是否已有数据
    record_count = storage_service.get_record_count()
    if record_count > 0:
        print(f"系统中已有 {record_count} 条记录，跳过添加测试数据...")
        return
    
    # 测试数据 1: 轮胎更换记录
    record1 = MaintenanceRecord()
    record1.aircraft_reg_no = "B-1234"
    record1.aircraft_type = "A320"
    record1.revision = 1
    record1.ata_code = "32"
    record1.work_type = "部件更换"
    record1.location = "上海浦东国际机场"
    record1.work_description = "左主起落架轮胎更换"
    record1.reference_document = "AMM 32-11-00"
    record1.is_rii = True
    
    # 故障信息
    record1.fault_info = FaultInfo(
        fim_code="FIM32-11",
        fault_description="轮胎磨损超过限制"
    )
    
    # 使用的零件
    record1.used_parts.append(PartInfo(
        part_number="A320-32-1100",
        serial_number="SN12345"
    ))
    
    # 使用的工具
    record1.used_tools = ["千斤顶", "扳手", "轮胎压力表"]
    
    # 测试测量数据
    record1.test_measure_data.append(TestMeasureData(
        test_item_name="轮胎压力",
        measured_values="120 PSI",
        is_pass=True
    ))
    
    # 更换件信息
    record1.replace_info.append(ReplaceInfo(
        removed_part_no="A320-32-1100",
        removed_serial_no="SN10001",
        removed_status="磨损",
        installed_part_no="A320-32-1100",
        installed_serial_no="SN12345",
        installed_source="航空公司库存",
        replacement_reason="磨损超过限制"
    ))
    
    # 签名信息
    record1.signatures.performed_by = "0x0000000000000000000000000000000000000002"
    record1.signatures.performed_by_name = "张三"
    record1.signatures.performed_by_id = "MECH001"
    record1.signatures.perform_time = int(datetime.now().timestamp())
    
    # 必检签名
    record1.signatures.rii_by = "0x0000000000000000000000000000000000000001"
    record1.signatures.rii_by_name = "管理员"
    record1.signatures.rii_by_id = "ADMIN001"
    
    # 放行签名
    record1.signatures.release_by = "0x0000000000000000000000000000000000000001"
    record1.signatures.release_by_name = "管理员"
    record1.signatures.release_by_id = "ADMIN001"
    record1.signatures.release_time = int(datetime.now().timestamp())
    
    # 生成记录ID
    record1.generate_record_id()
    record1.recorder = "0x0000000000000000000000000000000000000002"
    record1.timestamp = int(datetime.now().timestamp())
    
    # 更新状态为已发布
    from app.models.maintenance import RecordStatus
    record1.status = RecordStatus.RELEASED
    
    # 保存记录
    success = storage_service.add_record(record1)
    if success:
        print("测试数据 1 添加成功: 轮胎更换记录")
    else:
        print("测试数据 1 添加失败")
    
    # 测试数据 2: 发动机检查记录
    record2 = MaintenanceRecord()
    record2.aircraft_reg_no = "B-5678"
    record2.aircraft_type = "B737"
    record2.revision = 1
    record2.ata_code = "71"
    record2.work_type = "定期检查"
    record2.location = "北京首都国际机场"
    record2.work_description = "左发动机定期检查"
    record2.reference_document = "AMM 71-00-00"
    record2.is_rii = True
    
    # 使用的工具
    record2.used_tools = ["发动机检查工具包", "温度计", "振动分析仪"]
    
    # 测试测量数据
    record2.test_measure_data.append(TestMeasureData(
        test_item_name="发动机温度",
        measured_values="正常",
        is_pass=True
    ))
    record2.test_measure_data.append(TestMeasureData(
        test_item_name="发动机振动",
        measured_values="0.1 mm",
        is_pass=True
    ))
    
    # 签名信息
    record2.signatures.performed_by = "0x0000000000000000000000000000000000000002"
    record2.signatures.performed_by_name = "张三"
    record2.signatures.performed_by_id = "MECH001"
    record2.signatures.perform_time = int(datetime.now().timestamp())
    
    # 生成记录ID
    record2.generate_record_id()
    record2.recorder = "0x0000000000000000000000000000000000000002"
    record2.timestamp = int(datetime.now().timestamp())
    
    # 保存记录
    success = storage_service.add_record(record2)
    if success:
        print("测试数据 2 添加成功: 发动机检查记录")
    else:
        print("测试数据 2 添加失败")
    
    # 测试数据 3: 航电系统故障排查
    record3 = MaintenanceRecord()
    record3.aircraft_reg_no = "B-1234"
    record3.aircraft_type = "A320"
    record3.revision = 1
    record3.ata_code = "23"
    record3.work_type = "故障排查"
    record3.location = "广州白云国际机场"
    record3.work_description = "导航系统故障排查"
    record3.reference_document = "AMM 23-10-00"
    record3.is_rii = False
    
    # 故障信息
    record3.fault_info = FaultInfo(
        fim_code="FIM23-10",
        fault_description="导航显示器无显示"
    )
    
    # 使用的零件
    record3.used_parts.append(PartInfo(
        part_number="A320-23-1000",
        serial_number="SN54321"
    ))
    
    # 使用的工具
    record3.used_tools = ["万用表", "航电测试设备"]
    
    # 测试测量数据
    record3.test_measure_data.append(TestMeasureData(
        test_item_name="电压测试",
        measured_values="28V",
        is_pass=True
    ))
    record3.test_measure_data.append(TestMeasureData(
        test_item_name="信号测试",
        measured_values="正常",
        is_pass=True
    ))
    
    # 更换件信息
    record3.replace_info.append(ReplaceInfo(
        removed_part_no="A320-23-1000",
        removed_serial_no="SN99999",
        removed_status="故障",
        installed_part_no="A320-23-1000",
        installed_serial_no="SN54321",
        installed_source="航材库",
        replacement_reason="显示器故障"
    ))
    
    # 签名信息
    record3.signatures.performed_by = "0x0000000000000000000000000000000000000002"
    record3.signatures.performed_by_name = "张三"
    record3.signatures.performed_by_id = "MECH001"
    record3.signatures.perform_time = int(datetime.now().timestamp())
    
    # 生成记录ID
    record3.generate_record_id()
    record3.recorder = "0x0000000000000000000000000000000000000002"
    record3.timestamp = int(datetime.now().timestamp())
    
    # 保存记录
    success = storage_service.add_record(record3)
    if success:
        print("测试数据 3 添加成功: 航电系统故障排查")
    else:
        print("测试数据 3 添加失败")
    
    print("测试数据添加完成！")

if __name__ == "__main__":
    seed_data()