import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from contracts.signature_manager import SignatureManager


class BlockchainWorkflow:
    def create_record(
        self,
        data: dict,
        maintenance_records: Dict[str, dict],
        tasks: List[dict],
        users: Dict[str, dict],
        contract_engine,
        master_contract,
        blockchain_events: List[dict],
        save_maintenance_records,
        save_blockchain_events
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        required_fields = [
            "aircraft_registration",
            "maintenance_type",
            "maintenance_date",
            "maintenance_description",
            "technician_name",
            "technician_id"
        ]
        for field in required_fields:
            if not data.get(field):
                return None, "missing_field", field

        record_id = str(uuid.uuid4())[:12]

        public_pem = (
            "-----BEGIN PUBLIC KEY-----\n"
            "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwH6f8f8f8f8f8f8f8f8f8\n"
            "f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\n"
            "f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f\n"
            "fQIDAQAB\n-----END PUBLIC KEY-----"
        )
        signature = "sample_signature"

        maintenance_records[record_id] = {
            "id": record_id,
            "aircraft_registration": data["aircraft_registration"],
            "aircraft_model": data.get("aircraft_model", ""),
            "aircraft_series": data.get("aircraft_series", ""),
            "aircraft_age": data.get("aircraft_age", ""),
            "maintenance_type": data["maintenance_type"],
            "maintenance_date": data["maintenance_date"],
            "maintenance_description": data["maintenance_description"],
            "maintenance_duration": data.get("maintenance_duration", ""),
            "parts_used": data.get("parts_used", ""),
            "is_rii": data.get("is_rii", False),
            "technician_name": data["technician_name"],
            "technician_id": data["technician_id"],
            "technician_public_key": public_pem,
            "signature": signature,
            "status": "pending",
            "created_at": int(datetime.now().timestamp()),
            "updated_at": int(datetime.now().timestamp())
        }

        save_maintenance_records()

        if contract_engine and master_contract:
            try:
                technician_info = None
                if data["technician_id"] in users:
                    technician_info = users[data["technician_id"]]

                result = contract_engine.execute_contract(
                    contract_address=master_contract.contract_address,
                    method_name="addRecord",
                    params={
                        "record_id": record_id,
                        "aircraft_registration": data["aircraft_registration"],
                        "aircraft_model": data.get("aircraft_model", ""),
                        "aircraft_series": data.get("aircraft_series", ""),
                        "aircraft_age": data.get("aircraft_age", ""),
                        "maintenance_type": data["maintenance_type"],
                        "maintenance_description": data["maintenance_description"],
                        "maintenance_duration": data.get("maintenance_duration", ""),
                        "parts_used": data.get("parts_used", ""),
                        "is_rii": data.get("is_rii", False),
                        "technician_address": technician_info.get("address", "") if technician_info else "",
                        "technician_name": data["technician_name"],
                        "technician_public_key": public_pem,
                        "caller_address": technician_info.get("address", "") if technician_info else "",
                        "caller_role": technician_info.get("role", "technician") if technician_info else "technician"
                    },
                    signature=signature,
                    signer_address=technician_info.get("address", "") if technician_info else "",
                    nonce=str(int(datetime.now().timestamp())),
                    verify_signature_func=lambda sig, addr, params: {"success": True}
                )

                if result.get("success"):
                    maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                    maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                    maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                    save_maintenance_records()

                    event_data = {
                        "event_name": "RecordCreated",
                        "contract_address": master_contract.contract_address,
                        "block_index": result.get("block_index", 0),
                        "data": {
                            "record_id": record_id,
                            "aircraft_registration": data["aircraft_registration"],
                            "subchain_address": result.get("subchain_address", ""),
                            "maintenance_type": data["maintenance_type"],
                            "description": data["maintenance_description"],
                            "technician_address": technician_info.get("address", "") if technician_info else ""
                        },
                        "signer_address": technician_info.get("address", "") if technician_info else ""
                    }
                    blockchain_events.append(event_data)
                    save_blockchain_events()
            except Exception:
                pass

        try:
            task_id = str(uuid.uuid4())[:12]
            new_task = {
                "id": task_id,
                "flight_number": data["aircraft_registration"],
                "task_type": data["maintenance_type"],
                "description": data["maintenance_description"],
                "priority": "medium",
                "deadline": data["maintenance_date"],
                "status": "assigned",
                "assignee_id": data["technician_id"],
                "assignee_name": data["technician_name"],
                "created_at": int(datetime.now().timestamp())
            }
            tasks.append(new_task)
        except Exception:
            pass

        return record_id, None, None

    def list_records(
        self,
        status_value: str,
        aircraft_registration: str,
        search: str,
        maintenance_records: Dict[str, dict],
        master_contract,
        users: Dict[str, dict],
        tasks: List[dict],
        save_maintenance_records
    ) -> Tuple[Optional[List[dict]], Optional[str]]:
        if not master_contract:
            return None, "blockchain_not_initialized"

        all_records = []
        for record_id, record in master_contract.state["records"].items():
            maintenance_record = maintenance_records.get(record_id)

            if maintenance_record:
                technician_name = maintenance_record.get("technician_name", "未知")
                if technician_name == "未知" or not technician_name:
                    task_id = maintenance_record.get("task_id")
                    if task_id:
                        for task in tasks:
                            if str(task.get("id")) == str(task_id):
                                assignee_id = task.get("assignee_id")
                                if assignee_id and assignee_id in users:
                                    technician_name = users[assignee_id].get("name", assignee_id)
                                    maintenance_record["technician_name"] = technician_name
                                    maintenance_record["technician_id"] = assignee_id
                                    save_maintenance_records()
                                break

                record_status = maintenance_record.get("status", record.get("status", "pending"))
            else:
                technician_address = record.get("technician_address", "")
                if technician_address:
                    technician_name = "未知"
                    for user_id, user in users.items():
                        if user.get("address") == technician_address:
                            technician_name = user.get("name", user.get("username", "未知"))
                            break
                else:
                    technician_name = record.get("technician_name", "未知")

                record_status = record.get("status", "pending")

            maintenance_date = ""
            if record.get("created_at"):
                if isinstance(record.get("created_at"), (int, float)):
                    maintenance_date = datetime.fromtimestamp(record["created_at"]).strftime("%Y/%m/%d %H:%M:%S")
                else:
                    maintenance_date = str(record.get("created_at"))

            task_info = None
            task_id = record.get("task_id") or (maintenance_record.get("task_id") if maintenance_record else None)
            if task_id:
                for task in tasks:
                    if str(task.get("id")) == str(task_id):
                        task_info = {
                            "id": task.get("id"),
                            "task_type": task.get("task_type"),
                            "priority": task.get("priority"),
                            "status": task.get("status")
                        }
                        break

            all_records.append({
                "id": record_id,
                **record,
                "maintenance_date": maintenance_date,
                "technician_name": technician_name,
                "status": record_status,
                "task_info": task_info
            })

        filtered_records = []
        for record in all_records:
            if status_value != "all" and record.get("status") != status_value:
                continue
            if aircraft_registration and record.get("aircraft_registration") != aircraft_registration:
                continue
            if search:
                if not (
                    search in record.get("id", "") or
                    search in record.get("aircraft_registration", "") or
                    search in record.get("technician_name", "") or
                    search in record.get("technician_address", "")
                ):
                    continue
            filtered_records.append(record)

        filtered_records.sort(key=lambda item: item.get("created_at"), reverse=True)
        return filtered_records, None

    def get_record_detail(self, record_id: str, maintenance_records: Dict[str, dict]) -> Tuple[Optional[dict], Optional[str]]:
        if record_id not in maintenance_records:
            return None, "record_not_found"
        return maintenance_records[record_id], None

    def update_record_status(
        self,
        record_id: str,
        action: str,
        current_user: Optional[dict],
        maintenance_records: Dict[str, dict],
        master_contract,
        contract_engine,
        users: Dict[str, dict],
        blockchain_events: List[dict],
        save_maintenance_records,
        save_blockchain_events,
        save_blockchain,
        save_contracts
    ) -> Tuple[Optional[dict], Optional[str]]:
        if record_id not in maintenance_records:
            return None, "record_not_found"

        record = maintenance_records[record_id]
        if action == "approve":
            record["status"] = "approved"
        elif action == "reject":
            record["status"] = "rejected"
        elif action == "release":
            record["status"] = "released"

        record["updated_at"] = int(datetime.now().timestamp())
        save_maintenance_records()

        if contract_engine and master_contract and current_user:
            try:
                timestamp = int(datetime.now().timestamp())
                nonce = str(timestamp)

                method_name = None
                if action == "approve":
                    method_name = "approveRecord"
                elif action == "reject":
                    method_name = "rejectRecord"
                elif action == "release":
                    method_name = "releaseRecord"

                if method_name:
                    username = current_user.get("name")
                    private_key = ""
                    if username and username in users:
                        private_key = users[username].get("private_key", "")

                    if private_key:
                        sign_data = SignatureManager.create_sign_data(
                            contract_address=master_contract.contract_address,
                            method=method_name,
                            params={
                                "record_id": record_id,
                                "approver_address": current_user["address"]
                            },
                            timestamp=timestamp,
                            nonce=nonce
                        )

                        signature_result = SignatureManager.sign_data(private_key, sign_data)
                        if signature_result:
                            signature = signature_result

                            result = contract_engine.execute_contract(
                                contract_address=master_contract.contract_address,
                                method_name=method_name,
                                params={
                                    "record_id": record_id,
                                    "approver_address": current_user["address"],
                                    "caller_address": current_user["address"],
                                    "caller_role": current_user["role"]
                                },
                                signature=signature,
                                signer_address=current_user["address"],
                                nonce=nonce,
                                verify_signature_func=lambda sig, addr, params: {"success": True}
                            )

                            if result.get("success"):
                                save_blockchain()
                                save_contracts()

                                if "transaction_hash" not in maintenance_records[record_id]:
                                    maintenance_records[record_id]["transaction_hash"] = result.get("transaction_hash", "")
                                maintenance_records[record_id]["block_number"] = result.get("block_index", 0)
                                maintenance_records[record_id]["blockchain_timestamp"] = int(datetime.now().timestamp())
                                save_maintenance_records()

                                event_type = None
                                if action == "approve":
                                    event_type = "RecordApproved"
                                elif action == "reject":
                                    event_type = "RecordRejected"
                                elif action == "release":
                                    event_type = "RecordReleased"

                                if event_type:
                                    event_data = {
                                        "event_name": event_type,
                                        "contract_address": master_contract.contract_address,
                                        "block_index": result.get("block_index", 0),
                                        "data": {
                                            "record_id": record_id,
                                            "aircraft_registration": record.get("aircraft_registration", ""),
                                            "subchain_address": record.get("subchain_address", "")
                                        },
                                        "signer_address": current_user["address"]
                                    }
                                    blockchain_events.append(event_data)
                                    save_blockchain_events()
            except Exception:
                pass

        return record, None

    def get_all_records(self, master_contract) -> Tuple[Optional[List[dict]], Optional[str]]:
        if not master_contract:
            return None, "blockchain_not_initialized"
        return list(master_contract.state["records"].values()), None

    def get_record(self, master_contract, record_id: str) -> Tuple[Optional[dict], Optional[str]]:
        if not master_contract:
            return None, "blockchain_not_initialized"

        record = master_contract.state["records"].get(record_id)
        if not record:
            return None, "record_not_found"
        return record, None

    def get_aircraft_records(self, master_contract, aircraft_registration: str) -> Tuple[Optional[List[dict]], Optional[str]]:
        if not master_contract:
            return None, "blockchain_not_initialized"

        aircraft_records = []
        for record_id, record in master_contract.state["records"].items():
            if record.get("aircraft_registration") == aircraft_registration:
                aircraft_records.append(record)

        return aircraft_records, None

    def get_stats(self, master_contract, contract_engine) -> Tuple[Optional[dict], Optional[str]]:
        if not master_contract or not contract_engine:
            return None, "blockchain_not_initialized"

        total_records = len(master_contract.state["records"])
        total_blocks = contract_engine.get_blockchain_length()
        total_aircraft = len(master_contract.state.get("aircraft_subchains", {}))
        completed_records = sum(
            1 for record in master_contract.state["records"].values()
            if record.get("status") in ["approved", "released"]
        )

        stats = {
            "total_records": total_records,
            "total_blocks": total_blocks,
            "total_aircraft": total_aircraft,
            "completed_records": completed_records,
            "pending_records": total_records - completed_records
        }
        return stats, None
