"""Negotiation dialogue normalization must not stomp non-price AI replies."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app import normalize_negotiation_dialogue
from game_state import Customer, Item


def _seller():
    item = Item("羽毛笔", "Historical", "Good", False, 5000, 6000, "旧羽毛笔")
    return Customer(
        name="老陈",
        trait="hardball",
        role="seller",
        item=item,
        shop_level=1,
        marketer_active=False,
        shop_level_for_case=1,
        appraisal_room_for_case=1,
    )


def test_question_intent_keeps_authenticity_reply():
    customer = _seller()
    ai_line = "老陈把笔转了个面：「掌柜的，你问得细。这笔尖包浆看着老，纸匣也还在，我不敢拍胸脯说百分百，但不像新仿的。」"
    result = normalize_negotiation_dialogue(
        customer,
        ai_line,
        accepted=False,
        walk_out=False,
        new_offer=7595,
        intent="question",
        has_price_offer=False,
    )
    assert result == ai_line


def test_deal_marker_in_descriptive_text_not_confused_with_肯定():
    customer = _seller()
    ai_line = "老陈点点头：「肯定是老货，包装纸都泛黄了，但价钱还得按我说的来。」"
    result = normalize_negotiation_dialogue(
        customer,
        ai_line,
        accepted=False,
        walk_out=False,
        new_offer=7595,
        intent="offer",
        has_price_offer=True,
    )
    assert "肯定是老货" in result


def test_false_deal_claim_still_replaced():
    customer = _seller()
    ai_line = "老陈一拍桌子：「行，就成交了，$7595 拿走！」"
    result = normalize_negotiation_dialogue(
        customer,
        ai_line,
        accepted=False,
        walk_out=False,
        new_offer=7595,
        intent="offer",
        has_price_offer=True,
    )
    assert "这个价太低" in result or "诚意" in result


if __name__ == "__main__":
    test_question_intent_keeps_authenticity_reply()
    test_deal_marker_in_descriptive_text_not_confused_with_肯定()
    test_false_deal_claim_still_replaced()
    print("test_negotiation_dialogue_normalize: ok")
