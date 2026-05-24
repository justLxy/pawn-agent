"""Ensure buyer/seller customer copy stays consistent with trade role."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game_state import (
    Customer,
    Item,
    customer_dialogue_conflicts_role,
    negotiation_item_fields,
    normalize_customer_backstory,
)


def _item(**kwargs) -> Item:
  defaults = dict(
      name="清代白玉观音吊坠",
      category="Jewelry",
      condition="Good",
      is_fake=False,
      actual_value=30000,
      market_value=32000,
      description="玉质温润，雕工细腻。",
      story="赵二曾带着家传玉佩来典当，老母病重急用钱。",
  )
  defaults.update(kwargs)
  return Item(**defaults)


def test_buyer_backstory_rejects_seller_motivation():
    raw = "家中老母病重急用钱，想卖掉玉佩换钱。"
    fixed = normalize_customer_backstory("buyer", "赵二", "清代白玉观音吊坠", "Jewelry", raw)
    assert "卖" not in fixed or "看中" in fixed
    assert "典当" not in fixed


def test_buyer_negotiation_item_story_is_shop_inventory():
    fields = negotiation_item_fields("buyer", _item())
    assert "店内库存" in fields["item_story"]
    assert "赵二曾带着" not in fields["item_story"]


def test_buyer_dialogue_conflict_detects_pawn_speech():
    pawn_line = "掌柜的，我想把这块玉佩典当给你，你给个价收不收？"
    assert customer_dialogue_conflicts_role(pawn_line, "buyer")
    shop_line = "掌柜的，你柜里这件观音吊坠，我最多出两万八，成不成？"
    assert not customer_dialogue_conflicts_role(shop_line, "buyer")


def test_buyer_customer_normalizes_backstory_on_init():
    customer = Customer(
        name="赵二",
        trait="eager",
        role="buyer",
        item=_item(),
        shop_level=1,
        marketer_active=False,
        backstory="想卖掉玉佩换钱给母亲治病。",
    )
    assert customer_dialogue_conflicts_role(customer.backstory, "buyer") is False
    ctx = customer.negotiation_context()
    assert ctx["role"] == "buyer"
    assert "店内库存" in ctx["item_story"]
    assert "trade_mode_cn" in ctx


if __name__ == "__main__":
    test_buyer_backstory_rejects_seller_motivation()
    test_buyer_negotiation_item_story_is_shop_inventory()
    test_buyer_dialogue_conflict_detects_pawn_speech()
    test_buyer_customer_normalizes_backstory_on_init()
    print("test_customer_trade_role: ok")
