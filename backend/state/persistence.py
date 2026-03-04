def load_users(user_service):
    return user_service.load_users()


def save_users(user_service, users, user_roles):
    user_service.save_users(users, user_roles)


def load_tasks(task_service):
    return task_service.load_tasks()


def save_tasks(task_service, tasks):
    task_service.save_tasks(tasks)


def load_maintenance_records(record_service):
    return record_service.load_records()


def save_maintenance_records(record_service, records):
    record_service.save_records(records)


def load_blockchain_events(event_service):
    return event_service.load_events()


def save_blockchain_events(event_service, events):
    event_service.save_events(events)


def load_flights(flight_service):
    return flight_service.load_flights()


def save_flights(flight_service, flights):
    flight_service.save_flights(flights)
