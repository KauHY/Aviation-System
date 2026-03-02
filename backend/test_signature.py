import json
from contracts.signature_manager import SignatureManager

with open('users.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    usr02 = data.get('usr02', {})
    private_key = usr02.get('private_key', '')
    
    print(f"Private key type: {type(private_key)}")
    print(f"Private key length: {len(private_key)}")
    print(f"Private key first 100 chars: {private_key[:100]}")
    print(f"Private key last 100 chars: {private_key[-100:]}")
    
    # 检查是否包含字面的 \n
    if '\\n' in private_key:
        print("Private key contains literal \\n")
    else:
        print("Private key does NOT contain literal \\n")
    
    # 检查是否包含实际的换行符
    if '\n' in private_key:
        print("Private key contains actual newlines")
    else:
        print("Private key does NOT contain actual newlines")
    
    # 检查是否以正确的头部和尾部开始/结束
    if private_key.startswith('-----BEGIN PRIVATE KEY-----'):
        print("Private key starts with correct header")
    else:
        print("Private key does NOT start with correct header")
    
    if private_key.endswith('-----END PRIVATE KEY-----'):
        print("Private key ends with correct footer")
    else:
        print("Private key does NOT end with correct footer")
        print(f"Ends with: {private_key[-50:]}")
    
    # 尝试签名
    print("\n尝试签名...")
    try:
        sign_data = SignatureManager.create_sign_data(
            contract_address="0x123",
            method="test",
            params={},
            timestamp=1234567890,
            nonce="1234567890_test"
        )
        signature = SignatureManager.sign_data(private_key, sign_data)
        print(f"签名成功: {signature}")
    except Exception as e:
        print(f"签名失败: {e}")
        import traceback
        traceback.print_exc()