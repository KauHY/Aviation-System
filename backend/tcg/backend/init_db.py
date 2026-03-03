#!/usr/bin/env python3
"""
初始化数据库脚本
用于创建默认管理员用户
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.storage import storage_service
from app.models.user import User

def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    # 检查是否已有用户
    all_users = storage_service.get_all_users()
    if all_users:
        print("数据库已初始化，跳过...")
        return
    
    # 创建默认管理员用户
    admin_user = User(
        address="0x0000000000000000000000000000000000000001",
        name="管理员",
        emp_id="ADMIN001",
        is_authorized=True
    )
    
    success = storage_service.add_user(admin_user)
    if success:
        print("默认管理员用户创建成功！")
        print(f"管理员地址: {admin_user.address}")
        print(f"管理员姓名: {admin_user.name}")
        print(f"管理员工号: {admin_user.emp_id}")
    else:
        print("默认管理员用户创建失败！")
    
    # 创建测试用户
    test_user = User(
        address="0x0000000000000000000000000000000000000002",
        name="测试用户",
        emp_id="TEST001",
        is_authorized=True
    )
    
    success = storage_service.add_user(test_user)
    if success:
        print("测试用户创建成功！")
        print(f"测试用户地址: {test_user.address}")
        print(f"测试用户姓名: {test_user.name}")
        print(f"测试用户工号: {test_user.emp_id}")
    else:
        print("测试用户创建失败！")
    
    print("数据库初始化完成！")

if __name__ == "__main__":
    init_database()