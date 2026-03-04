import json
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
users_path = os.path.join(repo_root, "backend", "users.json")

with open(users_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    usr02 = data.get('usr02', {})
    private_key = usr02.get('private_key', '')
    
    print(f"Private key type: {type(private_key)}")
    print(f"Private key length: {len(private_key)}")
    print(f"Private key repr: {repr(private_key[:200])}")
    print(f"Private key contains \\n: {'\\n' in private_key}")
    print(f"Private key contains \\r: {'\\r' in private_key}")
    
    # 检查是否是标准的 PEM 格式
    if private_key.startswith('-----BEGIN PRIVATE KEY-----'):
        print("Private key starts with correct header")
    else:
        print("Private key does NOT start with correct header")
    
    if private_key.endswith('-----END PRIVATE KEY-----'):
        print("Private key ends with correct footer")
    else:
        print("Private key does NOT end with correct footer")
        print(f"Ends with: {private_key[-30:]}")