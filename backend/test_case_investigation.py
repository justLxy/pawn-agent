"""Case dossier investigation flow."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game_state import (
    CASE_INVESTIGATION_ACTIONS,
    Customer,
    GameStateManager,
    Item,
    build_case_clue_pool,
    build_initial_case_state,
    case_state_for_client,
)


def _item(**kwargs) -> Item:
    defaults = dict(
        name="测试玉佩",
        category="Jewelry",
        condition="Good",
        is_fake=True,
        actual_value=5000,
        market_value=6000,
        description="表面温润。",
        story="卖家说是家传，但包装日期对不上。",
        hidden_attrs=["可能关联名人旧藏"],
        authentication_tips=["观察沁色是否自然"],
    )
    defaults.update(kwargs)
    return Item(**defaults)


def _seller_customer(**kwargs) -> Customer:
    item = _item(**kwargs.pop("item_kwargs", {}))
    return Customer(
        name="测试卖家",
        trait=kwargs.get("trait", "fraud"),
        role="seller",
        item=item,
        shop_level=3,
        marketer_active=False,
        fraud_intent=True,
        shop_level_for_case=3,
        appraisal_room_for_case=2,
    )


def test_case_state_hides_clue_pool_from_client():
    customer = _seller_customer()
    public = case_state_for_client(customer.case_state)
    assert "clue_pool" not in public
    assert public["points_max"] >= 3
    assert len(build_case_clue_pool(customer)) >= 3


def test_item_player_view_masks_sensitive_fields():
    item = _item()
    view = item.to_dict(for_player_view=True)
    assert "is_fake" not in view
    assert view["hidden_attrs"] == []
    assert view["authentication_tips"] == []


def test_chat_investigation_reveals_fake_risk():
    state = GameStateManager(initialize=False)
    state.shop_level = 3
    state.facilities["appraisal_room"] = 2
    state.cash = 50000
    customer = _seller_customer()
    state.active_customer = customer
    result = state.investigate_case("chat")
    assert result.get("success") is True
    flags = customer.case_state["flags"]
    assert flags["knows_fake_risk"] is True
    assert flags["graceful_reject"] is True
    assert len(customer.case_state["clues"]) >= 1


def test_graceful_reject_skips_reputation_penalty():
    state = GameStateManager(initialize=False)
    state.reputation = 100
    customer = _seller_customer()
    customer.case_state = build_initial_case_state(customer, 3, 2)
    customer.case_state["flags"]["knows_fake_risk"] = True
    customer.case_state["flags"]["graceful_reject"] = True
    state.active_customer = customer
    before = state.reputation
    result = state.reject()
    assert result.get("success") is True
    assert state.reputation == before


def test_buying_undetected_fake_applies_penalty():
    state = GameStateManager(initialize=False)
    state.daily_summary = {"revenue": 0, "events": []}
    state.cash = 20000
    state.reputation = 50
    customer = _seller_customer()
    customer.current_offer = 3000
    customer.session_closed = None
    state.active_customer = customer
    before_cash = state.cash
    before_rep = state.reputation
    result = state.deal()
    assert result.get("success") is True
    assert state.cash < before_cash - 3000
    assert state.reputation < before_rep


def test_hidden_bonus_boosts_acquired_value():
    state = GameStateManager(initialize=False)
    state.daily_summary = {"revenue": 0, "events": []}
    state.cash = 20000
    customer = _seller_customer(item_kwargs={"is_fake": False, "actual_value": 8000, "market_value": 9000})
    customer.current_offer = 4000
    customer.case_state["flags"]["knows_hidden_bonus"] = True
    state.active_customer = customer
    state.deal()
    acquired = state.inventory[-1]
    assert acquired.actual_value >= 8000


def test_case_actions_registered():
    assert "chat" in CASE_INVESTIGATION_ACTIONS
    assert "records" in CASE_INVESTIGATION_ACTIONS


if __name__ == "__main__":
    test_case_state_hides_clue_pool_from_client()
    test_item_player_view_masks_sensitive_fields()
    test_chat_investigation_reveals_fake_risk()
    test_graceful_reject_skips_reputation_penalty()
    test_buying_undetected_fake_applies_penalty()
    test_hidden_bonus_boosts_acquired_value()
    test_case_actions_registered()
    print("test_case_investigation: ok")
