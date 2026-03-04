#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为现有用户生成私钥的脚本
"""
import json
import hashlib
import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

def generate_key_pair():
    """生成RSA公私钥对"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # 获取私钥的PEM格式
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # 获取公钥
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return public_pem, private_pem

def generate_address(public_pem):
    """根据公钥生成地址"""
    return "0x" + hashlib.sha256(public_pem.encode()).hexdigest()[:40]

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    users_path = os.path.join(repo_root, "backend", "users.json")
    # 读取用户数据
    try:
        with open(users_path, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except FileNotFoundError:
        print("错误: 找不到 users.json 文件")
        return
    
    print(f"开始为 {len(users)} 个用户生成私钥...")
    
    updated = False
    for username, user_info in users.items():
        # 检查是否已经有私钥
        if "private_key" in user_info and user_info["private_key"]:
            print(f"用户 {username} 已有私钥，跳过")
            continue
        
        # 生成公私钥对
        public_pem, private_pem = generate_key_pair()
        address = generate_address(public_pem)
        
        # 更新用户信息
        user_info["public_key"] = public_pem
        user_info["private_key"] = private_pem
        user_info["address"] = address
        
        if "employee_id" not in user_info or not user_info["employee_id"]:
            user_info["employee_id"] = "EMP" + address[-8:]
        
        updated = True
        print(f"✓ 为用户 {username} 生成公私钥对")
        print(f"  地址: {address}")
        print(f"  员工ID: {user_info['employee_id']}")
    
    if updated:
        # 保存用户数据
        with open(users_path, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        print(f"\n成功更新用户数据并保存到 users.json")
    else:
        print("\n所有用户都已拥有私钥，无需更新")

if __name__ == "__main__":
    main()
