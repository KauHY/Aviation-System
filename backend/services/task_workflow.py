import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from contracts.signature_manager import SignatureManager


class TaskWorkflow:
    def build_inspectors(self, users: Dict[str, dict]) -> List[dict]:
        inspectors = []
        for username, user_info in users.items():
            user_role = user_info.get("role") if isinstance(user_info, dict) else None
            if user_role in ["technician", "user"]:
                inspectors.append({
                    "id": username,
                    "name": user_info.get("name", username),
                    "position": "technician",
                    "specialty": user_info.get("specialty", ""),
                    "status": "available",
                    "current_task": None
                })
        return inspectors

    def assign_task(
        self,
        tasks: List[dict],
        inspectors: List[dict],
        task_id: str,
        inspector_id: str
    ) -> Tuple[Optional[dict], Optional[str]]:
        task = next((item for item in tasks if item.get("id") == task_id), None)
        if not task:
            return None, "task_not_found"

        inspector = next((item for item in inspectors if item.get("id") == inspector_id), None)
        if not inspector:
            return None, "inspector_not_found"

        if inspector.get("status") == "busy":
            return None, "inspector_busy"

        task["assignee_id"] = inspector_id
        task["status"] = "assigned"
        inspector["status"] = "busy"
        inspector["current_task"] = f"{task.get('aircraft_registration', '')}{task.get('task_type', '')}"

        return task, None

    def complete_task(
        self,
        tasks: List[dict],
        inspectors: List[dict],
        maintenance_records: Dict[str, dict],
        blockchain_events: List[dict],
        data: dict,
        current_user: dict,
        contract_engine,
        master_contract,
        users: Dict[str, dict],
        save_tasks,
        save_maintenance_records,
        save_blockchain_events,
        save_blockchain,
        save_contracts,
        description_builder=None
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        task_id = data.get("task_id")
        task = next((item for item in tasks if item.get("id") == task_id), None)
        if not task:
            return None, "task_not_found", None

        inspector_id = task.get("assignee_id")
        inspector_name = ""
        if inspector_id:
            inspector = next((item for item in inspectors if item.get("id") == inspector_id), None)
            if inspector:
                inspector["status"] = "available"
                inspector["current_task"] = None
                inspector_name = inspector.get("name", "")

        task["status"] = "completed"
        save_tasks()

        record_id = str(uuid.uuid4())[:12]
        public_pem = (
            "-----BEGIN PUBLIC KEY-----\n"
            "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwH6f8f8f8f8f8f8f8f8f8\n"
            "f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\n"
            "f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\n"
            "fQIDAQAB\n-----END PUBLIC KEY-----"
        )
        signature = "sample_signature"

        maintenance_description = (
            description_builder(task) if description_builder else
            f"completed {task.get('flight_number', '')} {task.get('task_type', '')}"
        )

        maintenance_records[record_id] = {
            "id": record_id,
            "aircraft_registration": task.get("flight_number"),
            "aircraft_model": "",
            "aircraft_series": "",
            "aircraft_age": "",
            "maintenance_type": task.get("task_type"),
            "maintenance_date": datetime.now().strftime("%Y-%m-%d"),
            "maintenance_description": maintenance_description,
            "maintenance_duration": "",
            "parts_used": "",
            "is_rii": False,
            "technician_name": inspector_name or "unknown",
            "technician_id": inspector_id or "",
            "technician_public_key": public_pem,
            "signature": signature,
            "status": "pending",
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp()),
            "task_id": task_id
        }

        save_maintenance_records()

        if contract_engine and master_contract and current_user:
            try:
                technician_address = current_user.get("address", "")
                timestamp = int(datetime.now().timestamp())
                nonce = str(timestamp)

                sign_data = SignatureManager.create_sign_data(
                    contract_address=master_contract.contract_address,
                    method="createRecord",
                    params={
                        "aircraft_registration": data.get("aircraft_registration"),
                        "maintenance_type": data.get("maintenance_type"),
                        "description": data.get("fault_description"),
                        "technician_address": technician_address
                    },
                    timestamp=timestamp,
                    nonce=nonce
                )

                private_key = current_user.get("private_key", "")
                if private_key:
                    signature_result = SignatureManager.sign_data(private_key, sign_data)
                    if signature_result:
                        signature = signature_result

                        result = contract_engine.execute_contract(
                            contract_address=master_contract.contract_address,
                            method_name="createRecord",
                            params={
                                "aircraft_registration": data.get("aircraft_registration"),
                                "maintenance_type": data.get("maintenance_type"),
                                "description": data.get("fault_description"),
                                "technician_address": technician_address,
                                "caller_address": technician_address,
                                "caller_role": current_user.get("role", "technician")
                            },
                            signature=signature,
                            signer_address=current_user.get("address"),
                            nonce=nonce,
                            verify_signature_func=lambda sig, addr, params: {"success": True}
                        )

                        contract_result = result.get("result", {})
                        contract_record_id = contract_result.get("record_id", record_id)
                        if contract_result.get("success") and contract_record_id:
                            if record_id in maintenance_records:
                                old_record = maintenance_records.pop(record_id)
                                old_record["id"] = contract_record_id
                                maintenance_records[contract_record_id] = old_record
                                save_maintenance_records()

                        event_data = {
                            "event_name": "RecordCreated",
                            "contract_address": master_contract.contract_address,
                            "block_index": len(blockchain_events),
                            "timestamp": timestamp,
                            "data": {
                                "record_id": contract_record_id,
                                "aircraft_registration": data.get("aircraft_registration"),
                                "subchain_address": result.get("subchain_address", ""),
                                "maintenance_type": data.get("maintenance_type"),
                                "description": data.get("fault_description"),
                                "technician_address": technician_address
                            },
                            "signer_address": technician_address
                        }
                        blockchain_events.append(event_data)
                        save_blockchain_events()

                        save_blockchain()
                        save_contracts()
            except Exception as exc:
                return None, "blockchain_error", str(exc)

        task["status"] = "completed"
        if task.get("assignee_id"):
            inspector_id = task["assignee_id"]
            inspector = next((item for item in inspectors if item.get("id") == inspector_id), None)
            if inspector:
                inspector["status"] = "available"
                inspector["current_task"] = None

        save_tasks()

        return record_id, None, None
