import json

# 读取区块链事件
with open('blockchain_events.json', 'r', encoding='utf-8') as f:
    blockchain_events = json.load(f)

# 读取维修记录
with open('maintenance_records.json', 'r', encoding='utf-8') as f:
    maintenance_records = json.load(f)

# 收集所有已上链的记录信息
onchain_records = {}
for event in blockchain_events:
    if event['event_name'] == 'RecordCreated':
        record_id = event['data']['record_id']
        if record_id not in onchain_records:
            onchain_records[record_id] = {
                'block_number': event['block_index'],
                'timestamp': event['timestamp']
            }

# 为每个已上链的记录添加区块链信息
updated_count = 0
for record_id, blockchain_info in onchain_records.items():
    if record_id in maintenance_records:
        record = maintenance_records[record_id]
        if 'transaction_hash' not in record:
            # 生成交易哈希（使用记录ID）
            record['transaction_hash'] = '0x' + record_id.replace('-', '')
            record['block_number'] = blockchain_info['block_number']
            record['blockchain_timestamp'] = blockchain_info['timestamp']
            updated_count += 1
            print(f"已更新记录 {record_id}: 区块 {blockchain_info['block_number']}, 时间戳 {blockchain_info['timestamp']}")

# 保存更新后的维修记录
with open('maintenance_records.json', 'w', encoding='utf-8') as f:
    json.dump(maintenance_records, f, ensure_ascii=False, indent=2)

print(f"\n总共更新了 {updated_count} 条记录")
