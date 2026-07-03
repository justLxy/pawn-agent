"""阶段一/二谈判智能：跨天记忆、套路识别、主动行为、说服力融合。"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game_state import Customer, Item
from negotiation_engine import _initial_state, _memory_modifiers, decide_negotiation


def _seller(current_offer=8000, limit_price=5500, trait="hardball", satisfaction=50):
    item = Item("龙纹古瓷算盘", "Historical", "Good", False, 8000, "旧算盘", market_value=9000)
    return Customer(
        name="老陈",
        trait=trait,
        role="seller",
        item=item,
        current_offer=current_offer,
        limit_price=limit_price,
        shop_level=1,
        marketer_active=False,
        satisfaction=satisfaction,
        shop_level_for_case=1,
        appraisal_room_for_case=1,
    )


def _fraud_seller(current_offer=8000, limit_price=5500):
    item = Item("鎏金怀表", "Antiquities", "Good", True, 900, "怀表", market_value=8000)
    c = Customer(
        name="油嘴老王",
        trait="fraud",
        role="seller",
        item=item,
        current_offer=current_offer,
        limit_price=limit_price,
        shop_level=1,
        marketer_active=False,
        shop_level_for_case=1,
        appraisal_room_for_case=1,
    )
    c.fraud_intent = True
    return c


# ---------- 阶段一：跨天记忆 ----------

def test_memory_modifiers_gratitude_and_grudge():
    grateful = _memory_modifiers(_seller(), {"positive_deals": 3, "negative_deals": 0})
    grudged = _memory_modifiers(_seller(), {"positive_deals": 0, "negative_deals": 3})
    assert grateful["trust_shift"] > 0
    assert grateful["concession_shift"] > 0
    assert grudged["trust_shift"] < 0
    assert grudged["extreme_shift"] > 0


def test_initial_state_trust_reflects_memory():
    base = _initial_state(_seller(satisfaction=50), memory=None)
    grateful = _initial_state(_seller(satisfaction=50), memory={"positive_deals": 3})
    grudged = _initial_state(_seller(satisfaction=50), memory={"negative_deals": 3})
    assert grateful["trust"] > base["trust"]
    assert grudged["trust"] < base["trust"]
    assert grateful["memory_mod"]["gratitude"] == 3.0


def test_grateful_customer_concedes_more_than_grudged():
    """同样的中间报价，感恩顾客的还价应比记仇顾客更接近成交（要价更低）。"""
    grateful = _seller(current_offer=8000, limit_price=5500)
    grudged = _seller(current_offer=8000, limit_price=5500)
    grateful.negotiation_state = _initial_state(grateful, {"positive_deals": 3})
    grudged.negotiation_state = _initial_state(grudged, {"negative_deals": 3})
    r_grateful = decide_negotiation(grateful, "我出 6000，行情就这样", 6000, "offer")
    r_grudged = decide_negotiation(grudged, "我出 6000，行情就这样", 6000, "offer")
    # 感恩顾客让步幅度更大 => 新要价更低（对玩家更有利）。
    assert r_grateful["new_offer"] <= r_grudged["new_offer"]


# ---------- 阶段一：套路组合识别 ----------

def test_combo_appraise_then_lowball_detected():
    customer = _seller(trait="expert", current_offer=8000, limit_price=5500)
    customer.case_state.setdefault("flags", {})["knows_fake_risk"] = True
    # 第一步：亮鉴定线索（evidence）
    decide_negotiation(customer, "我鉴定过了，这成色有来历问题", None, "persuade")
    # 第二步：立刻猛压价（price）——构成 appraise_then_lowball 连招
    result = decide_negotiation(customer, "所以我出 4000", 4000, "offer")
    assert result["decision_meta"]["combo"] == "appraise_then_lowball"


def test_repeated_tactic_decays():
    """复读同一句说服，收益递减，第二次不应比第一次更好谈。"""
    customer = _seller(trait="hesitant", current_offer=8000, limit_price=5500)
    customer.case_state.setdefault("flags", {})["knows_fake_risk"] = True
    first = decide_negotiation(customer, "看鉴定来历，这价得降", None, "persuade")
    second = decide_negotiation(customer, "看鉴定来历，这价得降", None, "persuade")
    assert second["decision_meta"]["repeat_count"] >= 1


# ---------- 阶段一：主动行为 ----------

def test_eager_customer_proactively_closes_on_stall():
    customer = _seller(trait="eager", current_offer=8000, limit_price=5500)
    decide_negotiation(customer, "我再想想这东西的来历", None, "persuade")
    result = decide_negotiation(customer, "你这货到底哪来的", None, "question")
    assert result["decision_reason"] == "proactive_close"
    # 急切型主动让价：卖家要价应低于初始要价。
    assert result["new_offer"] < 8000


def test_fraud_customer_gets_nervous_under_persuasion():
    customer = _fraud_seller(current_offer=8000, limit_price=5500)
    result = decide_negotiation(
        customer,
        "这来历不对，我要深度鉴定",
        None,
        "persuade",
        persuasion={"score": 0.8, "hits_weakness": True},
    )
    assert result["decision_reason"] == "fraud_nervous"
    assert result["new_offer"] < 8000


# ---------- 阶段二：说服力融合 ----------

def test_persuasion_score_helps_concession():
    """高说服力分应让卖家让步更多（新要价更低）。"""
    weak = _seller(current_offer=8000, limit_price=5500)
    strong = _seller(current_offer=8000, limit_price=5500)
    r_weak = decide_negotiation(weak, "便宜点吧", 6000, "offer", persuasion={"score": 0.05})
    r_strong = decide_negotiation(strong, "市场行情差，这价我出 6000", 6000, "offer", persuasion={"score": 0.9})
    assert r_strong["new_offer"] <= r_weak["new_offer"]


def test_persuasion_never_flips_price_direction_seller():
    """即便说服力满分，收购时顾客要价也不该低于其底线 limit_price。"""
    customer = _seller(current_offer=8000, limit_price=5500)
    result = decide_negotiation(customer, "无敌理由", 6000, "offer", persuasion={"score": 1.0, "hits_weakness": True})
    assert result["new_offer"] >= 5500


def test_persuasion_absent_falls_back_to_keywords():
    """不传 persuasion 时，关键词证据路径仍有效（向后兼容）。"""
    customer = _seller(trait="hesitant", current_offer=8000, limit_price=5500)
    customer.case_state.setdefault("flags", {})["knows_fake_risk"] = True
    result = decide_negotiation(customer, "根据鉴定来历，这价得再商量", None, "persuade")
    assert result["decision_meta"]["evidence_used"] is True


def test_backward_compatible_no_memory_no_persuasion():
    """完全不传新参数，行为应与旧签名一致、不报错。"""
    customer = _seller(current_offer=8000, limit_price=5500)
    result = decide_negotiation(customer, "我出 7000", 7000, "offer")
    assert result["accepted"] is True
    assert result["new_offer"] == 7000


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("test_negotiation_intelligence: ok")
