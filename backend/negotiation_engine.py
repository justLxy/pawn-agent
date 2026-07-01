"""Deterministic, server-authoritative pawn negotiation decisions."""
from __future__ import annotations

import random
import re
from typing import Any, Dict, Optional


TRAIT_RULES: Dict[str, Dict[str, float]] = {
    "hardball": {"concession": 0.10, "urgency": 0.25, "extreme": 0.42},
    "eager": {"concession": 0.24, "urgency": 0.82, "extreme": 0.30},
    "hesitant": {"concession": 0.15, "urgency": 0.50, "extreme": 0.34},
    "fraud": {"concession": 0.12, "urgency": 0.62, "extreme": 0.38},
    "expert": {"concession": 0.09, "urgency": 0.32, "extreme": 0.46},
}

EVIDENCE_WORDS = ("鉴定", "真伪", "来历", "来源", "成色", "款识", "材质", "记录", "线索", "包浆")
COURTESY_WORDS = ("请", "谢谢", "理解", "合作", "长期", "老顾客", "现金", "立刻付款")
HOSTILE_WORDS = ("骗", "滚", "蠢", "垃圾", "闭嘴", "宰", "坑我")


def _initial_state(customer: Any) -> Dict[str, Any]:
    rules = TRAIT_RULES.get(customer.trait, TRAIT_RULES["hesitant"])
    relationship_bonus = 0.12 if customer.relationship_level in ("loyal", "vip") else 0.05 if customer.is_returning else 0.0
    # 隐藏保留价扰动：每位顾客一个固定但玩家不可见的心理价扰动（±6%），
    # 让"精确压到极限价"变成一场赌博而非可解的最优出价。熟客扰动更小（更好谈）。
    noise_span = 0.03 if customer.relationship_level in ("loyal", "vip") else 0.06
    reserve_noise = round(random.uniform(-noise_span, noise_span), 4)
    return {
        "urgency": min(1.0, rules["urgency"] + relationship_bonus),
        "trust": max(0.0, min(1.0, customer.satisfaction / 100.0)),
        "reserve_noise": reserve_noise,
        "strategy": {
            "hardball": "anchor",
            "eager": "close_fast",
            "hesitant": "seek_reassurance",
            "fraud": "deflect",
            "expert": "evidence_first",
        }.get(customer.trait, "balanced"),
        "concession_count": 0,
        "tactic_counts": {},
        "last_player_offer": None,
        "contradictions": 0,
    }


def _tactic_signature(message: str, intent: str, has_evidence: bool) -> str:
    if intent in ("accept", "reject", "question"):
        return intent
    if has_evidence:
        return "evidence"
    if any(word in message for word in COURTESY_WORDS):
        return "relationship"
    if any(word in message for word in HOSTILE_WORDS):
        return "hostile"
    return "price" if re.search(r"\d", message) else "generic"


def _fallback_dialogue(customer: Any, accepted: bool, walk_out: bool, new_offer: int, reason: str) -> str:
    if accepted:
        return f"我把这个数又掂量了一遍。行，就按 ${new_offer:,}，这笔买卖今天定下来。"
    if walk_out:
        return "话已经说到这里了，再磨也没有意思。我先告辞，这笔买卖以后再说。"
    if reason == "repeated":
        return f"这套说法你刚才已经讲过了。要继续谈，就拿出新的依据；我的价还是 ${new_offer:,}。"
    if reason == "evidence":
        return f"你提的线索确实有分量，我愿意再让一步。现在按 ${new_offer:,} 继续谈。"
    if reason == "extreme":
        return f"这个数离实际太远，我没法认真接。要谈就回到 ${new_offer:,} 附近。"
    return f"我听明白了，但还没到点头的时候。现在能谈的数是 ${new_offer:,}。"


def decide_negotiation(
    customer: Any,
    player_message: str,
    player_offer: Optional[int],
    intent: str,
    negotiation_level: int = 1,
    charm_level: int = 1,
) -> Dict[str, Any]:
    state = dict(getattr(customer, "negotiation_state", {}) or _initial_state(customer))
    tactic_counts = dict(state.get("tactic_counts") or {})
    flags = (customer.case_state or {}).get("flags") or {}
    has_evidence = bool(flags.get("knows_fake_risk") or flags.get("knows_hidden_bonus")) and any(
        word in player_message for word in EVIDENCE_WORDS
    )
    signature = _tactic_signature(player_message, intent, has_evidence)
    repeat_count = int(tactic_counts.get(signature, 0))
    tactic_counts[signature] = repeat_count + 1
    state["tactic_counts"] = tactic_counts

    rules = TRAIT_RULES.get(customer.trait, TRAIT_RULES["hesitant"])
    trust = float(state.get("trust", 0.5))
    urgency = float(state.get("urgency", rules["urgency"]))
    skill = min(0.18, negotiation_level * 0.012 + charm_level * 0.008)
    # 证据加成随重复使用递减：同一套"亮线索"说辞刷第二、三次收益骤降，逼玩家换真招
    evidence_bonus = (0.16 * max(0.25, 1.0 - repeat_count * 0.45)) if has_evidence else 0.0
    repetition_penalty = min(0.22, repeat_count * 0.08)
    courtesy = 0.04 if any(word in player_message for word in COURTESY_WORDS) else 0.0
    hostility = 0.16 if any(word in player_message for word in HOSTILE_WORDS) else 0.0

    role_contradiction = (
        customer.role == "seller" and any(marker in player_message for marker in ("我卖给你", "你来买"))
    ) or (
        customer.role == "buyer" and any(marker in player_message for marker in ("我收你的", "你卖给我"))
    )
    if role_contradiction:
        state["contradictions"] = int(state.get("contradictions", 0)) + 1
        hostility += 0.10

    trust = max(0.0, min(1.0, trust + courtesy + evidence_bonus * 0.4 - hostility - repetition_penalty * 0.3))
    state["trust"] = trust
    current = max(1, int(customer.current_offer))
    limit_price = max(1, int(customer.limit_price))

    if intent == "reject":
        state["last_player_offer"] = player_offer
        customer.negotiation_state = state
        return {
            "dialogue": _fallback_dialogue(customer, False, True, current, "reject"),
            "new_offer": current,
            "patience_change": -1,
            "accepted": False,
            "walk_out": True,
            "parsed_offer": player_offer,
            "decision_reason": "reject",
        }

    if intent == "accept" and player_offer is None:
        player_offer = current

    if player_offer is None:
        quality = skill + evidence_bonus + courtesy - repetition_penalty - hostility
        patience_change = 1 if quality >= 0.18 else -1 if quality < -0.08 else 0
        customer.negotiation_state = state
        reason = "evidence" if has_evidence else "repeated" if repeat_count else "conversation"
        return {
            "dialogue": _fallback_dialogue(customer, False, False, current, reason),
            "new_offer": current,
            "patience_change": patience_change,
            "accepted": False,
            "walk_out": customer.patience + patience_change <= 0,
            "parsed_offer": None,
            "decision_reason": reason,
        }

    offer = max(1, int(player_offer))
    state["last_player_offer"] = offer
    reserve_noise = float(state.get("reserve_noise", 0.0))
    if customer.role == "seller":
        extreme = offer < int(current * rules["extreme"])
        # 保留价叠加隐藏扰动：玩家算不出精确阈值，压极限价有翻车风险
        effective_limit = int(limit_price * max(0.90, 1.02 - skill - trust * 0.035 - evidence_bonus * 0.35) * (1 + reserve_noise))
        accepted = offer >= current or offer >= effective_limit
        gap = max(0, current - limit_price)
        quality = max(0.03, rules["concession"] + urgency * 0.08 + skill + evidence_bonus - repetition_penalty - hostility)
        new_offer = min(current, max(limit_price, int(current - gap * min(0.55, quality))))
    else:
        extreme = offer > int(current * (2.2 + rules["extreme"]))
        effective_limit = int(limit_price * min(1.10, 0.98 + skill + trust * 0.035 + evidence_bonus * 0.35) * (1 + reserve_noise))
        accepted = offer <= current or offer <= effective_limit
        gap = max(0, limit_price - current)
        quality = max(0.03, rules["concession"] + urgency * 0.08 + skill + evidence_bonus - repetition_penalty - hostility)
        new_offer = max(current, min(limit_price, int(current + gap * min(0.55, quality))))

    if accepted:
        new_offer = min(offer, current) if customer.role == "seller" else max(offer, current)
        patience_change = 0
        walk_out = False
        reason = "accepted"
    else:
        penalty = hostility + repetition_penalty + (0.18 if extreme else 0.0)
        patience_change = -2 if penalty >= 0.30 else -1 if penalty >= 0.10 or extreme else 0
        walk_out = customer.patience + patience_change <= 0
        reason = "extreme" if extreme else "evidence" if has_evidence else "repeated" if repeat_count else "counter"
        state["concession_count"] = int(state.get("concession_count", 0)) + (1 if new_offer != current else 0)

    customer.negotiation_state = state
    return {
        "dialogue": _fallback_dialogue(customer, accepted, walk_out, new_offer, reason),
        "new_offer": max(1, int(new_offer)),
        "patience_change": patience_change,
        "accepted": accepted,
        "walk_out": walk_out,
        "parsed_offer": offer,
        "decision_reason": reason,
        "decision_meta": {
            "tactic": signature,
            "repeat_count": repeat_count,
            "evidence_used": has_evidence,
        },
    }
