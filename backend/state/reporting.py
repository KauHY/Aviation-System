from datetime import datetime


async def generate_report_data(
    report_type,
    start_date,
    end_date,
    report_detail_type,
    filters,
    maintenance_records,
    flights,
    contract_engine,
    users
):
    report_data = {
        "type": report_type,
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now().isoformat(),
        "data": []
    }

    if report_type == "maintenance":
        records = list(maintenance_records.values())
        if start_date and end_date:
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp()) + 86400
            records = [r for r in records if start_ts <= r.get("timestamp", 0) <= end_ts]

        if filters:
            filter_keywords = filters.split(",")
            for keyword in filter_keywords:
                keyword = keyword.strip()
                records = [
                    r for r in records
                    if keyword in r.get("aircraft_registration", "") or
                    keyword in r.get("maintenance_type", "")
                ]

        report_data["data"] = records
        report_data["summary"] = {
            "total": len(records),
            "by_type": {},
            "by_status": {}
        }

        for record in records:
            mtype = record.get("maintenance_type", "unknown")
            status_value = record.get("status", "unknown")
            report_data["summary"]["by_type"][mtype] = report_data["summary"]["by_type"].get(mtype, 0) + 1
            report_data["summary"]["by_status"][status_value] = report_data["summary"]["by_status"].get(status_value, 0) + 1

    elif report_type == "flight":
        flight_list = flights
        if start_date and end_date:
            flight_list = [f for f in flight_list if start_date <= f.get("date", "") <= end_date]

        if filters:
            filter_keywords = filters.split(",")
            for keyword in filter_keywords:
                keyword = keyword.strip()
                flight_list = [
                    f for f in flight_list
                    if keyword in f.get("flight_number", "") or
                    keyword in f.get("airline", "")
                ]

        report_data["data"] = flight_list
        report_data["summary"] = {
            "total": len(flight_list),
            "by_status": {},
            "by_airline": {}
        }

        for flight in flight_list:
            status_value = flight.get("status", "unknown")
            airline = flight.get("airline", "unknown")
            report_data["summary"]["by_status"][status_value] = report_data["summary"]["by_status"].get(status_value, 0) + 1
            report_data["summary"]["by_airline"][airline] = report_data["summary"]["by_airline"].get(airline, 0) + 1

    elif report_type == "blockchain":
        if contract_engine:
            blocks = contract_engine.get_all_blocks()
            if start_date and end_date:
                start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
                end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp()) + 86400
                blocks = [b for b in blocks if start_ts <= b.get("timestamp", 0) <= end_ts]

            report_data["data"] = blocks
            report_data["summary"] = {
                "total_blocks": len(blocks),
                "total_transactions": sum(len(b.get("transactions", [])) for b in blocks),
                "latest_block_hash": blocks[-1].get("hash", "") if blocks else ""
            }

    elif report_type == "user":
        user_list = list(users.values())
        report_data["data"] = user_list
        report_data["summary"] = {
            "total_users": len(user_list),
            "by_role": {}
        }

        for user in user_list:
            role = user.get("role", "user")
            report_data["summary"]["by_role"][role] = report_data["summary"]["by_role"].get(role, 0) + 1

    elif report_type == "aircraft":
        aircraft_list = []
        for record in maintenance_records.values():
            reg = record.get("aircraft_registration", "")
            if reg and reg not in [a.get("registration") for a in aircraft_list]:
                aircraft_list.append({
                    "registration": reg,
                    "maintenance_count": 0,
                    "last_maintenance": None
                })

        for aircraft in aircraft_list:
            reg = aircraft["registration"]
            aircraft_records = [r for r in maintenance_records.values() if r.get("aircraft_registration") == reg]
            aircraft["maintenance_count"] = len(aircraft_records)
            if aircraft_records:
                aircraft["last_maintenance"] = max(r.get("timestamp", 0) for r in aircraft_records)

        report_data["data"] = aircraft_list
        report_data["summary"] = {
            "total_aircraft": len(aircraft_list),
            "total_maintenance": sum(a["maintenance_count"] for a in aircraft_list)
        }

    elif report_type == "summary":
        report_data["summary"] = {
            "users": {
                "total": len(users),
                "by_role": {}
            },
            "flights": {
                "total": len(flights),
                "by_status": {}
            },
            "maintenance_records": {
                "total": len(maintenance_records),
                "by_type": {},
                "by_status": {}
            },
            "blockchain": {
                "total_blocks": len(contract_engine.get_all_blocks()) if contract_engine else 0
            }
        }

        for user in users.values():
            role = user.get("role", "user")
            report_data["summary"]["users"]["by_role"][role] = report_data["summary"]["users"]["by_role"].get(role, 0) + 1

        for flight in flights:
            status_value = flight.get("status", "unknown")
            report_data["summary"]["flights"]["by_status"][status_value] = report_data["summary"]["flights"]["by_status"].get(status_value, 0) + 1

        for record in maintenance_records.values():
            mtype = record.get("maintenance_type", "unknown")
            status_value = record.get("status", "unknown")
            report_data["summary"]["maintenance_records"]["by_type"][mtype] = report_data["summary"]["maintenance_records"]["by_type"].get(mtype, 0) + 1
            report_data["summary"]["maintenance_records"]["by_status"][status_value] = report_data["summary"]["maintenance_records"]["by_status"].get(status_value, 0) + 1

    return report_data
