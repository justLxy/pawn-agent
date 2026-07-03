"""Deterministic, server-authoritative pawn negotiation decisions.

设计原则：经济结果（成交价、让步幅度、是否离场）永远由本模块的确定性规则裁决，
LLM 只负责台词渲染与「说服力评估」这类软性输入——软输入会被 clamp 进合法区间，
不会让顾客做出违反价格方向的决定。这样既保留了「自然语言真正能说服顾客」的智能感，
又杜绝了模型幻觉导致的经济翻车。

三层智能：
1. 跨天记忆（memory）：顾客记得与你的成交次数、被你识破欺诈的次数、历史满意度，
   据此设定初始信任、让步意愿与恩怨修正。
2. 套路识别（tactic_counts / tactic_sequence）：单句重复递减收益，组合连招（如
   「鉴定→压价→装走」）会被识破并免疫，专家型免疫更快。
3. 主动行为（proactive）：急切型会主动催单让价，欺诈型面对证据会紧张松口，
   专家型对复读免疫。
"""
from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional


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

# 一名顾客在单场谈判里会被记住的最近战术序列长度（用于识别组合连招）。
TACTIC_SEQUENCE_MAX = 6


def _memory_modifiers(customer: Any, memory: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """把跨天记忆折算成信任 / 让步 / 恩怨修正。

    memory 来自 state.customer_registry 里该顾客的历史记录，可能字段：
    positive_deals（成交次数）、negative_deals（被识破欺诈次数）、satisfaction。
    没有记忆（新客）时返回中性修正。
    """
    memory = memory or {}
    positive = int(memory.get("positive_deals", 0) or 0)
    negative = int(memory.get("negative_deals", 0) or 0)
    # 感恩：成交越多越愿意让步、初始信任越高（边际递减，最多约 3 笔封顶）。
    gratitude = min(3, positive)
    # 记仇：被识破欺诈越多越防备，信任更低、极端阈值收紧（更难成交）。
    grudge = min(3, negative)
    trust_shift = gratitude * 0.06 - grudge * 0.11
    concession_shift = gratitude * 0.02 - grudge * 0.025
    # 记仇的顾客对「离谱报价」更敏感（extreme 阈值抬高 = 更容易判定离谱）。
    extreme_shift = grudge * 0.05
    return {
        "gratitude": float(gratitude),
        "grudge": float(grudge),
        "trust_shift": trust_shift,
        "concession_shift": concession_shift,
        "extreme_shift": extreme_shift,
    }


def _initial_state(customer: Any, memory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rules = TRAIT_RULES.get(customer.trait, TRAIT_RULES["hesitant"])
    relationship_bonus = 0.12 if customer.relationship_level in ("loyal", "vip") else 0.05 if customer.is_returning else 0.0
    # 隐藏保留价扰动：每位顾客一个固定但玩家不可见的心理价扰动（±6%），
    # 让"精确压到极限价"变成一场赌博而非可解的最优出价。熟客扰动更小（更好谈）。
    noise_span = 0.03 if customer.relationship_level in ("loyal", "vip") else 0.06
    reserve_noise = round(random.uniform(-noise_span, noise_span), 4)
    mem = _memory_modifiers(customer, memory)
    base_trust = max(0.0, min(1.0, customer.satisfaction / 100.0))
    return {
        "urgency": min(1.0, rules["urgency"] + relationship_bonus),
        "trust": max(0.0, min(1.0, base_trust + mem["trust_shift"])),
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
        "tactic_sequence": [],
        "stall_turns": 0,
        "last_player_offer": None,
        "contradictions": 0,
        # 记忆修正持久化，便于 to_dict 序列化后下一轮复用与调试。
        "memory_mod": {
            "gratitude": mem["gratitude"],
            "grudge": mem["grudge"],
            "concession_shift": mem["concession_shift"],
            "extreme_shift": mem["extreme_shift"],
        },
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


# 已知的「组合连招」：玩家按顺序打出这些战术时，老练顾客会识破并免疫。
# 键为连招名，值为需要匹配的战术序列后缀。
COMBO_PATTERNS: Dict[str, List[str]] = {
    "appraise_then_lowball": ["evidence", "price"],          # 鉴定亮线索后立刻猛压价
    "lowball_then_bluff_walk": ["price", "reject"],           # 压价后装作要走逼让步
    "flatter_then_lowball": ["relationship", "price"],        # 先套近乎再压价
}


def _detect_combo(sequence: List[str]) -> Optional[str]:
    for name, pattern in COMBO_PATTERNS.items():
        if len(sequence) >= len(pattern) and sequence[-len(pattern):] == pattern:
            return name
    return None


def _fallback_dialogue(customer: Any, accepted: bool, walk_out: bool, new_offer: int, reason: str) -> str:
    if accepted:
        return f"我把这个数又掂量了一遍。行，就按 ${new_offer:,}，这笔买卖今天定下来。"
    if walk_out:
        return "话已经说到这里了，再磨也没有意思。我先告辞，这笔买卖以后再说。"
    if reason == "repeated":
        return f"这套说法你刚才已经讲过了。要继续谈，就拿出新的依据；我的价还是 ${new_offer:,}。"
    if reason == "combo":
        return f"你这套路我见得多了——先探底再压价那一套，对我没用。价还是 ${new_offer:,}。"
    if reason == "evidence":
        return f"你提的线索确实有分量，我愿意再让一步。现在按 ${new_offer:,} 继续谈。"
    if reason == "extreme":
        return f"这个数离实际太远，我没法认真接。要谈就回到 ${new_offer:,} 附近。"
    if reason == "grudge":
        return f"上回的事我还记着呢，这次别想糊弄我。价我只能给到 ${new_offer:,}。"
    if reason == "proactive_close":
        return f"罢了罢了，我也不想耗着——${new_offer:,}，你要是点头咱现在就结了。"
    if reason == "fraud_nervous":
        return f"你、你查这么细做什么……行吧，${new_offer:,}，别再盘问了成不成？"
    return f"我听明白了，但还没到点头的时候。现在能谈的数是 ${new_offer:,}。"


def _resolve_persuasion(
    persuasion: Optional[Dict[str, Any]],
    has_evidence: bool,
    repeat_count: int,
) -> Dict[str, Any]:
    """把 LLM 说服力评估与关键词证据融合成一个统一的 [0,1] 力度分。

    persuasion（可选）：{"score": 0-1, "hits_weakness": bool}，由 ai_client 评估玩家发言。
    与旧的关键词 has_evidence 取 max 融合——即便没配置 LLM，关键词路径仍然有效。
    重复使用会衰减，逼玩家换真招而不是复读。
    """
    keyword_score = 0.75 if has_evidence else 0.0
    llm_score = 0.0
    hits_weakness = False
    if isinstance(persuasion, dict):
        try:
            llm_score = max(0.0, min(1.0, float(persuasion.get("score", 0.0))))
        except (TypeError, ValueError):
            llm_score = 0.0
        hits_weakness = bool(persuasion.get("hits_weakness", False))
    raw = max(keyword_score, llm_score)
    decay = max(0.25, 1.0 - repeat_count * 0.45)
    effective = raw * decay
    return {
        "raw": raw,
        "effective": effective,
        "hits_weakness": hits_weakness,
        "is_persuasive": effective >= 0.28,
    }


def decide_negotiation(
    customer: Any,
    player_message: str,
    player_offer: Optional[int],
    intent: str,
    negotiation_level: int = 1,
    charm_level: int = 1,
    memory: Optional[Dict[str, Any]] = None,
    persuasion: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state = dict(getattr(customer, "negotiation_state", {}) or _initial_state(customer, memory))
    tactic_counts = dict(state.get("tactic_counts") or {})
    sequence: List[str] = list(state.get("tactic_sequence") or [])
    memory_mod = dict(state.get("memory_mod") or {})
    grudge = float(memory_mod.get("grudge", 0.0))
    gratitude = float(memory_mod.get("gratitude", 0.0))
    flags = (customer.case_state or {}).get("flags") or {}
    has_evidence = bool(flags.get("knows_fake_risk") or flags.get("knows_hidden_bonus")) and any(
        word in player_message for word in EVIDENCE_WORDS
    )
    signature = _tactic_signature(player_message, intent, has_evidence)
    repeat_count = int(tactic_counts.get(signature, 0))
    tactic_counts[signature] = repeat_count + 1
    state["tactic_counts"] = tactic_counts
    sequence.append(signature)
    sequence = sequence[-TACTIC_SEQUENCE_MAX:]
    state["tactic_sequence"] = sequence

    rules = TRAIT_RULES.get(customer.trait, TRAIT_RULES["hesitant"])
    trust = float(state.get("trust", 0.5))
    urgency = float(state.get("urgency", rules["urgency"]))
    skill = min(0.18, negotiation_level * 0.012 + charm_level * 0.008)

    # 说服力：融合 LLM 评估与关键词证据，重复递减。
    persuade = _resolve_persuasion(persuasion, has_evidence, repeat_count)
    persuasion_strength = persuade["effective"]
    evidence_bonus = 0.16 * persuasion_strength
    if persuade["hits_weakness"]:
        evidence_bonus += 0.05

    # 组合连招识别：老练顾客（专家/强硬/欺诈）会识破并免疫，普通顾客识破较慢。
    combo = _detect_combo(sequence)
    combo_savvy = customer.trait in ("expert", "hardball", "fraud")
    combo_penalty = 0.0
    if combo:
        combo_penalty = 0.14 if combo_savvy else 0.06

    # 重复惩罚：专家型对复读免疫更快（惩罚更重）。
    repeat_scale = 0.11 if customer.trait == "expert" else 0.08
    repetition_penalty = min(0.24, repeat_count * repeat_scale) + combo_penalty
    courtesy = 0.04 if any(word in player_message for word in COURTESY_WORDS) else 0.0
    hostility = 0.16 if any(word in player_message for word in HOSTILE_WORDS) else 0.0
    # 记仇的顾客对礼貌收益打折、对敌意更敏感。
    if grudge > 0:
        courtesy *= max(0.3, 1.0 - grudge * 0.25)
        hostility += grudge * 0.03

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
        return _decide_no_offer(
            customer,
            state,
            current,
            skill,
            evidence_bonus,
            courtesy,
            repetition_penalty,
            hostility,
            persuade,
            has_evidence,
            combo,
            repeat_count,
            charm_level,
            grudge,
        )

    offer = max(1, int(player_offer))
    state["last_player_offer"] = offer
    state["stall_turns"] = 0
    reserve_noise = float(state.get("reserve_noise", 0.0))
    extreme_shift = float(memory_mod.get("extreme_shift", 0.0))
    concession_shift = float(memory_mod.get("concession_shift", 0.0))

    if customer.role == "seller":
        # 记仇抬高 extreme 系数 = 更容易判定报价离谱。
        extreme = offer < int(current * (rules["extreme"] + extreme_shift))
        # 保留价叠加隐藏扰动：玩家算不出精确阈值，压极限价有翻车风险。
        effective_limit = int(limit_price * max(0.90, 1.02 - skill - trust * 0.035 - evidence_bonus * 0.35) * (1 + reserve_noise))
        accepted = offer >= current or offer >= effective_limit
        gap = max(0, current - limit_price)
        quality = max(
            0.03,
            rules["concession"] + urgency * 0.08 + skill + evidence_bonus + concession_shift - repetition_penalty - hostility,
        )
        new_offer = min(current, max(limit_price, int(current - gap * min(0.55, quality))))
    else:
        extreme = offer > int(current * (2.2 + rules["extreme"] + extreme_shift))
        effective_limit = int(limit_price * min(1.10, 0.98 + skill + trust * 0.035 + evidence_bonus * 0.35) * (1 + reserve_noise))
        accepted = offer <= current or offer <= effective_limit
        gap = max(0, limit_price - current)
        quality = max(
            0.03,
            rules["concession"] + urgency * 0.08 + skill + evidence_bonus + concession_shift - repetition_penalty - hostility,
        )
        new_offer = max(current, min(limit_price, int(current + gap * min(0.55, quality))))

    if accepted:
        new_offer = min(offer, current) if customer.role == "seller" else max(offer, current)
        patience_change = 0
        walk_out = False
        reason = "accepted"
    else:
        penalty = hostility + repetition_penalty + (0.18 if extreme else 0.0)
        patience_change = -2 if penalty >= 0.30 else -1 if penalty >= 0.10 or extreme else 0
        # 说服到位可回一点耐心，抵消部分流失。
        if persuade["is_persuasive"] and patience_change < 0:
            patience_change += 1
        walk_out = customer.patience + patience_change <= 0
        if combo:
            reason = "combo"
        elif extreme:
            reason = "extreme"
        elif grudge > 0 and repeat_count == 0 and not persuade["is_persuasive"]:
            reason = "grudge"
        elif persuade["is_persuasive"]:
            reason = "evidence"
        elif repeat_count:
            reason = "repeated"
        else:
            reason = "counter"
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
            "persuasion_strength": round(persuasion_strength, 3),
            "hits_weakness": persuade["hits_weakness"],
            "combo": combo,
            "grudge": grudge,
            "gratitude": gratitude,
        },
    }


def _decide_no_offer(
    customer: Any,
    state: Dict[str, Any],
    current: int,
    skill: float,
    evidence_bonus: float,
    courtesy: float,
    repetition_penalty: float,
    hostility: float,
    persuade: Dict[str, Any],
    has_evidence: bool,
    combo: Optional[str],
    repeat_count: int,
    charm_level: int,
    grudge: float,
) -> Dict[str, Any]:
    """玩家在追问 / 说服但未报价时的分支，含顾客主动行为。"""
    stall_turns = int(state.get("stall_turns", 0)) + 1
    state["stall_turns"] = stall_turns
    rules = TRAIT_RULES.get(customer.trait, TRAIT_RULES["hesitant"])
    limit_price = max(1, int(customer.limit_price))

    quality = skill + evidence_bonus + courtesy - repetition_penalty - hostility
    patience_change = 1 if quality >= 0.18 else -1 if quality < -0.08 else 0
    new_offer = current
    reason = "conversation"

    # 主动行为 1：欺诈型面对有效证据/鉴定追问会紧张，主动松口让一小步。
    if customer.trait == "fraud" and persuade["is_persuasive"] and (customer.item.is_fake or customer.fraud_intent):
        gap = (current - limit_price) if customer.role == "seller" else (limit_price - current)
        if gap > 0:
            step = int(gap * 0.14)
            new_offer = current - step if customer.role == "seller" else current + step
            reason = "fraud_nervous"

    # 主动行为 2：急切型被反复拖延（stall），会主动催单让价推动成交。
    elif customer.trait == "eager" and stall_turns >= 2:
        gap = (current - limit_price) if customer.role == "seller" else (limit_price - current)
        if gap > 0:
            step = int(gap * min(0.4, 0.18 + rules["urgency"] * 0.12))
            new_offer = current - step if customer.role == "seller" else current + step
            reason = "proactive_close"
            patience_change = max(patience_change, 0)

    # 主动行为 3：识破组合连招时，专家/强硬型明确点破，不让步。
    elif combo and customer.trait in ("expert", "hardball", "fraud"):
        reason = "combo"
        patience_change = min(patience_change, -1)
    elif has_evidence or persuade["is_persuasive"]:
        reason = "evidence"
    elif repeat_count:
        reason = "repeated"
    elif grudge > 0 and not persuade["is_persuasive"]:
        reason = "grudge"

    if customer.role == "seller":
        new_offer = max(limit_price, min(current, int(new_offer)))
    else:
        new_offer = min(limit_price, max(current, int(new_offer)))

    walk_out = customer.patience + patience_change <= 0
    customer.negotiation_state = state
    return {
        "dialogue": _fallback_dialogue(customer, False, walk_out, new_offer, reason),
        "new_offer": max(1, int(new_offer)),
        "patience_change": patience_change,
        "accepted": False,
        "walk_out": walk_out,
        "parsed_offer": None,
        "decision_reason": reason,
        "decision_meta": {
            "tactic": "conversation",
            "repeat_count": repeat_count,
            "evidence_used": has_evidence,
            "persuasion_strength": round(persuade["effective"], 3),
            "hits_weakness": persuade["hits_weakness"],
            "combo": combo,
            "stall_turns": stall_turns,
        },
    }
