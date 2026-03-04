import hashlib
from datetime import datetime
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from contracts.contract_engine import ContractEngine
from contracts.maintenance_record_master_contract import MaintenanceRecordMasterContract
from contracts.aircraft_subchain_contract import AircraftSubchainContract
from contracts.base_contract import BaseContract


def initialize_blockchain(
    blockchain_storage_service,
    contracts_storage_service,
    maintenance_records,
    users
) -> Tuple[Optional[ContractEngine], Optional[MaintenanceRecordMasterContract]]:
    contract_engine = None
    master_contract = None

    try:
        contract_engine = ContractEngine()

        blockchain_data = blockchain_storage_service.load_blockchain()
        if blockchain_data:
            try:
                if "blocks" in blockchain_data and len(blockchain_data["blocks"]) > 1:
                    contract_engine.blocks = blockchain_data["blocks"]
                    if contract_engine.blocks:
                        contract_engine.latest_block_hash = contract_engine.blocks[-1].get(
                            "hash",
                            "0x0000000000000000000000000000000000000000000000000000000000000000"
                        )
                    print(f"Loaded {len(contract_engine.blocks)} blocks from blockchain.json")
            except Exception as exc:
                print("Failed to load blockchain.json, using new chain: " + str(exc))

        contracts_data = contracts_storage_service.load_contracts()
        if contracts_data:
            try:
                if "contracts" in contracts_data and contracts_data["contracts"]:
                    for contract_address, contract_info in contracts_data["contracts"].items():
                        contract_name = contract_info.get("contract_name", "")
                        state = contract_info.get("state", {})

                        if contract_name == "MaintenanceRecordMasterContract":
                            master_contract = MaintenanceRecordMasterContract(contract_address)
                            master_contract.state = state
                            contract_engine.register_contract(master_contract)
                            print(f"Loaded master contract: {contract_address}")
                        elif contract_name == "AircraftSubchainContract":
                            aircraft_info = state.get("aircraft_info", {})
                            aircraft_reg = aircraft_info.get("aircraft_registration", "")
                            aircraft_type = aircraft_info.get("aircraft_type", "")
                            master_address = aircraft_info.get("master_contract_address", "")

                            subchain_contract = AircraftSubchainContract(
                                contract_address,
                                aircraft_reg,
                                aircraft_type,
                                master_address
                            )
                            subchain_contract.state = state
                            contract_engine.register_contract(subchain_contract)
                            print(f"Loaded subchain contract: {contract_address} (aircraft: {aircraft_reg})")

                    print(f"Loaded {len(contracts_data['contracts'])} contracts from contracts.json")
            except Exception as exc:
                print("Failed to load contracts.json, creating new contract set: " + str(exc))

        if not master_contract:
            master_contract_address = BaseContract.generate_address("MaintenanceRecordMasterContract")
            master_contract = MaintenanceRecordMasterContract(master_contract_address)
            contract_engine.register_contract(master_contract)
            print(f"Created new master contract: {master_contract_address}")

        print(f"Blockchain initialized, master chain: {master_contract.contract_address}")
        migrate_maintenance_records_to_contract(
            contract_engine,
            master_contract,
            maintenance_records,
            users,
            blockchain_storage_service,
            contracts_storage_service
        )
    except Exception as exc:
        print("Failed to initialize blockchain: " + str(exc))
        import traceback
        traceback.print_exc()
        contract_engine = None
        master_contract = None

    return contract_engine, master_contract


def ensure_users_have_keys(users, user_roles, user_service) -> None:
    try:
        updated = False
        for username, user_info in users.items():
            if (
                "public_key" not in user_info or not user_info["public_key"] or
                "private_key" not in user_info or not user_info["private_key"]
            ):
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )

                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ).decode("utf-8")

                public_key = private_key.public_key()
                public_pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ).decode("utf-8")

                address = "0x" + hashlib.sha256(public_pem.encode()).hexdigest()[:40]

                user_info["public_key"] = public_pem
                user_info["private_key"] = private_pem
                user_info["address"] = address
                if "employee_id" not in user_info:
                    user_info["employee_id"] = "EMP" + address[-8:]

                updated = True
                print(f"Generated key pair for user {username}: {address}")

        if updated:
            user_service.save_users(users, user_roles)
            print("User data updated")
    except Exception as exc:
        print("Failed to ensure user keys: " + str(exc))


def migrate_maintenance_records_to_contract(
    contract_engine,
    master_contract,
    maintenance_records,
    users,
    blockchain_storage_service,
    contracts_storage_service
) -> None:
    if not contract_engine or not master_contract:
        return

    try:
        if contract_engine.get_blockchain_length() > 1:
            print("Blockchain already has data, skip migration")
            return

        records_to_migrate = list(maintenance_records.values())
        if not records_to_migrate:
            print("No maintenance records to migrate")
            return

        print(f"Migrating {len(records_to_migrate)} records to contract...")

        for record in records_to_migrate:
            try:
                aircraft_reg = record.get("aircraft_registration", "")
                if aircraft_reg and aircraft_reg not in master_contract.state["aircraft_subchains"]:
                    subchain_address = BaseContract.generate_address(
                        "AircraftSubchainContract",
                        {"aircraft_registration": aircraft_reg}
                    )

                    master_contract.state["aircraft_subchains"][aircraft_reg] = {
                        "aircraft_registration": aircraft_reg,
                        "aircraft_type": record.get("aircraft_model", "unknown"),
                        "subchain_address": subchain_address,
                        "record_count": 0,
                        "created_at": int(datetime.now().timestamp()),
                        "latest_block_hash": "0"
                    }

                    subchain_contract = AircraftSubchainContract(
                        subchain_address,
                        aircraft_reg,
                        record.get("aircraft_model", "unknown"),
                        master_contract.contract_address
                    )
                    contract_engine.register_contract(subchain_contract)

                    print(f"Created aircraft subchain: {aircraft_reg} -> {subchain_address}")

                record_id = record.get("id", "")
                if record_id not in master_contract.state["records"]:
                    master_contract.state["records"][record_id] = {
                        "id": record_id,
                        "aircraft_registration": record.get("aircraft_registration", ""),
                        "subchain_address": master_contract.state["aircraft_subchains"].get(
                            record.get("aircraft_registration", ""), {}
                        ).get("subchain_address", ""),
                        "maintenance_type": record.get("maintenance_type", ""),
                        "maintenance_date": record.get("maintenance_date", ""),
                        "maintenance_description": record.get("maintenance_description", ""),
                        "status": record.get("status", "pending"),
                        "technician_address": record.get("technician_id", ""),
                        "technician_name": record.get("technician_name", "unknown"),
                        "approver_address": "",
                        "created_at": record.get("created_at", int(datetime.now().timestamp())),
                        "updated_at": record.get("updated_at", int(datetime.now().timestamp())),
                        "block_index": contract_engine.get_blockchain_length(),
                        "subchain_block_index": 0
                    }

                    master_contract.state["stats"]["total_records"] += 1
                    status_value = record.get("status", "pending")
                    if status_value == "pending":
                        master_contract.state["stats"]["pending_count"] += 1
                    elif status_value == "approved":
                        master_contract.state["stats"]["approved_count"] += 1
                    elif status_value == "released":
                        master_contract.state["stats"]["released_count"] += 1

                    subchain_address = master_contract.state["aircraft_subchains"].get(
                        aircraft_reg, {}
                    ).get("subchain_address", "")

                    if subchain_address:
                        subchain_contract = contract_engine.get_contract(subchain_address)
                        if subchain_contract and record_id not in subchain_contract.state["records"]:
                            subchain_contract.state["records"][record_id] = {
                                "id": record_id,
                                "maintenance_type": record.get("maintenance_type", ""),
                                "description": record.get("maintenance_description", ""),
                                "status": record.get("status", "pending"),
                                "technician_address": record.get("technician_id", ""),
                                "approver_address": "",
                                "created_at": record.get("created_at", int(datetime.now().timestamp())),
                                "updated_at": record.get("updated_at", int(datetime.now().timestamp())),
                                "block_index": contract_engine.get_blockchain_length(),
                                "master_record_id": record_id
                            }

                            subchain_contract.state["stats"]["total_records"] += 1
                            if status_value == "pending":
                                subchain_contract.state["stats"]["pending_count"] += 1
                            elif status_value == "approved":
                                subchain_contract.state["stats"]["approved_count"] += 1
                            elif status_value == "released":
                                subchain_contract.state["stats"]["released_count"] += 1

                            if aircraft_reg in master_contract.state["aircraft_subchains"]:
                                master_contract.state["aircraft_subchains"][aircraft_reg]["record_count"] += 1

                    technician_name = record.get("technician_name", "unknown")
                    technician_id = record.get("technician_id", "")

                    tech_address = ""
                    if technician_id:
                        for _, user_info in users.items():
                            if user_info.get("username") == technician_id:
                                tech_address = user_info.get("address", "")
                                break

                    block = contract_engine._create_block(
                        contract_address=master_contract.contract_address,
                        method="migrateRecord",
                        params={
                            "record_id": record_id,
                            "aircraft_registration": record.get("aircraft_registration", ""),
                            "maintenance_type": record.get("maintenance_type", ""),
                            "description": record.get("maintenance_description", ""),
                            "technician_address": tech_address,
                            "technician_name": technician_name
                        },
                        signature="migration_signature",
                        signer_address=tech_address if tech_address else "system",
                        nonce=f"migration_{record_id}",
                        events=[]
                    )

                    contract_engine.blocks.append(block)
                    contract_engine.latest_block_hash = block["hash"]

                    print(f"Migrated record: {record_id} -> block {block['index']}")

            except Exception as exc:
                print("Failed to migrate record: " + str(exc))
                continue

        save_blockchain(contract_engine, blockchain_storage_service)
        save_contracts(contract_engine, contracts_storage_service)

        print(f"Migration completed, chain length: {contract_engine.get_blockchain_length()}")

    except Exception as exc:
        print("Failed to migrate maintenance records: " + str(exc))


def save_blockchain(contract_engine, blockchain_storage_service) -> None:
    if not contract_engine:
        return

    try:
        blockchain_data = {
            "blocks": contract_engine.get_all_blocks(),
            "latest_block_hash": contract_engine.latest_block_hash
        }
        blockchain_storage_service.save_blockchain(blockchain_data)
        print(f"Saved blockchain data, blocks: {len(contract_engine.get_all_blocks())}")
    except Exception as exc:
        print("Failed to save blockchain data: " + str(exc))


def save_contracts(contract_engine, contracts_storage_service) -> None:
    if not contract_engine:
        return

    try:
        contracts_data = {}
        for address, contract in contract_engine.get_all_contracts().items():
            contracts_data[address] = contract.to_dict()

        contracts_storage_service.save_contracts({"contracts": contracts_data})
        print(f"Saved contract data, contracts: {len(contracts_data)}")
    except Exception as exc:
        print("Failed to save contract data: " + str(exc))
