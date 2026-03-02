import hashlib
from typing import List, Optional


class MerkleTree:
    def __init__(self, transactions: List[dict]):
        self.transactions = transactions
        self.leaves = [self._hash_transaction(tx) for tx in transactions]
        self.root = self._calculate_root() if self.leaves else "0"

    def _hash_transaction(self, transaction: dict) -> str:
        data = str(sorted(transaction.items()))
        return hashlib.sha256(data.encode()).hexdigest()

    def _calculate_root(self) -> str:
        if not self.leaves:
            return "0"
        
        current_level = self.leaves.copy()
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            
            current_level = next_level
        
        return current_level[0] if current_level else "0"

    def get_root(self) -> str:
        return self.root

    def get_proof(self, transaction_index: int) -> List[dict]:
        if transaction_index < 0 or transaction_index >= len(self.leaves):
            return []
        
        proof = []
        current_level = self.leaves.copy()
        index = transaction_index
        
        while len(current_level) > 1:
            if index % 2 == 0:
                sibling_index = index + 1
                sibling = current_level[sibling_index] if sibling_index < len(current_level) else current_level[index]
                proof.append({
                    "position": "right",
                    "hash": sibling
                })
            else:
                sibling_index = index - 1
                proof.append({
                    "position": "left",
                    "hash": current_level[sibling_index]
                })
            
            index = index // 2
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            
            current_level = next_level
        
        return proof

    @staticmethod
    def verify_proof(leaf_hash: str, proof: List[dict], root: str) -> bool:
        current_hash = leaf_hash
        
        for proof_element in proof:
            if proof_element["position"] == "left":
                combined = proof_element["hash"] + current_hash
            else:
                combined = current_hash + proof_element["hash"]
            
            current_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return current_hash == root
