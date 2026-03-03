#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于Python的民航飞机检修记录存证系统
使用FastAPI实现的Web应用
"""

import os
import sys
import hashlib
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

# 添加后端目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.storage import StorageService
from app.services.auth import AuthService
from app.models.maintenance import MaintenanceRecord

# 配置
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 初始化服务
storage = StorageService()
auth = AuthService()

# 初始化FastAPI应用
app = FastAPI(title="民航飞机检修记录系统")

# 配置模板和静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# OAuth2密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 工具函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """验证令牌"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        address: str = payload.get("sub")
        if address is None:
            raise credentials_exception
        return address
    except JWTError:
        raise credentials_exception

async def get_current_user(request: Request):
    """获取当前用户"""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        address = verify_token(token)
        return auth.get_user_by_address(address)
    except:
        return None

# 路由
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    """首页"""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "current_user": current_user}
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    address: str = Form(...),
    password: str = Form(...)
):
    """登录处理"""
    user = auth.authenticate(address, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "用户地址或密码错误"}
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["address"]}, expires_delta=access_token_expires
    )
    
    # 设置cookie并重定向到首页
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/logout")
async def logout():
    """登出"""
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="access_token")
    return response

@app.get("/add-record", response_class=HTMLResponse)
async def add_record_page(request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    """添加记录页面"""
    if not current_user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "add_record.html", 
        {"request": request, "current_user": current_user}
    )

@app.post("/add-record")
async def add_record(
    request: Request,
    aircraft_reg_no: str = Form(...),
    aircraft_type: str = Form(...),
    aircraft_series: str = Form(...),
    aircraft_owner: str = Form(...),
    job_card_no: str = Form(...),
    task_type: str = Form(...),
    task_description: str = Form(...),
    mechanic_id: str = Form(...),
    mechanic_name: str = Form(...),
    work_end_time: str = Form(...),
    hours_accumulated: float = Form(...),
    manpower_required: int = Form(...),
    fault_description: str = Form(...),
    fault_location: str = Form(...),
    fault_cause: str = Form(...),
    fault_handling_method: str = Form(...),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """添加记录处理"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    # 创建记录
    record = MaintenanceRecord()
    record.aircraft_reg_no = aircraft_reg_no
    record.aircraft_type = aircraft_type
    record.aircraft_series = aircraft_series
    record.aircraft_owner = aircraft_owner
    record.job_card_no = job_card_no
    record.task_type = task_type
    record.task_description = task_description
    record.mechanic_id = mechanic_id
    record.mechanic_name = mechanic_name
    record.work_start_time = datetime.now().isoformat()
    record.work_end_time = work_end_time
    record.hours_accumulated = hours_accumulated
    record.manpower_required = manpower_required
    record.status = "COMPLETED"
    
    # 故障信息
    record.fault_description = fault_description
    record.fault_location = fault_location
    record.fault_cause = fault_cause
    record.fault_handling_method = fault_handling_method
    
    # 生成记录ID
    record.generate_record_id()
    
    # 工作者签名
    record.signatures.worker_id = current_user['address']
    record.signatures.worker_name = current_user['name']
    record.signatures.worker_sign_time = datetime.now().isoformat()
    record.signatures.worker_signed = True
    
    # 保存记录
    success = storage.add_record(record)
    
    if success:
        return templates.TemplateResponse(
            "add_record.html", 
            {
                "request": request, 
                "current_user": current_user,
                "success": "记录添加成功！",
                "record_id": record.record_id
            }
        )
    else:
        return templates.TemplateResponse(
            "add_record.html", 
            {
                "request": request, 
                "current_user": current_user,
                "error": "记录添加失败！"
            }
        )

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    """查询记录页面"""
    return templates.TemplateResponse(
        "search.html", 
        {"request": request, "current_user": current_user}
    )

@app.post("/search")
async def search(
    request: Request,
    search_type: str = Form(...),
    search_value: str = Form(...),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """查询记录处理"""
    records = []
    error = None
    
    try:
        if search_type == "record_id":
            record = storage.get_record_by_id(search_value)
            if record:
                records = [record]
        elif search_type == "aircraft":
            records = storage.get_records_by_aircraft(search_value)
        elif search_type == "job_card":
            records = storage.get_records_by_job_card(search_value)
        elif search_type == "mechanic":
            records = storage.get_records_by_mechanic(search_value)
        elif search_type == "all":
            records = storage.get_all_records()
    except Exception as e:
        error = f"查询失败: {str(e)}"
    
    return templates.TemplateResponse(
        "search.html", 
        {
            "request": request, 
            "current_user": current_user,
            "records": records,
            "error": error,
            "search_type": search_type,
            "search_value": search_value
        }
    )

@app.get("/record/{record_id}", response_class=HTMLResponse)
async def record_detail(
    request: Request,
    record_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """记录详情页面"""
    record = storage.get_record_by_id(record_id)
    if not record:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request, 
                "current_user": current_user,
                "error": "记录不存在"
            }
        )
    return templates.TemplateResponse(
        "record_detail.html", 
        {
            "request": request, 
            "current_user": current_user,
            "record": record
        }
    )

@app.get("/signature/{record_id}", response_class=HTMLResponse)
async def signature_page(
    request: Request,
    record_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """签名页面"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    record = storage.get_record_by_id(record_id)
    if not record:
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request, 
                "current_user": current_user,
                "error": "记录不存在"
            }
        )
    
    return templates.TemplateResponse(
        "signature.html", 
        {
            "request": request, 
            "current_user": current_user,
            "record": record
        }
    )

@app.post("/signature/{record_id}")
async def signature(
    request: Request,
    record_id: str,
    signature_type: str = Form(...),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """签名处理"""
    if not current_user:
        return RedirectResponse(url="/login")
    
    success = False
    message = ""
    
    try:
        if signature_type == "peer_check":
            success = storage.sign_peer_check(record_id, current_user['address'], current_user['name'])
            message = "互检签名成功！" if success else "互检签名失败！"
        elif signature_type == "rii":
            success = storage.sign_rii(record_id, current_user['address'], current_user['name'])
            message = "必检签名成功！" if success else "必检签名失败！"
        elif signature_type == "release":
            success = storage.sign_release(record_id, current_user['address'], current_user['name'])
            message = "放行签名成功！" if success else "放行签名失败！"
    except Exception as e:
        message = f"签名失败: {str(e)}"
    
    record = storage.get_record_by_id(record_id)
    return templates.TemplateResponse(
        "signature.html", 
        {
            "request": request, 
            "current_user": current_user,
            "record": record,
            "message": message,
            "success": success
        }
    )

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    """用户管理页面"""
    if not current_user or not current_user.get('is_admin'):
        return templates.TemplateResponse(
            "error.html", 
            {
                "request": request, 
                "current_user": current_user,
                "error": "只有管理员才能访问此页面"
            }
        )
    
    users = auth.get_authorized_users()
    return templates.TemplateResponse(
        "users.html", 
        {
            "request": request, 
            "current_user": current_user,
            "users": users
        }
    )

@app.get("/blockchain", response_class=HTMLResponse)
async def blockchain_page(request: Request, current_user: Optional[dict] = Depends(get_current_user)):
    """区块链可视化页面"""
    records = storage.get_all_records()
    
    # 按时间戳排序，模拟区块链
    records.sort(key=lambda x: x.get('timestamp', 0))
    
    # 为每个记录生成前一个区块的哈希（基于时间戳）
    blockchain = []
    prev_hash = "0" * 64  # 创世区块的前哈希
    
    for record in records:
        # 生成区块哈希
        block_data = f"{prev_hash}-{record.get('timestamp', 0)}-{record.get('recordId', '')}"
        block_hash = hashlib.sha256(block_data.encode()).hexdigest()
        
        # 构建区块数据
        block = {
            "index": len(blockchain),
            "hash": block_hash,
            "previous_hash": prev_hash,
            "timestamp": record.get('timestamp', 0),
            "record": record
        }
        
        blockchain.append(block)
        prev_hash = block_hash
    
    return templates.TemplateResponse(
        "blockchain.html", 
        {
            "request": request, 
            "current_user": current_user,
            "blockchain": blockchain
        }
    )

@app.post("/users/authorize")
async def authorize_user(
    request: Request,
    address: str = Form(...),
    name: str = Form(...),
    employee_id: str = Form(...),
    password: str = Form(...),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """授权用户"""
    if not current_user or not current_user.get('is_admin'):
        return RedirectResponse(url="/")
    
    success = auth.authorize_user(address, name, employee_id, password)
    message = "用户授权成功！" if success else "用户授权失败！"
    
    users = auth.get_authorized_users()
    return templates.TemplateResponse(
        "users.html", 
        {
            "request": request, 
            "current_user": current_user,
            "users": users,
            "message": message,
            "success": success
        }
    )

@app.post("/users/revoke")
async def revoke_user(
    request: Request,
    address: str = Form(...),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """取消用户授权"""
    if not current_user or not current_user.get('is_admin'):
        return RedirectResponse(url="/")
    
    success = auth.revoke_user(address)
    message = "用户授权取消成功！" if success else "用户授权取消失败！"
    
    users = auth.get_authorized_users()
    return templates.TemplateResponse(
        "users.html", 
        {
            "request": request, 
            "current_user": current_user,
            "users": users,
            "message": message,
            "success": success
        }
    )

# 错误页面
@app.get("/error", response_class=HTMLResponse)
async def error_page(
    request: Request,
    error: str = "未知错误",
    current_user: Optional[dict] = Depends(get_current_user)
):
    """错误页面"""
    return templates.TemplateResponse(
        "error.html", 
        {
            "request": request, 
            "current_user": current_user,
            "error": error
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)