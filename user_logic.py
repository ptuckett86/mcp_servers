"""Reference implementations for user-data coding scenarios."""

from collections import Counter

USERS = [
    {"id": "u1", "fname": "Landon", "lname": "Tuckett", "manager": "u2"},
    {"id": "u2", "fname": "Jane", "lname": "Smith", "manager": None},
    {"id": "u3", "fname": "Alex", "lname": "Adams", "manager": "u2"},
    {"id": "u4", "fname": "Chris", "lname": "Brown", "manager": "u1"},
]

def find_user(users, user_id):
    return next((u for u in users if u["id"] == user_id), None)

def users_reporting_to(users, manager_id):
    return [u for u in users if u["manager"] == manager_id]

def sort_users(users):
    return sorted(users, key=lambda u: (u["lname"].lower(), u["fname"].lower()))

def direct_reports(users, user_id):
    return [u for u in users if u["manager"] == user_id]

def find_manager(users, user_id):
    by_id = {u["id"]: u for u in users}
    user = by_id.get(user_id)
    if user is None or user.get("manager") is None:
        return None
    return by_id.get(user["manager"])

def count_by_manager(users):
    return Counter(u["manager"] for u in users if u.get("manager") is not None)

def users_without_manager(users):
    return [u for u in users if u.get("manager") is None]

def search_first_name(users, text):
    needle = text.lower()
    return [u for u in users if needle in u["fname"].lower()]

def users_with_missing_manager(users):
    ids = {u["id"] for u in users}
    return [
        u for u in users
        if u.get("manager") is not None and u["manager"] not in ids
    ]

def all_reports(users, manager_id):
    reports = []
    frontier = [manager_id]
    visited_managers = set()

    while frontier:
        current_manager = frontier.pop()
        if current_manager in visited_managers:
            continue
        visited_managers.add(current_manager)

        direct = [u for u in users if u.get("manager") == current_manager]
        for user in direct:
            if user["id"] not in {r["id"] for r in reports}:
                reports.append(user)
                frontier.append(user["id"])

    return reports
