"""Stale negotiation finalize guard (reject while stream in flight)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import build_stale_negotiation_payload, is_stale_negotiation_finalize
from game_state import Customer, GameStateManager, Item


def _customer(customer_id: str = "cust-a", session_closed=None) -> Customer:
    item = Item(
        name="测试怀表",
        category="Jewelry",
        condition="Good",
        is_fake=False,
        actual_value=1000,
        market_value=1200,
        description="测试物品",
        story="测试",
        hidden_attrs=[],
        authentication_tips=[],
    )
    customer = Customer(name="老王", trait="normal", role="seller", item=item, shop_level=1, marketer_active=False)
    customer.customer_id = customer_id
    customer.session_closed = session_closed
    return customer


def test_stale_when_session_closed():
    state = GameStateManager()
    state.active_customer = _customer(session_closed="walk_out")
    assert is_stale_negotiation_finalize(state, "cust-a") is True


def test_stale_when_customer_changed():
    state = GameStateManager()
    state.active_customer = _customer(customer_id="cust-b")
    assert is_stale_negotiation_finalize(state, "cust-a") is True


def test_not_stale_during_active_negotiation():
    state = GameStateManager()
    state.active_customer = _customer()
    assert is_stale_negotiation_finalize(state, "cust-a") is False


def test_stale_payload_marks_stale():
    state = GameStateManager()
    state.active_customer = _customer(session_closed="walk_out")
    player = {"id": 1, "shop_name": "测试当铺"}
    payload = build_stale_negotiation_payload(player, state)
    assert payload["stale"] is True
    assert payload["negotiation"]["stale"] is True
    assert payload["deal_completed"] is False


if __name__ == "__main__":
    test_stale_when_session_closed()
    test_stale_when_customer_changed()
    test_not_stale_during_active_negotiation()
    test_stale_payload_marks_stale()
    print("ok")
