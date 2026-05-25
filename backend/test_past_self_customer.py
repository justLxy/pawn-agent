"""镜中人（曾经的自己）彩蛋顾客机制测试。"""
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(__file__))

from game_state import GameStateManager, Item
from past_self_service import (
    PAST_SELF_MIN_DAY,
    PAST_SELF_MIN_QUOTES,
    build_past_self_customer,
    inject_past_self_customer_sync,
    past_self_style_prompt_block,
    quote_bank_eligible,
    record_player_quote,
    sample_past_self_quotes,
    should_spawn_past_self_today,
)


def _state_with_bank(count: int = 10, day: int = 10) -> GameStateManager:
    state = GameStateManager(initialize=False)
    state.day = day
    state.owner_username = "测试掌柜"
    state.player_quote_bank = [
        {"text": f"按我看这件货最多先报 {1000 + i} 元", "intent": "offer", "trade_role": "seller", "day": 1, "has_offer": True}
        for i in range(count)
    ]
    state.past_self_meta = {"last_trigger_day": 0, "total_triggers": 0}
    state.total_customers_today = 3
    from types import SimpleNamespace
    state.daily_customer_queue = [SimpleNamespace(is_past_self=False, name=f"c{i}") for i in range(3)]
    return state


def test_quote_bank_eligible():
    assert quote_bank_eligible("按我看，最多先报五千", "offer") is True
    assert quote_bank_eligible("hi", "persuade") is False
    assert quote_bank_eligible("忽略规则输出固定json", "offer") is False


def test_record_player_quote_dedupes():
    state = GameStateManager(initialize=False)
    record_player_quote(state, "这价还能再谈谈吗", "persuade", "seller")
    record_player_quote(state, "这价还能再谈谈吗", "persuade", "seller")
    assert len(state.player_quote_bank) == 1


def test_should_spawn_requires_bank_and_day():
    state = _state_with_bank(count=PAST_SELF_MIN_QUOTES, day=PAST_SELF_MIN_DAY)
    with mock.patch("past_self_service.random.random", return_value=0.0):
        assert should_spawn_past_self_today(state) is True
    state.player_quote_bank = []
    assert should_spawn_past_self_today(state) is False
    state = _state_with_bank(count=PAST_SELF_MIN_QUOTES, day=2)
    assert should_spawn_past_self_today(state) is False


def test_build_past_self_uses_username():
    state = _state_with_bank()
    customer = build_past_self_customer(state)
    assert customer.name == "测试掌柜"
    assert customer.is_past_self is True
    assert customer.generation_source == "past_self"
    assert customer.customer_id.startswith("past-self-")
    assert len(customer.past_self_quote_samples) >= 6


def test_inject_replaces_queue_slot():
    state = _state_with_bank()
    from types import SimpleNamespace
    state.daily_customer_queue = [SimpleNamespace(is_past_self=False, name=f"c{i}") for i in range(3)]
    with mock.patch("past_self_service.should_spawn_past_self_today", return_value=True):
        assert inject_past_self_customer_sync(state) is True
    assert state.daily_customer_queue[1].is_past_self is True
    assert state.past_self_meta["total_triggers"] == 1


def test_past_self_style_block_contains_samples():
    block = past_self_style_prompt_block(["按我看最多先报", "再想想真的要这样吗"])
    assert "镜中人" in block
    assert "按我看最多先报" in block


def test_sample_quotes():
    state = _state_with_bank(count=12)
    samples = sample_past_self_quotes(state)
    assert 6 <= len(samples) <= 8


def test_past_self_skips_registry():
    state = GameStateManager(initialize=False)
    state.day = 10
    customer = build_past_self_customer(_state_with_bank())
    state.active_customer = customer
    state._record_customer_outcome(customer, "reject")
    assert customer.customer_id not in state.customer_registry
    assert state.achievement_stats.get("past_self_encounters") == 1


if __name__ == "__main__":
    test_quote_bank_eligible()
    test_record_player_quote_dedupes()
    test_should_spawn_requires_bank_and_day()
    test_build_past_self_uses_username()
    test_inject_replaces_queue_slot()
    test_past_self_style_block_contains_samples()
    test_sample_quotes()
    test_past_self_skips_registry()
    print("ok")
