import json
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
users_path = os.path.join(repo_root, "backend", "users.json")

try:
    with open(users_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f'用户数量: {len(data)}')
        print(f'用户列表: {list(data.keys())}')
        
        # 检查 usr02 是否存在
        if 'usr02' in data:
            print(f'usr02 存在: {data["usr02"]}')
        else:
            print('usr02 不存在')
            
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()