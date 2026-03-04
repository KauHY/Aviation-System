from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import app_state
from services.auth_workflow import AuthWorkflow

router = APIRouter()
auth_workflow = AuthWorkflow()

@router.post("/api/auth/register")
async def register_user(request: Request):
    """用户注册"""
    try:
        data = await request.json()
        result, error_code, error_detail = auth_workflow.register_user(
            data=data,
            users=app_state.users,
            user_roles=app_state.user_roles,
            auth=app_state.auth,
            save_user_data=app_state.save_user_data
        )

        if error_code == "missing_fields":
            return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})
        if error_code == "weak_password":
            return JSONResponse(status_code=400, content={"error": "密码长度至少6位"})
        if error_code == "username_exists":
            return JSONResponse(status_code=400, content={"error": "用户名已存在"})
        if error_code:
            return JSONResponse(status_code=500, content={"error": "注册失败: " + str(error_detail or "unknown")})

        return JSONResponse(status_code=200, content={
            "message": "注册成功",
            "username": result["username"],
            "role": result["role"],
            "address": result["address"],
            "employee_id": result["employee_id"],
            "public_key": result["public_key"],
            "private_key": result["private_key"],
            "info": "您的私钥已存储在服务器，系统将自动使用私钥进行签名操作。"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "注册失败: " + str(e)})

@router.post("/api/auth/login")
async def login_user(request: Request):
    """用户登录"""
    try:
        data = await request.json()
        result, error_code, error_detail = auth_workflow.login_user(
            data=data,
            users=app_state.users,
            user_roles=app_state.user_roles,
            auth=app_state.auth,
            create_access_token=app_state.create_access_token,
            access_token_minutes=app_state.ACCESS_TOKEN_EXPIRE_MINUTES,
            save_user_data=app_state.save_user_data
        )

        if error_code == "missing_fields":
            return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})
        if error_code == "invalid_credentials":
            return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        if error_code:
            return JSONResponse(status_code=500, content={"error": "登录失败: " + str(error_detail or "unknown")})

        return JSONResponse(status_code=200, content={
            "message": "登录成功",
            "username": result["username"],
            "role": result["role"],
            "address": result["address"],
            "public_key": result["public_key"],
            "private_key": result["private_key"],
            "employee_id": result["employee_id"],
            "access_token": result["access_token"]
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
        payload, error_code = auth_workflow.get_payload_from_request(
            request,
            app_state.SECRET_KEY,
            app_state.ALGORITHM
        )
        if error_code:
            return JSONResponse(status_code=401, content={"error": "未授权"})

        current_username = payload.get("username") if payload else None
        if not current_username:
            return JSONResponse(status_code=401, content={"error": "未授权"})

        success, error_code, error_detail = auth_workflow.update_profile(
            current_username=current_username,
            data=data,
            users=app_state.users,
            save_user_data=app_state.save_user_data
        )

        if error_code == "missing_current_password":
            return JSONResponse(status_code=400, content={"error": "请输入当前密码"})
        if error_code == "invalid_password":
            return JSONResponse(status_code=400, content={"error": "当前密码错误"})
        if error_code == "user_not_found":
            return JSONResponse(status_code=404, content={"error": "用户不存在"})
        if error_code:
            return JSONResponse(status_code=500, content={"error": "更新个人信息失败: " + str(error_detail or "unknown")})

        if success:
            return JSONResponse(status_code=200, content={"message": "个人信息更新成功"})
    except Exception as e:
        print(f"[DEBUG] 更新个人信息失败: {e}")
        return JSONResponse(status_code=500, content={"error": "更新个人信息失败: " + str(e)})

@router.get("/api/user/current")
async def get_current_user(request: Request):
    """获取当前用户信息"""
    try:
        payload, error_code = auth_workflow.get_payload_from_request(
            request,
            app_state.SECRET_KEY,
            app_state.ALGORITHM
        )
        if error_code:
            return JSONResponse(status_code=401, content={"error": "未授权"})

        current_username = payload.get("username") if payload else None
        if not current_username:
            return JSONResponse(status_code=401, content={"error": "未授权"})

        user_data = auth_workflow.get_current_user_data(current_username, app_state.users)
        if not user_data:
            return JSONResponse(status_code=404, content={"error": "用户不存在"})

        return JSONResponse(status_code=200, content=user_data)
    except Exception as e:
        print(f"[DEBUG] 获取用户信息失败: {e}")
        return JSONResponse(status_code=500, content={"error": "获取用户信息失败: " + str(e)})


@router.get("/api/user/keys/{username}")
async def get_user_keys(username: str):
    """获取用户的公私钥"""
    try:
        result = auth_workflow.get_user_keys(username, app_state.users)
        if not result:
            return JSONResponse(status_code=404, content={"error": "用户不存在"})

        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取用户密钥失败: " + str(e)})
