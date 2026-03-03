#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证服务模块
"""

import os
import json
from typing import Dict, Optional

class AuthService:
    def __init__(self):
        self.users_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'users.json')
        self._ensure_users_file()
        # 尝试导入passlib，如果失败则使用简单的密码验证
        self.use_passlib = False
        self.pwd_context = None
        try:
            from passlib.context import CryptContext
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            self.use_passlib = True
        except Exception as e:
            print(f"Passlib导入失败，使用简单密码验证: {e}")
    
    def _ensure_users_file(self):
        """确保用户文件存在"""
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    def _load_users(self) -> Dict:
        """加载用户数据"""
        with open(self.users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_users(self, users: Dict):
        """保存用户数据"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def get_user_by_address(self, address: str) -> Optional[Dict]:
        """根据地址获取用户"""
        users = self._load_users()
        return users.get(address)
    
    def authenticate(self, address: str, password: str) -> Optional[Dict]:
        """验证用户"""
        user = self.get_user_by_address(address)
        if not user:
            return None
        
        # 检查用户数据是否完整，如果缺少password字段，为其添加默认密码
        if 'password' not in user:
            # 为现有用户添加默认密码 '123456'
            users = self._load_users()
            users[address]['password'] = self.get_password_hash('123456')
            # 确保字段名一致性
            if 'empId' in users[address] and 'employee_id' not in users[address]:
                users[address]['employee_id'] = users[address]['empId']
            if 'is_admin' not in users[address]:
                users[address]['is_admin'] = users[address].get('isAuthorized', False) and address == "0x0000000000000000000000000000000000000001"
            self._save_users(users)
            user = users[address]
        
        if not self.verify_password(password, user['password']):
            return None
        
        return user
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        # 确保密码长度不超过72字节
        plain_password = plain_password[:72]
        if self.use_passlib and self.pwd_context:
            try:
                return self.pwd_context.verify(plain_password, hashed_password)
            except Exception as e:
                print(f"Passlib验证失败，使用简单密码验证: {e}")
                # 如果passlib验证失败，使用简单的字符串比较
                return plain_password == hashed_password
        else:
            # 使用简单的字符串比较
            return plain_password == hashed_password
    
    def get_password_hash(self, password: str) -> str:
        """获取密码哈希"""
        # 确保密码长度不超过72字节
        password = password[:72]
        if self.use_passlib and self.pwd_context:
            try:
                return self.pwd_context.hash(password)
            except Exception as e:
                print(f"Passlib哈希失败，使用原始密码: {e}")
                # 如果passlib哈希失败，返回原始密码
                return password
        else:
            # 返回原始密码
            return password
    
    def authorize_user(self, address: str, name: str, employee_id: str, password: str) -> bool:
        """授权用户"""
        users = self._load_users()
        
        if address in users:
            return False
        
        users[address] = {
            'address': address,
            'name': name,
            'employee_id': employee_id,
            'password': self.get_password_hash(password),
            'is_admin': False
        }
        
        self._save_users(users)
        return True
    
    def revoke_user(self, address: str) -> bool:
        """取消用户授权"""
        users = self._load_users()
        
        if address not in users:
            return False
        
        del users[address]
        self._save_users(users)
        return True
    
    def get_authorized_users(self) -> list:
        """获取所有授权用户"""
        users = self._load_users()
        return list(users.values())
    
    def create_default_users(self):
        """创建默认用户"""
        users = self._load_users()
        
        # 默认管理员用户
        admin_address = "0x0000000000000000000000000000000000000001"
        if admin_address not in users:
            users[admin_address] = {
                'address': admin_address,
                'name': "管理员",
                'employee_id': "ADMIN001",
                'password': self.get_password_hash("123456"),
                'is_admin': True
            }
        
        # 默认测试用户
        test_address = "0x0000000000000000000000000000000000000002"
        if test_address not in users:
            users[test_address] = {
                'address': test_address,
                'name': "测试用户",
                'employee_id': "TEST001",
                'password': self.get_password_hash("123456"),
                'is_admin': False
            }
        
        self._save_users(users)