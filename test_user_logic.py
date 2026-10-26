"""Pytest tests for the user-data scenarios.

Run from this directory:
    pytest -q

The tests import the reference implementations from user_logic.py.
"""

from collections import Counter

from user_logic import (
    USERS,
    all_reports,
    count_by_manager,
    direct_reports,
    find_manager,
    find_user,
    search_first_name,
    sort_users,
    users_reporting_to,
    users_with_missing_manager,
    users_without_manager,
)


def test_1_find_user_by_id():
    assert find_user(USERS, "u3") == USERS[2]
    assert find_user(USERS, "missing") is None
    assert find_user([], "u1") is None

def test_2_users_reporting_to_manager():
    assert [u["id"] for u in users_reporting_to(USERS, "u2")] == ["u1", "u3"]
    assert users_reporting_to(USERS, "missing") == []
    assert users_reporting_to([], "u2") == []

def test_3_sort_by_last_then_first_name():
    result = sort_users(USERS)
    assert [u["id"] for u in result] == ["u3", "u4", "u2", "u1"]
    assert USERS[0]["id"] == "u1"  # sorted() must not mutate the original list
    assert sort_users([]) == []

def test_4_direct_reports():
    assert [u["id"] for u in direct_reports(USERS, "u2")] == ["u1", "u3"]
    assert [u["id"] for u in direct_reports(USERS, "u1")] == ["u4"]
    assert direct_reports(USERS, "missing") == []

def test_5_find_manager():
    assert find_manager(USERS, "u1") == USERS[1]
    assert find_manager(USERS, "u2") is None  # top-level user
    assert find_manager(USERS, "missing") is None

def test_6_count_users_per_manager():
    assert count_by_manager(USERS) == Counter({"u2": 2, "u1": 1})
    assert count_by_manager([]) == Counter()

def test_7_users_without_manager():
    assert [u["id"] for u in users_without_manager(USERS)] == ["u2"]
    assert users_without_manager([]) == []

def test_8_case_insensitive_first_name_search():
    assert [u["id"] for u in search_first_name(USERS, "lan")] == ["u1"]
    assert [u["id"] for u in search_first_name(USERS, "JANE")] == ["u2"]
    assert search_first_name(USERS, "not-a-name") == []
    assert search_first_name([], "alex") == []

def test_9_missing_manager_references():
    broken = USERS + [
        {"id": "u5", "fname": "Morgan", "lname": "Lee", "manager": "u999"}
    ]
    assert [u["id"] for u in users_with_missing_manager(broken)] == ["u5"]
    assert users_with_missing_manager(USERS) == []
    assert users_with_missing_manager([]) == []

def test_10_all_direct_and_indirect_reports():
    # u2 manages u1 and u3; u1 manages u4.
    result = all_reports(USERS, "u2")
    assert {u["id"] for u in result} == {"u1", "u3", "u4"}

    # A cycle must not make the function loop forever.
    cyclic = [
        {"id": "a", "fname": "A", "lname": "A", "manager": "b"},
        {"id": "b", "fname": "B", "lname": "B", "manager": "a"},
    ]
    assert {u["id"] for u in all_reports(cyclic, "a")} == {"a", "b"}
    assert all_reports([], "u1") == []
