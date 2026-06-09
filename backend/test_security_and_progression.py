"""Security boundaries, negotiation behavior, and long-run progression."""
import os
import random
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from fastapi import HTTPException
from auth import delete_player_account, register_player
from database import init_db
from game_state import Customer, GameStateManager, Item
from negotiation_engine import decide_negotiation
from online_services import _public_item, buy_listing, list_item, load_state, save_state


def _item(**overrides):
    values = {
        "name": "测试旧表",
        "category": "Jewelry",
        "condition": "Good",
        "is_fake": True,
        "actual_value": 1200,
        "market_value": 9000,
        "description": "用于测试的旧表。",
        "hidden_attrs": ["隐藏签名"],
        "authentication_tips": ["检查机芯编号"],
    }
    values.update(overrides)
    return Item(**values)


def _customer(trait="hesitant", **overrides):
    return Customer(
        name="测试顾客",
        trait=trait,
        role="seller",
        item=_item(),
        shop_level=1,
        marketer_active=False,
        current_offer=10000,
        limit_price=7000,
        fraud_intent=True,
        transaction_prefs=["立即拿现金"],
        persuasion_points=["引用鉴定线索"],
        **overrides,
    )


def _assert_no_secret_keys(value):
    forbidden = {"actual_value", "is_fake", "limit_price", "fraud_intent", "market_value"}
    if isinstance(value, dict):
        assert forbidden.isdisjoint(value.keys())
        for nested in value.values():
            _assert_no_secret_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_no_secret_keys(nested)


def test_client_state_and_market_items_hide_server_secrets():
    state = GameStateManager(initialize=False)
    item = _item()
    customer = _customer()
    state.inventory = [item]
    state.active_customer = customer
    state.daily_customer_queue = [_customer()]
    public = state.to_dict()
    _assert_no_secret_keys(public)
    assert "persuasion_points" not in public["active_customer"]
    assert public["daily_customer_queue"] == []
    assert "action_previews" in public["inventory"][0]

    market_item = _public_item(item)
    _assert_no_secret_keys(market_item)
    assert "market_value" not in market_item

    state.inventory = [item]
    state.cash = 100000
    appraisal = state.appraise_inventory_item(item.id)
    _assert_no_secret_keys(appraisal)
    assert "appraised_fake" in appraisal


def test_repeated_tactics_decay_and_evidence_has_value():
    repeated = _customer()
    first = decide_negotiation(repeated, "市场就这样，我出 4000", 4000, "offer")
    repeated.current_offer = first["new_offer"]
    second = decide_negotiation(repeated, "市场就这样，我出 4000", 4000, "offer")
    assert second["decision_meta"]["repeat_count"] == 1
    assert second["patience_change"] <= first["patience_change"]

    evidence = _customer()
    evidence.case_state["flags"]["knows_fake_risk"] = True
    evidence_result = decide_negotiation(evidence, "鉴定发现机芯编号和来历对不上，我出 4000", 4000, "offer")
    assert evidence_result["decision_meta"]["evidence_used"] is True
    assert evidence_result["new_offer"] <= first["new_offer"]


def test_fixed_seed_thousand_negotiations_keep_traits_distinct():
    random.seed(20260609)
    concessions = {"hardball": [], "eager": [], "hesitant": [], "fraud": [], "expert": []}
    for index in range(1000):
        trait = list(concessions)[index % len(concessions)]
        customer = _customer(trait=trait)
        offer = random.randint(3000, 6500)
        result = decide_negotiation(customer, f"我出 {offer}", offer, "offer")
        concessions[trait].append(10000 - result["new_offer"])
    averages = {trait: sum(values) / len(values) for trait, values in concessions.items()}
    assert averages["eager"] > averages["hesitant"] > averages["hardball"]
    assert averages["eager"] > averages["expert"]


def test_progression_content_and_long_run_economy_stay_playable():
    random.seed(20260609)
    state = GameStateManager()
    assert state.choose_specialization("restoration")["success"]
    assert "error" in state.choose_specialization("jewelry")
    for target_day in (30, 100, 300):
        while state.day < target_day:
            state.day += 1
            state._apply_economy_tick()
            state._refresh_market_trends()
            state._ensure_progression_content()
        assert 0.65 <= state.economy_index <= 2.5
        assert all(0.72 <= value <= 1.5 for value in state.market_trends.values())
        assert state.daily_challenge
        assert state.weekly_challenge
        assert state.market_cycle.get("next_hot_category")


def test_collection_rewards_are_one_time_and_commissions_do_not_refresh_same_day():
    state = GameStateManager()
    state.day = 3
    state._ensure_progression_content()
    first_commission = state.active_commission
    assert first_commission
    state.active_commission = None
    state._ensure_progression_content()
    assert state.active_commission is None

    state.inventory = [
        _item(name=f"套装-{index}", category="Jewelry", is_fake=False, actual_value=1000, market_value=1000)
        for index in range(3)
    ]
    cash_before = state.cash
    state._update_collection_rewards()
    first_reward_cash = state.cash
    state._update_collection_rewards()
    assert first_reward_cash > cash_before
    assert state.cash == first_reward_cash


def test_stale_state_write_is_rejected():
    init_db()
    suffix = uuid.uuid4().hex[:10]
    auth = register_player(f"version_{suffix}", "secure-pass-123", f"版本铺_{suffix}")
    player_id = int(auth["player"]["id"])
    try:
        initial = GameStateManager()
        save_state(player_id, initial)
        first = load_state(player_id)
        stale = load_state(player_id)
        first.cash += 100
        save_state(player_id, first)
        stale.cash += 999999
        with pytest.raises(HTTPException) as exc:
            save_state(player_id, stale)
        assert exc.value.status_code == 409
    finally:
        delete_player_account(player_id)


def test_concurrent_market_purchase_only_settles_once():
    init_db()
    suffix = uuid.uuid4().hex[:10]
    auths = [
        register_player(f"m{role}_{suffix}", "secure-pass-123", f"{role}铺_{suffix}")
        for role in ("s", "a", "b")
    ]
    seller_id, buyer_a_id, buyer_b_id = [int(auth["player"]["id"]) for auth in auths]
    try:
        seller = GameStateManager()
        item = _item(is_fake=False, actual_value=1000, market_value=1000)
        seller.inventory.append(item)
        save_state(seller_id, seller)
        save_state(buyer_a_id, GameStateManager())
        save_state(buyer_b_id, GameStateManager())
        listing_id = list_item(seller_id, item.id, 1000)["listing_id"]

        def attempt(buyer_id):
            try:
                buy_listing(buyer_id, listing_id)
                return "success"
            except HTTPException:
                return "rejected"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (buyer_a_id, buyer_b_id)))

        assert results.count("success") == 1
        assert results.count("rejected") == 1
        owned_ids = [
            owned.id
            for buyer_id in (buyer_a_id, buyer_b_id)
            for owned in load_state(buyer_id).inventory
        ]
        assert owned_ids.count(item.id) == 1
    finally:
        for auth in auths:
            delete_player_account(int(auth["player"]["id"]))
