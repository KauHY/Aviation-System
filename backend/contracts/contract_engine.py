import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_contract import BaseContract
from .event_system import EventSystem
from .merkle_tree import MerkleTree
from .state_root import StateRoot


class ContractEngine:
    def __init__(self):
        self.contracts: Dict[str, BaseContract] = {}
        self.blocks: List[Dict[str, Any]] = []
        self.used_nonces: set = set()
        self.event_system = EventSystem()
        self.latest_block_hash = "0x0000000000000000000000000000000000000000000000000000000000000000"
        
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_block = {
            "index": 0,
            "hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "previous_hash": "0x0000000000000000000000000000000000000000000000000000000000000",
            "timestamp": int(datetime.now().timestamp()),
            "merkle_root": "0",
            "contract_address": "",
            "method": "",
            "params": {},
            "signature": "",
            "state_root": "0",
            "signer_address": "",
            "nonce": "",
            "events": []
        }
        self.blocks.append(genesis_block)
        self.latest_block_hash = genesis_block["hash"]

    def register_contract(self, contract: BaseContract):
        self.contracts[contract.contract_address] = contract

    def get_contract(self, contract_address: str) -> Optional[BaseContract]:
        return self.contracts.get(contract_address)

    def get_all_contracts(self) -> Dict[str, BaseContract]:
        return self.contracts.copy()

    def execute_contract(self, contract_address: str, method_name: str, 
                        params: Dict[str, Any], signature: str, 
                        signer_address: str, nonce: str, 
                        verify_signature_func: callable) -> Dict[str, Any]:
        contract = self.get_contract(contract_address)
        if not contract:
            return {"success": False, "error": "合约不存在"}

        if nonce in self.used_nonces:
            return {"success": False, "error": "Nonce已被使用"}
        
        methods = contract.get_methods()
        if method_name not in methods:
            return {"success": False, "error": "方法不存在"}

        verification_result = verify_signature_func(signature, signer_address, params)
        if not verification_result.get("success", False):
            return {"success": False, "error": "签名验证失败"}

        self.used_nonces.add(nonce)

        method = methods[method_name]
        result = method(**params)
        
        print(f"[DEBUG] 合约方法执行结果: {result}")
        print(f"[DEBUG] 合约方法执行结果类型: {type(result)}")
        print(f"[DEBUG] 合约方法执行结果是否包含success: {'success' in result if isinstance(result, dict) else 'N/A'}")
        print(f"[DEBUG] 合约方法执行结果是否包含result: {'result' in result if isinstance(result, dict) else 'N/A'}")
        print(f"[DEBUG] 合约方法执行结果是否包含record_id: {'record_id' in result if isinstance(result, dict) else 'N/A'}")
        
        contract.set_block_index(len(self.blocks))
        
        block = self._create_block(
            contract_address=contract_address,
            method=method_name,
            params=params,
            signature=signature,
            signer_address=signer_address,
            nonce=nonce,
            events=contract.get_events()
        )
        
        self.blocks.append(block)
        self.latest_block_hash = block["hash"]

        return {
            "success": True,
            "result": result,
            "block": block,
            "block_hash": block["hash"],
            "block_index": block["index"]
        }

    def _create_block(self, contract_address: str, method: str, 
                     params: Dict[str, Any], signature: str, 
                     signer_address: str, nonce: str, 
                     events: List[Dict[str, Any]]) -> Dict[str, Any]:
        previous_block = self.blocks[-1]
        block_index = len(self.blocks)
        
        transactions = [{
            "id": f"tx_{block_index}_{method}",
            "type": method,
            "params": params,
            "signature": signature,
            "signer_address": signer_address
        }]
        
        merkle_tree = MerkleTree(transactions)
        merkle_root = merkle_tree.get_root()
        
        contract = self.get_contract(contract_address)
        state_root = StateRoot.calculate(contract.get_state()) if contract else "0"
        
        block_data = {
            "index": block_index,
            "previous_hash": previous_block["hash"],
            "timestamp": int(datetime.now().timestamp()),
            "merkle_root": merkle_root,
            "contract_address": contract_address,
            "method": method,
            "params": params,
            "signature": signature,
            "state_root": state_root,
            "signer_address": signer_address,
            "nonce": nonce,
            "events": events,
            "transactions": transactions
        }
        
        block_hash = self._calculate_block_hash(block_data)
        block_data["hash"] = block_hash
        
        return block_data

    def _calculate_block_hash(self, block: Dict[str, Any]) -> str:
        data = (
            str(block["index"]) +
            block["previous_hash"] +
            str(block["timestamp"]) +
            block["merkle_root"] +
            block["contract_address"] +
            block["method"] +
            json.dumps(block["params"], sort_keys=True) +
            block["state_root"] +
            block["signer_address"] +
            block["nonce"]
        )
        return "0x" + hashlib.sha256(data.encode()).hexdigest()[:64]

    def get_block(self, block_index: int) -> Optional[Dict[str, Any]]:
        if 0 <= block_index < len(self.blocks):
            return self.blocks[block_index]
        return None

    def get_latest_block(self) -> Dict[str, Any]:
        return self.blocks[-1]

    def get_all_blocks(self) -> List[Dict[str, Any]]:
        return self.blocks.copy()

    def get_blockchain_length(self) -> int:
        return len(self.blocks)

    def verify_blockchain(self) -> bool:
        for i in range(1, len(self.blocks)):
            current_block = self.blocks[i]
            previous_block = self.blocks[i - 1]
            
            if current_block["previous_hash"] != previous_block["hash"]:
                return False
            
            calculated_hash = self._calculate_block_hash(current_block)
            if calculated_hash != current_block["hash"]:
                return False
        
        return True

    def get_contract_state(self, contract_address: str) -> Optional[Dict[str, Any]]:
        contract = self.get_contract(contract_address)
        if contract:
            return contract.get_state()
        return None

    def get_contract_events(self, contract_address: str) -> List[Dict[str, Any]]:
        contract = self.get_contract(contract_address)
        if contract:
            return contract.get_events()
        return []

    def get_all_events(self) -> List[Dict[str, Any]]:
        all_events = []
        for contract in self.contracts.values():
            all_events.extend(contract.get_events())
        return all_events

    def get_contract_blocks(self, contract_address: str) -> List[Dict[str, Any]]:
        contract = self.get_contract(contract_address)
        if contract:
            block_index = contract.get_block_index()
            if block_index > 0:
                return self.blocks[:block_index + 1]
        return []

    def get_subchain_records(self, contract_address: str) -> List[Dict[str, Any]]:
        contract = self.get_contract(contract_address)
        if contract and hasattr(contract, 'state'):
            records = contract.state.get('records', {})
            return list(records.values())
        return []

    def clear_nonces(self):
        self.used_nonces.clear()
