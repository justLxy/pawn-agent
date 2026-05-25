from dataclasses import dataclass
from typing import Dict, List, Tuple

from npc_market_config import NPC_SHOP_COUNT

# 旧版部署若已创建 NPC，启动时会把用户名/店名迁移到新人设（避免重复建号）
LEGACY_NPC_USERNAME: Dict[str, str] = {
    "oldtown_clear": "ChenMu_98",
    "jade_collects": "linxiaoyu",
    "aureum_exchange": "SuYating",
    "alley_pickr88": "ZhouLaoshou",
    "marco_vintage92": "Takashi_K",
    "seven_st_pawn": "MeiZiLan",
}


@dataclass(frozen=True)
class NpcPersona:
    key: str
    username: str
    shop_name: str
    archetype: str
    category_weights: Dict[str, float]
    rarity_weights: Dict[str, float]
    condition_weights: Dict[str, float]
    price_low: float
    price_high: float
    shop_level: int
    reputation: int
    day: int
    cash: int
    # 在线时本 tick 变离线的概率 / 离线时本 tick 变在线的概率（人人不同，整体多数时间在线）
    online_drop_rate: float = 0.2
    online_return_rate: float = 0.85
    list_action_weight: float = 0.28
    reprice_action_weight: float = 0.22
    delist_action_weight: float = 0.18
    trade_action_weight: float = 0.17
    showcase_action_weight: float = 0.15


def _w(*pairs: Tuple[str, float]) -> Dict[str, float]:
    return dict(pairs)


ALL_CATEGORIES = ("Pop Culture", "Art", "Jewelry", "Antiquities", "Historical")
DEFAULT_RARITY = _w(("common", 0.45), ("rare", 0.32), ("epic", 0.17), ("legendary", 0.06))
DEFAULT_CONDITION = _w(("Poor", 0.3), ("Good", 0.5), ("Mint", 0.2))


NPC_PERSONAS: List[NpcPersona] = [
    NpcPersona(
        key="clearance",
        username="ChenMu_98",
        shop_name="差不多得了",
        archetype="clearance",
        category_weights=_w(("Pop Culture", 0.35), ("Jewelry", 0.3), ("Art", 0.15), ("Antiquities", 0.12), ("Historical", 0.08)),
        rarity_weights=_w(("common", 0.55), ("rare", 0.3), ("epic", 0.12), ("legendary", 0.03)),
        condition_weights=_w(("Poor", 0.4), ("Good", 0.45), ("Mint", 0.15)),
        price_low=0.35,
        price_high=0.65,
        shop_level=3,
        reputation=108,
        day=31,
        cash=58000,
        online_drop_rate=0.1,
        online_return_rate=0.92,
    ),
    NpcPersona(
        key="collector",
        username="linxiaoyu",
        shop_name="仅供观赏请勿摸",
        archetype="collector",
        category_weights=_w(("Art", 0.38), ("Antiquities", 0.35), ("Historical", 0.12), ("Jewelry", 0.08), ("Pop Culture", 0.07)),
        rarity_weights=_w(("common", 0.25), ("rare", 0.38), ("epic", 0.27), ("legendary", 0.1)),
        condition_weights=_w(("Poor", 0.12), ("Good", 0.38), ("Mint", 0.5)),
        price_low=0.95,
        price_high=1.3,
        shop_level=6,
        reputation=162,
        day=58,
        cash=112000,
        online_drop_rate=0.08,
        online_return_rate=0.9,
    ),
    NpcPersona(
        key="luxury",
        username="SuYating",
        shop_name="情绪税代收点",
        archetype="luxury",
        category_weights=_w(("Jewelry", 0.4), ("Historical", 0.32), ("Art", 0.15), ("Antiquities", 0.1), ("Pop Culture", 0.03)),
        rarity_weights=_w(("common", 0.12), ("rare", 0.28), ("epic", 0.38), ("legendary", 0.22)),
        condition_weights=_w(("Poor", 0.08), ("Good", 0.42), ("Mint", 0.5)),
        price_low=1.15,
        price_high=1.75,
        shop_level=5,
        reputation=148,
        day=49,
        cash=92000,
        online_drop_rate=0.12,
        online_return_rate=0.94,
    ),
    NpcPersona(
        key="bargain",
        username="ZhouLaoshou",
        shop_name="吃亏是福研究中心",
        archetype="bargain",
        category_weights={cat: 0.2 for cat in ALL_CATEGORIES},
        rarity_weights=DEFAULT_RARITY,
        condition_weights=_w(("Poor", 0.45), ("Good", 0.45), ("Mint", 0.1)),
        price_low=0.45,
        price_high=0.85,
        shop_level=2,
        reputation=96,
        day=24,
        cash=42000,
        online_drop_rate=0.09,
        online_return_rate=0.95,
    ),
    NpcPersona(
        key="vintage",
        username="Takashi_K",
        shop_name="上个世纪的废话",
        archetype="vintage",
        category_weights=_w(("Pop Culture", 0.42), ("Antiquities", 0.32), ("Art", 0.14), ("Jewelry", 0.08), ("Historical", 0.04)),
        rarity_weights=_w(("common", 0.4), ("rare", 0.35), ("epic", 0.2), ("legendary", 0.05)),
        condition_weights=_w(("Poor", 0.25), ("Good", 0.5), ("Mint", 0.25)),
        price_low=0.8,
        price_high=1.1,
        shop_level=4,
        reputation=128,
        day=41,
        cash=72000,
        online_drop_rate=0.11,
        online_return_rate=0.91,
    ),
    NpcPersona(
        key="generalist",
        username="MeiZiLan",
        shop_name="路过别问在不在",
        archetype="generalist",
        category_weights={cat: 0.2 for cat in ALL_CATEGORIES},
        rarity_weights=DEFAULT_RARITY,
        condition_weights=DEFAULT_CONDITION,
        price_low=0.85,
        price_high=1.05,
        shop_level=3,
        reputation=118,
        day=36,
        cash=61000,
        online_drop_rate=0.1,
        online_return_rate=0.93,
    ),
]


def active_personas() -> List[NpcPersona]:
    return NPC_PERSONAS[: max(1, min(NPC_SHOP_COUNT, len(NPC_PERSONAS)))]
