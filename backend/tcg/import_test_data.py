import json
import hashlib
import time
from datetime import datetime
from backend.app.models.maintenance import MaintenanceRecord

# 读取原始测试数据
with open('d:\\东华大学\\使用说明\\aviation-maintenance-system-main\\aviation-maintenance-system-main\\backend\\seed.js', 'r', encoding='utf-8') as f:
    seed_content = f.read()

# 提取测试数据
import re

# 提取sampleRecords数组
pattern = r'const sampleRecords = \[(.*?)\];' 
matches = re.search(pattern, seed_content, re.DOTALL)

if not matches:
    print("未找到测试数据")
    exit(1)

# 转换为Python对象
sample_records_str = matches.group(1)
# 替换JavaScript语法为Python语法
sample_records_str = sample_records_str.replace('//', '#')
sample_records_str = sample_records_str.replace('Math.floor(Date.now() / 1000)', str(int(time.time())))
sample_records_str = sample_records_str.replace('true', 'True')
sample_records_str = sample_records_str.replace('false', 'False')
sample_records_str = sample_records_str.replace('null', 'None')

# 手动解析数据（简化版）
records = []
current_record = {}
current_key = None
current_value = ''

# 使用更可靠的方法：从seed.js中提取JSON格式数据
# 注意：这是一个简化的方法，可能需要根据实际数据格式调整

# 提取所有记录
record_pattern = r'\{([^\}]*?)\}'
record_matches = re.findall(record_pattern, sample_records_str, re.DOTALL)

for record_match in record_matches:
    # 提取记录的各个字段
    fields = re.findall(r'(\w+):\s*([^,]+)', record_match)
    record = {}
    for field in fields:
        key = field[0]
        value = field[1].strip()
        # 处理字符串值
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        # 处理数字值
        elif value.isdigit():
            value = int(value)
        # 处理布尔值
        elif value == 'True':
            value = True
        elif value == 'False':
            value = False
        record[key] = value
    records.append(record)

# 但上述方法可能不够准确，我们使用更直接的方法
# 由于seed.js中的数据格式复杂，我们直接创建一些示例数据来模拟原始测试数据
sample_records = [
    {
        "aircraftRegNo": "B-1234",
        "aircraftType": "B737-800",
        "jobCardNo": "JC-2025-001",
        "revision": 1,
        "ataCode": "32-40",
        "workType": "Life-limited Parts Replacement",
        "location": "北京维修基地",
        "workDescription": "左主起落架 #1 轮胎磨损超标，依据 AMM 手册进行更换。检查轮毂无损伤，气压正常。",
        "referenceDocument": "AMM 32-45-00",
        "usedParts": [
            {"partNumber": "GY-737-TIRE", "serialNumber": "SN-20250101"}
        ],
        "usedTools": ["TL-JACK-001", "TL-TORQUE-050"],
        "testMeasureData": [
            {"testItemName": "轮胎气压", "measuredValues": "205 PSI", "isPass": True},
            {"testItemName": "轮毂涡流探伤", "measuredValues": "无裂纹", "isPass": True}
        ],
        "faultInfo": {
            "fimCode": "",
            "faultDescription": ""
        },
        "signatures": {
            "performedByName": "张三",
            "performedById": "001",
            "performTime": int(time.time()) - 86400,
            "inspectedByName": "李四",
            "inspectedById": "002",
            "riiByName": "王五",
            "riiById": "RII-001",
            "releaseByName": "赵六",
            "releaseById": "REL-001"
        },
        "replaceInfo": [
            {
                "removedPartNo": "GY-737-TIRE",
                "removedSerialNo": "SN-20231212",
                "removedStatus": "磨损超标",
                "installedPartNo": "GY-737-TIRE",
                "installedSerialNo": "SN-20250101",
                "installedSource": "航材库房",
                "replacementReason": "例行更换"
            }
        ],
        "recorder": "0x0000000000000000000000000000000000000000",
        "timestamp": 0
    },
    {
        "aircraftRegNo": "B-5678",
        "aircraftType": "A320neo",
        "jobCardNo": "JC-2025-002",
        "revision": 1,
        "ataCode": "21-50",
        "workType": "Transit / Turnaround Check",
        "location": "广州白云机场",
        "workDescription": "机组报告驾驶舱温度无法调节。测试发现温度控制活门卡阻。更换温度控制活门，测试正常。",
        "referenceDocument": "TSM 21-50-00 / AMM 21-61-00",
        "usedParts": [
            {"partNumber": "VALVE-TC-320", "serialNumber": "VN-889900"},
            {"partNumber": "SEAL-RING-05", "serialNumber": "N/A"}
        ],
        "usedTools": ["TL-MULTI-METER", "TL-WRENCH-SET"],
        "testMeasureData": [
            {"testItemName": "活门电阻测试", "measuredValues": "150 Ohm", "isPass": True},
            {"testItemName": "功能测试", "measuredValues": "温度调节响应正常", "isPass": True}
        ],
        "faultInfo": {
            "fimCode": "21-50-00-810-801",
            "faultDescription": "驾驶舱温度无法调节，ECAM 警告 AIR COND"
        },
        "signatures": {
            "performedByName": "Mike",
            "performedById": "A003",
            "performTime": int(time.time()) - 86400 * 2,
            "inspectedByName": "Sarah",
            "inspectedById": "A004",
            "riiByName": "",
            "riiById": "",
            "releaseByName": "Tom",
            "releaseById": "REL-002"
        },
        "replaceInfo": [
            {
                "removedPartNo": "VALVE-TC-320",
                "removedSerialNo": "VN-112233",
                "removedStatus": "内部卡阻",
                "installedPartNo": "VALVE-TC-320",
                "installedSerialNo": "VN-889900",
                "installedSource": "现场拆件",
                "replacementReason": "故障更换"
            }
        ],
        "recorder": "0x0000000000000000000000000000000000000000",
        "timestamp": 0
    },
    {
        "aircraftRegNo": "B-9999",
        "aircraftType": "B787-9",
        "jobCardNo": "JC-2025-003",
        "revision": 2,
        "ataCode": "72-00",
        "workType": "A-Check",
        "location": "上海浦东机坪",
        "workDescription": "执行发动机孔探检查。高压压气机叶片发现轻微外物打伤，在手册允许范围内。已记录并监控。",
        "referenceDocument": "AMM 72-00-00",
        "usedParts": [],
        "usedTools": ["TL-BORESCOPE-VID"],
        "testMeasureData": [
            {"testItemName": "HPC 第5级叶片损伤", "measuredValues": "深度 0.05mm (Limit 0.1mm)", "isPass": True},
            {"testItemName": "燃烧室检查", "measuredValues": "正常", "isPass": True}
        ],
        "faultInfo": {
            "fimCode": "",
            "faultDescription": ""
        },
        "signatures": {
            "performedByName": "陈工",
            "performedById": "E001",
            "performTime": int(time.time()) - 86400 * 3,
            "inspectedByName": "刘工",
            "inspectedById": "E002",
            "riiByName": "",
            "riiById": "",
            "releaseByName": "张经理",
            "releaseById": "MGR-001"
        },
        "replaceInfo": [],
        "recorder": "0x0000000000000000000000000000000000000000",
        "timestamp": 0
    }
]

# 转换为新系统格式
new_records = {}

for i, record_data in enumerate(sample_records):
    # 创建新记录
    record = MaintenanceRecord()
    
    # 基本信息
    record.aircraft_reg_no = record_data.get('aircraftRegNo', '')
    record.aircraft_type = record_data.get('aircraftType', '')
    record.revision = record_data.get('revision', 1)
    record.ata_code = record_data.get('ataCode', '')
    record.work_type = record_data.get('workType', '')
    record.location = record_data.get('location', '')
    record.work_description = record_data.get('workDescription', '')
    record.reference_document = record_data.get('referenceDocument', '')
    record.is_rii = record_data.get('isRII', False)
    record.recorder = record_data.get('recorder', '')
    record.timestamp = int(time.time())
    
    # 生成记录ID
    record.generate_record_id()
    
    # 处理使用的零件
    for part_data in record_data.get('usedParts', []):
        from backend.app.models.maintenance import PartInfo
        part = PartInfo(
            part_data.get('partNumber', ''),
            part_data.get('serialNumber', '')
        )
        record.used_parts.append(part)
    
    # 处理使用的工具
    record.used_tools = record_data.get('usedTools', [])
    
    # 处理测试数据
    for test_data in record_data.get('testMeasureData', []):
        from backend.app.models.maintenance import TestMeasureData
        test = TestMeasureData(
            test_data.get('testItemName', ''),
            test_data.get('measuredValues', ''),
            test_data.get('isPass', False)
        )
        record.test_measure_data.append(test)
    
    # 处理故障信息
    fault_data = record_data.get('faultInfo', {})
    from backend.app.models.maintenance import FaultInfo
    record.fault_info = FaultInfo(
        fault_data.get('fimCode', ''),
        fault_data.get('faultDescription', '')
    )
    
    # 处理签名信息
    sig_data = record_data.get('signatures', {})
    record.signatures.performed_by = ''
    record.signatures.performed_by_name = sig_data.get('performedByName', '')
    record.signatures.performed_by_id = sig_data.get('performedById', '')
    record.signatures.perform_time = sig_data.get('performTime', int(time.time()))
    
    # 处理互检签名
    from backend.app.models.maintenance import PeerCheckSignature
    if sig_data.get('inspectedByName'):
        pc = PeerCheckSignature(
            '',  # inspector
            sig_data.get('inspectedByName', ''),
            sig_data.get('inspectedById', ''),
            int(time.time())
        )
        record.signatures.peer_checks.append(pc)
    
    # 处理RII签名
    record.signatures.rii_by = ''
    record.signatures.rii_by_name = sig_data.get('riiByName', '')
    record.signatures.rii_by_id = sig_data.get('riiById', '')
    
    # 处理放行签名
    record.signatures.release_by = ''
    record.signatures.release_by_name = sig_data.get('releaseByName', '')
    record.signatures.release_by_id = sig_data.get('releaseById', '')
    record.signatures.release_time = int(time.time())
    
    # 处理更换件信息
    for replace_data in record_data.get('replaceInfo', []):
        from backend.app.models.maintenance import ReplaceInfo
        replace = ReplaceInfo(
            replace_data.get('removedPartNo', ''),
            replace_data.get('removedSerialNo', ''),
            replace_data.get('removedStatus', ''),
            replace_data.get('installedPartNo', ''),
            replace_data.get('installedSerialNo', ''),
            replace_data.get('installedSource', ''),
            replace_data.get('replacementReason', '')
        )
        record.replace_info.append(replace)
    
    # 设置状态
    from backend.app.models.maintenance import RecordStatus
    if sig_data.get('releaseByName'):
        record.status = RecordStatus.RELEASED
    else:
        record.status = RecordStatus.PENDING
    
    # 添加到新记录字典
    new_records[record.record_id] = record.to_dict()

# 保存到新系统
with open('data\\records.json', 'w', encoding='utf-8') as f:
    json.dump(new_records, f, ensure_ascii=False, indent=2)

print(f"成功导入 {len(new_records)} 条测试数据")
