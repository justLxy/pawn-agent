"""Negotiation economic reconciliation (screenshot regression)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import format_offer_change_narration, normalize_negotiation_dialogue, terminal_negotiation_dialogue
from game_state import Customer, Item
from negotiation_economics import (
    dialogue_contradicts_economics,
    negotiation_deal_price,
    reconcile_negotiation_economics,
    should_auto_accept_negotiation,
)


def _seller_customer(current_offer: int = 8000, limit_price: int = 5500):
    item = Item("龙纹古瓷算盘", "Historical", "Good", False, 8000, 9000, "旧算盘")
    return Customer(
        name="老陈",
        trait="hardball",
        role="seller",
        item=item,
        current_offer=current_offer,
        limit_price=limit_price,
        shop_level=1,
        marketer_active=False,
        shop_level_for_case=1,
        appraisal_room_for_case=1,
    )


def test_seller_auto_accept_when_player_bids_above_ask():
    customer = _seller_customer(current_offer=7000)
    ai = {
        "dialogue": "老陈把货往回一收：「这个价太低，要谈至少得看见 $7,000 的诚意。」",
        "new_offer": 7000,
        "patience_change": -1,
        "accepted": False,
        "walk_out": False,
    }
    result = reconcile_negotiation_economics(customer, ai, player_offer=10000, intent="offer")
    assert result["accepted"] is True
    assert result["new_offer"] == 7000
    assert result["walk_out"] is False


def test_deal_price_is_min_bid_and_ask_for_acquisition():
    assert negotiation_deal_price("seller", 10000, 7000) == 7000
    assert negotiation_deal_price("seller", 5000, 7000) == 5000


def test_dialogue_contradicts_when_bid_exceeds_floor():
    assert dialogue_contradicts_economics(
        "seller",
        "这个价太低，至少 $7,000 诚意",
        10000,
        7000,
        8000,
    )


def test_normalize_replaces_contradictory_refusal():
    customer = _seller_customer(current_offer=7000)
    line = normalize_negotiation_dialogue(
        customer,
        "老陈：「10000 还太低，至少 7000 诚意。」",
        False,
        False,
        7000,
        intent="offer",
        has_price_offer=True,
        player_offer=10000,
    )
    assert "太低" not in line or "不低" in line


def test_narration_includes_player_bid():
    text = format_offer_change_narration("seller", 8000, 7000, player_offer=10000)
    assert "降至 $7,000" in text
    assert "你已出价 $10,000" in text


def test_terminal_seller_reject_when_bid_already_high():
    customer = _seller_customer()
    line = terminal_negotiation_dialogue(customer, False, False, 8000, player_offer=10000)
    assert "太低" not in line
    assert "$10,000" in line


def test_should_auto_accept_seller():
    assert should_auto_accept_negotiation("seller", 10000, 7000, 5500, "offer")
    assert not should_auto_accept_negotiation("seller", 5000, 7000, 6000, "offer")


def test_ai_accept_with_ask_price_reconciled_to_player_bid():
    """Regression: player $2500 vs ask $3440 — accepted dialogue must not stay at $3440."""
    customer = _seller_customer(current_offer=3440, limit_price=2400)
    ai = {
        "dialogue": "行，$3,440，这件东西归你。",
        "new_offer": 3440,
        "patience_change": 0,
        "accepted": True,
        "walk_out": False,
    }
    result = reconcile_negotiation_economics(customer, ai, player_offer=2500, intent="offer")
    assert result["accepted"] is True
    assert result["new_offer"] == 2500


def test_ai_false_accept_below_limit_becomes_counter():
    customer = _seller_customer(current_offer=3440, limit_price=3200)
    ai = {
        "dialogue": "行，成交。",
        "new_offer": 3440,
        "patience_change": 0,
        "accepted": True,
        "walk_out": False,
    }
    result = reconcile_negotiation_economics(customer, ai, player_offer=2500, intent="offer")
    assert result["accepted"] is False
    assert result["new_offer"] <= 3440
    assert result.get("_force_terminal_dialogue") is True


def test_accepted_terminal_dialogue_uses_deal_price_not_ask():
    customer = _seller_customer(current_offer=3440, limit_price=2400)
    line = terminal_negotiation_dialogue(customer, True, False, 2500, player_offer=2500)
    assert "$2,500" in line
    assert "$3,440" not in line


if __name__ == "__main__":
    test_seller_auto_accept_when_player_bids_above_ask()
    test_deal_price_is_min_bid_and_ask_for_acquisition()
    test_dialogue_contradicts_when_bid_exceeds_floor()
    test_normalize_replaces_contradictory_refusal()
    test_narration_includes_player_bid()
    test_terminal_seller_reject_when_bid_already_high()
    test_should_auto_accept_seller()
    test_ai_accept_with_ask_price_reconciled_to_player_bid()
    test_ai_false_accept_below_limit_becomes_counter()
    test_accepted_terminal_dialogue_uses_deal_price_not_ask()
    print("test_negotiation_economics: ok")
