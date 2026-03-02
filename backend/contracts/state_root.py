import hashlib
import json
from typing import Dict, Any


class StateRoot:
    @staticmethod
    def calculate(state: Dict[str, Any]) -> str:
        if not state:
            return "0"
        
        sorted_state = dict(sorted(state.items()))
        state_json = json.dumps(sorted_state, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(state_json.encode()).hexdigest()

    @staticmethod
    def calculate_from_dict(state_dict: Dict[str, Any]) -> str:
        root_hashes = {}
        
        for key, value in state_dict.items():
            if isinstance(value, dict):
                root_hashes[key] = StateRoot.calculate(value)
            else:
                root_hashes[key] = hashlib.sha256(str(value).encode()).hexdigest()
        
        return StateRoot.calculate(root_hashes)

    @staticmethod
    def verify(state: Dict[str, Any], expected_root: str) -> bool:
        calculated_root = StateRoot.calculate(state)
        return calculated_root == expected_root
