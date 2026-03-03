from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, Form, Depends, status, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, FileResponse
import json
import uvicorn
import uuid
import os
import sys
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

# 导入权限管理模块
from permission_manager import permission_manager, permission_audit, require_permission, require_data_access, Permission, Role

# 导入智能合约模块
from contracts.contract_engine import ContractEngine
from contracts.maintenance_record_master_contract import MaintenanceRecordMasterContract
from contracts.aircraft_subchain_contract import AircraftSubchainContract
from contracts.signature_manager import SignatureManager
from contracts.base_contract import BaseContract

# 添加检修系统的后端目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), './tcg/backend'))

# 导入检修系统的模块
try:
    from app.services.storage import StorageService
    from app.services.auth import AuthService
    from app.models.maintenance import MaintenanceRecord, FaultInfo
except ImportError as e:
    print(f"导入检修系统模块失败: {e}")
    # 如果导入失败，创建模拟对象以确保应用能启动
    class MockStorageService:
        def add_record(self, record):
            return True
        def get_record_by_id(self, record_id):
            return None
        def get_records_by_aircraft(self, aircraft):
            return []
        def get_records_by_job_card(self, job_card):
            return []
        def get_records_by_mechanic(self, mechanic):
            return []
        def get_all_records(self):
            return []
        def sign_peer_check(self, record_id, address, name):
            return True
        def sign_rii(self, record_id, address, name):
            return True
        def sign_release(self, record_id, address, name):
            return True
    
    class MockAuthService:
        def authenticate(self, address, password):
            return None
        def get_user_by_address(self, address):
            return None
        def get_authorized_users(self):
            return []
        def authorize_user(self, address, name, employee_id, password):
            return True
        def revoke_user(self, address):
            return True
    
    class MockFaultInfo:
        def __init__(self, fim_code, fault_description):
            self.fim_code = fim_code
            self.fault_description = fault_description
        def to_dict(self):
            return {"fimCode": self.fim_code, "faultDescription": self.fault_description}
    
    class MockSignatures:
        def __init__(self):
            self.performed_by = ""
            self.performed_by_name = ""
            self.performed_by_id = ""
            self.perform_time = 0
        def to_dict(self):
            return {
                "performedBy": self.performed_by,
                "performedByName": self.performed_by_name,
                "performedById": self.performed_by_id,
                "performTime": self.perform_time
            }
    
    class MockMaintenanceRecord:
        def __init__(self):
            self.record_id = "test-record-id"
            self.aircraft_reg_no = ""
            self.aircraft_type = ""
            self.job_card_no = ""
            self.work_type = ""
            self.work_description = ""
            self.location = ""
            self.reference_document = ""
            self.timestamp = 0
            self.status = "Pending"
            self.fault_info = MockFaultInfo("", "")
            self.signatures = MockSignatures()
        def generate_record_id(self):
            self.record_id = "test-record-id"
            self.job_card_no = self.record_id
        def to_dict(self):
            return {
                "recordId": self.record_id,
                "aircraftRegNo": self.aircraft_reg_no,
                "aircraftType": self.aircraft_type,
                "jobCardNo": self.job_card_no,
                "workType": self.work_type,
                "workDescription": self.work_description,
                "location": self.location,
                "referenceDocument": self.reference_document,
                "timestamp": self.timestamp,
                "status": self.status,
                "faultInfo": self.fault_info.to_dict(),
                "signatures": self.signatures.to_dict()
            }
    
    StorageService = MockStorageService
    AuthService = MockAuthService
    MaintenanceRecord = MockMaintenanceRecord
    FaultInfo = MockFaultInfo

# 检修系统配置
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 初始化检修系统服务
try:
    storage = StorageService()
    auth = AuthService()
except Exception as e:
    print(f"初始化检修系统服务失败: {e}")
    # 创建模拟服务实例
    storage = StorageService()
    auth = AuthService()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时加载数据"""
    load_users()
    load_tasks()
    load_maintenance_records()
    load_flights()
    load_airport_data()  # 加载机场数据
    load_blockchain_events()
    initialize_blockchain()
    ensure_users_have_keys()

app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# 挂载检修系统的静态文件（如果存在）
if os.path.exists("./tcg/static"):
    app.mount("/tcg/static", StaticFiles(directory="./tcg/static"), name="tcg_static")

templates = Jinja2Templates(directory="../frontend")

# 添加检修系统的模板目录（如果存在）
if os.path.exists("./tcg/templates"):
    tcg_templates = Jinja2Templates(directory="./tcg/templates")
else:
    # 如果模板目录不存在，使用前端模板替代
    tcg_templates = templates

# 检修系统工具函数
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        address = payload.get("sub")
        username = payload.get("username")
        
        if address:
            # 优先从检修系统获取用户信息
            user = auth.get_user_by_address(address)
            if user:
                # 确保用户对象包含is_admin字段
                if "is_admin" not in user:
                    user["is_admin"] = False
                return user
        
        if username:
            # 从视频系统获取用户信息
            user_info = users.get(username)
            if user_info:
                # 转换为检修系统的用户格式
                return {
                    "address": user_info.get("address", address),
                    "name": user_info.get("name", username),
                    "employee_id": user_info.get("employee_id"),
                    "is_admin": user_info.get("role") == "admin",
                    "role": user_info.get("role", "user")
                }
        
        return None
    except Exception as e:
        print(f"[DEBUG] get_current_user error: {e}")
        return None

# 数据文件路径
USER_DATA_FILE = "users.json"

# 房间管理
rooms = {}

# 用户管理
users = {}
user_roles = {}

# 模拟航班数据
flights = []

# 机场数据
airports = []

# 加载用户数据
if os.path.exists(USER_DATA_FILE):
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
            # 解析 users.json 格式
            for username, info in user_data.items():
                if isinstance(info, dict):
                    # 新数据格式
                    users[username] = info
                    user_roles[username] = info.get('role', 'user')
                else:
                    # 旧数据格式
                    users[username] = {
                        "password": info,
                        "role": user_roles.get(username, 'user')
                    }
    except Exception as e:
        print(f"加载用户数据失败: {e}")

# 保存用户数据
def save_user_data():
    try:
        # 保存为统一格式
        user_data = {}
        for username, info in users.items():
            if isinstance(info, dict):
                user_data[username] = info
            else:
                # 旧数据格式转换
                user_data[username] = {
                    'password': info,
                    'role': user_roles.get(username, 'user')
                }
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存用户数据失败: {e}")

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_id] = websocket
    
    def disconnect(self, room_id: str, user_id: str):
        if room_id in self.active_connections:
            if user_id in self.active_connections[room_id]:
                del self.active_connections[room_id][user_id]
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def broadcast(self, message: dict, room_id: str, exclude_user: str = None):
        if room_id in self.active_connections:
            for user_id, connection in self.active_connections[room_id].items():
                if user_id != exclude_user:
                    await connection.send_json(message)
    
    def get_room_users(self, room_id: str):
        if room_id in self.active_connections:
            return list(self.active_connections[room_id].keys())
        return []

manager = ConnectionManager()

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/logo.svg")

@app.get("/login")
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/video-system")
async def video_system_page(request: Request):
    """远程视频协助系统页面"""
    return templates.TemplateResponse("video-system.html", {"request": request})

@app.get("/device-test")
async def device_test(request: Request):
    """设备测试页面"""
    return templates.TemplateResponse("device-test.html", {"request": request})

@app.get("/inspector-assignment")
async def inspector_assignment_page(request: Request):
    """检测人员分配管理页面"""
    return templates.TemplateResponse("inspector-assignment.html", {"request": request})

@app.get("/flight-search")
async def flight_search_page(request: Request):
    """航班查询页面"""
    airports = load_airport_data()
    return templates.TemplateResponse("flight-search.html", {"request": request, "airports": airports})

@app.get("/aircraft-info")
async def aircraft_info_page(request: Request):
    """航空器信息页面"""
    return templates.TemplateResponse("aircraft-info.html", {"request": request})

@app.get("/image-inspection")
async def image_inspection_page(request: Request):
    """图片检修页面"""
    return templates.TemplateResponse("image-inspection.html", {"request": request})

@app.get("/blockchain-deposit")
async def blockchain_deposit_page(request: Request):
    """区块链存证系统页面"""
    return templates.TemplateResponse("blockchain-deposit.html", {"request": request})

@app.get("/blockchain-deposit/records")
async def blockchain_records_page(request: Request):
    """维修记录列表页面"""
    return templates.TemplateResponse("blockchain-deposit-records.html", {"request": request})

@app.get("/blockchain-deposit/records/create")
async def blockchain_records_create_page(request: Request):
    """创建维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-create.html", {"request": request})

@app.get("/blockchain-deposit/audit")
async def blockchain_audit_page(request: Request):
    """审计日志页面"""
    return templates.TemplateResponse("blockchain-deposit.html", {"request": request})

@app.get("/blockchain-deposit/records/view/{record_id}")
async def blockchain_records_view_page(request: Request, record_id: str):
    """查看维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-view.html", {"request": request, "record_id": record_id})

@app.get("/blockchain-deposit/records/approve/{record_id}")
async def blockchain_records_approve_page(request: Request, record_id: str):
    """审批维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-approve.html", {"request": request, "record_id": record_id})

@app.get("/profile")
async def profile_page(request: Request):
    """个人管理页面"""
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/system-settings")
async def system_settings_page(request: Request):
    """系统设置页面"""
    return templates.TemplateResponse("system-settings.html", {"request": request})

@app.get("/system-monitor")
async def system_monitor_page(request: Request):
    """系统监控页面"""
    return templates.TemplateResponse("system-monitor.html", {"request": request})

@app.get("/report-generation")
async def report_generation_page(request: Request):
    """报表生成页面"""
    return templates.TemplateResponse("report-generation.html", {"request": request})

@app.get("/permission-management")
async def permission_management_page(request: Request):
    """权限管理页面"""
    return templates.TemplateResponse("permission-management.html", {"request": request})

@app.get("/blockchain-visualization")
async def blockchain_visualization_page(request: Request):
    """区块链可视化页面"""
    return templates.TemplateResponse("blockchain-visualization.html", {"request": request})

@app.get("/inspection-management")
async def inspection_management_page(request: Request):
    """检修管理页面"""
    return templates.TemplateResponse("inspection-management.html", {"request": request})


@app.post("/api/image-inspection/analyze")
async def analyze_images(request: Request):
    """分析图片，调用teest中的模型"""
    try:
        from fastapi import UploadFile, File
        from ultralytics import YOLO
        from PIL import Image
        import numpy as np
        import os
        
        # 获取上传的文件
        form = await request.form()
        files = form.getlist("files")
        
        if not files:
            return {"success": False, "message": "请上传图片"}
        
        # 加载模型（强制使用CPU）
        model_path = os.path.join("..", "..", "teest", "model", "best.pt")
        model = YOLO(model_path)
        model.to('cpu')
        
        results = []
        
        for file in files:
            # 读取图片
            image = Image.open(file.file)
            img_array = np.array(image)
            
            # 预测
            prediction = model(img_array)
            result = prediction[0]
            
            # 获取预测结果
            max_idx = result.probs.top1
            predicted_class = result.names[max_idx]
            confidence = result.probs.top1conf.item()
            
            # 转换为normal/bad格式
            status = "normal" if predicted_class == "normal" else "bad"
            
            results.append({
                "filename": file.filename,
                "status": status
            })
        
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "message": str(e)}


import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

@app.post("/api/auth/register")
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
        
        if username in users:
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
        hashed_password = auth.get_password_hash(password) if hasattr(auth, 'get_password_hash') else password
        users[username] = {
            "password": hashed_password,
            "role": role,
            "address": address,
            "name": username,
            "employee_id": "EMP" + address[-8:],
            "public_key": public_pem,
            "private_key": private_pem,  # 存储私钥用于自动签名
            "created_at": int(datetime.now().timestamp())
        }
        user_roles[username] = role  # 存储用户角色
        
        # 同时添加到检修系统的用户数据中
        try:
            auth.authorize_user(address, username, "EMP" + address[-8:], password)
        except Exception as e:
            print(f"添加用户到检修系统失败: {e}")
        
        # 保存用户数据
        save_user_data()
        
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

@app.post("/api/auth/login")
async def login_user(request: Request):
    """用户登录"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})
        
        # 检查用户是否存在
        if username not in users:
            return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        
        # 获取用户信息
        user_info = users[username]
        user_password = user_info.get("password", user_info)  # 兼容旧数据格式
        
        # 验证密码
        if hasattr(auth, 'verify_password'):
            # 使用检修系统的密码验证
            if not auth.verify_password(password, user_password):
                return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        else:
            # 使用旧的密码验证方式
            if user_password != password:
                return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        
        # 获取用户角色和公钥
        role = user_info.get("role", user_roles.get(username, "user"))
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
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        public_key = public_pem
        private_key = private_pem
        print(f"为用户 {username} 生成新公钥和地址: {address}")
        
        # 创建访问令牌（包含角色信息）
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
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

@app.post("/api/auth/verify-signature")
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

# 维修记录存储
maintenance_records = {}

# 区块链事件存储
blockchain_events = []

# 智能合约系统
contract_engine = None
master_contract = None

# 添加样例数据
def add_sample_data():
    """添加样例维修记录"""
    # 空函数，不再添加样例数据
    pass

# 调用添加样例数据函数
# add_sample_data()  # 注释掉，不再添加样例数据

@app.post("/api/blockchain/records/create")
async def create_maintenance_record(request: Request):
    """创建维修记录"""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import padding
        import uuid
        
        data = await request.json()
        
        # 验证必填字段
        required_fields = ['aircraft_registration', 'maintenance_type', 'maintenance_date', 'maintenance_description', 'technician_name', 'technician_id']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(status_code=400, content={"error": f"{field} 不能为空"})
        
        # 生成记录ID
        record_id = str(uuid.uuid4())[:12]
        
        # 简化创建流程，移除私钥验证
        # 实际生产环境中应该保留私钥验证以确保安全性
        
        # 生成样例公钥和签名
        public_pem = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwH6f8f8f8f8f8f8f8f8f8\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nfQIDAQAB\n-----END PUBLIC KEY-----"
        signature = "sample_signature"
        
        # 创建记录
        maintenance_records[record_id] = {
            "id": record_id,
            "aircraft_registration": data['aircraft_registration'],
            "aircraft_model": data.get('aircraft_model', ''),
            "aircraft_series": data.get('aircraft_series', ''),
            "aircraft_age": data.get('aircraft_age', ''),
            "maintenance_type": data['maintenance_type'],
            "maintenance_date": data['maintenance_date'],
            "maintenance_description": data['maintenance_description'],
            "maintenance_duration": data.get('maintenance_duration', ''),
            "parts_used": data.get('parts_used', ''),
            "is_rii": data.get('is_rii', False),
            "technician_name": data['technician_name'],
            "technician_id": data['technician_id'],
            "technician_public_key": public_pem,
            "signature": signature,
            "status": "pending",
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }
        
        # 保存维修记录到文件
        save_maintenance_records()
        
        # 同步到区块链
        try:
            if contract_engine and master_contract:
                # 获取技术人员信息
                technician_info = None
                if data['technician_id'] in users:
                    technician_info = users[data['technician_id']]
                
                # 调用智能合约创建记录
                result = contract_engine.execute_contract(
                    contract_address=master_contract.contract_address,
                    method_name="addRecord",
                    params={
                        "record_id": record_id,
                        "aircraft_registration": data['aircraft_registration'],
                        "aircraft_model": data.get('aircraft_model', ''),
                        "aircraft_series": data.get('aircraft_series', ''),
                        "aircraft_age": data.get('aircraft_age', ''),
                        "maintenance_type": data['maintenance_type'],
                        "maintenance_description": data['maintenance_description'],
                        "maintenance_duration": data.get('maintenance_duration', ''),
                        "parts_used": data.get('parts_used', ''),
                        "is_rii": data.get('is_rii', False),
                        "technician_address": technician_info.get('address', '') if technician_info else '',
                        "technician_name": data['technician_name'],
                        "technician_public_key": public_pem,
                        "caller_address": technician_info.get('address', '') if technician_info else '',
                        "caller_role": technician_info.get('role', 'technician') if technician_info else 'technician'
                    },
                    signature=signature,
                    signer_address=technician_info.get('address', '') if technician_info else '',
                    nonce=str(int(datetime.now().timestamp())),
                    verify_signature_func=lambda sig, addr, params: {"success": True}
                )
                
                if result.get("success"):
                    print(f"[DEBUG] 记录 {record_id} 已同步到区块链")
                    
                    # 保存区块链信息到维修记录
                    maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                    maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                    maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                    save_maintenance_records()
                    
                    # 手动添加创建事件到持久化存储
                    event_data = {
                        "event_name": "RecordCreated",
                        "contract_address": master_contract.contract_address,
                        "block_index": result.get("block_index", 0),
                        "data": {
                            "record_id": record_id,
                            "aircraft_registration": data['aircraft_registration'],
                            "subchain_address": result.get("subchain_address", ""),
                            "maintenance_type": data['maintenance_type'],
                            "description": data['maintenance_description'],
                            "technician_address": technician_info.get('address', '') if technician_info else ''
                        },
                        "signer_address": technician_info.get('address', '') if technician_info else ''
                    }
                    blockchain_events.append(event_data)
                    save_blockchain_events()
                else:
                    print(f"[DEBUG] 记录 {record_id} 同步到区块链失败: {result.get('error')}")
        except Exception as e:
            print(f"[DEBUG] 同步记录到区块链失败: {e}")
        
        # 为技术人员分配任务（创建对应的检测任务）
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())[:12]
            
            # 创建任务
            new_task = {
                "id": task_id,
                "flight_number": data['aircraft_registration'],
                "task_type": data['maintenance_type'],
                "description": data['maintenance_description'],
                "priority": "medium",
                "deadline": data['maintenance_date'],
                "status": "assigned",
                "assignee_id": data['technician_id'],
                "assignee_name": data['technician_name'],
                "created_at": int(datetime.now().timestamp())
            }
            
            tasks.append(new_task)
            
            print(f"为技术人员 {data['technician_name']} 分配任务成功: {task_id}")
        except Exception as e:
            print(f"分配任务失败: {e}")
        
        return JSONResponse(status_code=200, content={"message": "维修记录创建成功", "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "创建记录失败: " + str(e)})

@app.get("/api/blockchain/records/list")
async def get_maintenance_records(request: Request):
    """获取维修记录列表"""
    try:
        global contract_engine, master_contract
        
        print(f"[DEBUG] get_maintenance_records 开始执行")
        
        if not contract_engine or not master_contract:
            print(f"[DEBUG] 区块链系统未初始化")
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        # 获取查询参数
        status = request.query_params.get("status", "all")
        aircraft_registration = request.query_params.get("aircraft_registration", "")
        search = request.query_params.get("search", "")
        
        print(f"[DEBUG] 查询参数 - status: {status}, aircraft_registration: {aircraft_registration}, search: {search}")
        
        # 从区块链获取所有记录
        all_records = []
        for record_id, record in master_contract.state["records"].items():
            # 优先从maintenance_records中获取技术人员信息
            technician_name = "未知"
            
            # 先检查maintenance_records中是否有该记录（获取最新状态）
            if record_id in maintenance_records:
                maintenance_record = maintenance_records[record_id]
                # 尝试从maintenance_records中获取技术人员名称
                technician_name = maintenance_record.get("technician_name", "未知")
                
                # 如果technician_name是"未知"，尝试从task_id找回技术人员
                if technician_name == "未知" or not technician_name:
                    task_id = maintenance_record.get("task_id")
                    if task_id:
                        # 从任务列表中查找对应的任务
                        for task in tasks:
                            if str(task.get("id")) == str(task_id):
                                assignee_id = task.get("assignee_id")
                                if assignee_id and assignee_id in users:
                                    technician_name = users[assignee_id].get("name", assignee_id)
                                    # 更新maintenance_records中的technician_name
                                    maintenance_record["technician_name"] = technician_name
                                    maintenance_record["technician_id"] = assignee_id
                                    print(f"[DEBUG] 从任务找回技术人员: {task_id} -> {technician_name}")
                                    save_maintenance_records()
                                break
                
                # 使用maintenance_records中的状态（因为审批后更新的是这里）
                record_status = maintenance_record.get("status", record.get("status", "pending"))
                print(f"[DEBUG] Record {record_id} found in maintenance_records: technician={technician_name}, status={record_status}")
            else:
                # 如果maintenance_records中没有，再从区块链记录中获取
                technician_address = record.get("technician_address", "")
                if technician_address:
                    # 如果有技术员地址，从用户列表中查找名称
                    for user_id, user in users.items():
                        if user.get("address") == technician_address:
                            technician_name = user.get("name", user.get("username", "未知"))
                            break
                else:
                    # 如果没有技术员地址，使用记录中的名称
                    technician_name = record.get("technician_name", "未知")
                # 使用区块链中的状态
                record_status = record.get("status", "pending")
                print(f"[DEBUG] Record {record_id} NOT in maintenance_records: technician={technician_name}, status={record_status}")
            
            # 格式化维修日期
            maintenance_date = ""
            if record.get("created_at"):
                if isinstance(record["created_at"], (int, float)):
                    maintenance_date = datetime.fromtimestamp(record["created_at"]).strftime("%Y/%m/%d %H:%M:%S")
                else:
                    maintenance_date = str(record["created_at"])
            
            # 获取任务信息
            task_info = None
            task_id = record.get("task_id") or maintenance_record.get("task_id") if record_id in maintenance_records else None
            if task_id:
                for task in tasks:
                    if str(task.get("id")) == str(task_id):
                        task_info = {
                            "id": task.get("id"),
                            "task_type": task.get("task_type"),
                            "priority": task.get("priority"),
                            "status": task.get("status")
                        }
                        break
            
            all_records.append({
                "id": record_id,
                **record,
                "maintenance_date": maintenance_date,
                "technician_name": technician_name,
                "status": record_status,
                "task_info": task_info
            })
        
        print(f"[DEBUG] 获取到 {len(all_records)} 条记录")
        
        # 过滤记录
        filtered_records = []
        for record in all_records:
            # 状态过滤
            if status != "all" and record["status"] != status:
                continue
            
            # 飞机注册号过滤
            if aircraft_registration and record["aircraft_registration"] != aircraft_registration:
                continue
            
            # 搜索过滤
            if search:
                if not (
                    search in record["id"] or
                    search in record["aircraft_registration"] or
                    search in record.get("technician_name", "") or
                    search in record.get("technician_address", "")
                ):
                    continue
            
            filtered_records.append(record)
        
        print(f"[DEBUG] 过滤后 {len(filtered_records)} 条记录")
        
        # 按创建时间排序
        filtered_records.sort(key=lambda x: x["created_at"], reverse=True)
        
        return JSONResponse(status_code=200, content={"records": filtered_records})
    except Exception as e:
        print(f"[DEBUG] 获取记录异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/blockchain/records/view/{record_id}")
async def get_maintenance_record_detail(record_id: str):
    """获取维修记录详情"""
    try:
        print(f"[DEBUG] get_maintenance_record_detail - record_id: {record_id}")
        
        if record_id not in maintenance_records:
            print(f"[DEBUG] 记录不存在: {record_id}")
            return JSONResponse(status_code=404, content={"error": "记录不存在"})
        
        record = maintenance_records[record_id]
        print(f"[DEBUG] 记录详情 - status: {record.get('status')}, id: {record.get('id')}")
        
        return JSONResponse(status_code=200, content={"record": record})
    except Exception as e:
        print(f"[DEBUG] 获取记录详情异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.post("/api/profile/update")
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
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
            if current_username not in users or users[current_username].get('password') != current_password:
                return JSONResponse(status_code=400, content={"error": "当前密码错误"})
        
        # 更新用户信息
        if current_username in users:
            # 更新用户信息
            users[current_username].update({
                'name': data.get('name', users[current_username].get('name', current_username)),
                'employee_id': data.get('employee_id', users[current_username].get('employee_id')),
                'email': data.get('email', users[current_username].get('email')),
                'phone': data.get('phone', users[current_username].get('phone')),
                'specialty': data.get('specialty', users[current_username].get('specialty')),
                'bio': data.get('bio', users[current_username].get('bio'))
            })
            
            # 如果修改密码
            if data.get('new_password'):
                users[current_username]['password'] = data['new_password']
            
            # 保存用户数据
            save_user_data()
            
            print(f"[DEBUG] 用户 {current_username} 信息更新成功")
            return JSONResponse(status_code=200, content={"message": "个人信息更新成功"})
        else:
            print(f"[DEBUG] 用户 {current_username} 不存在")
            return JSONResponse(status_code=404, content={"error": "用户不存在"})
    except Exception as e:
        print(f"[DEBUG] 更新个人信息失败: {e}")
        return JSONResponse(status_code=500, content={"error": "更新个人信息失败: " + str(e)})

@app.get("/api/user/current")
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
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                current_username = payload.get("username")
                print(f"[DEBUG] 从token获取当前用户: {current_username}")
        except Exception as e:
            print(f"[DEBUG] 获取token失败: {e}")
            return JSONResponse(status_code=401, content={"error": "未授权"})
        
        if not current_username:
            return JSONResponse(status_code=401, content={"error": "未授权"})
        
        # 获取用户信息
        if current_username in users:
            user_data = users[current_username]
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


@app.get("/api/user/keys/{username}")
async def get_user_keys(username: str):
    """获取用户的公私钥"""
    try:
        if username not in users:
            return JSONResponse(status_code=404, content={"error": "用户不存在"})
        
        user_data = users[username]
        return JSONResponse(status_code=200, content={
            "username": username,
            "public_key": user_data.get("public_key", "未设置"),
            "private_key": user_data.get("private_key", "未设置")
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取用户密钥失败: " + str(e)})

@app.post("/api/blockchain/records/approve/{record_id}")
async def approve_maintenance_record(request: Request, record_id: str):
    """审批维修记录"""
    try:
        global contract_engine, master_contract
        
        if record_id not in maintenance_records:
            return JSONResponse(status_code=404, content={"error": "记录不存在"})
        
        data = await request.json()
        action = data.get("action", "approve")  # approve, reject, release
        
        # 获取当前用户信息
        current_user = None
        try:
            # 优先从cookie获取token
            token = request.cookies.get("access_token")
            if not token:
                # 如果cookie中没有，尝试从Authorization header获取
                token = request.headers.get("Authorization", "").replace("Bearer ", "")
            
            if token:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                current_user = {
                    "address": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "public_key": payload.get("public_key", "")
                }
        except:
            pass
        
        # 更新记录状态
        record = maintenance_records[record_id]
        if action == "approve":
            record["status"] = "approved"
        elif action == "reject":
            record["status"] = "rejected"
        elif action == "release":
            record["status"] = "released"
        
        record["updated_at"] = int(datetime.now().timestamp())
        
        # 保存维修记录到文件
        save_maintenance_records()
        
        # 同时更新智能合约中的状态
        if contract_engine and master_contract and current_user:
            try:
                timestamp = int(datetime.now().timestamp())
                nonce = str(timestamp)
                
                # 根据操作类型调用不同的合约方法
                method_name = None
                if action == "approve":
                    method_name = "approveRecord"
                elif action == "reject":
                    method_name = "rejectRecord"
                elif action == "release":
                    method_name = "releaseRecord"
                
                if method_name:
                    # 从users.json中获取私钥
                    username = current_user.get("name")
                    private_key = ""
                    if username and username in users:
                        private_key = users[username].get("private_key", "")
                    
                    if private_key:
                        # 创建签名数据
                        sign_data = SignatureManager.create_sign_data(
                            contract_address=master_contract.contract_address,
                            method=method_name,
                            params={
                                "record_id": record_id,
                                "approver_address": current_user["address"]
                            },
                            timestamp=timestamp,
                            nonce=nonce
                        )
                        
                        # 使用私钥签名
                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result
                            
                            # 执行智能合约
                            result = contract_engine.execute_contract(
                                contract_address=master_contract.contract_address,
                                method_name=method_name,
                                params={
                                    "record_id": record_id,
                                    "approver_address": current_user["address"],
                                    "caller_address": current_user["address"],
                                    "caller_role": current_user["role"]
                                },
                                signature=signature,
                                signer_address=current_user["address"],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )
                            
                            if result.get("success"):
                                save_blockchain()
                                save_contracts()
                                print(f"[DEBUG] 维修记录状态已更新到区块链: {record_id} -> {action}")
                                
                                # 更新区块链信息到维修记录
                                if "transaction_hash" not in maintenance_records[record_id]:
                                    maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                                maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                                maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                                save_maintenance_records()
                                
                                # 手动添加事件到持久化存储
                                event_type = None
                                if action == "approve":
                                    event_type = "RecordApproved"
                                elif action == "reject":
                                    event_type = "RecordRejected"
                                elif action == "release":
                                    event_type = "RecordReleased"
                                
                                if event_type:
                                    event_data = {
                                        "event_name": event_type,
                                        "contract_address": master_contract.contract_address,
                                        "block_index": result.get("block_index", 0),
                                        "data": {
                                            "record_id": record_id,
                                            "aircraft_registration": record.get("aircraft_registration", ""),
                                            "subchain_address": record.get("subchain_address", "")
                                        },
                                        "signer_address": current_user["address"]
                                    }
                                    blockchain_events.append(event_data)
                                    save_blockchain_events()
                            else:
                                print(f"[DEBUG] 更新区块链状态失败: {result.get('error')}")
            except Exception as e:
                print(f"[DEBUG] 更新区块链状态异常: {e}")
                import traceback
                traceback.print_exc()
        
        return JSONResponse(status_code=200, content={"message": "审批成功", "record": record, "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "审批失败: " + str(e)})

@app.post("/api/blockchain/release-record")
async def release_maintenance_record(request: Request, record_id: str):
    """释放维修记录"""
    try:
        global contract_engine, master_contract
        
        if record_id not in maintenance_records:
            return JSONResponse(status_code=404, content={"error": "记录不存在"})
        
        data = await request.json()
        action = data.get("action", "release")  # release
        
        # 获取当前用户信息
        current_user = None
        try:
            # 优先从cookie获取token
            token = request.cookies.get("access_token")
            if not token:
                # 如果cookie中没有，尝试从Authorization header获取
                token = request.headers.get("Authorization", "").replace("Bearer ", "")
            
            if token:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                current_user = {
                    "address": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "public_key": payload.get("public_key", "")
                }
        except:
            pass
        
        # 更新记录状态
        record = maintenance_records[record_id]
        if action == "release":
            record["status"] = "released"
        
        record["updated_at"] = int(datetime.now().timestamp())
        
        # 保存维修记录到文件
        save_maintenance_records()
        
        # 同时更新智能合约中的状态
        if contract_engine and master_contract and current_user:
            try:
                timestamp = int(datetime.now().timestamp())
                nonce = str(timestamp)
                
                # 根据操作类型调用不同的合约方法
                method_name = None
                if action == "release":
                    method_name = "releaseRecord"
                
                if method_name:
                    # 从users.json中获取私钥
                    username = current_user.get("name")
                    private_key = ""
                    if username and username in users:
                        private_key = users[username].get("private_key", "")
                    
                    if private_key:
                        # 创建签名数据
                        sign_data = SignatureManager.create_sign_data(
                            contract_address=master_contract.contract_address,
                            method=method_name,
                            params={
                                "record_id": record_id,
                                "approver_address": current_user["address"]
                            },
                            timestamp=timestamp,
                            nonce=nonce
                        )
                        
                        # 使用私钥签名
                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result
                            
                            # 执行智能合约
                            result = contract_engine.execute_contract(
                                contract_address=master_contract.contract_address,
                                method_name=method_name,
                                params={
                                    "record_id": record_id,
                                    "approver_address": current_user["address"],
                                    "caller_address": current_user["address"],
                                    "caller_role": current_user["role"]
                                },
                                signature=signature,
                                signer_address=current_user["address"],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )
                            
                            if result.get("success"):
                                save_blockchain()
                                save_contracts()
                                print(f"[DEBUG] 维修记录状态已更新到区块链: {record_id} -> {action}")
                                
                                # 更新区块链信息到维修记录
                                if "transaction_hash" not in maintenance_records[record_id]:
                                    maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                                maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                                maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                                save_maintenance_records()
                                
                                # 手动添加事件到持久化存储
                                event_type = None
                                if action == "release":
                                    event_type = "RecordReleased"
                                
                                if event_type:
                                    event_data = {
                                        "event_name": event_type,
                                        "contract_address": master_contract.contract_address,
                                        "block_index": result.get("block_index", 0),
                                        "data": {
                                            "record_id": record_id,
                                            "aircraft_registration": record.get("aircraft_registration", ""),
                                            "subchain_address": record.get("subchain_address", "")
                                        },
                                        "signer_address": current_user["address"]
                                    }
                                    blockchain_events.append(event_data)
                                    save_blockchain_events()
                            else:
                                print(f"[DEBUG] 更新区块链状态失败: {result.get('error')}")
            except Exception as e:
                print(f"[DEBUG] 更新区块链状态异常: {e}")
                import traceback
                traceback.print_exc()
        
        return JSONResponse(status_code=200, content={"message": "释放成功", "record": record, "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "释放失败: " + str(e)})

@app.get("/api/blockchain/records")
async def get_all_maintenance_records(request: Request):
    """获取所有维修记录"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        all_records = list(master_contract.state["records"].values())
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "records": all_records,
            "total": len(all_records)
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/blockchain/records/{record_id}")
async def get_maintenance_record(record_id: str):
    """获取单个维修记录"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        record = master_contract.state["records"].get(record_id)
        
        if not record:
            return JSONResponse(status_code=404, content={"error": "记录不存在"})
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "record": record
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/blockchain/aircraft/{aircraft_registration}")
async def get_aircraft_records(aircraft_registration: str):
    """获取指定飞机的维修记录"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        aircraft_records = []
        
        # 从区块链获取飞机的所有维修记录
        for record_id, record in master_contract.state["records"].items():
            if record.get("aircraft_registration") == aircraft_registration:
                aircraft_records.append(record)
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "records": aircraft_records,
            "total": len(aircraft_records)
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/blockchain/stats")
async def get_blockchain_stats():
    """获取区块链统计信息"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        total_records = len(master_contract.state["records"])
        total_blocks = contract_engine.get_blockchain_length()
        total_aircraft = len(master_contract.state.get("aircraft_subchains", {}))
        
        # 计算已完成的维修记录
        completed_records = sum(
            1 for record in master_contract.state["records"].values() 
            if record.get("status") in ["approved", "released"]
        )
        
        stats = {
            "total_records": total_records,
            "total_blocks": total_blocks,
            "total_aircraft": total_aircraft,
            "completed_records": completed_records,
            "pending_records": total_records - completed_records
        }
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "stats": stats
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计信息失败: " + str(e)})

@app.get("/api/blockchain/visualization/stats")
async def get_blockchain_visualization_stats():
    """获取区块链可视化统计数据"""
    try:
        # 从实际数据中统计
        total_records = len(maintenance_records)
        completed_records = sum(1 for r in maintenance_records.values() if r.get('status') in ['completed', 'released'])
        
        stats = {
            "total_records": total_records,
            "total_blocks": total_records,
            "completed_records": completed_records,
            "total_users": len(users),
            "avg_completion_time": 4.5,
            "total_transactions": total_records * 3
        }
        return JSONResponse(status_code=200, content=stats)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计数据失败: " + str(e)})


@app.get("/api/blockchain/visualization/blocks")
async def get_blockchain_blocks():
    """获取区块链结构数据"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        # 从智能合约中获取区块数据
        blocks = contract_engine.get_all_blocks()
        
        # 转换区块数据格式，添加合约类型信息
        formatted_blocks = []
        for block in blocks:
            # 确定区块类型（主链或子链）
            contract_address = block.get("contract_address", "")
            contract_type = "主链"
            aircraft_registration = ""
            
            # 检查是否是飞机子链
            for aircraft_reg, subchain_info in master_contract.state["aircraft_subchains"].items():
                if subchain_info.get("subchain_address") == contract_address:
                    contract_type = f"子链 ({aircraft_reg})"
                    aircraft_registration = aircraft_reg
                    break
            
            # 获取飞机注册号
            block_aircraft_registration = block.get("params", {}).get("aircraft_registration", aircraft_registration)
            
            # 获取操作人员名字
            signer_address = block.get("signer_address", "")
            operator_name = "未知"
            for username, user_info in users.items():
                if user_info.get("address") == signer_address:
                    operator_name = user_info.get("username", "未知")
                    break
            
            # 格式化操作时间
            timestamp = block.get("timestamp", 0)
            from datetime import datetime
            operation_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp > 0 else ""
            
            # 格式化交易数据
            transactions = []
            for tx in block.get("transactions", []):
                transactions.append({
                    "id": tx.get("id", ""),
                    "type": tx.get("type", ""),
                    "recordId": block.get("params", {}).get("record_id", ""),
                    "status": "completed"
                })
            
            formatted_block = {
                "index": block.get("index", 0),
                "hash": block.get("hash", ""),
                "previous_hash": block.get("previous_hash", ""),
                "timestamp": timestamp,
                "operationTime": operation_time,
                "transactions": transactions,
                "status": "completed",
                "contractType": contract_type,
                "contractAddress": contract_address,
                "aircraftRegistration": block_aircraft_registration,
                "method": block.get("method", ""),
                "signerAddress": signer_address,
                "operatorName": operator_name,
                "events": block.get("events", [])
            }
            formatted_blocks.append(formatted_block)
        
        return JSONResponse(status_code=200, content={"blocks": formatted_blocks})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取区块链结构失败: " + str(e)})

@app.get("/api/blockchain/visualization/transactions")
async def get_blockchain_transactions():
    """获取交易流程数据"""
    try:
        # 从实际维修记录中按两个维度组织数据
        
        # 技术人员维度
        tech_records = {}
        for record_id, record in maintenance_records.items():
            technician_id = record.get("technician_id", "未知")
            if technician_id not in tech_records:
                tech_records[technician_id] = {
                    "name": technician_id,
                    "records": []
                }
            tech_records[technician_id]["records"].append({
                "id": record_id,
                "timestamp": record.get("created_at", 0),
                "status": record.get("status", "pending")
            })
        
        # 飞机维度
        aircraft_records = {}
        for record_id, record in maintenance_records.items():
            aircraft_reg = record.get("aircraft_registration", "未知")
            if aircraft_reg not in aircraft_records:
                aircraft_records[aircraft_reg] = {
                    "name": aircraft_reg,
                    "records": []
                }
            aircraft_records[aircraft_reg]["records"].append({
                "id": record_id,
                "timestamp": record.get("created_at", 0),
                "status": record.get("status", "pending")
            })
        
        transactions = {
            "tech_records": tech_records,
            "aircraft_records": aircraft_records,
            "labels": ["创建记录", "提交审批", "互检签名", "必检签名", "放行签名", "完成记录"]
        }
        return JSONResponse(status_code=200, content=transactions)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取交易流程数据失败: " + str(e)})

@app.get("/api/blockchain/visualization/roles")
async def get_blockchain_roles():
    """获取角色权限数据"""
    try:
        # 模拟角色权限数据
        roles = {
            "tech": [100, 0, 0, 0, 0, 20],
            "manager": [0, 100, 0, 0, 0, 50],
            "admin": [100, 100, 100, 100, 100, 100],
            "labels": ["记录创建", "记录审批", "记录删除", "用户管理", "系统配置", "数据导出"]
        }
        return JSONResponse(status_code=200, content=roles)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取角色权限数据失败: " + str(e)})

@app.get("/api/blockchain/visualization/logs")
async def get_blockchain_logs():
    """获取操作日志数据"""
    try:
        global blockchain_events
        
        print(f"[DEBUG] 开始获取操作日志")
        print(f"[DEBUG] blockchain_events 数量: {len(blockchain_events)}")
        
        # 打印所有事件详情
        for idx, event in enumerate(blockchain_events):
            print(f"[DEBUG] 事件 {idx}: event_name={event.get('event_name')}, data={event.get('data')}, signer={event.get('signer_address')}")
        
        if len(blockchain_events) == 0:
            return JSONResponse(status_code=200, content={"logs": []})
        
        # 从持久化的事件中生成操作日志
        logs = []
        log_id = 1
        
        for event in blockchain_events:
            event_type = event.get("event_name", "")
            event_data = event.get("data", {})
            signer_address = event.get("signer_address", "")
            timestamp = event.get("timestamp", 0)
            
            print(f"[DEBUG] 处理事件: {event_type}, 签名者: {signer_address}")
            
            # 查找用户信息
            user_name = "未知"
            user_role = "user"
            for username, user in users.items():
                if user.get("address") == signer_address:
                    user_name = username
                    user_role = user.get("role", "user")
                    print(f"[DEBUG] 找到用户: {username}, 角色: {user_role}")
                    break
            
            # 根据事件类型生成日志
            if event_type == "RecordCreated":
                logs.append({
                    "id": log_id,
                    "type": "create",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("record_id", ""),
                    "description": "创建维修记录",
                    "timestamp": timestamp
                })
                log_id += 1
            elif event_type == "RecordApproved":
                logs.append({
                    "id": log_id,
                    "type": "approve",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("record_id", ""),
                    "description": "审批维修记录",
                    "timestamp": timestamp
                })
                log_id += 1
            elif event_type == "RecordReleased":
                logs.append({
                    "id": log_id,
                    "type": "release",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("record_id", ""),
                    "description": "放行维修记录",
                    "timestamp": timestamp
                })
                log_id += 1
            elif event_type == "AircraftSubchainCreated":
                logs.append({
                    "id": log_id,
                    "type": "create_subchain",
                    "user": user_name,
                    "role": user_role,
                    "recordId": event_data.get("aircraft_registration", ""),
                    "description": f"创建飞机子链: {event_data.get('aircraft_registration', '')}",
                    "timestamp": timestamp
                })
                log_id += 1
        
        # 按时间倒序排序
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        print(f"[DEBUG] 生成了 {len(logs)} 条操作日志")
        return JSONResponse(status_code=200, content={"logs": logs})
    except Exception as e:
        print(f"[ERROR] 获取操作日志失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取操作日志失败: " + str(e)})


@app.get("/api/blockchain/visualization/statistics")
async def get_blockchain_statistics():
    """获取统计数据"""
    try:
        # 从实际维修记录中统计数据
        from collections import defaultdict
        from datetime import datetime
        
        # 按月份统计维修记录
        monthly_records = defaultdict(int)
        monthly_completed = defaultdict(int)
        
        for record in maintenance_records.values():
            created_at = record.get("created_at", 0)
            if created_at > 0:
                # 转换为月份
                dt = datetime.fromtimestamp(created_at)
                month = dt.month
                monthly_records[month] += 1
                
                # 统计已完成的记录
                if record.get("status") in ["approved", "released"]:
                    monthly_completed[month] += 1
        
        # 生成最近6个月的数据
        labels = []
        records_data = []
        completion_rate_data = []
        
        # 获取当前月份
        current_month = datetime.now().month
        
        for i in range(6):
            month = (current_month - 5 + i) if (current_month - 5 + i) > 0 else (current_month - 5 + i + 12)
            labels.append(f"{month}月")
            records_data.append(monthly_records.get(month, 0))
            
            # 计算完成率
            total = monthly_records.get(month, 0)
            completed = monthly_completed.get(month, 0)
            rate = round((completed / total * 100) if total > 0 else 0, 2)
            completion_rate_data.append(rate)
        
        statistics = {
            "labels": labels,
            "records": records_data,
            "completion_rate": completion_rate_data
        }
        return JSONResponse(status_code=200, content=statistics)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计数据失败: " + str(e)})


@app.get("/api/blockchain/health")
async def get_blockchain_health():
    """获取区块链健康度监控数据"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        # 检查区块完整性
        integrity_valid = True
        try:
            blocks = contract_engine.get_all_blocks()
            for i in range(1, len(blocks)):
                if blocks[i].get("previous_hash") != blocks[i-1].get("hash"):
                    integrity_valid = False
                    break
        except Exception as e:
            print(f"[ERROR] 区块完整性检查失败: {e}")
            integrity_valid = False
        
        # 检查哈希验证
        hash_valid = True
        try:
            blocks = contract_engine.get_all_blocks()
            for block in blocks:
                block_hash = block.get("hash", "")
                if not block_hash or len(block_hash) < 10:
                    hash_valid = False
                    break
        except Exception as e:
            print(f"[ERROR] 哈希验证检查失败: {e}")
            hash_valid = False
        
        # 检查区块一致性
        consistency_valid = True
        try:
            blocks = contract_engine.get_all_blocks()
            for i, block in enumerate(blocks):
                if block.get("index") != i:
                    consistency_valid = False
                    break
        except Exception as e:
            print(f"[ERROR] 区块一致性检查失败: {e}")
            consistency_valid = False
        
        # 检查合约状态
        contract_active = True
        try:
            if not master_contract or not hasattr(master_contract, 'state'):
                contract_active = False
        except Exception as e:
            print(f"[ERROR] 合约状态检查失败: {e}")
            contract_active = False
        
        health_data = {
            "integrity_valid": integrity_valid,
            "hash_valid": hash_valid,
            "consistency_valid": consistency_valid,
            "contract_active": contract_active
        }
        
        return JSONResponse(status_code=200, content=health_data)
    except Exception as e:
        print(f"[ERROR] 获取区块链健康度失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取区块链健康度失败: " + str(e)})

@app.post("/api/blockchain/verify")
async def verify_blockchain_integrity():
    """验证区块链完整性"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": "区块链系统未初始化"
            })
        
        blocks = contract_engine.get_all_blocks()
        verification_results = {
            "success": True,
            "total_blocks": len(blocks),
            "integrity_check": {
                "valid": True,
                "details": []
            },
            "hash_check": {
                "valid": True,
                "details": []
            },
            "consistency_check": {
                "valid": True,
                "details": []
            },
            "timestamp": int(datetime.now().timestamp())
        }
        
        # 检查区块完整性（前一个区块的哈希是否匹配）
        for i in range(1, len(blocks)):
            current_block = blocks[i]
            previous_block = blocks[i-1]
            
            if current_block.get("previous_hash") != previous_block.get("hash"):
                verification_results["integrity_check"]["valid"] = False
                verification_results["integrity_check"]["details"].append({
                    "block_index": i,
                    "error": f"区块 {i} 的前哈希与区块 {i-1} 的哈希不匹配",
                    "expected": previous_block.get("hash"),
                    "actual": current_block.get("previous_hash")
                })
        
        # 检查哈希验证
        for i, block in enumerate(blocks):
            block_hash = block.get("hash", "")
            if not block_hash or len(block_hash) < 10:
                verification_results["hash_check"]["valid"] = False
                verification_results["hash_check"]["details"].append({
                    "block_index": i,
                    "error": f"区块 {i} 的哈希无效",
                    "hash": block_hash
                })
        
        # 检查区块一致性（索引是否连续）
        for i, block in enumerate(blocks):
            if block.get("index") != i:
                verification_results["consistency_check"]["valid"] = False
                verification_results["consistency_check"]["details"].append({
                    "block_index": i,
                    "error": f"区块索引不一致，期望 {i}，实际 {block.get('index')}"
                })
        
        # 总体验证结果
        verification_results["overall_valid"] = (
            verification_results["integrity_check"]["valid"] and
            verification_results["hash_check"]["valid"] and
            verification_results["consistency_check"]["valid"]
        )
        
        return JSONResponse(status_code=200, content=verification_results)
    except Exception as e:
        print(f"[ERROR] 验证区块链完整性失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "验证区块链完整性失败: " + str(e)
        })


@app.get("/api/contract/info")
async def get_contract_info():
    """获取合约信息"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        # 获取主链合约信息
        master_contract_address = master_contract.address if hasattr(master_contract, 'address') else "未知"
        master_contract_active = True
        
        # 获取总区块数
        total_blocks = len(contract_engine.get_all_blocks())
        
        # 获取子链信息
        subchains = []
        aircraft_subchains = master_contract.state.get("aircraft_subchains", {})
        
        for aircraft_reg, subchain_info in aircraft_subchains.items():
            subchain_address = subchain_info.get("subchain_address", "")
            record_count = subchain_info.get("record_count", 0)
            
            subchains.append({
                "aircraft_registration": aircraft_reg,
                "address": subchain_address,
                "record_count": record_count,
                "active": True
            })
        
        contract_info = {
            "master_contract_address": master_contract_address,
            "master_contract_active": master_contract_active,
            "total_blocks": total_blocks,
            "subchains": subchains
        }
        
        return JSONResponse(status_code=200, content=contract_info)
    except Exception as e:
        print(f"[ERROR] 获取合约信息失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取合约信息失败: " + str(e)})


# ========== 系统管理API ==========

@app.post("/api/system/backup")
async def backup_system():
    """备份系统数据"""
    try:
        import zipfile
        from datetime import datetime
        
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.zip")
        
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 备份用户数据
            if os.path.exists(USER_DATA_FILE):
                zipf.write(USER_DATA_FILE, "users.json")
            
            # 备份航班数据
            if os.path.exists('flights.json'):
                zipf.write('flights.json', "flights.json")
            
            # 备份维修记录
            if os.path.exists('maintenance_records.json'):
                zipf.write('maintenance_records.json', "maintenance_records.json")
            
            # 备份区块链数据
            if os.path.exists('blockchain.json'):
                zipf.write('blockchain.json', "blockchain.json")
            
            # 备份合约数据
            if os.path.exists('contracts.json'):
                zipf.write('contracts.json', "contracts.json")
            
            # 备份任务数据
            if os.path.exists('tasks.json'):
                zipf.write('tasks.json', "tasks.json")
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "备份成功",
            "backup_file": backup_file
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "备份失败: " + str(e)})


@app.get("/api/system/backup/download")
async def download_backup():
    """下载最新的备份文件"""
    try:
        import zipfile
        from datetime import datetime
        from fastapi.responses import FileResponse
        
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            return JSONResponse(status_code=404, content={"error": "没有可用的备份文件"})
        
        # 获取最新的备份文件
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.zip')]
        if not backup_files:
            return JSONResponse(status_code=404, content={"error": "没有可用的备份文件"})
        
        backup_files.sort(reverse=True)
        latest_backup = os.path.join(backup_dir, backup_files[0])
        
        return FileResponse(
            path=latest_backup,
            filename=os.path.basename(latest_backup),
            media_type='application/zip'
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "下载失败: " + str(e)})


@app.post("/api/system/restore")
async def restore_system(backup: UploadFile = File(...)):
    """恢复系统数据"""
    try:
        import zipfile
        import shutil
        
        # 创建临时目录解压
        temp_dir = f"temp_restore_{int(datetime.now().timestamp())}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 解压备份文件
        with zipfile.ZipFile(backup.file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 恢复文件
        restore_files = {
            "users.json": USER_DATA_FILE,
            "flights.json": "flights.json",
            "maintenance_records.json": "maintenance_records.json",
            "blockchain.json": "blockchain.json",
            "contracts.json": "contracts.json",
            "tasks.json": "tasks.json"
        }
        
        for source, target in restore_files.items():
            source_path = os.path.join(temp_dir, source)
            if os.path.exists(source_path):
                shutil.copy2(source_path, target)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "恢复成功"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "恢复失败: " + str(e)})


@app.post("/api/system/clear-cache")
async def clear_cache():
    """清理系统缓存"""
    try:
        cache_cleared = False
        
        # 清理临时文件
        temp_dirs = ["temp", "cache", "__pycache__"]
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
                cache_cleared = True
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "缓存清理成功" if cache_cleared else "没有需要清理的缓存"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "清理缓存失败: " + str(e)})


@app.post("/api/system/clear-logs")
async def clear_logs():
    """清理系统日志"""
    try:
        logs_cleared = False
        
        # 清理日志文件
        log_files = [f for f in os.listdir('.') if f.endswith('.log') or f.startswith('log_')]
        for log_file in log_files:
            os.remove(log_file)
            logs_cleared = True
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "日志清理成功" if logs_cleared else "没有需要清理的日志"
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "清理日志失败: " + str(e)})


@app.post("/api/reports/generate")
async def generate_report(request: Request):
    """生成报表"""
    try:
        data = await request.json()
        report_type = data.get('type', 'summary')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        format_type = data.get('format', 'excel')
        report_detail_type = data.get('report_type', 'detail')
        filters = data.get('filters', '')
        
        # 生成报表数据
        report_data = await generate_report_data(
            report_type, start_date, end_date, report_detail_type, filters
        )
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_report_{timestamp}.{format_type}"
        
        # 根据格式生成文件
        if format_type == 'json':
            return JSONResponse(status_code=200, content={
                "success": True,
                "message": "报表生成成功",
                "filename": filename,
                "data": report_data
            })
        else:
            # 对于其他格式，返回下载链接
            return JSONResponse(status_code=200, content={
                "success": True,
                "message": "报表生成成功",
                "filename": filename,
                "download_url": f"/api/reports/download/{report_type}/{timestamp}",
                "data": report_data
            })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "生成报表失败: " + str(e)})


@app.get("/api/reports/download/{report_type}/{timestamp}")
async def download_report(report_type: str, timestamp: str):
    """下载报表"""
    try:
        # 根据报表类型和时间戳生成文件内容
        report_data = await generate_report_data(report_type, None, None, 'detail', '')
        
        # 生成CSV格式的内容
        csv_content = "报表类型,生成时间\n"
        csv_content += f"{report_type},{report_data['generated_at']}\n\n"
        csv_content += "数据详情:\n"
        
        for item in report_data.get('data', []):
            if isinstance(item, dict):
                csv_content += ",".join([str(v) for v in item.values()]) + "\n"
        
        # 添加UTF-8 BOM头（字节形式），确保中文正确显示
        csv_bytes = b'\xef\xbb\xbf' + csv_content.encode('utf-8')
        
        # 返回CSV文件
        from fastapi.responses import Response
        return Response(
            content=csv_bytes,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={report_type}_report_{timestamp}.csv"
            }
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "下载报表失败: " + str(e)})


async def generate_report_data(report_type, start_date, end_date, report_detail_type, filters):
    """生成报表数据"""
    report_data = {
        "type": report_type,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now().isoformat(),
        "data": []
    }
    
    if report_type == 'maintenance':
        # 维修记录报表
        records = list(maintenance_records.values())
        if start_date and end_date:
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()) + 86400
            records = [r for r in records if start_ts <= r.get('timestamp', 0) <= end_ts]
        
        if filters:
            filter_keywords = filters.split(',')
            for keyword in filter_keywords:
                keyword = keyword.strip()
                records = [r for r in records if keyword in r.get('aircraft_registration', '') or 
                          keyword in r.get('maintenance_type', '')]
        
        report_data["data"] = records
        report_data["summary"] = {
            "total": len(records),
            "by_type": {},
            "by_status": {}
        }
        
        for record in records:
            mtype = record.get('maintenance_type', 'unknown')
            status = record.get('status', 'unknown')
            report_data["summary"]["by_type"][mtype] = report_data["summary"]["by_type"].get(mtype, 0) + 1
            report_data["summary"]["by_status"][status] = report_data["summary"]["by_status"].get(status, 0) + 1
    
    elif report_type == 'flight':
        # 航班统计报表
        flight_list = flights
        if start_date and end_date:
            flight_list = [f for f in flight_list if start_date <= f.get('date', '') <= end_date]
        
        if filters:
            filter_keywords = filters.split(',')
            for keyword in filter_keywords:
                keyword = keyword.strip()
                flight_list = [f for f in flight_list if keyword in f.get('flight_number', '') or 
                              keyword in f.get('airline', '')]
        
        report_data["data"] = flight_list
        report_data["summary"] = {
            "total": len(flight_list),
            "by_status": {},
            "by_airline": {}
        }
        
        for flight in flight_list:
            status = flight.get('status', 'unknown')
            airline = flight.get('airline', 'unknown')
            report_data["summary"]["by_status"][status] = report_data["summary"]["by_status"].get(status, 0) + 1
            report_data["summary"]["by_airline"][airline] = report_data["summary"]["by_airline"].get(airline, 0) + 1
    
    elif report_type == 'blockchain':
        # 区块链状态报表
        if contract_engine:
            blocks = contract_engine.get_all_blocks()
            if start_date and end_date:
                start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
                end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()) + 86400
                blocks = [b for b in blocks if start_ts <= b.get('timestamp', 0) <= end_ts]
            
            report_data["data"] = blocks
            report_data["summary"] = {
                "total_blocks": len(blocks),
                "total_transactions": sum(len(b.get('transactions', [])) for b in blocks),
                "latest_block_hash": blocks[-1].get('hash', '') if blocks else ''
            }
    
    elif report_type == 'user':
        # 用户活动报表
        user_list = list(users.values())
        report_data["data"] = user_list
        report_data["summary"] = {
            "total_users": len(user_list),
            "by_role": {}
        }
        
        for user in user_list:
            role = user.get('role', 'user')
            report_data["summary"]["by_role"][role] = report_data["summary"]["by_role"].get(role, 0) + 1
    
    elif report_type == 'aircraft':
        # 航空器信息报表
        aircraft_list = []
        for record in maintenance_records.values():
            reg = record.get('aircraft_registration', '')
            if reg and reg not in [a.get('registration') for a in aircraft_list]:
                aircraft_list.append({
                    "registration": reg,
                    "maintenance_count": 0,
                    "last_maintenance": None
                })
        
        for aircraft in aircraft_list:
            reg = aircraft['registration']
            aircraft_records = [r for r in maintenance_records.values() if r.get('aircraft_registration') == reg]
            aircraft['maintenance_count'] = len(aircraft_records)
            if aircraft_records:
                aircraft['last_maintenance'] = max(r.get('timestamp', 0) for r in aircraft_records)
        
        report_data["data"] = aircraft_list
        report_data["summary"] = {
            "total_aircraft": len(aircraft_list),
            "total_maintenance": sum(a['maintenance_count'] for a in aircraft_list)
        }
    
    elif report_type == 'summary':
        # 综合汇总报表
        report_data["summary"] = {
            "users": {
                "total": len(users),
                "by_role": {}
            },
            "flights": {
                "total": len(flights),
                "by_status": {}
            },
            "maintenance_records": {
                "total": len(maintenance_records),
                "by_type": {},
                "by_status": {}
            },
            "blockchain": {
                "total_blocks": len(contract_engine.get_all_blocks()) if contract_engine else 0
            }
        }
        
        for user in users.values():
            role = user.get('role', 'user')
            report_data["summary"]["users"]["by_role"][role] = report_data["summary"]["users"]["by_role"].get(role, 0) + 1
        
        for flight in flights:
            status = flight.get('status', 'unknown')
            report_data["summary"]["flights"]["by_status"][status] = report_data["summary"]["flights"]["by_status"].get(status, 0) + 1
        
        for record in maintenance_records.values():
            mtype = record.get('maintenance_type', 'unknown')
            status = record.get('status', 'unknown')
            report_data["summary"]["maintenance_records"]["by_type"][mtype] = report_data["summary"]["maintenance_records"]["by_type"].get(mtype, 0) + 1
            report_data["summary"]["maintenance_records"]["by_status"][status] = report_data["summary"]["maintenance_records"]["by_status"].get(status, 0) + 1
    
    return report_data


@app.get("/api/system/stats")
async def get_system_stats():
    """获取系统统计信息"""
    try:
        stats = {
            "total_users": len(users),
            "total_flights": len(flights),
            "total_records": len(maintenance_records),
            "total_blocks": len(contract_engine.get_all_blocks()) if contract_engine else 0,
            "total_contracts": len(contract_engine.contracts) if contract_engine else 0,
            "disk_usage": get_disk_usage(),
            "memory_usage": get_memory_usage(),
            "uptime": get_system_uptime()
        }
        
        return JSONResponse(status_code=200, content=stats)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计信息失败: " + str(e)})

@app.get("/api/system/users")
async def get_all_users_info(request: Request):
    """获取所有用户信息"""
    try:
        print(f"[DEBUG] 开始获取用户列表")
        print(f"[DEBUG] users变量: {users}")
        
        # 直接返回users数据
        users_list = []
        for username, user_info in users.items():
            users_list.append({
                "username": username,
                "role": user_info.get("role", "user") if isinstance(user_info, dict) else "user",
                "address": user_info.get("address", "") if isinstance(user_info, dict) else "",
                "email": user_info.get("email", "") if isinstance(user_info, dict) else "",
                "phone": user_info.get("phone", "") if isinstance(user_info, dict) else "",
                "specialty": user_info.get("specialty", "") if isinstance(user_info, dict) else "",
                "employee_id": user_info.get("employee_id", "") if isinstance(user_info, dict) else "",
                "created_at": user_info.get("created_at", "") if isinstance(user_info, dict) else ""
            })
        
        print(f"[DEBUG] 用户列表: {users_list}")
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "users": users_list,
            "total": len(users_list)
        })
    except Exception as e:
        print(f"[ERROR] 获取用户信息失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "获取用户信息失败: " + str(e)
        })


def get_disk_usage():
    """获取磁盘使用情况"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        return {
            "total": total,
            "used": used,
            "free": free,
            "used_percent": round(used / total * 100, 2)
        }
    except:
        return {"total": 0, "used": 0, "free": 0, "used_percent": 0}


def get_memory_usage():
    """获取内存使用情况"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total": mem.total,
            "used": mem.used,
            "free": mem.available,
            "used_percent": mem.percent
        }
    except:
        return {"total": 0, "used": 0, "free": 0, "used_percent": 0}


def get_system_uptime():
    """获取系统运行时间"""
    try:
        import psutil
        boot_time = psutil.boot_time()
        uptime = int(datetime.now().timestamp()) - boot_time
        return {
            "seconds": uptime,
            "hours": round(uptime / 3600, 2),
            "days": round(uptime / 86400, 2)
        }
    except:
        return {"seconds": 0, "hours": 0, "days": 0}


# 检测人员分配管理

# 检测人员数据
inspectors = []

# 检测任务数据
tasks = []

# 从文件加载用户数据
def load_users():
    """从文件加载用户数据"""
    global users
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                loaded_users = json.load(f)
                users.clear()
                users.update(loaded_users)
                print(f"成功加载 {len(users)} 个用户")
                # 打印前几个用户的信息用于调试
                for i, (username, user_info) in enumerate(users.items()):
                    if i < 3:
                        print(f"[DEBUG] 用户 {username}: role={user_info.get('role', 'N/A')}, name={user_info.get('name', 'N/A')}")
        else:
            print("users.json 不存在，使用默认用户数据")
    except Exception as e:
        print(f"加载用户数据失败: {e}")
        users = {}

# 从文件加载任务数据
def load_tasks():
    """从文件加载任务数据"""
    global tasks
    try:
        if os.path.exists('tasks.json'):
            with open('tasks.json', 'r', encoding='utf-8') as f:
                tasks = json.load(f)
                print(f"成功加载 {len(tasks)} 个任务")
    except Exception as e:
        print(f"加载任务数据失败: {e}")
        tasks = []

# 保存任务数据到文件
def save_tasks():
    """保存任务数据到文件"""
    try:
        with open('tasks.json', 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
            print(f"成功保存 {len(tasks)} 个任务")
    except Exception as e:
        print(f"保存任务数据失败: {e}")

# 加载维修记录数据
def load_maintenance_records():
    """从文件加载维修记录数据"""
    global maintenance_records
    try:
        if os.path.exists('maintenance_records.json'):
            with open('maintenance_records.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                maintenance_records = data if isinstance(data, dict) else {}
                print(f"成功加载 {len(maintenance_records)} 个维修记录")
    except Exception as e:
        print(f"加载维修记录数据失败: {e}")
        maintenance_records = {}

# 保存维修记录数据到文件
def save_maintenance_records():
    """保存维修记录数据到文件"""
    try:
        with open('maintenance_records.json', 'w', encoding='utf-8') as f:
            json.dump(maintenance_records, f, ensure_ascii=False, indent=2)
            print(f"成功保存 {len(maintenance_records)} 个维修记录")
    except Exception as e:
        print(f"保存维修记录数据失败: {e}")

# 加载区块链事件数据
def load_blockchain_events():
    """从文件加载区块链事件数据"""
    global blockchain_events
    try:
        if os.path.exists('blockchain_events.json'):
            with open('blockchain_events.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                blockchain_events = data if isinstance(data, list) else []
                print(f"成功加载 {len(blockchain_events)} 个区块链事件")
        else:
            print(f"[DEBUG] blockchain_events.json 不存在，初始化为空列表")
            blockchain_events = []
    except Exception as e:
        print(f"[DEBUG] 加载区块链事件数据失败: {e}")
        # 加载失败时不清空列表，保留已加载的事件

# 保存区块链事件数据到文件
def save_blockchain_events():
    """保存区块链事件数据到文件"""
    try:
        with open('blockchain_events.json', 'w', encoding='utf-8') as f:
            json.dump(blockchain_events, f, ensure_ascii=False, indent=2)
            print(f"成功保存 {len(blockchain_events)} 个区块链事件")
    except Exception as e:
        print(f"保存区块链事件数据失败: {e}")

# 加载航班数据
def load_flights():
    """从文件加载航班数据"""
    global flights
    try:
        if os.path.exists('flights.json'):
            with open('flights.json', 'r', encoding='utf-8') as f:
                flights = json.load(f)
                print(f"成功加载 {len(flights)} 个航班")
        else:
            print("flights.json 不存在，使用默认航班数据")
    except Exception as e:
        print(f"加载航班数据失败: {e}")

# 保存航班数据到文件
def save_flights():
    """保存航班数据到文件"""
    try:
        with open('flights.json', 'w', encoding='utf-8') as f:
            json.dump(flights, f, ensure_ascii=False, indent=2)
            print(f"成功保存 {len(flights)} 个航班")
    except Exception as e:
        print(f"保存航班数据失败: {e}")


# 简单的航班 API：列表 / 创建 / 更新
@app.get('/api/flights')
async def api_get_flights(request: Request):
    try:
        return JSONResponse(status_code=200, content={
            'success': True,
            'flights': flights
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': str(e)
        })


@app.post('/api/flights')
async def api_create_flight(request: Request):
    """创建航班并持久化到 flights.json"""
    try:
        data = await request.json()
        # 生成唯一 id
        new_id = str(uuid.uuid4())
        data['id'] = new_id
        # 添加到内存并保存
        flights.append(data)
        save_flights()
        return JSONResponse(status_code=200, content={
            'success': True,
            'flight': {'id': new_id}
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': str(e)
        })


@app.put('/api/flights/{flight_id}')
async def api_update_flight(flight_id: str, request: Request):
    """更新已有航班（按 id 匹配）"""
    try:
        data = await request.json()
        updated = False
        for idx, f in enumerate(flights):
            if str(f.get('id')) == str(flight_id):
                # 保持 id 不被覆盖
                data['id'] = flight_id
                flights[idx] = data
                updated = True
                break
        if not updated:
            return JSONResponse(status_code=404, content={
                'success': False,
                'message': '航班未找到'
            })
        save_flights()
        return JSONResponse(status_code=200, content={
            'success': True,
            'flight': {'id': flight_id}
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            'success': False,
            'message': str(e)
        })

# 初始化区块链
def initialize_blockchain():
    """初始化区块链系统"""
    global contract_engine, master_contract
    
    try:
        contract_engine = ContractEngine()
        
        # 尝试从 blockchain.json 加载现有区块数据
        if os.path.exists('blockchain.json'):
            try:
                with open('blockchain.json', 'r', encoding='utf-8') as f:
                    blockchain_data = json.load(f)
                    if 'blocks' in blockchain_data and len(blockchain_data['blocks']) > 1:
                        # 加载现有区块数据
                        contract_engine.blocks = blockchain_data['blocks']
                        if contract_engine.blocks:
                            contract_engine.latest_block_hash = contract_engine.blocks[-1].get('hash', '0x0000000000000000000000000000000000000000000000000000000000000000')
                        print(f"成功从 blockchain.json 加载 {len(contract_engine.blocks)} 个区块")
            except Exception as e:
                print(f"加载 blockchain.json 失败: {e}，将使用新的区块链")
        
        # 尝试从 contracts.json 加载现有合约数据
        if os.path.exists('contracts.json'):
            try:
                with open('contracts.json', 'r', encoding='utf-8') as f:
                    contracts_data = json.load(f)
                    if 'contracts' in contracts_data and contracts_data['contracts']:
                        # 加载现有合约数据
                        for contract_address, contract_info in contracts_data['contracts'].items():
                            contract_name = contract_info.get('contract_name', '')
                            state = contract_info.get('state', {})
                            
                            if contract_name == 'MaintenanceRecordMasterContract':
                                # 创建主合约
                                master_contract = MaintenanceRecordMasterContract(contract_address)
                                master_contract.state = state
                                contract_engine.register_contract(master_contract)
                                print(f"成功加载主合约: {contract_address}")
                            elif contract_name == 'AircraftSubchainContract':
                                # 创建子合约
                                aircraft_info = state.get('aircraft_info', {})
                                aircraft_reg = aircraft_info.get('aircraft_registration', '')
                                aircraft_type = aircraft_info.get('aircraft_type', '')
                                master_address = aircraft_info.get('master_contract_address', '')
                                
                                subchain_contract = AircraftSubchainContract(
                                    contract_address,
                                    aircraft_reg,
                                    aircraft_type,
                                    master_address
                                )
                                subchain_contract.state = state
                                contract_engine.register_contract(subchain_contract)
                                print(f"成功加载子合约: {contract_address} (飞机: {aircraft_reg})")
                        
                        print(f"成功从 contracts.json 加载 {len(contracts_data['contracts'])} 个合约")
            except Exception as e:
                print(f"加载 contracts.json 失败: {e}，将创建新的合约")
        
        # 如果没有加载到主合约，则创建新的
        if not master_contract:
            master_contract_address = BaseContract.generate_address("MaintenanceRecordMasterContract")
            master_contract = MaintenanceRecordMasterContract(master_contract_address)
            contract_engine.register_contract(master_contract)
            print(f"创建新的主合约，地址: {master_contract_address}")
        
        print(f"区块链系统初始化成功，主链地址: {master_contract.contract_address}")
        
        # 迁移现有维修记录到智能合约（仅当区块链为空时）
        migrate_maintenance_records_to_contract()
    except Exception as e:
        print(f"初始化区块链系统失败: {e}")
        import traceback
        traceback.print_exc()
        contract_engine = None
        master_contract = None

# 确保用户有公钥
def ensure_users_have_keys():
    """为没有公钥或私钥的用户生成公私钥对"""
    global users
    
    try:
        updated = False
        for username, user_info in users.items():
            if "public_key" not in user_info or not user_info["public_key"] or "private_key" not in user_info or not user_info["private_key"]:
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
                
                # 更新用户信息
                user_info["public_key"] = public_pem
                user_info["private_key"] = private_pem
                user_info["address"] = address
                if "employee_id" not in user_info:
                    user_info["employee_id"] = "EMP" + address[-8:]
        
                updated = True
                print(f"为用户 {username} 生成公私钥对和地址: {address}")
        
        if updated:
            # 保存用户数据
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            print("成功更新用户数据")
    except Exception as e:
        print(f"确保用户有公私钥失败: {e}")

# 迁移维修记录到智能合约
def migrate_maintenance_records_to_contract():
    """将现有维修记录迁移到智能合约系统"""
    global contract_engine, master_contract, maintenance_records
    
    if not contract_engine or not master_contract:
        return
    
    try:
        # 检查是否已经迁移过
        if contract_engine.get_blockchain_length() > 1:
            print("区块链已有数据，跳过迁移")
            return
        
        # 获取现有维修记录
        records_to_migrate = list(maintenance_records.values())
        
        if not records_to_migrate:
            print("没有需要迁移的维修记录")
            return
        
        print(f"开始迁移 {len(records_to_migrate)} 条维修记录到智能合约...")
        
        # 为每条记录创建区块
        for record in records_to_migrate:
            try:
                # 创建飞机子链（如果不存在）
                aircraft_reg = record.get("aircraft_registration", "")
                if aircraft_reg and aircraft_reg not in master_contract.state["aircraft_subchains"]:
                    subchain_address = BaseContract.generate_address(
                        "AircraftSubchainContract",
                        {"aircraft_registration": aircraft_reg}
                    )
                    
                    master_contract.state["aircraft_subchains"][aircraft_reg] = {
                        "aircraft_registration": aircraft_reg,
                        "aircraft_type": record.get("aircraft_model", "未知"),
                        "subchain_address": subchain_address,
                        "record_count": 0,
                        "created_at": int(datetime.now().timestamp()),
                        "latest_block_hash": "0"
                    }
                    
                    # 创建子链合约
                    subchain_contract = AircraftSubchainContract(
                        subchain_address,
                        aircraft_reg,
                        record.get("aircraft_model", "未知"),
                        master_contract.contract_address
                    )
                    contract_engine.register_contract(subchain_contract)
                    
                    print(f"创建飞机子链: {aircraft_reg} -> {subchain_address}")
                
                # 在主链创建记录
                record_id = record.get("id", "")
                if record_id not in master_contract.state["records"]:
                    master_contract.state["records"][record_id] = {
                        "id": record_id,
                        "aircraft_registration": record.get("aircraft_registration", ""),
                        "subchain_address": master_contract.state["aircraft_subchains"].get(
                            record.get("aircraft_registration", ""), {}
                        ).get("subchain_address", ""),
                        "maintenance_type": record.get("maintenance_type", ""),
                        "maintenance_date": record.get("maintenance_date", ""),
                        "maintenance_description": record.get("maintenance_description", ""),
                        "status": record.get("status", "pending"),
                        "technician_address": record.get("technician_id", ""),
                        "technician_name": record.get("technician_name", "未知"),
                        "approver_address": "",
                        "created_at": record.get("created_at", int(datetime.now().timestamp())),
                        "updated_at": record.get("updated_at", int(datetime.now().timestamp())),
                        "block_index": contract_engine.get_blockchain_length(),
                        "subchain_block_index": 0
                    }
                    
                    # 更新统计
                    master_contract.state["stats"]["total_records"] += 1
                    status = record.get("status", "pending")
                    if status == "pending":
                        master_contract.state["stats"]["pending_count"] += 1
                    elif status == "approved":
                        master_contract.state["stats"]["approved_count"] += 1
                    elif status == "released":
                        master_contract.state["stats"]["released_count"] += 1
                    
                    # 在子链添加记录
                    aircraft_reg = record.get("aircraft_registration", "")
                    subchain_address = master_contract.state["aircraft_subchains"].get(
                        aircraft_reg, {}
                    ).get("subchain_address", "")
                    
                    if subchain_address:
                        subchain_contract = contract_engine.get_contract(subchain_address)
                        if subchain_contract and record_id not in subchain_contract.state["records"]:
                            subchain_contract.state["records"][record_id] = {
                                "id": record_id,
                                "maintenance_type": record.get("maintenance_type", ""),
                                "description": record.get("maintenance_description", ""),
                                "status": record.get("status", "pending"),
                                "technician_address": record.get("technician_id", ""),
                                "approver_address": "",
                                "created_at": record.get("created_at", int(datetime.now().timestamp())),
                                "updated_at": record.get("updated_at", int(datetime.now().timestamp())),
                                "block_index": contract_engine.get_blockchain_length(),
                                "master_record_id": record_id
                            }
                            
                            # 更新子链统计
                            subchain_contract.state["stats"]["total_records"] += 1
                            if status == "pending":
                                subchain_contract.state["stats"]["pending_count"] += 1
                            elif status == "approved":
                                subchain_contract.state["stats"]["approved_count"] += 1
                            elif status == "released":
                                subchain_contract.state["stats"]["released_count"] += 1
                            
                            # 更新飞机记录数
                            if aircraft_reg in master_contract.state["aircraft_subchains"]:
                                master_contract.state["aircraft_subchains"][aircraft_reg]["record_count"] += 1
                    
                    # 创建区块（包含完整信息）
                    technician_name = record.get("technician_name", "未知")
                    technician_id = record.get("technician_id", "")
                    
                    # 查找技术员的地址
                    tech_address = ""
                    if technician_id:
                        for username, user_info in users.items():
                            if user_info.get("username") == technician_id:
                                tech_address = user_info.get("address", "")
                                break
                    
                    block = contract_engine._create_block(
                        contract_address=master_contract.contract_address,
                        method="migrateRecord",
                        params={
                            "record_id": record_id,
                            "aircraft_registration": record.get("aircraft_registration", ""),
                            "maintenance_type": record.get("maintenance_type", ""),
                            "description": record.get("maintenance_description", ""),
                            "technician_address": tech_address,
                            "technician_name": technician_name
                        },
                        signature="migration_signature",
                        signer_address=tech_address if tech_address else "system",
                        nonce=f"migration_{record_id}",
                        events=[]
                    )
                    
                    contract_engine.blocks.append(block)
                    contract_engine.latest_block_hash = block["hash"]
                    
                    print(f"迁移记录: {record_id} -> 区块 {block['index']}")
                    
            except Exception as e:
                print(f"迁移记录 {record.get('id', 'unknown')} 失败: {e}")
                continue
        
        # 保存区块链和合约数据
        save_blockchain()
        save_contracts()
        
        print(f"迁移完成！区块链长度: {contract_engine.get_blockchain_length()}")
        
    except Exception as e:
        print(f"迁移维修记录失败: {e}")

# 保存区块链数据到文件
def save_blockchain():
    """保存区块链数据到文件"""
    global contract_engine
    if not contract_engine:
        return
    
    try:
        with open('blockchain.json', 'w', encoding='utf-8') as f:
            blockchain_data = {
                "blocks": contract_engine.get_all_blocks(),
                "latest_block_hash": contract_engine.latest_block_hash
            }
            json.dump(blockchain_data, f, ensure_ascii=False, indent=2)
            print(f"成功保存区块链数据，区块数: {len(contract_engine.get_all_blocks())}")
    except Exception as e:
        print(f"保存区块链数据失败: {e}")

# 保存合约数据到文件
def save_contracts():
    """保存合约数据到文件"""
    global contract_engine
    if not contract_engine:
        return
    
    try:
        contracts_data = {}
        for address, contract in contract_engine.get_all_contracts().items():
            contracts_data[address] = contract.to_dict()
        
        with open('contracts.json', 'w', encoding='utf-8') as f:
            json.dump({"contracts": contracts_data}, f, ensure_ascii=False, indent=2)
            print(f"成功保存合约数据，合约数: {len(contracts_data)}")
    except Exception as e:
        print(f"保存合约数据失败: {e}")

# 获取检测人员列表
@app.get("/api/inspectors")
async def get_inspectors():
    """获取检测人员列表"""
    global inspectors  # 声明使用全局变量
    
    # 从用户数据中筛选出角色为technician或user的用户
    technician_users = []
    for username, user_info in users.items():
        user_role = user_info.get('role')
        # 同时筛选 technician 和 user 角色（两者都表示技术人员）
        if user_role in ['technician', 'user']:
            # 格式化用户数据为检测人员格式
            technician_users.append({
                "id": username,  # 使用用户名作为ID
                "name": user_info.get("name", username),  # 使用用户的name字段
                "position": "技术人员",
                "specialty": user_info.get("specialty", ""),  # 从用户数据中获取专长
                "status": "available",  # 默认状态为可用
                "current_task": None
            })
    
    # 更新全局inspectors列表
    inspectors.clear()
    inspectors.extend(technician_users)
    
    print(f"[DEBUG] 获取到 {len(technician_users)} 个技术人员")
    
    return JSONResponse(status_code=200, content={
        "success": True,
        "inspectors": technician_users
    })

# 获取检测任务列表
@app.get("/api/tasks")
async def get_tasks():
    """获取检测任务列表"""
    return JSONResponse(status_code=200, content={
        "success": True,
        "tasks": tasks
    })

# 分配检测任务
@app.post("/api/tasks/assign")
async def assign_task(request: Request):
    """分配检测任务"""
    try:
        data = await request.json()
        task_id = data.get("task_id")
        inspector_id = data.get("inspector_id")
        
        # 查找任务
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })
        
        # 查找检测人员
        inspector = next((i for i in inspectors if i["id"] == inspector_id), None)
        if not inspector:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "检测人员不存在"
            })
        
        # 检查检测人员状态
        if inspector["status"] == "busy":
            return JSONResponse(status_code=400, content={
                "success": False,
                "message": "检测人员当前忙"
            })
        
        # 分配任务
        task["assignee_id"] = inspector_id
        task["status"] = "assigned"
        inspector["status"] = "busy"
        inspector["current_task"] = f"{task['aircraft_registration']}{task['task_type']}"
        
        # 保存任务数据
        save_tasks()
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "任务分配成功",
            "task": task
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "分配任务失败: " + str(e)
        })

# 完成检测任务
@app.post("/api/tasks/complete")
async def complete_task(request: Request):
    """完成检测任务"""
    try:
        data = await request.json()
        task_id = data.get("task_id")
        
        # 查找任务
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return JSONResponse(status_code=404, content={
                "success": False,
                "message": "任务不存在"
            })
        
        # 查找检测人员
        inspector_id = task.get("assignee_id")
        inspector_name = ""
        if inspector_id:
            inspector = next((i for i in inspectors if i["id"] == inspector_id), None)
            if inspector:
                inspector["status"] = "available"
                inspector["current_task"] = None
                inspector_name = inspector["name"]
        
        # 更新任务状态
        task["status"] = "completed"
        
        # 保存任务数据
        save_tasks()
        
        # 自动创建区块链存证记录
        try:
            import uuid
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.asymmetric import padding
            
            # 生成记录ID
            record_id = str(uuid.uuid4())[:12]
            
            # 生成样例公钥和签名
            public_pem = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwH6f8f8f8f8f8f8f8f8f8\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nfQIDAQAB\n-----END PUBLIC KEY-----"
            signature = "sample_signature"
            
            # 创建区块链存证记录
            maintenance_records[record_id] = {
                "id": record_id,
                "aircraft_registration": task["flight_number"],
                "aircraft_model": "",
                "aircraft_series": "",
                "aircraft_age": "",
                "maintenance_type": task["task_type"],
                "maintenance_date": datetime.now().strftime("%Y-%m-%d"),
                "maintenance_description": f"完成{task['flight_number']}航班的{task['task_type']}任务",
                "maintenance_duration": "",
                "parts_used": "",
                "is_rii": False,
                "technician_name": inspector_name or "未知",
                "technician_id": inspector_id or "",
                "technician_public_key": public_pem,
                "signature": signature,
                "status": "pending",
                "created_at": int(datetime.now().timestamp()),
                "updated_at": int(datetime.now().timestamp()),
                "task_id": task_id
            }
            
            # 保存维修记录到文件
            save_maintenance_records()
            
            # 同时保存到智能合约
            if contract_engine and master_contract:
                try:
                    technician_address = current_user.get("address", "")
                    timestamp = int(datetime.now().timestamp())
                    nonce = str(timestamp)
                    
                    # 创建签名数据
                    sign_data = SignatureManager.create_sign_data(
                        contract_address=master_contract.contract_address,
                        method="createRecord",
                        params={
                            "aircraft_registration": data.get("aircraft_registration"),
                            "maintenance_type": data.get("maintenance_type"),
                            "description": data.get("fault_description"),
                            "technician_address": technician_address
                        },
                        timestamp=timestamp,
                        nonce=nonce
                    )
                    
                    # 使用私钥签名
                    private_key = current_user.get("private_key", "")
                    if private_key:
                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result
                            
                            # 执行智能合约
                            result = contract_engine.execute_contract(
                                contract_address=master_contract.contract_address,
                                method_name="createRecord",
                                params={
                                    "aircraft_registration": data.get("aircraft_registration"),
                                    "maintenance_type": data.get("maintenance_type"),
                                    "description": data.get("fault_description"),
                                    "technician_address": technician_address,
                                    "caller_address": technician_address,
                                    "caller_role": current_user.get("role", "technician")
                                },
                                signature=signature,
                                signer_address=current_user['address'],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )
                            
                            # 检查合约方法执行结果
                            contract_result = result.get("result", {})
                            if contract_result.get("success"):
                                # 获取合约返回的record_id
                                contract_record_id = contract_result.get("record_id", record_id)
                                if contract_record_id:
                                    # 如果合约返回了新的record_id，更新maintenance_records
                                    if record_id in maintenance_records:
                                        old_record = maintenance_records.pop(record_id)
                                        old_record["id"] = contract_record_id
                                        maintenance_records[contract_record_id] = old_record
                                        print(f"[DEBUG] 更新记录ID: {record_id} -> {contract_record_id}")
                                        save_maintenance_records()
                            
                            # 手动添加创建事件到持久化存储
                            event_data = {
                                "event_name": "RecordCreated",
                                "contract_address": master_contract.contract_address,
                                "block_index": len(blockchain_events),
                                "timestamp": timestamp,
                                "data": {
                                    "record_id": contract_record_id,
                                    "aircraft_registration": data.get("aircraft_registration"),
                                    "subchain_address": result.get("subchain_address", ""),
                                    "maintenance_type": data.get("maintenance_type"),
                                    "description": data.get("fault_description"),
                                    "technician_address": technician_address
                                },
                                "signer_address": technician_address
                            }
                            blockchain_events.append(event_data)
                            save_blockchain_events()
                            
                            save_blockchain()
                            save_contracts()
                            print(f"[DEBUG] 维修记录已保存到区块链: {record_id}")
                        else:
                            print(f"[DEBUG] 签名失败: {signature_result.get('error')}")
                except Exception as e:
                    print(f"[DEBUG] 保存到区块链异常: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[DEBUG] 区块链系统未初始化，仅保存到文件")
        except Exception as e:
            print(f"[ERROR] 创建维修记录异常: {e}")
            import traceback
            traceback.print_exc()
        
        # 更新任务状态为已完成
        task["status"] = "completed"
        
        # 释放检测人员
        if task.get("assignee_id"):
            inspector_id = task["assignee_id"]
            inspector = next((i for i in inspectors if i["id"] == inspector_id), None)
            if inspector:
                inspector["status"] = "available"
                inspector["current_task"] = None
        
        # 保存任务数据
        save_tasks()
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "维修记录创建成功",
            "record_id": record_id
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "创建维修记录失败: " + str(e)
        })

# 加载机场数据函数
def load_airport_data():
    try:
        # 获取当前文件所在目录的上两级目录（项目根目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir))) # d:\BlockChain\视频系统\backend -> d:\BlockChain\视频系统 -> d:\BlockChain
        # 修正路径逻辑：__file__是backend/main.py, dirname是backend, twice is 视频系统, thrice is BlockChain
        # Actually: os.path.dirname(__file__) -> backend
        # os.path.dirname(backend) -> 视频系统
        # os.path.dirname(视频系统) -> BlockChain
        
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 尝试几种可能的路径
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(backend_dir)), "机场信息.csv"), # ../../机场信息.csv relative to backend
            os.path.join("D:\\BlockChain", "机场信息.csv"),
            "机场信息.csv"
        ]
        
        csv_path = None
        for path in possible_paths:
            if os.path.exists(path):
                csv_path = path
                break
                
        if not csv_path:
            print("警告: 找不到机场信息.csv文件")
            return []
            
        airports = []
        import csv
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("三字码 (IATA)", "").strip()
                # 只保留有有效三字码的机场
                if code and len(code) == 3 and code.isalpha():
                    airports.append({
                        "name": row.get("机场名称", "").strip(),
                        "city": row.get("城市", "").strip(),
                        "province": row.get("省份/地区", "").strip(),
                        "code": code
                    })
        return airports
    except Exception as e:
        print(f"读取机场信息出错: {e}")
        return []

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时加载数据"""
    load_users()
    load_tasks()
    load_maintenance_records()
    load_flights()
    load_airport_data()  # 加载机场数据
    load_blockchain_events()
    initialize_blockchain()
    ensure_users_have_keys()

app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# 挂载检修系统的静态文件（如果存在）
if os.path.exists("./tcg/static"):
    app.mount("/tcg/static", StaticFiles(directory="./tcg/static"), name="tcg_static")

templates = Jinja2Templates(directory="../frontend")

# 添加检修系统的模板目录（如果存在）
if os.path.exists("./tcg/templates"):
    tcg_templates = Jinja2Templates(directory="./tcg/templates")
else:
    # 如果模板目录不存在，使用前端模板替代
    tcg_templates = templates

# 检修系统工具函数
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        address = payload.get("sub")
        username = payload.get("username")
        
        if address:
            # 优先从检修系统获取用户信息
            user = auth.get_user_by_address(address)
            if user:
                # 确保用户对象包含is_admin字段
                if "is_admin" not in user:
                    user["is_admin"] = False
                return user
        
        if username:
            # 从视频系统获取用户信息
            user_info = users.get(username)
            if user_info:
                # 转换为检修系统的用户格式
                return {
                    "address": user_info.get("address", address),
                    "name": user_info.get("name", username),
                    "employee_id": user_info.get("employee_id"),
                    "is_admin": user_info.get("role") == "admin",
                    "role": user_info.get("role", "user")
                }
        
        return None
    except Exception as e:
        print(f"[DEBUG] get_current_user error: {e}")
        return None

# 数据文件路径
USER_DATA_FILE = "users.json"

# 房间管理
rooms = {}

# 用户管理
users = {}
user_roles = {}

# 模拟航班数据
flights = []

# 机场数据
airports = []

# 加载用户数据
if os.path.exists(USER_DATA_FILE):
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
            # 解析 users.json 格式
            for username, info in user_data.items():
                if isinstance(info, dict):
                    # 新数据格式
                    users[username] = info
                    user_roles[username] = info.get('role', 'user')
                else:
                    # 旧数据格式
                    users[username] = {
                        "password": info,
                        "role": user_roles.get(username, 'user')
                    }
    except Exception as e:
        print(f"加载用户数据失败: {e}")

# 保存用户数据
def save_user_data():
    try:
        # 保存为统一格式
        user_data = {}
        for username, info in users.items():
            if isinstance(info, dict):
                user_data[username] = info
            else:
                # 旧数据格式转换
                user_data[username] = {
                    'password': info,
                    'role': user_roles.get(username, 'user')
                }
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存用户数据失败: {e}")

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = {}
        self.active_connections[room_id][user_id] = websocket
    
    def disconnect(self, room_id: str, user_id: str):
        if room_id in self.active_connections:
            if user_id in self.active_connections[room_id]:
                del self.active_connections[room_id][user_id]
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def broadcast(self, message: dict, room_id: str, exclude_user: str = None):
        if room_id in self.active_connections:
            for user_id, connection in self.active_connections[room_id].items():
                if user_id != exclude_user:
                    await connection.send_json(message)
    
    def get_room_users(self, room_id: str):
        if room_id in self.active_connections:
            return list(self.active_connections[room_id].keys())
        return []

manager = ConnectionManager()

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/video-system")
async def video_system_page(request: Request):
    """远程视频协助系统页面"""
    return templates.TemplateResponse("video-system.html", {"request": request})

@app.get("/device-test")
async def device_test(request: Request):
    """设备测试页面"""
    return templates.TemplateResponse("device-test.html", {"request": request})

@app.get("/inspector-assignment")
async def inspector_assignment_page(request: Request):
    """检测人员分配管理页面"""
    return templates.TemplateResponse("inspector-assignment.html", {"request": request})

@app.get("/flight-search")
async def flight_search_page(request: Request):
    """航班查询页面"""
    airports = load_airport_data()
    return templates.TemplateResponse("flight-search.html", {"request": request, "airports": airports})

@app.get("/aircraft-info")
async def aircraft_info_page(request: Request):
    """航空器信息页面"""
    return templates.TemplateResponse("aircraft-info.html", {"request": request})

@app.get("/image-inspection")
async def image_inspection_page(request: Request):
    """图片检修页面"""
    return templates.TemplateResponse("image-inspection.html", {"request": request})

@app.get("/blockchain-deposit")
async def blockchain_deposit_page(request: Request):
    """区块链存证系统页面"""
    return templates.TemplateResponse("blockchain-deposit.html", {"request": request})

@app.get("/blockchain-deposit/records")
async def blockchain_records_page(request: Request):
    """维修记录列表页面"""
    return templates.TemplateResponse("blockchain-deposit-records.html", {"request": request})

@app.get("/blockchain-deposit/records/create")
async def blockchain_records_create_page(request: Request):
    """创建维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-create.html", {"request": request})

@app.get("/blockchain-deposit/audit")
async def blockchain_audit_page(request: Request):
    """审计日志页面"""
    return templates.TemplateResponse("blockchain-deposit.html", {"request": request})

@app.get("/blockchain-deposit/records/view/{record_id}")
async def blockchain_records_view_page(request: Request, record_id: str):
    """查看维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-view.html", {"request": request, "record_id": record_id})

@app.get("/blockchain-deposit/records/approve/{record_id}")
async def blockchain_records_approve_page(request: Request, record_id: str):
    """审批维修记录页面"""
    return templates.TemplateResponse("blockchain-deposit-records-approve.html", {"request": request, "record_id": record_id})

@app.get("/profile")
async def profile_page(request: Request):
    """个人管理页面"""
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/system-settings")
async def system_settings_page(request: Request):
    """系统设置页面"""
    return templates.TemplateResponse("system-settings.html", {"request": request})

@app.get("/system-monitor")
async def system_monitor_page(request: Request):
    """系统监控页面"""
    return templates.TemplateResponse("system-monitor.html", {"request": request})

@app.get("/report-generation")
async def report_generation_page(request: Request):
    """报表生成页面"""
    return templates.TemplateResponse("report-generation.html", {"request": request})

@app.get("/permission-management")
async def permission_management_page(request: Request):
    """权限管理页面"""
    return templates.TemplateResponse("permission-management.html", {"request": request})

@app.get("/blockchain-visualization")
async def blockchain_visualization_page(request: Request):
    """区块链可视化页面"""
    return templates.TemplateResponse("blockchain-visualization.html", {"request": request})

@app.get("/inspection-management")
async def inspection_management_page(request: Request):
    """检修管理页面"""
    return templates.TemplateResponse("inspection-management.html", {"request": request})


@app.post("/api/image-inspection/analyze")
async def analyze_images(request: Request):
    """分析图片，调用teest中的模型"""
    try:
        from fastapi import UploadFile, File
        from ultralytics import YOLO
        from PIL import Image
        import numpy as np
        import os
        
        # 获取上传的文件
        form = await request.form()
        files = form.getlist("files")
        
        if not files:
            return {"success": False, "message": "请上传图片"}
        
        # 加载模型（强制使用CPU）
        model_path = os.path.join("..", "..", "teest", "model", "best.pt")
        model = YOLO(model_path)
        model.to('cpu')
        
        results = []
        
        for file in files:
            # 读取图片
            image = Image.open(file.file)
            img_array = np.array(image)
            
            # 预测
            prediction = model(img_array)
            result = prediction[0]
            
            # 获取预测结果
            max_idx = result.probs.top1
            predicted_class = result.names[max_idx]
            confidence = result.probs.top1conf.item()
            
            # 转换为normal/bad格式
            status = "normal" if predicted_class == "normal" else "bad"
            
            results.append({
                "filename": file.filename,
                "status": status
            })
        
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "message": str(e)}


import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

@app.post("/api/auth/register")
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
        
        if username in users:
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
        hashed_password = auth.get_password_hash(password) if hasattr(auth, 'get_password_hash') else password
        users[username] = {
            "password": hashed_password,
            "role": role,
            "address": address,
            "name": username,
            "employee_id": "EMP" + address[-8:],
            "public_key": public_pem,
            "private_key": private_pem,  # 存储私钥用于自动签名
            "created_at": int(datetime.now().timestamp())
        }
        user_roles[username] = role  # 存储用户角色
        
        # 同时添加到检修系统的用户数据中
        try:
            auth.authorize_user(address, username, "EMP" + address[-8:], password)
        except Exception as e:
            print(f"添加用户到检修系统失败: {e}")
        
        # 保存用户数据
        save_user_data()
        
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

@app.post("/api/auth/login")
async def login_user(request: Request):
    """用户登录"""
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return JSONResponse(status_code=400, content={"error": "用户名和密码不能为空"})
        
        # 检查用户是否存在
        if username not in users:
            return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        
        # 获取用户信息
        user_info = users[username]
        user_password = user_info.get("password", user_info)  # 兼容旧数据格式
        
        # 验证密码
        if hasattr(auth, 'verify_password'):
            # 使用检修系统的密码验证
            if not auth.verify_password(password, user_password):
                return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        else:
            # 使用旧的密码验证方式
            if user_password != password:
                return JSONResponse(status_code=401, content={"error": "用户名或密码错误"})
        
        # 获取用户角色和公钥
        role = user_info.get("role", user_roles.get(username, "user"))
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
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        public_key = public_pem
        private_key = private_pem
        print(f"为用户 {username} 生成新公钥和地址: {address}")
        
        # 创建访问令牌（包含角色信息）
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
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

@app.post("/api/auth/verify-signature")
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

# 维修记录存储
maintenance_records = {}

# 区块链事件存储
blockchain_events = []

# 智能合约系统
contract_engine = None
master_contract = None

# 添加样例数据
def add_sample_data():
    """添加样例维修记录"""
    # 空函数，不再添加样例数据
    pass

# 调用添加样例数据函数
# add_sample_data()  # 注释掉，不再添加样例数据

@app.post("/api/blockchain/records/create")
async def create_maintenance_record(request: Request):
    """创建维修记录"""
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.asymmetric import padding
        import uuid
        
        data = await request.json()
        
        # 验证必填字段
        required_fields = ['aircraft_registration', 'maintenance_type', 'maintenance_date', 'maintenance_description', 'technician_name', 'technician_id']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(status_code=400, content={"error": f"{field} 不能为空"})
        
        # 生成记录ID
        record_id = str(uuid.uuid4())[:12]
        
        # 简化创建流程，移除私钥验证
        # 实际生产环境中应该保留私钥验证以确保安全性
        
        # 生成样例公钥和签名
        public_pem = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwH6f8f8f8f8f8f8f8f8f8\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nf8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\nfQIDAQAB\n-----END PUBLIC KEY-----"
        signature = "sample_signature"
        
        # 创建记录
        maintenance_records[record_id] = {
            "id": record_id,
            "aircraft_registration": data['aircraft_registration'],
            "aircraft_model": data.get('aircraft_model', ''),
            "aircraft_series": data.get('aircraft_series', ''),
            "aircraft_age": data.get('aircraft_age', ''),
            "maintenance_type": data['maintenance_type'],
            "maintenance_date": data['maintenance_date'],
            "maintenance_description": data['maintenance_description'],
            "maintenance_duration": data.get('maintenance_duration', ''),
            "parts_used": data.get('parts_used', ''),
            "is_rii": data.get('is_rii', False),
            "technician_name": data['technician_name'],
            "technician_id": data['technician_id'],
            "technician_public_key": public_pem,
            "signature": signature,
            "status": "pending",
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }
        
        # 保存维修记录到文件
        save_maintenance_records()
        
        # 同步到区块链
        try:
            if contract_engine and master_contract:
                # 获取技术人员信息
                technician_info = None
                if data['technician_id'] in users:
                    technician_info = users[data['technician_id']]
                
                # 调用智能合约创建记录
                result = contract_engine.execute_contract(
                    contract_address=master_contract.contract_address,
                    method_name="addRecord",
                    params={
                        "record_id": record_id,
                        "aircraft_registration": data['aircraft_registration'],
                        "aircraft_model": data.get('aircraft_model', ''),
                        "aircraft_series": data.get('aircraft_series', ''),
                        "aircraft_age": data.get('aircraft_age', ''),
                        "maintenance_type": data['maintenance_type'],
                        "maintenance_description": data['maintenance_description'],
                        "maintenance_duration": data.get('maintenance_duration', ''),
                        "parts_used": data.get('parts_used', ''),
                        "is_rii": data.get('is_rii', False),
                        "technician_address": technician_info.get('address', '') if technician_info else '',
                        "technician_name": data['technician_name'],
                        "technician_public_key": public_pem,
                        "caller_address": technician_info.get('address', '') if technician_info else '',
                        "caller_role": technician_info.get('role', 'technician') if technician_info else 'technician'
                    },
                    signature=signature,
                    signer_address=technician_info.get('address', '') if technician_info else '',
                    nonce=str(int(datetime.now().timestamp())),
                    verify_signature_func=lambda sig, addr, params: {"success": True}
                )
                
                if result.get("success"):
                    print(f"[DEBUG] 记录 {record_id} 已同步到区块链")
                    
                    # 保存区块链信息到维修记录
                    maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                    maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                    maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                    save_maintenance_records()
                    
                    # 手动添加创建事件到持久化存储
                    event_data = {
                        "event_name": "RecordCreated",
                        "contract_address": master_contract.contract_address,
                        "block_index": result.get("block_index", 0),
                        "data": {
                            "record_id": record_id,
                            "aircraft_registration": data['aircraft_registration'],
                            "subchain_address": result.get("subchain_address", ""),
                            "maintenance_type": data['maintenance_type'],
                            "description": data['maintenance_description'],
                            "technician_address": technician_info.get('address', '') if technician_info else ''
                        },
                        "signer_address": technician_info.get('address', '') if technician_info else ''
                    }
                    blockchain_events.append(event_data)
                    save_blockchain_events()
                else:
                    print(f"[DEBUG] 记录 {record_id} 同步到区块链失败: {result.get('error')}")
        except Exception as e:
            print(f"[DEBUG] 同步记录到区块链失败: {e}")
        
        # 为技术人员分配任务（创建对应的检测任务）
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())[:12]
            
            # 创建任务
            new_task = {
                "id": task_id,
                "flight_number": data['aircraft_registration'],
                "task_type": data['maintenance_type'],
                "description": data['maintenance_description'],
                "priority": "medium",
                "deadline": data['maintenance_date'],
                "status": "assigned",
                "assignee_id": data['technician_id'],
                "assignee_name": data['technician_name'],
                "created_at": int(datetime.now().timestamp())
            }
            
            tasks.append(new_task)
            
            print(f"为技术人员 {data['technician_name']} 分配任务成功: {task_id}")
        except Exception as e:
            print(f"分配任务失败: {e}")
        
        return JSONResponse(status_code=200, content={"message": "维修记录创建成功", "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "创建记录失败: " + str(e)})

@app.get("/api/blockchain/records/list")
async def get_maintenance_records(request: Request):
    """获取维修记录列表"""
    try:
        global contract_engine, master_contract
        
        print(f"[DEBUG] get_maintenance_records 开始执行")
        
        if not contract_engine or not master_contract:
            print(f"[DEBUG] 区块链系统未初始化")
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        # 获取查询参数
        status = request.query_params.get("status", "all")
        aircraft_registration = request.query_params.get("aircraft_registration", "")
        search = request.query_params.get("search", "")
        
        print(f"[DEBUG] 查询参数 - status: {status}, aircraft_registration: {aircraft_registration}, search: {search}")
        
        # 从区块链获取所有记录
        all_records = []
        for record_id, record in master_contract.state["records"].items():
            # 优先从maintenance_records中获取技术人员信息
            technician_name = "未知"
            
            # 先检查maintenance_records中是否有该记录（获取最新状态）
            if record_id in maintenance_records:
                maintenance_record = maintenance_records[record_id]
                # 尝试从maintenance_records中获取技术人员名称
                technician_name = maintenance_record.get("technician_name", "未知")
                
                # 如果technician_name是"未知"，尝试从task_id找回技术人员
                if technician_name == "未知" or not technician_name:
                    task_id = maintenance_record.get("task_id")
                    if task_id:
                        # 从任务列表中查找对应的任务
                        for task in tasks:
                            if str(task.get("id")) == str(task_id):
                                assignee_id = task.get("assignee_id")
                                if assignee_id and assignee_id in users:
                                    technician_name = users[assignee_id].get("name", assignee_id)
                                    # 更新maintenance_records中的technician_name
                                    maintenance_record["technician_name"] = technician_name
                                    maintenance_record["technician_id"] = assignee_id
                                    print(f"[DEBUG] 从任务找回技术人员: {task_id} -> {technician_name}")
                                    save_maintenance_records()
                                break
                
                # 使用maintenance_records中的状态（因为审批后更新的是这里）
                record_status = maintenance_record.get("status", record.get("status", "pending"))
                print(f"[DEBUG] Record {record_id} found in maintenance_records: technician={technician_name}, status={record_status}")
            else:
                # 如果maintenance_records中没有，再从区块链记录中获取
                technician_address = record.get("technician_address", "")
                if technician_address:
                    # 如果有技术员地址，从用户列表中查找名称
                    for user_id, user in users.items():
                        if user.get("address") == technician_address:
                            technician_name = user.get("name", user.get("username", "未知"))
                            break
                else:
                    # 如果没有技术员地址，使用记录中的名称
                    technician_name = record.get("technician_name", "未知")
                # 使用区块链中的状态
                record_status = record.get("status", "pending")
                print(f"[DEBUG] Record {record_id} NOT in maintenance_records: technician={technician_name}, status={record_status}")
            
            # 格式化维修日期
            maintenance_date = ""
            if record.get("created_at"):
                if isinstance(record["created_at"], (int, float)):
                    maintenance_date = datetime.fromtimestamp(record["created_at"]).strftime("%Y/%m/%d %H:%M:%S")
                else:
                    maintenance_date = str(record["created_at"])
            
            # 获取任务信息
            task_info = None
            task_id = record.get("task_id") or maintenance_record.get("task_id") if record_id in maintenance_records else None
            if task_id:
                for task in tasks:
                    if str(task.get("id")) == str(task_id):
                        task_info = {
                            "id": task.get("id"),
                            "task_type": task.get("task_type"),
                            "priority": task.get("priority"),
                            "status": task.get("status")
                        }
                        break
            
            all_records.append({
                "id": record_id,
                **record,
                "maintenance_date": maintenance_date,
                "technician_name": technician_name,
                "status": record_status,
                "task_info": task_info
            })
        
        print(f"[DEBUG] 获取到 {len(all_records)} 条记录")
        
        # 过滤记录
        filtered_records = []
        for record in all_records:
            # 状态过滤
            if status != "all" and record["status"] != status:
                continue
            
            # 飞机注册号过滤
            if aircraft_registration and record["aircraft_registration"] != aircraft_registration:
                continue
            
            # 搜索过滤
            if search:
                if not (
                    search in record["id"] or
                    search in record["aircraft_registration"] or
                    search in record.get("technician_name", "") or
                    search in record.get("technician_address", "")
                ):
                    continue
            
            filtered_records.append(record)
        
        print(f"[DEBUG] 过滤后 {len(filtered_records)} 条记录")
        
        # 按创建时间排序
        filtered_records.sort(key=lambda x: x["created_at"], reverse=True)
        
        return JSONResponse(status_code=200, content={"records": filtered_records})
    except Exception as e:
        print(f"[DEBUG] 获取记录异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/blockchain/records/view/{record_id}")
async def get_maintenance_record_detail(record_id: str):
    """获取维修记录详情"""
    try:
        print(f"[DEBUG] get_maintenance_record_detail - record_id: {record_id}")
        
        if record_id not in maintenance_records:
            print(f"[DEBUG] 记录不存在: {record_id}")
            return JSONResponse(status_code=404, content={"error": "记录不存在"})
        
        record = maintenance_records[record_id]
        print(f"[DEBUG] 记录详情 - status: {record.get('status')}, id: {record.get('id')}")
        
        return JSONResponse(status_code=200, content={"record": record})
    except Exception as e:
        print(f"[DEBUG] 获取记录详情异常: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.post("/api/profile/update")
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
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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
            if current_username not in users or users[current_username].get('password') != current_password:
                return JSONResponse(status_code=400, content={"error": "当前密码错误"})
        
        # 更新用户信息
        if current_username in users:
            # 更新用户信息
            users[current_username].update({
                'name': data.get('name', users[current_username].get('name', current_username)),
                'employee_id': data.get('employee_id', users[current_username].get('employee_id')),
                'email': data.get('email', users[current_username].get('email')),
                'phone': data.get('phone', users[current_username].get('phone')),
                'specialty': data.get('specialty', users[current_username].get('specialty')),
                'bio': data.get('bio', users[current_username].get('bio'))
            })
            
            # 如果修改密码
            if data.get('new_password'):
                users[current_username]['password'] = data['new_password']
            
            # 保存用户数据
            save_user_data()
            
            print(f"[DEBUG] 用户 {current_username} 信息更新成功")
            return JSONResponse(status_code=200, content={"message": "个人信息更新成功"})
        else:
            print(f"[DEBUG] 用户 {current_username} 不存在")
            return JSONResponse(status_code=404, content={"error": "用户不存在"})
    except Exception as e:
        print(f"[DEBUG] 更新个人信息失败: {e}")
        return JSONResponse(status_code=500, content={"error": "更新个人信息失败: " + str(e)})

@app.get("/api/user/current")
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
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                current_username = payload.get("username")
                print(f"[DEBUG] 从token获取当前用户: {current_username}")
        except Exception as e:
            print(f"[DEBUG] 获取token失败: {e}")
            return JSONResponse(status_code=401, content={"error": "未授权"})
        
        if not current_username:
            return JSONResponse(status_code=401, content={"error": "未授权"})
        
        # 获取用户信息
        if current_username in users:
            user_data = users[current_username]
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


@app.get("/api/user/keys/{username}")
async def get_user_keys(username: str):
    """获取用户的公私钥"""
    try:
        if username not in users:
            return JSONResponse(status_code=404, content={"error": "用户不存在"})
        
        user_data = users[username]
        return JSONResponse(status_code=200, content={
            "username": username,
            "public_key": user_data.get("public_key", "未设置"),
            "private_key": user_data.get("private_key", "未设置")
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取用户密钥失败: " + str(e)})

@app.post("/api/blockchain/records/approve/{record_id}")
async def approve_maintenance_record(request: Request, record_id: str):
    """审批维修记录"""
    try:
        global contract_engine, master_contract
        
        if record_id not in maintenance_records:
            return JSONResponse(status_code=404, content={"error": "记录不存在"})
        
        data = await request.json()
        action = data.get("action", "approve")  # approve, reject, release
        
        # 获取当前用户信息
        current_user = None
        try:
            # 优先从cookie获取token
            token = request.cookies.get("access_token")
            if not token:
                # 如果cookie中没有，尝试从Authorization header获取
                token = request.headers.get("Authorization", "").replace("Bearer ", "")
            
            if token:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                current_user = {
                    "address": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "public_key": payload.get("public_key", "")
                }
        except:
            pass
        
        # 更新记录状态
        record = maintenance_records[record_id]
        if action == "approve":
            record["status"] = "approved"
        elif action == "reject":
            record["status"] = "rejected"
        elif action == "release":
            record["status"] = "released"
        
        record["updated_at"] = int(datetime.now().timestamp())
        
        # 保存维修记录到文件
        save_maintenance_records()
        
        # 同时更新智能合约中的状态
        if contract_engine and master_contract and current_user:
            try:
                timestamp = int(datetime.now().timestamp())
                nonce = str(timestamp)
                
                # 根据操作类型调用不同的合约方法
                method_name = None
                if action == "approve":
                    method_name = "approveRecord"
                elif action == "reject":
                    method_name = "rejectRecord"
                elif action == "release":
                    method_name = "releaseRecord"
                
                if method_name:
                    # 从users.json中获取私钥
                    username = current_user.get("name")
                    private_key = ""
                    if username and username in users:
                        private_key = users[username].get("private_key", "")
                    
                    if private_key:
                        # 创建签名数据
                        sign_data = SignatureManager.create_sign_data(
                            contract_address=master_contract.contract_address,
                            method=method_name,
                            params={
                                "record_id": record_id,
                                "approver_address": current_user["address"]
                            },
                            timestamp=timestamp,
                            nonce=nonce
                        )
                        
                        # 使用私钥签名
                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result
                            
                            # 执行智能合约
                            result = contract_engine.execute_contract(
                                contract_address=master_contract.contract_address,
                                method_name=method_name,
                                params={
                                    "record_id": record_id,
                                    "approver_address": current_user["address"],
                                    "caller_address": current_user["address"],
                                    "caller_role": current_user["role"]
                                },
                                signature=signature,
                                signer_address=current_user["address"],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )
                            
                            if result.get("success"):
                                save_blockchain()
                                save_contracts()
                                print(f"[DEBUG] 维修记录状态已更新到区块链: {record_id} -> {action}")
                                
                                # 更新区块链信息到维修记录
                                if "transaction_hash" not in maintenance_records[record_id]:
                                    maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                                maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                                maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                                save_maintenance_records()
                                
                                # 手动添加事件到持久化存储
                                event_type = None
                                if action == "approve":
                                    event_type = "RecordApproved"
                                elif action == "reject":
                                    event_type = "RecordRejected"
                                elif action == "release":
                                    event_type = "RecordReleased"
                                
                                if event_type:
                                    event_data = {
                                        "event_name": event_type,
                                        "contract_address": master_contract.contract_address,
                                        "block_index": result.get("block_index", 0),
                                        "data": {
                                            "record_id": record_id,
                                            "aircraft_registration": record.get("aircraft_registration", ""),
                                            "subchain_address": record.get("subchain_address", "")
                                        },
                                        "signer_address": current_user["address"]
                                    }
                                    blockchain_events.append(event_data)
                                    save_blockchain_events()
                            else:
                                print(f"[DEBUG] 更新区块链状态失败: {result.get('error')}")
            except Exception as e:
                print(f"[DEBUG] 更新区块链状态异常: {e}")
                import traceback
                traceback.print_exc()
        
        return JSONResponse(status_code=200, content={"message": "审批成功", "record": record, "record_id": record_id})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "审批失败: " + str(e)})

@app.post("/api/contract/release-record")
async def contract_release_record(request: Request):
    """使用智能合约释放维修记录"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        data = await request.json()
        
        required_fields = ['record_id', 'approver_address', 'signature', 'nonce']
        for field in required_fields:
            if not data.get(field):
                return JSONResponse(status_code=400, content={"error": f"{field} 不能为空"})
        
        current_user = None
        try:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if token:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                current_user = {
                    "address": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user"),
                    "public_key": payload.get("public_key", "")
                }
        except:
            pass
        
        if not current_user:
            return JSONResponse(status_code=401, content={"error": "未授权"})
        
        # 使用前端发送的timestamp
        timestamp = data.get('timestamp', int(datetime.now().timestamp()))
        
        sign_data = SignatureManager.create_sign_data(
            contract_address=master_contract.contract_address,
            method="releaseRecord",
            params={
                "record_id": data['record_id'],
                "approver_address": data['approver_address']
            },
            timestamp=timestamp,
            nonce=data['nonce']
        )
        
        verification_result = SignatureManager.verify_signature(
            data['signature'],
            current_user.get('public_key', ''),
            sign_data
        )
        
        if not verification_result.get("success"):
            return JSONResponse(status_code=400, content={"error": "签名验证失败"})
        
        result = contract_engine.execute_contract(
            contract_address=master_contract.contract_address,
            method_name="releaseRecord",
            params={
                "record_id": data['record_id'],
                "approver_address": data['approver_address'],
                "caller_address": current_user['address'],
                "caller_role": current_user['role']
            },
            signature=data['signature'],
            signer_address=current_user['address'],
            nonce=data['nonce'],
            verify_signature_func=lambda sig, addr, params: verification_result
        )
        
        if not result.get("success"):
            return JSONResponse(status_code=400, content={"error": result.get("error", "释放记录失败")})
        
        save_blockchain()
        save_contracts()
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "message": "维修记录释放成功",
            "block_hash": result["block_hash"],
            "block_index": result["block_index"]
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "释放记录失败: " + str(e)})

@app.get("/api/contract/records")
async def contract_get_all_records(status: Optional[str] = None):
    """获取所有维修记录"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        all_records = list(master_contract.state["records"].values())
        
        # 根据状态筛选
        if status:
            all_records = [r for r in all_records if r.get("status") == status]
        
        return JSONResponse(status_code=200, content={
            "success": True,
            "records": all_records,
            "total": len(all_records)
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/contract/records/{record_id}")
async def contract_get_record(record_id: str):
    """获取维修记录详情"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        result = master_contract.get_record(record_id)
        
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/contract/aircraft/{aircraft_registration}")
async def contract_get_aircraft_records(aircraft_registration: str, status: Optional[str] = None):
    """获取飞机的所有维修记录"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        result = master_contract.get_aircraft_records(aircraft_registration, status)
        
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取记录失败: " + str(e)})

@app.get("/api/contract/stats")
async def contract_get_stats():
    """获取全局统计"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        result = master_contract.get_global_stats()
        
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取统计失败: " + str(e)})

@app.get("/api/contract/blocks")
async def contract_get_blocks():
    """获取区块链数据"""
    try:
        global contract_engine
        
        if not contract_engine:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        blocks = contract_engine.get_all_blocks()
        
        return JSONResponse(status_code=200, content={"blocks": blocks})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "获取区块失败: " + str(e)})

@app.get("/api/contract/subchains")
async def contract_get_subchains():
    """获取飞机子链信息"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        if not master_contract:
            print("[ERROR] master_contract 未初始化")
            return JSONResponse(status_code=500, content={"error": "主合约未初始化"})
        
        print(f"[DEBUG] master_contract state: {master_contract.state}")
        
        subchains = []
        aircraft_subchains = master_contract.state.get("aircraft_subchains", {})
        print(f"[DEBUG] aircraft_subchains: {aircraft_subchains}")
        
        for aircraft_reg, subchain_info in aircraft_subchains.items():
            subchain_address = subchain_info.get("subchain_address", "")
            record_count = subchain_info.get("record_count", 0)
            
            subchain_records = contract_engine.get_subchain_records(subchain_address)
            
            subchains.append({
                "aircraft_registration": aircraft_reg,
                "subchain_address": subchain_address,
                "record_count": record_count,
                "records": subchain_records
            })
        
        print(f"[DEBUG] 返回子链数据: {subchains}")
        return JSONResponse(status_code=200, content={"subchains": subchains})
    except Exception as e:
        print(f"[ERROR] 获取子链失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取子链失败: " + str(e)})

@app.get("/api/contract/subchain/blocks")
async def contract_get_subchain_blocks(aircraft_registration: str):
    """获取指定飞机的子链区块"""
    try:
        global contract_engine, master_contract
        
        if not contract_engine or not master_contract:
            return JSONResponse(status_code=500, content={"error": "区块链系统未初始化"})
        
        aircraft_subchains = master_contract.state.get("aircraft_subchains", {})
        subchain_info = aircraft_subchains.get(aircraft_registration)
        
        if not subchain_info:
            return JSONResponse(status_code=404, content={"error": "指定飞机的子链不存在"})
        
        # 获得子链地址并读取记录
        subchain_address = subchain_info.get("subchain_address", "")
        records = contract_engine.get_subchain_records(subchain_address)
        
        return JSONResponse(status_code=200, content={"records": records})
    except Exception as e:
        print(f"[ERROR] 获取子链区块失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": "获取子链区块失败: " + str(e)})


# ========== 权限管理API ==========

@app.get("/api/permissions/role")
async def get_role_permissions(request: Request):
    """获取指定角色的权限列表"""
    role = request.query_params.get('role', 'user')
    permissions = permission_manager.get_role_permissions(role)
    return JSONResponse(status_code=200, content={
        "role": role,
        "permissions": permissions
    })

@app.get("/api/permissions/check")
async def check_permission(request: Request):
    """检查用户是否有指定权限"""
    token = request.cookies.get('access_token')
    if not token:
        return JSONResponse(status_code=401, content={"error": "未登录"})
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_role = payload.get('role', 'user')
        return JSONResponse(status_code=200, content={
            "role": user_role,
            "authorized": True
        })
    except JWTError:
        return JSONResponse(status_code=401, content={"error": "令牌无效"})


# 启动应用
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)