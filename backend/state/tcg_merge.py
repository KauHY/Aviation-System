import json
import os
from datetime import datetime
from typing import Optional


def _normalize_tcg_username(base_name: str, address: str, users: dict) -> str:
    base_name = (base_name or "").strip() or address[-8:]
    if base_name not in users:
        return base_name
    return f"{base_name}_tcg_{address[-6:]}"


def _map_tcg_role(user_info: dict, address: str) -> str:
    is_admin = bool(user_info.get("is_admin")) or address == "0x0000000000000000000000000000000000000001"
    is_authorized = bool(user_info.get("isAuthorized")) or bool(user_info.get("is_authorized"))
    if is_admin:
        return "admin"
    if is_authorized:
        return "technician"
    return "user"


def _map_tcg_status(status_value: str) -> str:
    if not status_value:
        return "pending"
    status_value = status_value.strip().lower()
    if status_value in ["released", "release"]:
        return "released"
    if status_value in ["approved", "approve"]:
        return "approved"
    if status_value in ["rejected", "reject"]:
        return "rejected"
    return "pending"


def merge_tcg_data(
    tcg_data_dir: Optional[str],
    users: dict,
    maintenance_records: dict,
    load_users_fn,
    load_records_fn,
    save_users_fn,
    save_records_fn
) -> dict:
    if tcg_data_dir is None:
        tcg_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tcg", "data")

    tcg_users_path = os.path.join(tcg_data_dir, "users.json")
    tcg_records_path = os.path.join(tcg_data_dir, "records.json")

    if not os.path.exists(tcg_users_path) and not os.path.exists(tcg_records_path):
        return {
            "users_merged": 0,
            "records_merged": 0,
            "reason": "tcg \u6570\u636e\u4e0d\u5b58\u5728"
        }

    if load_users_fn:
        load_users_fn()
    if load_records_fn:
        load_records_fn()

    address_index = {
        info.get("address"): username
        for username, info in users.items()
        if isinstance(info, dict) and info.get("address")
    }

    users_merged = 0
    records_merged = 0

    if os.path.exists(tcg_users_path):
        try:
            with open(tcg_users_path, "r", encoding="utf-8") as handle:
                tcg_users = json.load(handle) or {}
        except Exception as exc:
            print("Failed to load tcg users: " + str(exc))
            tcg_users = {}

        for address, user_info in tcg_users.items():
            if not isinstance(user_info, dict):
                continue

            existing_username = address_index.get(address)
            if existing_username:
                existing_user = users.get(existing_username, {})
                if user_info.get("name") and not existing_user.get("name"):
                    existing_user["name"] = user_info.get("name")
                if user_info.get("employee_id") or user_info.get("empId"):
                    existing_user.setdefault("employee_id", user_info.get("employee_id") or user_info.get("empId"))
                if user_info.get("password") and not existing_user.get("password"):
                    existing_user["password"] = user_info.get("password")
                existing_user.setdefault("is_admin", bool(user_info.get("is_admin")))
                continue

            username = _normalize_tcg_username(user_info.get("name"), address, users)
            role = _map_tcg_role(user_info, address)
            password = user_info.get("password") or "123456"

            users[username] = {
                "password": password,
                "role": role,
                "address": address,
                "name": user_info.get("name", username),
                "employee_id": user_info.get("employee_id") or user_info.get("empId"),
                "is_admin": role == "admin"
            }
            address_index[address] = username
            users_merged += 1

    if os.path.exists(tcg_records_path):
        try:
            with open(tcg_records_path, "r", encoding="utf-8") as handle:
                tcg_records = json.load(handle) or {}
        except Exception as exc:
            print("Failed to load tcg records: " + str(exc))
            tcg_records = {}

        for record_id, record in tcg_records.items():
            if not isinstance(record, dict):
                continue

            new_id = record_id
            if new_id in maintenance_records:
                new_id = f"{record_id}_tcg"
                if new_id in maintenance_records:
                    continue

            timestamp = record.get("timestamp") or 0
            maintenance_date = ""
            if isinstance(timestamp, (int, float)) and timestamp > 0:
                maintenance_date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

            used_parts = record.get("usedParts", [])
            parts_used = ",".join([
                part.get("partNumber", "")
                for part in used_parts
                if isinstance(part, dict)
            ])

            signatures = record.get("signatures", {}) or {}
            technician_name = signatures.get("performedByName") or signatures.get("releaseByName") or "unknown"
            technician_id = signatures.get("performedById") or signatures.get("releaseById") or ""

            maintenance_records[new_id] = {
                "id": new_id,
                "aircraft_registration": record.get("aircraftRegNo", ""),
                "aircraft_model": record.get("aircraftType", ""),
                "aircraft_series": "",
                "aircraft_age": "",
                "maintenance_type": record.get("workType", ""),
                "maintenance_date": maintenance_date,
                "maintenance_description": record.get("workDescription", ""),
                "maintenance_duration": "",
                "parts_used": parts_used,
                "is_rii": bool(record.get("isRII")),
                "technician_name": technician_name,
                "technician_id": technician_id,
                "technician_public_key": "",
                "signature": "",
                "status": _map_tcg_status(record.get("status")),
                "created_at": int(timestamp) if timestamp else int(datetime.now().timestamp()),
                "updated_at": int(timestamp) if timestamp else int(datetime.now().timestamp()),
                "source": "tcg",
                "tcg_record_id": record_id,
                "tcg_record": record
            }
            records_merged += 1

    if users_merged or records_merged:
        if save_users_fn:
            save_users_fn()
        if save_records_fn:
            save_records_fn()

    return {"users_merged": users_merged, "records_merged": records_merged}
