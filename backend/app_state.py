from datetime import timedelta
from typing import Optional

from fastapi import Request

from state.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    USER_DATA_FILE,
    TASK_DATA_FILE,
    FLIGHT_DATA_FILE,
    MAINTENANCE_RECORDS_FILE,
    BLOCKCHAIN_EVENTS_FILE,
    BLOCKCHAIN_FILE,
    CONTRACTS_FILE
)
from state.services_registry import (
    user_service,
    task_service,
    flight_service,
    maintenance_record_service,
    blockchain_event_service,
    blockchain_storage_service,
    contracts_storage_service
)
from state.auth_service import AuthService
from state.token_utils import (
    create_access_token as _create_access_token,
    verify_token as _verify_token,
    get_current_user_from_token as _get_current_user_from_token
)
from state.connection_manager import ConnectionManager
from state.persistence import (
    load_users as _load_users,
    save_users as _save_users,
    load_tasks as _load_tasks,
    save_tasks as _save_tasks,
    load_maintenance_records as _load_maintenance_records,
    save_maintenance_records as _save_maintenance_records,
    load_blockchain_events as _load_blockchain_events,
    save_blockchain_events as _save_blockchain_events,
    load_flights as _load_flights,
    save_flights as _save_flights
)
from state.blockchain_ops import (
    initialize_blockchain as _initialize_blockchain,
    ensure_users_have_keys as _ensure_users_have_keys,
    migrate_maintenance_records_to_contract as _migrate_maintenance_records_to_contract,
    save_blockchain as _save_blockchain,
    save_contracts as _save_contracts
)
from state.system_metrics import (
    get_disk_usage as _get_disk_usage,
    get_memory_usage as _get_memory_usage,
    get_system_uptime as _get_system_uptime
)
from state.reporting import generate_report_data as _generate_report_data
from state.airports import load_airport_data as _load_airport_data
from state.tcg_merge import merge_tcg_data as _merge_tcg_data

# 房间管理
rooms = {}

# 用户管理
users = {}
user_roles = {}

# 模拟航班数据
flights = []

# 机场数据
airports = []

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


auth = AuthService(lambda: users)
manager = ConnectionManager()


def _replace_mapping(target: dict, new_data: dict) -> None:
    target.clear()
    target.update(new_data or {})


def _replace_list(target: list, new_items: list) -> None:
    target.clear()
    target.extend(new_items or [])


# 加载用户数据
try:
    loaded_users, loaded_roles = _load_users(user_service)
    _replace_mapping(users, loaded_users)
    _replace_mapping(user_roles, loaded_roles)
except Exception as e:
    print(f"加载用户数据失败: {e}")


# 检修系统工具函数
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    return _create_access_token(data, SECRET_KEY, ALGORITHM, expires_delta)


def verify_token(token: str):
    """验证令牌"""
    return _verify_token(token, SECRET_KEY, ALGORITHM)


async def get_current_user_from_token(request: Request):
    """获取当前用户"""
    return await _get_current_user_from_token(request, SECRET_KEY, ALGORITHM, auth, users)


# 保存用户数据
def save_user_data():
    try:
        _save_users(user_service, users, user_roles)
    except Exception as e:
        print(f"保存用户数据失败: {e}")


# 添加样例数据
def add_sample_data():
    """添加样例维修记录"""
    # 空函数，不再添加样例数据
    pass


# 从文件加载用户数据
def load_users():
    """从文件加载用户数据"""
    try:
        loaded_users, loaded_roles = _load_users(user_service)
        _replace_mapping(users, loaded_users)
        _replace_mapping(user_roles, loaded_roles)
        print(f"成功加载 {len(users)} 个用户")
        for i, (username, user_info) in enumerate(users.items()):
            if i < 3:
                print(f"[DEBUG] 用户 {username}: role={user_info.get('role', 'N/A')}, name={user_info.get('name', 'N/A')}")
    except Exception as e:
        print(f"加载用户数据失败: {e}")
        users.clear()
        user_roles.clear()


# 从文件加载任务数据
def load_tasks():
    """从文件加载任务数据"""
    try:
        loaded_tasks = _load_tasks(task_service)
        _replace_list(tasks, loaded_tasks)
        print(f"成功加载 {len(tasks)} 个任务")
    except Exception as e:
        print(f"加载任务数据失败: {e}")
        tasks.clear()


# 保存任务数据到文件
def save_tasks():
    """保存任务数据到文件"""
    try:
        _save_tasks(task_service, tasks)
        print(f"成功保存 {len(tasks)} 个任务")
    except Exception as e:
        print(f"保存任务数据失败: {e}")


# 加载维修记录数据
def load_maintenance_records():
    """从文件加载维修记录数据"""
    try:
        loaded_records = _load_maintenance_records(maintenance_record_service)
        _replace_mapping(maintenance_records, loaded_records)
        print(f"成功加载 {len(maintenance_records)} 个维修记录")
    except Exception as e:
        print(f"加载维修记录数据失败: {e}")
        maintenance_records.clear()


# 保存维修记录数据到文件
def save_maintenance_records():
    """保存维修记录数据到文件"""
    try:
        _save_maintenance_records(maintenance_record_service, maintenance_records)
        print(f"成功保存 {len(maintenance_records)} 个维修记录")
    except Exception as e:
        print(f"保存维修记录数据失败: {e}")


# 合并 tcg 数据到主系统 JSON 文件
def merge_tcg_data(tcg_data_dir: Optional[str] = None):
    return _merge_tcg_data(
        tcg_data_dir,
        users,
        maintenance_records,
        load_users,
        load_maintenance_records,
        save_user_data,
        save_maintenance_records
    )


# 加载区块链事件数据
def load_blockchain_events():
    """从文件加载区块链事件数据"""
    try:
        loaded_events = _load_blockchain_events(blockchain_event_service)
        _replace_list(blockchain_events, loaded_events)
        print(f"成功加载 {len(blockchain_events)} 个区块链事件")
    except Exception as e:
        print(f"[DEBUG] 加载区块链事件数据失败: {e}")


# 保存区块链事件数据到文件
def save_blockchain_events():
    """保存区块链事件数据到文件"""
    try:
        _save_blockchain_events(blockchain_event_service, blockchain_events)
        print(f"成功保存 {len(blockchain_events)} 个区块链事件")
    except Exception as e:
        print(f"保存区块链事件数据失败: {e}")


# 加载航班数据
def load_flights():
    """从文件加载航班数据"""
    try:
        loaded_flights = _load_flights(flight_service)
        _replace_list(flights, loaded_flights)
        print(f"成功加载 {len(flights)} 个航班")
    except Exception as e:
        print(f"加载航班数据失败: {e}")


# 保存航班数据到文件
def save_flights():
    """保存航班数据到文件"""
    try:
        _save_flights(flight_service, flights)
        print(f"成功保存 {len(flights)} 个航班")
    except Exception as e:
        print(f"保存航班数据失败: {e}")


# 加载机场数据函数
def load_airport_data():
    return _load_airport_data()


# 初始化区块链
def initialize_blockchain():
    """初始化区块链系统"""
    global contract_engine, master_contract

    contract_engine, master_contract = _initialize_blockchain(
        blockchain_storage_service,
        contracts_storage_service,
        maintenance_records,
        users
    )


# 确保用户有公钥
def ensure_users_have_keys():
    """为没有公钥或私钥的用户生成公私钥对"""
    try:
        _ensure_users_have_keys(users, user_roles, user_service)
    except Exception as e:
        print(f"确保用户有公私钥失败: {e}")


# 迁移维修记录到智能合约
def migrate_maintenance_records_to_contract():
    """将现有维修记录迁移到智能合约系统"""
    global contract_engine, master_contract

    if not contract_engine or not master_contract:
        return

    try:
        _migrate_maintenance_records_to_contract(
            contract_engine,
            master_contract,
            maintenance_records,
            users,
            blockchain_storage_service,
            contracts_storage_service
        )
    except Exception as e:
        print(f"迁移维修记录失败: {e}")


# 保存区块链数据到文件
def save_blockchain():
    """保存区块链数据到文件"""
    if not contract_engine:
        return

    try:
        _save_blockchain(contract_engine, blockchain_storage_service)
    except Exception as e:
        print(f"保存区块链数据失败: {e}")


# 保存合约数据到文件
def save_contracts():
    """保存合约数据到文件"""
    if not contract_engine:
        return

    try:
        _save_contracts(contract_engine, contracts_storage_service)
    except Exception as e:
        print(f"保存合约数据失败: {e}")


def get_disk_usage():
    """获取磁盘使用情况"""
    return _get_disk_usage()


def get_memory_usage():
    """获取内存使用情况"""
    return _get_memory_usage()


def get_system_uptime():
    """获取系统运行时间"""
    return _get_system_uptime()


async def generate_report_data(report_type, start_date, end_date, report_detail_type, filters):
    """生成报表数据"""
    return await _generate_report_data(
        report_type,
        start_date,
        end_date,
        report_detail_type,
        filters,
        maintenance_records,
        flights,
        contract_engine,
        users
    )
