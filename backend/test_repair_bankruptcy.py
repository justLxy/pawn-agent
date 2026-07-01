"""修复失败代价 + 破产递增代价：确保风险/回报张力。"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(__file__))

from game_state import GameStateManager, Item


def _repairing_item(condition="Good", market_value=10000, actual_value=8000):
    item = Item("待修古物", "Antiquities", condition, False, actual_value,
                "测试", market_value=market_value)
    item.status = "repairing"
    item.repair_days_remaining = 1
    return item


def test_repair_failure_now_reduces_market_value():
    random.seed(1)
    # 找一个必失败的场景：0 级技能 + 强制随机失败
    state = GameStateManager()
    item = _repairing_item(market_value=10000)
    state.inventory = [item]
    # 强制失败且不触发 botch：patch random 使 success_chance 判定失败、botch 判定 False
    seq = iter([0.99, 0.99])  # 第一个>success_chance→失败；第二个>0.28→非botch
    import game_state as gs
    orig = gs.random.random
    gs.random.random = lambda: next(seq, 0.99)
    try:
        state._process_repairs()
    finally:
        gs.random.random = orig
    # 市值必须下降（旧逻辑只降 actual_value，此处验证回归修复）
    assert item.market_value < 10000, f"修复失败未下调市值：{item.market_value}"


def test_repair_botch_downgrades_condition():
    state = GameStateManager()
    item = _repairing_item(condition="Good", market_value=10000)
    state.inventory = [item]
    import game_state as gs
    seq = iter([0.99, 0.01])  # 失败 + botch(<0.28)
    orig = gs.random.random
    gs.random.random = lambda: next(seq, 0.01)
    try:
        state._process_repairs()
    finally:
        gs.random.random = orig
    assert item.condition == "Poor", f"botch 未降级成色：{item.condition}"
    assert item.market_value <= 7300


def test_bankruptcy_streak_escalates_interest_and_resets():
    state = GameStateManager()
    state.cash = 100
    state.day = 3
    # 制造巨额固定支出使其破产：雇满员工 + 高设施不易，改为直接压现金
    state.cash = -5000  # 结算前的现金；end_day 会再扣成本，必然告急
    state.day_ended = False
    r1 = state.end_day()
    assert state.bankruptcy_streak == 1
    # 第二天继续告急 → 利率上调
    state.day_ended = False
    state.day += 1
    state.cash = -5000
    rate_before = state.loan["interest_rate"]
    state.end_day()
    assert state.bankruptcy_streak == 2
    assert state.loan["interest_rate"] > rate_before, "连续告急未上调利率"
    # 恢复偿付能力后归零
    state.day_ended = False
    state.day += 1
    state.cash = 500000
    state.end_day()
    assert state.bankruptcy_streak == 0
