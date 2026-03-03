import json
import os
from typing import List, Optional, Dict
from datetime import datetime

from app.models.maintenance import MaintenanceRecord, RecordStatus
from app.models.user import User

class StorageService:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
        self.records_file = os.path.join(self.data_dir, "records.json")
        self.users_file = os.path.join(self.data_dir, "users.json")
        self.indices_file = os.path.join(self.data_dir, "indices.json")
        
        # 初始化存储文件
        self._init_files()
    
    def _init_files(self):
        """初始化存储文件"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 初始化记录文件
        if not os.path.exists(self.records_file):
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        # 初始化用户文件
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        # 初始化索引文件
        if not os.path.exists(self.indices_file):
            indices = {
                "aircraftRecords": {},  # 飞机注册号 -> 记录ID列表
                "jobCardRecords": {},   # 工卡号 -> 记录ID列表
                "mechanicRecords": {},  # 机械师工号 -> 记录ID列表
                "allRecordIds": []      # 所有记录ID列表
            }
            with open(self.indices_file, 'w', encoding='utf-8') as f:
                json.dump(indices, f, ensure_ascii=False, indent=2)
    
    def _load_records(self) -> Dict[str, Dict]:
        """加载所有记录"""
        with open(self.records_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_records(self, records: Dict[str, Dict]):
        """保存记录"""
        with open(self.records_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    
    def _load_users(self) -> Dict[str, Dict]:
        """加载所有用户"""
        with open(self.users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_users(self, users: Dict[str, Dict]):
        """保存用户"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def _load_indices(self) -> Dict:
        """加载索引"""
        with open(self.indices_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_indices(self, indices: Dict):
        """保存索引"""
        with open(self.indices_file, 'w', encoding='utf-8') as f:
            json.dump(indices, f, ensure_ascii=False, indent=2)
    
    # ================= 记录相关操作 =================
    
    def add_record(self, record: MaintenanceRecord) -> bool:
        """添加检修记录"""
        try:
            # 加载现有记录
            records = self._load_records()
            
            # 检查记录是否已存在
            if record.record_id in records:
                return False
            
            # 保存记录
            records[record.record_id] = record.to_dict()
            self._save_records(records)
            
            # 更新索引
            indices = self._load_indices()
            
            # 更新飞机记录索引
            if record.aircraft_reg_no not in indices["aircraftRecords"]:
                indices["aircraftRecords"][record.aircraft_reg_no] = []
            indices["aircraftRecords"][record.aircraft_reg_no].append(record.record_id)
            
            # 更新工卡号索引
            if record.job_card_no not in indices["jobCardRecords"]:
                indices["jobCardRecords"][record.job_card_no] = []
            indices["jobCardRecords"][record.job_card_no].append(record.record_id)
            
            # 更新机械师索引
            if record.signatures.performed_by_id:
                if record.signatures.performed_by_id not in indices["mechanicRecords"]:
                    indices["mechanicRecords"][record.signatures.performed_by_id] = []
                indices["mechanicRecords"][record.signatures.performed_by_id].append(record.record_id)
            
            # 更新所有记录ID列表
            indices["allRecordIds"].append(record.record_id)
            
            self._save_indices(indices)
            
            return True
        except Exception as e:
            print(f"添加记录失败: {e}")
            return False
    
    def get_record_by_id(self, record_id: str) -> Optional[Dict]:
        """根据记录ID获取记录"""
        records = self._load_records()
        if record_id in records:
            return records[record_id]
        return None
    
    def get_records_by_aircraft(self, aircraft_reg_no: str) -> List[Dict]:
        """根据飞机注册号获取记录"""
        records = self._load_records()
        result = []
        
        # 直接从记录中搜索，不依赖索引
        for record in records.values():
            if record.get('aircraftRegNo') == aircraft_reg_no:
                result.append(record)
        
        # 按时间戳倒序排序
        result.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return result
    
    def get_records_by_job_card(self, job_card_no: str) -> List[Dict]:
        """根据工卡号获取记录"""
        records = self._load_records()
        result = []
        
        # 直接从记录中搜索，不依赖索引
        for record in records.values():
            if record.get('jobCardNo') == job_card_no:
                result.append(record)
        
        return result
    
    def get_records_by_mechanic(self, mechanic_id: str) -> List[Dict]:
        """根据机械师工号获取记录"""
        records = self._load_records()
        result = []
        
        # 直接从记录中搜索，不依赖索引
        for record in records.values():
            signatures = record.get('signatures', {})
            if signatures.get('performedById') == mechanic_id:
                result.append(record)
        
        return result
    
    def get_all_records(self) -> List[Dict]:
        """获取所有记录"""
        records = self._load_records()
        return list(records.values())
    
    def sign_peer_check(self, record_id: str, user_address: str, user_name: str) -> bool:
        """互检签名"""
        try:
            records = self._load_records()
            if record_id not in records:
                return False
            
            record = records[record_id]
            record['signatures']['peerCheckedById'] = user_address
            record['signatures']['peerCheckedByName'] = user_name
            record['signatures']['peerCheckedAt'] = datetime.now().isoformat()
            
            self._save_records(records)
            return True
        except Exception as e:
            print(f"互检签名失败: {e}")
            return False
    
    def sign_rii(self, record_id: str, user_address: str, user_name: str) -> bool:
        """必检签名"""
        try:
            records = self._load_records()
            if record_id not in records:
                return False
            
            record = records[record_id]
            record['signatures']['inspectedById'] = user_address
            record['signatures']['inspectedByName'] = user_name
            record['signatures']['inspectedAt'] = datetime.now().isoformat()
            
            self._save_records(records)
            return True
        except Exception as e:
            print(f"必检签名失败: {e}")
            return False
    
    def sign_release(self, record_id: str, user_address: str, user_name: str) -> bool:
        """放行签名"""
        try:
            records = self._load_records()
            if record_id not in records:
                return False
            
            record = records[record_id]
            record['signatures']['releasedById'] = user_address
            record['signatures']['releasedByName'] = user_name
            record['signatures']['releasedAt'] = datetime.now().isoformat()
            record['status'] = 'Released'
            
            self._save_records(records)
            return True
        except Exception as e:
            print(f"放行签名失败: {e}")
            return False
    
    def get_record_count(self) -> int:
        """获取记录总数"""
        indices = self._load_indices()
        return len(indices["allRecordIds"])
    
    def update_record(self, record: MaintenanceRecord) -> bool:
        """更新记录"""
        try:
            records = self._load_records()
            if record.record_id not in records:
                return False
            
            records[record.record_id] = record.to_dict()
            self._save_records(records)
            return True
        except Exception as e:
            print(f"更新记录失败: {e}")
            return False
    
    # ================= 用户相关操作 =================
    
    def add_user(self, user: User) -> bool:
        """添加用户"""
        try:
            users = self._load_users()
            users[user.address] = user.to_dict()
            self._save_users(users)
            return True
        except Exception as e:
            print(f"添加用户失败: {e}")
            return False
    
    def get_user_by_address(self, address: str) -> Optional[User]:
        """根据地址获取用户"""
        users = self._load_users()
        if address in users:
            return User.from_dict(users[address])
        return None
    
    def get_all_users(self) -> List[User]:
        """获取所有用户"""
        users = self._load_users()
        return [User.from_dict(user_data) for user_data in users.values()]
    
    def update_user(self, user: User) -> bool:
        """更新用户"""
        try:
            users = self._load_users()
            if user.address not in users:
                return False
            
            users[user.address] = user.to_dict()
            self._save_users(users)
            return True
        except Exception as e:
            print(f"更新用户失败: {e}")
            return False
    
    def get_authorized_users(self) -> List[User]:
        """获取所有授权用户"""
        users = self._load_users()
        return [User.from_dict(user_data) for user_data in users.values() if user_data.get("isAuthorized", False)]

# 创建全局存储服务实例
storage_service = StorageService()