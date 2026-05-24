"""Verify player-trade rollback on account reset."""
import json
import os
import sys
import tempfile
import time
import uuid

# Run from backend/: python test_reset_rollback.py
sys.path.insert(0, os.path.dirname(__file__))

os.environ["PAWNSHOP_DB_PATH"] = tempfile.mktemp(suffix=".db")

from database import get_connection, init_db
from game_state import GameStateManager, Item
from online_services import (
    buy_listing,
    buy_showcase_item,
    list_item,
    load_state,
    reset_player_data,
    save_state,
)


def _create_player(username: str, cash: int = 10000) -> int:
    now = int(time.time())
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO players (username, shop_name, password_hash, salt, token, online, created_at, last_seen)
            VALUES (?, ?, 'x', 'y', ?, 0, ?, ?)
            """,
            (username, f"{username}铺", f"tok_{username}", now, now),
        )
        player_id = int(cur.lastrowid)
    state = GameStateManager()
    state.cash = cash
    save_state(player_id, state)
    return player_id


def _make_item(name: str = "测试怀表") -> Item:
    return Item(
        name=name,
        category="Jewelry",
        condition="Good",
        is_fake=False,
        actual_value=5000,
        market_value=5000,
        description="测试物品",
        item_id=str(uuid.uuid4())[:12],
    )


def _seller_list(seller_id: int, price: int = 1000) -> str:
    state = load_state(seller_id)
    item = _make_item()
    state.inventory.append(item)
    save_state(seller_id, state)
    result = list_item(seller_id, item.id, price)
    return result["listing_id"]


def test_buy_then_reset():
    seller_id = _create_player("seller_a")
    buyer_id = _create_player("buyer_b")
    seller_before = load_state(seller_id)
    cash_before = seller_before.cash
    listing_id = _seller_list(seller_id, 5000)

    buy_listing(buyer_id, listing_id)
    seller_after_buy = load_state(seller_id)
    assert seller_after_buy.cash == cash_before + 4750

    reset_player_data(buyer_id, "buyer_b铺", GameStateManager())
    seller_after_reset = load_state(seller_id)
    buyer_after = load_state(buyer_id)

    assert seller_after_reset.cash == cash_before, f"expected {cash_before}, got {seller_after_reset.cash}"
    assert len(seller_after_reset.inventory) == 1
    assert buyer_after.cash == 10000
    print("OK: buy then reset rolls back seller cash and returns item")


def test_list_then_reset():
    seller_id = _create_player("seller_c")
    buyer_id = _create_player("buyer_d")
    cash_before = load_state(seller_id).cash
    listing_id = _seller_list(seller_id, 5000)
    buy_listing(buyer_id, listing_id)

    buyer_state = load_state(buyer_id)
    item_id = buyer_state.inventory[0].id
    buyer_state.inventory[0].last_trade_at = 0
    save_state(buyer_id, buyer_state)
    list_item(buyer_id, item_id, 6000)

    reset_player_data(buyer_id, "buyer_d铺", GameStateManager())
    seller_after = load_state(seller_id)
    buyer_after = load_state(buyer_id)

    assert seller_after.cash == cash_before
    assert len(seller_after.inventory) == 1
    assert buyer_after.cash == 10000
    with get_connection() as conn:
        active = conn.execute(
            "SELECT COUNT(*) AS c FROM market_listings WHERE seller_id = ? AND status = 'active'",
            (buyer_id,),
        ).fetchone()["c"]
    assert active == 0
    print("OK: buy, relist, then reset rolls back and cancels buyer listing")


def test_resell_to_third_party_no_rollback():
    seller_id = _create_player("seller_e")
    buyer_id = _create_player("buyer_f")
    third_id = _create_player("third_g", cash=20000)
    cash_before = load_state(seller_id).cash
    listing_id = _seller_list(seller_id, 5000)
    buy_listing(buyer_id, listing_id)

    buyer_state = load_state(buyer_id)
    item_id = buyer_state.inventory[0].id
    buyer_state.inventory[0].last_trade_at = 0
    save_state(buyer_id, buyer_state)
    relist = list_item(buyer_id, item_id, 6000)
    buy_listing(third_id, relist["listing_id"])

    reset_player_data(buyer_id, "buyer_f铺", GameStateManager())
    seller_after = load_state(seller_id)
    third_after = load_state(third_id)

    assert seller_after.cash == cash_before + 4750, "seller should keep income when item was resold"
    assert len(third_after.inventory) == 1
    print("OK: resell to third party then reset does not claw back original seller")


def main():
    init_db()
    test_buy_then_reset()
    test_list_then_reset()
    test_resell_to_third_party_no_rollback()
    print("All rollback scenarios passed.")


if __name__ == "__main__":
    main()
