import json

with open('users.json', 'r', encoding='utf-8') as f:
    content = f.read()
    
# 检查文件中是否包含字面的 \n
if '\\n' in content:
    print("文件中包含字面的 \\n")
else:
    print("文件中不包含字面的 \\n")
    
# 检查文件中是否包含实际的换行符
if '\n' in content:
    print("文件中包含实际的换行符")
else:
    print("文件中不包含实际的换行符")
    
# 检查 usr02 的 private_key
data = json.loads(content)
usr02 = data.get('usr02', {})
private_key = usr02.get('private_key', '')

print(f"\nusr02 private_key 长度: {len(private_key)}")
print(f"usr02 private_key 前200字符: {private_key[:200]}")
print(f"usr02 private_key 后200字符: {private_key[-200:]}")

# 检查是否包含字面的 \n
if '\\n' in private_key:
    print("usr02 private_key 包含字面的 \\n")
else:
    print("usr02 private_key 不包含字面的 \\n")
    
# 检查是否包含实际的换行符
if '\n' in private_key:
    print("usr02 private_key 包含实际的换行符")
else:
    print("usr02 private_key 不包含实际的换行符")