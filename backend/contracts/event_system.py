import json
from typing import List, Dict, Any
from datetime import datetime


class Event:
    def __init__(self, event_name: str, contract_address: str, block_index: int, 
                 data: Dict[str, Any], signer_address: str = ""):
        self.event_name = event_name
        self.contract_address = contract_address
        self.block_index = block_index
        self.timestamp = int(datetime.now().timestamp())
        self.data = data
        self.signer_address = signer_address

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_name": self.event_name,
            "contract_address": self.contract_address,
            "block_index": self.block_index,
            "timestamp": self.timestamp,
            "data": self.data,
            "signer_address": self.signer_address
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EventSystem:
    def __init__(self):
        self.events: List[Event] = []

    def emit(self, event_name: str, contract_address: str, block_index: int,
             data: Dict[str, Any], signer_address: str = "") -> Event:
        event = Event(event_name, contract_address, block_index, data, signer_address)
        self.events.append(event)
        return event

    def get_events_by_contract(self, contract_address: str) -> List[Event]:
        return [e for e in self.events if e.contract_address == contract_address]

    def get_events_by_name(self, event_name: str) -> List[Event]:
        return [e for e in self.events if e.event_name == event_name]

    def get_events_by_contract_and_name(self, contract_address: str, 
                                        event_name: str) -> List[Event]:
        return [e for e in self.events 
                if e.contract_address == contract_address and e.event_name == event_name]

    def get_events_by_block(self, block_index: int) -> List[Event]:
        return [e for e in self.events if e.block_index == block_index]

    def get_events_by_signer(self, signer_address: str) -> List[Event]:
        return [e for e in self.events if e.signer_address == signer_address]

    def get_all_events(self) -> List[Event]:
        return self.events.copy()

    def clear_events(self):
        self.events.clear()

    def to_dict_list(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.events]
