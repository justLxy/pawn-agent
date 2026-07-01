"""Hard economic checks for pawn negotiation (AI output reconciliation)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def negotiation_deal_price(role: str, player_offer: Optional[int], current_offer: int) -> int:
    """Agreed transaction price written to current_offer before deal()."""
    current_offer = max(1, int(current_offer))
    if player_offer is None or player_offer <= 0:
        return current_offer
    player_offer = int(player_offer)
    if role == "seller":
        # Player acquires: pay the lower of player bid and seller ask.
        return min(player_offer, current_offer)
    # Player sells: customer pays their bid when it meets the shop ask.
    if current_offer >= player_offer:
        return current_offer
    return max(player_offer, current_offer)


def _skill_relief(negotiation_level: int, charm_level: int) -> float:
    return 0.015 * negotiation_level + 0.01 * charm_level


def should_auto_accept_negotiation(
    role: str,
    player_offer: Optional[int],
    current_offer: int,
    limit_price: int,
    intent: str,
    negotiation_level: int = 1,
    charm_level: int = 1,
    reserve_noise: float = 0.0,
) -> bool:
    if intent == "accept":
        return True
    if player_offer is None or player_offer <= 0:
        return False
    relief = _skill_relief(negotiation_level, charm_level)
    # 隐藏保留价扰动：玩家看不到、也算不出精确阈值，压极限价有翻车风险。
    noise = 1.0 + float(reserve_noise)
    if role == "seller":
        if player_offer >= current_offer:
            return True
        return player_offer >= int(limit_price * (1 - relief) * noise)
    if player_offer <= current_offer:
        return True
    return player_offer <= int(limit_price * (1 + relief) * noise)


def dialogue_contradicts_economics(
    role: str,
    dialogue: str,
    player_offer: Optional[int],
    new_offer: int,
    current_offer: int,
) -> bool:
    if player_offer is None or player_offer <= 0:
        return False
    text = dialogue or ""
    if role == "seller":
        if player_offer >= new_offer and any(marker in text for marker in ("太低", "不够", "没诚意")):
            return True
        if player_offer >= current_offer and "太低" in text:
            return True
    else:
        if player_offer <= new_offer and any(marker in text for marker in ("太高", "太贵", "接不住", "太黑")):
            return True
        if player_offer <= current_offer and "太高" in text:
            return True
    return False


def clamp_counter_offer(role: str, new_offer: int, current_offer: int, limit_price: int, player_offer: Optional[int]) -> int:
    new_offer = max(1, int(new_offer))
    if player_offer is None or player_offer <= 0:
        return new_offer
    if role == "seller":
        if player_offer >= current_offer:
            return min(new_offer, current_offer, player_offer)
        return max(limit_price, min(new_offer, player_offer))
    if player_offer <= current_offer:
        return max(new_offer, current_offer, player_offer)
    return min(limit_price, max(new_offer, player_offer))


def reconcile_negotiation_economics(
    customer: Any,
    ai_response: Dict[str, Any],
    player_offer: Optional[int],
    intent: str,
    negotiation_level: int = 1,
    charm_level: int = 1,
) -> Dict[str, Any]:
    """Correct AI outcomes that violate role-aware price direction."""
    result = dict(ai_response)
    if intent == "reject":
        return result

    role = customer.role
    current_offer = int(customer.current_offer)
    limit_price = int(customer.limit_price)
    reserve_noise = float((getattr(customer, "negotiation_state", None) or {}).get("reserve_noise", 0.0))

    auto_accept = should_auto_accept_negotiation(
        role, player_offer, current_offer, limit_price, intent, negotiation_level, charm_level, reserve_noise
    )
    if auto_accept:
        deal_price = negotiation_deal_price(role, player_offer, current_offer)
        result["accepted"] = True
        result["walk_out"] = False
        result["new_offer"] = deal_price
        result["patience_change"] = max(0, int(result.get("patience_change", 0)))
        return result

    if bool(result.get("walk_out")):
        return result

    # AI may set accepted=true while leaving new_offer at the old ask — reject or fix before deal().
    if bool(result.get("accepted")):
        result["accepted"] = False
        result["new_offer"] = clamp_counter_offer(
            role,
            int(result.get("new_offer", current_offer)),
            current_offer,
            limit_price,
            player_offer,
        )
        result["_force_terminal_dialogue"] = True
        return result

    new_offer = clamp_counter_offer(
        role,
        int(result.get("new_offer", current_offer)),
        current_offer,
        limit_price,
        player_offer,
    )
    result["new_offer"] = new_offer

    dialogue = str(result.get("dialogue") or "")
    if dialogue_contradicts_economics(role, dialogue, player_offer, new_offer, current_offer):
        if role == "seller" and player_offer is not None and player_offer >= current_offer:
            deal_price = negotiation_deal_price(role, player_offer, current_offer)
            result["accepted"] = True
            result["walk_out"] = False
            result["new_offer"] = deal_price
            result["patience_change"] = max(0, int(result.get("patience_change", 0)))
        else:
            result["_force_terminal_dialogue"] = True

    return result
