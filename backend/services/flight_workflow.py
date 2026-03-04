import uuid
from typing import List, Optional, Tuple


class FlightWorkflow:
    def create_flight(self, flights: List[dict], data: dict) -> str:
        new_id = str(uuid.uuid4())
        data["id"] = new_id
        flights.append(data)
        return new_id

    def update_flight(self, flights: List[dict], flight_id: str, data: dict) -> bool:
        for idx, flight in enumerate(flights):
            if str(flight.get("id")) == str(flight_id):
                data["id"] = flight_id
                flights[idx] = data
                return True
        return False
