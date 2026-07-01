"""反套利：刚从玩家市场/同业购入的货，冷却期内系统出售不给正差价。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from game_state import GameStateManager, Item, RESELL_COOLDOWN_SECONDS


def _stored_item(purchase_price: int, market_value: int, last_trade_at=None) -> Item:
    item = Item(
        "测试藏品", "Antiquities", "Good", False, market_value,
        "用于反套利测试", rarity="common", market_value=market_value,
        last_trade_at=last_trade_at,
    )
    item.status = "stored"
    item.purchase_price = purchase_price
    return item


def _state_with(item: Item) -> GameStateManager:
    state = GameStateManager()
    state.inventory = [item]
    state.cash = 0
    return state


def test_fresh_market_purchase_cannot_be_flipped_for_profit():
    # 以远低于市值的价格从市场购入，last_trade_at 为刚刚
    item = _stored_item(purchase_price=100, market_value=10000, last_trade_at=int(time.time()))
    state = _state_with(item)
    result = state.sell_item(item.id)
    assert result.get("success")
    # 冷却期内最多按购入价回收，不能靠差价套利
    assert result["price"] <= 100, f"套利未被拦截，卖出价 {result['price']}"


def test_cooldown_expired_purchase_sells_at_market():
    old = int(time.time()) - RESELL_COOLDOWN_SECONDS - 10
    item = _stored_item(purchase_price=100, market_value=10000, last_trade_at=old)
    state = _state_with(item)
    result = state.sell_item(item.id)
    assert result.get("success")
    # 冷却已过，正常按市值区间出售，远高于购入价
    assert result["price"] > 100


def test_walkin_purchase_unaffected():
    # 散客收来的货没有 last_trade_at，不受冷却影响
    item = _stored_item(purchase_price=100, market_value=10000, last_trade_at=None)
    state = _state_with(item)
    result = state.sell_item(item.id)
    assert result.get("success")
    assert result["price"] > 100
