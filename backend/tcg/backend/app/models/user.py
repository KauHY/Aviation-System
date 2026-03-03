class User:
    def __init__(self, address: str, name: str, emp_id: str, is_authorized: bool = False):
        self.address = address
        self.name = name
        self.emp_id = emp_id
        self.is_authorized = is_authorized
    
    def to_dict(self):
        return {
            "address": self.address,
            "name": self.name,
            "empId": self.emp_id,
            "isAuthorized": self.is_authorized
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建用户实例"""
        return cls(
            address=data.get("address", ""),
            name=data.get("name", ""),
            emp_id=data.get("empId", ""),
            is_authorized=data.get("isAuthorized", False)
        )