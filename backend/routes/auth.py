import json
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

import app_state

router = APIRouter()

@router.post("/api/auth/register")
async def register_user(request: Request):
    """用户注册"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "user")  # 默认角色为user

        if not username or not password:
            return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})

        if len(password) < 6:
            return JSONResponse(status_code=400, content={"error": "密码长度至少6位"})

        if username in app_state.users:
            return JSONResponse(status_code=400, content={"error": "用户名已存在"})

        # 生成RSA公私钥对
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

        # 生成唯一地址（基于公钥）
        address = "0x" + hashlib.sha256(public_pem.encode()).hexdigest()[:40]

        # 存储用户信息（包括私钥，用于自动签名）
        hashed_password = app_state.auth.get_password_hash(password) if hasattr(app_state.auth, 'get_password_hash') else password
        app_state.users[username] = {
            "password": hashed_password,
            "role": role,
            "address": address,
            "name": username,
            "employee_id": "EMP" + address[-8:],
            "public_key": public_pem,
            "private_key": private_pem,  # 存储私钥用于自动签名
            "created_at": int(datetime.now().timestamp())
        }
        app_state.user_roles[username] = role  # 存储用户角色

        # 同时添加到检修系统的用户数据中
        try:
            app_state.auth.authorize_user(address, username, "EMP" + address[-8:], password)
        except Exception as e:
            print(f"添加用户到检修系统失败: {e}")

        # 保存用户数据
        app_state.save_user_data()

        return JSONResponse(status_code=200, content={
            "message": "注册成功",
            "username": username,
            "role": role,
            "address": address,
            "employee_id": "EMP" + address[-8:],
            "public_key": public_pem,
            "private_key": private_pem,  # 私钥已存储在服务器，用于自动签名
            "info": "您的私钥已存储在服务器，系统将自动使用私钥进行签名操作。"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "注册失败: " + str(e)})

@router.post("/api/auth/login")
async def login_user(request: Request):
    """用户登录"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})

        # 检查用户是否存在
        if username not in app_state.users:
            return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})

        # 获取用户信息
        user_info = app_state.users[username]
        user_password = user_info.get("password", user_info)  # 兼容旧数据格式

        # 验证密码
        if hasattr(app_state.auth, 'verify_password'):
            # 使用检修系统的密码验证
            if not app_state.auth.verify_password(password, user_password):
                return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        else:
            # 使用旧的密码验证方式
            if user_password != password:
                return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})

        # 获取用户角色和公钥
        role = user_info.get("role", app_state.user_roles.get(username, "user"))
        address = user_info.get("address", "0x" + hashlib.sha256(username.encode()).hexdigest()[:40])
        public_key = user_info.get("public_key", "")
        private_key = ""

        # 每次登录都生成新的公私钥对（为了安全）
        private_key_obj = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # 获取私钥的PEM格式
        private_pem = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        # 获取公钥
        public_key_obj = private_key_obj.public_key()
        public_pem = public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

        # 生成唯一地址（基于公钥）
        address = "0x" + hashlib.sha256(public_pem.encode()).hexdigest()[:40]

        # 更新用户信息
        user_info["public_key"] = public_pem
        user_info["address"] = address
        if "employee_id" not in user_info:
            user_info["employee_id"] = "EMP" + address[-8:]

        # 保存用户数据
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(app_state.users, f, ensure_ascii=False, indent=2)

        public_key = public_pem
        private_key = private_pem
        print(f"为用户 {username} 生成新公钥和地址: {address}")

        # 创建访问令牌（包含角色信息）
        access_token_expires = timedelta(minutes=app_state.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = app_state.create_access_token(
            data={
                "sub": address,
                "username": username,
                "public_key": public_key,
                "role": role
            },
            expires_delta=access_token_expires
        )

        return JSONResponse(status_code=200, content={
            "message": "登录成功",
            "username": username,
            "role": role,
            "address": address,
            "public_key": public_key,
            "private_key": private_key,
            "employee_id": user_info.get("employee_id", "EMP" + address[-8:]),
            "access_token": access_token
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "登录失败: " + str(e)})

@router.post("/api/auth/verify-signature")
async def verify_signature(request: Request):
    """验证用户签名"""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import padding

        data = await request.json()
        signature = data.get("signature")
        public_key_pem = data.get("public_key")
        message = data.get("message")

        if not signature or not public_key_pem or not message:
            return JSONResponse(status_code=400, content={"error": "签名、公钥和消息不能为空"})

        # 加载公钥
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )

        # 验证签名
        try:
            public_key.verify(
                bytes.fromhex(signature),
                message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return JSONResponse(status_code=200, content={"message": "签名验证成功", "valid": True})
        except Exception as e:
            return JSONResponse(status_code=401, content={"error": "签名验证失败", "valid": False})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "验证签名失败: " + str(e)})

@router.post("/api/profile/update")
async def update_profile(request: Request):
    """更新个人信息"""
    try:
        data = await request.json()

        # 从token获取当前用户
        current_username = None
        try:
            # 优先从cookie获取token
            token = request.cookies.get("access_token")
            if not token:
                # 如果cookie中没有，尝试从Authorization header获取
                token = request.headers.get("Authorization", "").replace("Bearer ", "")

            if token:
                payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
                current_username = payload.get("username")
                print(f"[DEBUG] 从token获取当前用户: {current_username}")
        except Exception as e:
            print(f"[DEBUG] 获取token失败: {e}")
            return JSONResponse(status_code=401, content={"error": "未授权"})

        if not current_username:
            return JSONResponse(status_code=401, content={"error": "未授权"})

        # 验证当前密码（如果修改密码）
        if data.get('new_password'):
            current_password = data.get('current_password')
            if not current_password:
                return JSONResponse(status_code=400, content={"error": "请输入当前密码"})

            # 验证当前密码
            if current_username not in app_state.users or app_state.users[current_username].get('password') != current_password:
                return JSONResponse(status_code=400, content={"error": "当前密码错误"})

        # 更新用户信息
        if current_username in app_state.users:
            # 更新用户信息
            app_state.users[current_username].update({
                'name': data.get('name', app_state.users[current_username].get('name', current_username)),
                'employee_id': data.get('employee_id', app_state.users[current_username].get('employee_id')),
                'email': data.get('email', app_state.users[current_username].get('email')),
                'phone': data.get('phone', app_state.users[current_username].get('phone')),
                'specialty': data.get('specialty', app_state.users[current_username].get('specialty')),
                'bio': data.get('bio', app_state.users[current_username].get('bio'))
            })

            # 如果修改密码
            if data.get('new_password'):
                app_state.users[current_username]['password'] = data['new_password']

            # 保存用户数据
            app_state.save_user_data()

            print(f"[DEBUG] 用户 {current_username} 信息更新成功")
            return JSONResponse(status_code=200, content={"message": "个人信息更新成功"})
        else:
            print(f"[DEBUG] 用户 {current_username} 不存在")
            return JSONResponse(status_code=404, content={"error": "用户不存在"})
    except Exception as e:
        print(f"[DEBUG] 更新个人信息失败: {e}")
        return JSONResponse(status_code=500, content={"error": "更新个人信息失败: " + str(e)})

@router.get("/api/user/current")
async def get_current_user(request: Request):
    """获取当前用户信息"""
    try:
        # 从token获取当前用户
        current_username = None
        try:
            # 优先从cookie获取token
            token = request.cookies.get("access_token")
            if not token:
                # 如果cookie中没有，尝试从Authorization header获取
                token = request.headers.get("Authorization", "").replace("Bearer ", "")

            if token:
                payload = jwt.decode(token, app_state.SECRET_KEY, algorithms=[app_state.ALGORITHM])
                current_username = payload.get("username")
                print(f"[DEBUG] 从token获取当前用户: {current_username}")
        except Exception as e:
            print(f"[DEBUG] 获取token失败: {e}")
            return JSONResponse(status_code=401, content={"error": "未授权"})

        if not current_username:
            return JSONResponse(status_code=401, content={"error": "未授权"})

        # 获取用户信息
        if current_username in app_state.users:
            user_data = app_state.users[current_username]
            print(f"[DEBUG] 获取用户信息成功: {current_username}")
            return JSONResponse(status_code=200, content={
                "username": current_username,
                "name": user_data.get("name", current_username),
                "employee_id": user_data.get("employee_id"),
                "email": user_data.get("email"),
                "phone": user_data.get("phone"),
                "specialty": user_data.get("specialty"),
                "bio": user_data.get("bio"),
                "role": user_data.get("role"),
                "address": user_data.get("address"),
                "public_key": user_data.get("public_key")
            })
        else:
            print(f"[DEBUG] 用户 {current_username} 不存在")
            return JSONResponse(status_code=404, content={"error": "用户不存在"})
    except Exception as e:
        print(f"[DEBUG] 获取用户信息失败: {e}")
        return JSONResponse(status_code=500, content={"error": "获取用户信息失败: " + str(e)})


@router.get("/api/user/keys/{username}")
async def get_user_keys(username: str):
    """获取用户的公私钥"""
    try:
        if username not in app_state.users:
            return JSONResponse(status_code=404, content={"error": "用户不存在"})

        user_data = app_state.users[username]
        return JSONResponse(status_code=200, content={
            "username": username,
            "public_key": user_data.get("public_key", "未设置"),
            "private_key": user_data.get("private_key", "未设置")
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取用户密钥失败: " + str(e)})
