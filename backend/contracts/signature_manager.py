import json
from typing import Dict, Any
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization


class SignatureManager:
    @staticmethod
    def sign_data(private_key_pem: str, data: Dict[str, Any]) -> str:
        try:
            if isinstance(private_key_pem, dict):
                private_key_pem = private_key_pem.get("private_key", "")
            
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            
            message = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            
            signature = private_key.sign(
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return signature.hex()
        except Exception as e:
            raise Exception(f"签名失败: {str(e)}")

    @staticmethod
    def verify_signature(signature_hex: str, public_key_pem: str, 
                        data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode('utf-8'),
                backend=default_backend()
            )
            
            message = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            
            print(f"[DEBUG] 验证签名 - 数据: {data}")
            print(f"[DEBUG] 验证签名 - JSON: {json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))}")
            print(f"[DEBUG] 验证签名 - 消息长度: {len(message)}")
            print(f"[DEBUG] 验证签名 - 签名长度: {len(signature_hex)}")
            
            try:
                public_key.verify(
                    bytes.fromhex(signature_hex),
                    message,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
                print(f"[DEBUG] 验证签名 - 成功")
                return {"success": True, "valid": True}
            except Exception as e:
                print(f"[DEBUG] 验证签名 - 失败: {str(e)}")
                return {"success": False, "valid": False, "error": f"签名验证失败: {str(e)}"}
        except Exception as e:
            print(f"[DEBUG] 加载公钥失败: {str(e)}")
            return {"success": False, "valid": False, "error": f"加载公钥失败: {str(e)}"}

    @staticmethod
    def create_sign_data(contract_address: str, method: str, params: Dict[str, Any], 
                       timestamp: int, nonce: str) -> Dict[str, Any]:
        return {
            "contract_address": contract_address,
            "method": method,
            "params": params,
            "timestamp": timestamp,
            "nonce": nonce
        }

    @staticmethod
    def verify_nonce(nonce: str, used_nonces: set, max_age_seconds: int = 300) -> bool:
        if nonce in used_nonces:
            return False
        
        try:
            timestamp = int(nonce.split('_')[0])
            current_time = int(__import__('time').time())
            
            if abs(current_time - timestamp) > max_age_seconds:
                return False
            
            return True
        except Exception:
            return False
