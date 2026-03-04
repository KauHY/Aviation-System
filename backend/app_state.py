import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request, WebSocket, status
from jose import JWTError, jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from contracts.contract_engine import ContractEngine
from contracts.maintenance_record_master_contract import MaintenanceRecordMasterContract
from contracts.aircraft_subchain_contract import AircraftSubchainContract
from contracts.base_contract import BaseContract

# 检修系统配置
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class AuthService:
    def __init__(self):
        self.use_passlib = False
        self.pwd_context = None
        try:
            from passlib.context import CryptContext
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            self.use_passlib = True
        except Exception as e:
            print(f"Passlib导入失败，使用简单密码验证: {e}")

    def _find_user_by_address(self, address: str):
        for user_info in users.values():
            if user_info.get("address") == address:
                return user_info
        return None

    def get_user_by_address(self, address: str):
        return self._find_user_by_address(address)

    def authenticate(self, address: str, password: str):
        user = self._find_user_by_address(address)
        if not user:
            return None
        stored_password = user.get("password", "")
        if not self.verify_password(password, stored_password):
            return None
        return user

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        plain_password = (plain_password or "")[:72]
        if self.use_passlib and self.pwd_context:
            try:
                return self.pwd_context.verify(plain_password, hashed_password)
            except Exception as e:
                print(f"Passlib验证失败，使用简单密码验证: {e}")
                return plain_password == hashed_password
        return plain_password == hashed_password

    def get_password_hash(self, password: str) -> str:
        password = (password or "")[:72]
        if self.use_passlib and self.pwd_context:
            try:
                return self.pwd_context.hash(password)
            except Exception as e:
                print(f"Passlib哈希失败，使用原始密码: {e}")
                return password
        return password

    def authorize_user(self, address: str, name: str, employee_id: str, password: str) -> bool:
        existing = self._find_user_by_address(address)
        if existing:
            return False
        username = name or address[-8:]
        if username in users:
            username = f"{username}_{address[-6:]}"
        users[username] = {
            "password": self.get_password_hash(password),
            "role": "user",
            "address": address,
            "name": name or username,
            "employee_id": employee_id,
            "created_at": int(datetime.now().timestamp())
        }
        return True

    def revoke_user(self, address: str) -> bool:
        for username, user_info in list(users.items()):
            if user_info.get("address") == address:
                del users[username]
                return True
        return False

    def get_authorized_users(self) -> list:
        return list(users.values())


auth = AuthService()

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

async def get_current_user_from_token(request: Request):
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

# 维修记录存储
maintenance_records = {}

# 区块链事件存储
blockchain_events = []

# 智能合约系统
contract_engine = None
master_contract = None

# 检测人员数据
inspectors = []

# 检测任务数据
tasks = []

# 添加样例数据
def add_sample_data():
    """添加样例维修记录"""
    # 空函数，不再添加样例数据
    pass

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


def _normalize_tcg_username(base_name: str, address: str):
    base_name = (base_name or "").strip() or address[-8:]
    if base_name not in users:
        return base_name
    return f"{base_name}_tcg_{address[-6:]}"


def _map_tcg_role(user_info: dict, address: str):
    is_admin = bool(user_info.get("is_admin")) or address == "0x0000000000000000000000000000000000000001"
    is_authorized = bool(user_info.get("isAuthorized")) or bool(user_info.get("is_authorized"))
    if is_admin:
        return "admin"
    if is_authorized:
        return "technician"
    return "user"


def _map_tcg_status(status_value: str):
    if not status_value:
        return "pending"
    status_value = status_value.strip().lower()
    if status_value in ["released", "release"]:
        return "released"
    if status_value in ["approved", "approve"]:
        return "approved"
    if status_value in ["rejected", "reject"]:
        return "rejected"
    return "pending"


def merge_tcg_data(tcg_data_dir: Optional[str] = None):
    """合并 tcg 数据到主系统 JSON 文件"""
    if tcg_data_dir is None:
        tcg_data_dir = os.path.join(os.path.dirname(__file__), "tcg", "data")

    tcg_users_path = os.path.join(tcg_data_dir, "users.json")
    tcg_records_path = os.path.join(tcg_data_dir, "records.json")

    if not os.path.exists(tcg_users_path) and not os.path.exists(tcg_records_path):
        return {"users_merged": 0, "records_merged": 0, "reason": "tcg 数据不存在"}

    load_users()
    load_maintenance_records()

    address_index = {
        info.get("address"): username
        for username, info in users.items()
        if isinstance(info, dict) and info.get("address")
    }

    users_merged = 0
    records_merged = 0

    if os.path.exists(tcg_users_path):
        try:
            with open(tcg_users_path, "r", encoding="utf-8") as f:
                tcg_users = json.load(f) or {}
        except Exception as e:
            print(f"加载 tcg users 失败: {e}")
            tcg_users = {}

        for address, user_info in tcg_users.items():
            if not isinstance(user_info, dict):
                continue

            existing_username = address_index.get(address)
            if existing_username:
                existing_user = users.get(existing_username, {})
                if user_info.get("name") and not existing_user.get("name"):
                    existing_user["name"] = user_info.get("name")
                if user_info.get("employee_id") or user_info.get("empId"):
                    existing_user.setdefault("employee_id", user_info.get("employee_id") or user_info.get("empId"))
                if user_info.get("password") and not existing_user.get("password"):
                    existing_user["password"] = user_info.get("password")
                existing_user.setdefault("is_admin", bool(user_info.get("is_admin")))
                continue

            username = _normalize_tcg_username(user_info.get("name"), address)
            role = _map_tcg_role(user_info, address)
            password = user_info.get("password") or "123456"

            users[username] = {
                "password": password,
                "role": role,
                "address": address,
                "name": user_info.get("name", username),
                "employee_id": user_info.get("employee_id") or user_info.get("empId"),
                "is_admin": role == "admin"
            }
            address_index[address] = username
            users_merged += 1

    if os.path.exists(tcg_records_path):
        try:
            with open(tcg_records_path, "r", encoding="utf-8") as f:
                tcg_records = json.load(f) or {}
        except Exception as e:
            print(f"加载 tcg records 失败: {e}")
            tcg_records = {}

        for record_id, record in tcg_records.items():
            if not isinstance(record, dict):
                continue

            new_id = record_id
            if new_id in maintenance_records:
                new_id = f"{record_id}_tcg"
                if new_id in maintenance_records:
                    continue

            timestamp = record.get("timestamp") or 0
            maintenance_date = ""
            if isinstance(timestamp, (int, float)) and timestamp > 0:
                maintenance_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

            used_parts = record.get("usedParts", [])
            parts_used = ",".join([p.get("partNumber", "") for p in used_parts if isinstance(p, dict)])

            signatures = record.get("signatures", {}) or {}
            technician_name = signatures.get("performedByName") or signatures.get("releaseByName") or "未知"
            technician_id = signatures.get("performedById") or signatures.get("releaseById") or ""

            maintenance_records[new_id] = {
                "id": new_id,
                "aircraft_registration": record.get("aircraftRegNo", ""),
                "aircraft_model": record.get("aircraftType", ""),
                "aircraft_series": "",
                "aircraft_age": "",
                "maintenance_type": record.get("workType", ""),
                "maintenance_date": maintenance_date,
                "maintenance_description": record.get("workDescription", ""),
                "maintenance_duration": "",
                "parts_used": parts_used,
                "is_rii": bool(record.get("isRII")),
                "technician_name": technician_name,
                "technician_id": technician_id,
                "technician_public_key": "",
                "signature": "",
                "status": _map_tcg_status(record.get("status")),
                "created_at": int(timestamp) if timestamp else int(datetime.now().timestamp()),
                "updated_at": int(timestamp) if timestamp else int(datetime.now().timestamp()),
                "source": "tcg",
                "tcg_record_id": record_id,
                "tcg_record": record
            }
            records_merged += 1

    if users_merged or records_merged:
        save_user_data()
        save_maintenance_records()

    return {"users_merged": users_merged, "records_merged": records_merged}

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

# 加载机场数据函数
def load_airport_data():
    try:
        # 获取当前文件所在目录的上两级目录（项目根目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        # 修正路径逻辑：__file__是backend/main.py, dirname是backend, twice is 视频系统, thrice is BlockChain
        # Actually: os.path.dirname(__file__) -> backend
        # os.path.dirname(backend) -> 视频系统
        # os.path.dirname(视频系统) -> BlockChain

        backend_dir = os.path.dirname(os.path.abspath(__file__))

        # 尝试几种可能的路径
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(backend_dir)), "机场信息.csv"),
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

        airports_list = []
        import csv
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row.get("三字码 (IATA)", "").strip()
                # 只保留有有效三字码的机场
                if code and len(code) == 3 and code.isalpha():
                    airports_list.append({
                        "name": row.get("机场名称", "").strip(),
                        "city": row.get("城市", "").strip(),
                        "province": row.get("省份/地区", "").strip(),
                        "code": code
                    })
        return airports_list
    except Exception as e:
        print(f"读取机场信息出错: {e}")
        return []

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
                    status_value = record.get("status", "pending")
                    if status_value == "pending":
                        master_contract.state["stats"]["pending_count"] += 1
                    elif status_value == "approved":
                        master_contract.state["stats"]["approved_count"] += 1
                    elif status_value == "released":
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
                            if status_value == "pending":
                                subchain_contract.state["stats"]["pending_count"] += 1
                            elif status_value == "approved":
                                subchain_contract.state["stats"]["approved_count"] += 1
                            elif status_value == "released":
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
            status_value = record.get('status', 'unknown')
            report_data["summary"]["by_type"][mtype] = report_data["summary"]["by_type"].get(mtype, 0) + 1
            report_data["summary"]["by_status"][status_value] = report_data["summary"]["by_status"].get(status_value, 0) + 1

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
            status_value = flight.get('status', 'unknown')
            airline = flight.get('airline', 'unknown')
            report_data["summary"]["by_status"][status_value] = report_data["summary"]["by_status"].get(status_value, 0) + 1
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
            status_value = flight.get('status', 'unknown')
            report_data["summary"]["flights"]["by_status"][status_value] = report_data["summary"]["flights"]["by_status"].get(status_value, 0) + 1

        for record in maintenance_records.values():
            mtype = record.get('maintenance_type', 'unknown')
            status_value = record.get('status', 'unknown')
            report_data["summary"]["maintenance_records"]["by_type"][mtype] = report_data["summary"]["maintenance_records"]["by_type"].get(mtype, 0) + 1
            report_data["summary"]["maintenance_records"]["by_status"][status_value] = report_data["summary"]["maintenance_records"]["by_status"].get(status_value, 0) + 1

    return report_data
