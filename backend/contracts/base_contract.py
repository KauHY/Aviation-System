import hashlib
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from .event_system import EventSystem


class BaseContract(ABC):
    def __init__(self, contract_address: str, contract_name: str):
        self.contract_address = contract_address
        self.contract_name = contract_name
        self.state: Dict[str, Any] = {}
        self.event_system = EventSystem()
        self.created_at = int(datetime.now().timestamp())
        self.updated_at = int(datetime.now().timestamp())
        self.block_index = 0

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_methods(self) -> Dict[str, callable]:
        pass

    def update_state(self, new_state: Dict[str, Any]):
        self.state = new_state
        self.updated_at = int(datetime.now().timestamp())

    def set_block_index(self, block_index: int):
        self.block_index = block_index

    def get_block_index(self) -> int:
        return self.block_index

    def emit_event(self, event_name: str, data: Dict[str, Any], 
                   signer_address: str = ""):
        self.event_system.emit(
            event_name=event_name,
            contract_address=self.contract_address,
            block_index=self.block_index,
            data=data,
            signer_address=signer_address
        )

    def get_events(self) -> List[Dict[str, Any]]:
        return self.event_system.get_events_by_contract(self.contract_address)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_address": self.contract_address,
            "contract_name": self.contract_name,
            "state": self.state,
            "events": self.event_system.to_dict_list(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @staticmethod
    def generate_address(contract_name: str, params: Dict[str, Any] = None) -> str:
        data = contract_name
        if params:
            data += json.dumps(params, sort_keys=True)
        data += str(int(datetime.now().timestamp()))
        return "0x" + hashlib.sha256(data.encode()).hexdigest()[:40]
