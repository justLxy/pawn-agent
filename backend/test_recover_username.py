"""Username recovery by password."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from auth import count_online_players, recover_usernames_by_password, register_player


def test_recover_single_and_duplicate_passwords():
    suffix = os.urandom(4).hex()
    password = f"pwd_{suffix}"
    user_a = f"recover_a_{suffix}"
    user_b = f"recover_b_{suffix}"
    register_player(user_a, password, f"当铺A_{suffix}")
    register_player(user_b, password, f"当铺B_{suffix}")

    found = recover_usernames_by_password(password)
    assert user_a in found
    assert user_b in found

    missing = recover_usernames_by_password(f"wrong_{suffix}")
    assert missing == []


def test_count_online_players():
    now = 1_700_000_000
    assert count_online_players(now=now) >= 0


if __name__ == "__main__":
    test_recover_single_and_duplicate_passwords()
    test_count_online_players()
    print("ok")
