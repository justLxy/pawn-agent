import random
from typing import Dict, List, Optional

from game_state import (
    CONDITION_MULTIPLIER,
    ITEM_TEMPLATES,
    RARITY_INFO,
    GameStateManager,
    Item,
)
from npc_market_config import FAKE_ITEM_RATE
from npc_personas import NpcPersona
from online_services import reference_price


def _weighted_choice(weights: Dict[str, float]) -> str:
    keys = list(weights.keys())
    vals = [weights[k] for k in keys]
    return random.choices(keys, weights=vals, k=1)[0]


def _clamp_price_for_rarity(rarity: str, ref: int, price: int) -> int:
    min_p = int(ref * 0.3)
    max_p = int(ref * 3)
    if rarity == "legendary":
        price = max(price, int(ref * 0.85))
    if rarity == "common":
        price = min(price, int(ref * 1.4))
    return max(min_p, min(max_p, price))


def persona_list_price(persona: NpcPersona, item: Item, jitter: float = 1.0) -> int:
    ref = reference_price(item)
    low = persona.price_low * jitter
    high = persona.price_high * jitter
    target = ref * random.uniform(low, high)
    price = int(round(target))
    return _clamp_price_for_rarity(item.rarity, ref, price)


def build_npc_item(
    persona: NpcPersona,
    state: GameStateManager,
    avoid_names: Optional[List[str]] = None,
) -> Item:
    avoid_names = avoid_names or []
    category = _weighted_choice(persona.category_weights)
    template = random.choice(ITEM_TEMPLATES[category])
    condition = _weighted_choice(persona.condition_weights)
    rarity = _weighted_choice(persona.rarity_weights)

    raw_value = template["mint_val"] if condition == "Mint" else template["good_val"] if condition == "Good" else template["poor_val"]
    value = int(raw_value * RARITY_INFO[rarity]["multiplier"] * state.economy_index * random.uniform(0.88, 1.12))
    is_fake = random.random() < FAKE_ITEM_RATE
    if is_fake:
        value = max(15, int(value * random.uniform(0.12, 0.2)))
    market_value = int(value * state.market_trends.get(category, 1.0) * CONDITION_MULTIPLIER.get(condition, 1.0))
    market_value = max(10, market_value)

    temp = GameStateManager(initialize=False)
    temp.economy_index = state.economy_index
    temp.market_trends = dict(state.market_trends)
    temp.day = state.day
    item = temp._generate_item_from_template(template, category, avoid_names=avoid_names)
    item.condition = condition
    item.rarity = rarity if rarity in RARITY_INFO else "common"
    item.is_fake = is_fake
    item.actual_value = value
    item.market_value = market_value
    item.base_value_at_purchase = market_value
    item.rarity_cn = RARITY_INFO[item.rarity]["name_cn"]
    item.status = "stored"
    item.content_source = "local"
    if persona.archetype in ("collector", "vintage") and not item.story:
        item.story = f"原主人在{state.day}天前将它送到【{persona.shop_name}】，留下了一段简短来历说明。"
    return item


def persona_showcase_target(persona: NpcPersona, state: GameStateManager) -> int:
    capacity = state.display_capacity()
    lo = max(1, persona.showcase_count_min)
    hi = max(lo, min(persona.showcase_count_max, capacity))
    return random.randint(lo, hi)


def apply_npc_showcase_layout(state: GameStateManager, persona: NpcPersona, target: Optional[int] = None) -> int:
    """重新摆放橱窗：每人陈列件数不同，且不超过展示柜容量。"""
    target = target if target is not None else persona_showcase_target(persona, state)
    for item in state.inventory:
        if item.status == "displayed":
            item.status = "stored"
            item.display_slot = None
            item.showcase_price = None
    stored = [i for i in state.inventory if i.status == "stored"]
    random.shuffle(stored)
    picked = stored[:target]
    for idx, item in enumerate(picked):
        item.status = "displayed"
        item.display_slot = idx
    return len(picked)


def seed_npc_inventory(persona: NpcPersona, state: GameStateManager, size: int) -> int:
    names: List[str] = []
    for _ in range(size):
        item = build_npc_item(persona, state, avoid_names=names)
        names.append(item.name)
        state.inventory.append(item)
    return apply_npc_showcase_layout(state, persona)
