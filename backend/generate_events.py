import json
from datetime import datetime

# 读取维修记录
with open('maintenance_records.json', 'r', encoding='utf-8') as f:
    maintenance_records = json.load(f)

# 读取用户信息
with open('users.json', 'r', encoding='utf-8') as f:
    users = json.load(f)

# 获取第一个管理员和管理人员的地址
manager_address = None
admin_address = None

for username, user in users.items():
    if user.get('role') == 'manager' and manager_address is None:
        manager_address = user.get('address', '')
    elif user.get('role') == 'admin' and admin_address is None:
        admin_address = user.get('address', '')
    
    if manager_address and admin_address:
        break

print(f"管理人员地址: {manager_address}")
print(f"管理员地址: {admin_address}")

# 创建事件列表
blockchain_events = []

# 为每个维修记录创建事件
for record_id, record in maintenance_records.items():
    technician_id = record.get('technician_id', '')
    technician_name = record.get('technician_name', '')
    
    # 获取技术人员地址
    technician_address = ''
    if technician_id in users:
        technician_address = users[technician_id].get('address', '')
    
    # 创建 RecordCreated 事件
    created_event = {
        "event_name": "RecordCreated",
        "contract_address": "0x0000000000000000000000000000000000000001",
        "block_index": len(blockchain_events),
        "timestamp": record.get('created_at', int(datetime.now().timestamp())),
        "data": {
            "record_id": record_id,
            "aircraft_registration": record.get('aircraft_registration', ''),
            "subchain_address": "",
            "maintenance_type": record.get('maintenance_type', ''),
            "description": record.get('maintenance_description', ''),
            "technician_address": technician_address
        },
        "signer_address": technician_address
    }
    blockchain_events.append(created_event)
    
    # 根据状态创建相应的事件
    status = record.get('status', '')
    if status == 'approved':
        approved_event = {
            "event_name": "RecordApproved",
            "contract_address": "0x0000000000000000000000000000000000000001",
            "block_index": len(blockchain_events),
            "timestamp": record.get('updated_at', int(datetime.now().timestamp())),
            "data": {
                "record_id": record_id,
                "aircraft_registration": record.get('aircraft_registration', ''),
                "subchain_address": ""
            },
            "signer_address": manager_address or "0xmanager_address"
        }
        blockchain_events.append(approved_event)
    elif status == 'released':
        approved_event = {
            "event_name": "RecordApproved",
            "contract_address": "0x0000000000000000000000000000000000000001",
            "block_index": len(blockchain_events),
            "timestamp": record.get('updated_at', int(datetime.now().timestamp())) - 100,
            "data": {
                "record_id": record_id,
                "aircraft_registration": record.get('aircraft_registration', ''),
                "subchain_address": ""
            },
            "signer_address": manager_address or "0xmanager_address"
        }
        blockchain_events.append(approved_event)
        
        released_event = {
            "event_name": "RecordReleased",
            "contract_address": "0x0000000000000000000000000000000000000001",
            "block_index": len(blockchain_events),
            "timestamp": record.get('updated_at', int(datetime.now().timestamp())),
            "data": {
                "record_id": record_id,
                "aircraft_registration": record.get('aircraft_registration', ''),
                "subchain_address": ""
            },
            "signer_address": admin_address or "0xadmin_address"
        }
        blockchain_events.append(released_event)
    elif status == 'rejected':
        rejected_event = {
            "event_name": "RecordRejected",
            "contract_address": "0x0000000000000000000000000000000000000001",
            "block_index": len(blockchain_events),
            "timestamp": record.get('updated_at', int(datetime.now().timestamp())),
            "data": {
                "record_id": record_id,
                "aircraft_registration": record.get('aircraft_registration', ''),
                "subchain_address": ""
            },
            "signer_address": manager_address or "0xmanager_address"
        }
        blockchain_events.append(rejected_event)

# 保存事件到文件
with open('blockchain_events.json', 'w', encoding='utf-8') as f:
    json.dump(blockchain_events, f, ensure_ascii=False, indent=2)

print(f"成功创建 {len(blockchain_events)} 个区块链事件")
print(f"事件文件已保存到 blockchain_events.json")
