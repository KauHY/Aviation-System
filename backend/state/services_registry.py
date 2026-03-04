from services.json_store import JsonStore
from services.users import UserService
from services.tasks import TaskService
from services.flights import FlightService
from services.maintenance_records import MaintenanceRecordService
from services.blockchain_events import BlockchainEventService
from services.blockchain_storage import BlockchainStorageService
from services.contracts_storage import ContractsStorageService

from state.config import (
    USER_DATA_FILE,
    TASK_DATA_FILE,
    FLIGHT_DATA_FILE,
    MAINTENANCE_RECORDS_FILE,
    BLOCKCHAIN_EVENTS_FILE,
    BLOCKCHAIN_FILE,
    CONTRACTS_FILE
)

user_service = UserService(JsonStore(USER_DATA_FILE, lambda: {}))
task_service = TaskService(JsonStore(TASK_DATA_FILE, lambda: []))
flight_service = FlightService(JsonStore(FLIGHT_DATA_FILE, lambda: []))
maintenance_record_service = MaintenanceRecordService(JsonStore(MAINTENANCE_RECORDS_FILE, lambda: {}))
blockchain_event_service = BlockchainEventService(JsonStore(BLOCKCHAIN_EVENTS_FILE, lambda: []))
blockchain_storage_service = BlockchainStorageService(JsonStore(BLOCKCHAIN_FILE, lambda: {}))
contracts_storage_service = ContractsStorageService(JsonStore(CONTRACTS_FILE, lambda: {}))
