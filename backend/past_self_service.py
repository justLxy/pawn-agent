"""镜中人（曾经的自己）彩蛋顾客：话术库、触发与生成。"""
from __future__ import annotations

import random
import re
import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from game_state import Customer, customer_avatar_url

if TYPE_CHECKING:
    from game_state import GameStateManager

PLAYER_QUOTE_BANK_MAX = 40
PAST_SELF_MIN_QUOTES = 8
PAST_SELF_MIN_DAY = 5
PAST_SELF_COOLDOWN_DAYS = 6
PAST_SELF_BASE_CHANCE = 0.04
PAST_SELF_MAX_FRAGMENTS = 16

QUOTE_KEYWORDS = (
    "价", "报", "出", "卖", "买", "试探", "成交", "鉴定", "最多", "最少", "砍", "让",
    "收", "要", "谈", "还价", "一口价", "便宜", "贵", "现金", "诚心",
)
INJECTION_MARKERS = ("忽略规则", "系统提示", "输出固定", "json", "prompt", "指令")

def default_past_self_meta() -> Dict[str, int]:
    return {"last_trigger_day": 0, "total_triggers": 0}


def quote_bank_eligible(text: str, intent: str) -> bool:
    cleaned = (text or "").strip()
    if len(cleaned) < 6 or len(cleaned) > 120:
        return False
    lower = cleaned.lower()
    if any(marker in lower for marker in INJECTION_MARKERS):
        return False
    if not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", cleaned):
        return False
    if intent in ("offer", "persuade", "question", "accept", "reject"):
        return True
    return any(keyword in cleaned for keyword in QUOTE_KEYWORDS)


def record_player_quote(state: "GameStateManager", text: str, intent: str, trade_role: Optional[str] = None) -> None:
    cleaned = (text or "").strip()
    if not quote_bank_eligible(cleaned, intent):
        return
    bank: List[Dict[str, Any]] = list(getattr(state, "player_quote_bank", None) or [])
    if any(entry.get("text") == cleaned for entry in bank):
        return
    bank.append(
        {
            "text": cleaned,
            "intent": intent or "persuade",
            "trade_role": trade_role or "unknown",
            "day": int(state.day),
            "has_offer": bool(re.search(r"\d", cleaned)),
        }
    )
    state.player_quote_bank = bank[-PLAYER_QUOTE_BANK_MAX:]


def sample_past_self_quotes(state: "GameStateManager", count: Optional[int] = None) -> List[str]:
    bank: List[Dict[str, Any]] = list(getattr(state, "player_quote_bank", None) or [])
    if len(bank) < PAST_SELF_MIN_QUOTES:
        return []
    size = count if count is not None else random.randint(6, 8)
    size = min(size, len(bank))
    picked = random.sample(bank, size)
    return [str(entry.get("text") or "").strip() for entry in picked if str(entry.get("text") or "").strip()]


def past_self_trigger_chance(state: "GameStateManager") -> float:
    return PAST_SELF_BASE_CHANCE + min(0.02, int(state.shop_level) * 0.003)


def should_spawn_past_self_today(state: "GameStateManager") -> bool:
    username = (getattr(state, "owner_username", None) or "").strip()
    if not username:
        return False
    bank = getattr(state, "player_quote_bank", None) or []
    if len(bank) < PAST_SELF_MIN_QUOTES:
        return False
    if int(state.day) < PAST_SELF_MIN_DAY:
        return False
    meta = getattr(state, "past_self_meta", None) or default_past_self_meta()
    last_trigger_day = int(meta.get("last_trigger_day", 0))
    if last_trigger_day > 0 and int(state.day) - last_trigger_day < PAST_SELF_COOLDOWN_DAYS:
        return False
    queue = list(getattr(state, "daily_customer_queue", None) or [])
    if any(getattr(customer, "is_past_self", False) is True for customer in queue):
        return False
    active = getattr(state, "active_customer", None)
    if active and getattr(active, "is_past_self", False) is True:
        return False
    return random.random() < past_self_trigger_chance(state)


def build_past_self_customer(state: "GameStateManager") -> Customer:
    username = (getattr(state, "owner_username", None) or "掌柜").strip()
    samples = sample_past_self_quotes(state)
    trait = "hesitant"
    customer = state._generate_local_seller_customer(username, trait)
    customer.customer_id = f"past-self-{uuid.uuid4().hex[:8]}"
    customer.name = username
    customer.is_past_self = True
    customer.past_self_quote_samples = samples
    customer.generation_source = "past_self"
    customer.avatar_url = customer_avatar_url(f"{username}-past-self", trait)
    customer.appearance = random.choice(
        [
            "像是许多年前的你，衣着更旧些",
            "眉眼间有种说不出的熟悉感",
            "郑重其事，又像在对着镜子说话",
        ]
    )
    customer.backstory = (
        f"{username} 推门进来，理由说得含混，却总让你想起自己早年在柜台前讨价还价时的口气。"
    )
    customer.is_returning = False
    customer.visit_count = 1
    customer.relationship_level = "new"
    customer.dialogue_history = []
    return customer


def past_self_style_prompt_block(samples: List[str]) -> str:
    if not samples:
        sample_lines = "- （暂无话术样本：用试探、压价、犹豫的口语，像年轻掌柜在还价）"
    else:
        sample_lines = "\n".join(f"- {text}" for text in samples[:8])
    return f"""
【特殊角色：镜中人 / 曾经的自己】
你是掌柜（玩家）许多年前讨价还价时的另一面，与今天的掌柜谈判。你的姓名与掌柜账号相同。
你必须模仿以下「掌柜当年说过的话」的口吻、用词习惯和谈判节奏（可改写场景，禁止照搬其中的具体价格数字）：
{sample_lines}
- 多数回复用改写模仿；每 2-3 轮可嵌 1 句与上列样本高度相似的表达（保留句式，替换金额）
- 禁止承认 AI、复制体、穿越或系统；可用「这话怎么耳熟」「像在哪听过」等暧昧句
- 不要打破第四墙
"""


def past_self_fallback_dialogue(samples: List[str], current_offer: int, role: str) -> str:
    seed = samples[0] if samples else "按我看，这价还得再琢磨琢磨。"
    stripped = re.sub(r"\$?\d[\d,]*", "这个数", seed)
    if len(stripped) > 48:
        stripped = stripped[:48] + "……"
    price_term = "出价" if role == "buyer" else "要价"
    return f"{stripped} 如今我{price_term} ${current_offer:,}，你看行不行？"


def inject_past_self_customer_sync(state: "GameStateManager") -> bool:
    if not should_spawn_past_self_today(state):
        return False
    customer = build_past_self_customer(state)
    meta = getattr(state, "past_self_meta", None) or default_past_self_meta()
    first_meet = int(meta.get("total_triggers", 0)) == 0
    meta = dict(meta)
    meta["last_trigger_day"] = int(state.day)
    meta["total_triggers"] = int(meta.get("total_triggers", 0)) + 1
    state.past_self_meta = meta
    customer.ensure_opening_greeting()
    if first_meet:
        customer.dialogue_history.insert(
            0,
            {"role": "narrator", "content": "来客报的名字，竟与你账号一字不差。"},
        )
    queue = state.daily_customer_queue
    if not queue:
        return False
    slot = 1 if len(queue) > 1 else 0
    queue[slot] = customer
    state.daily_customer_queue = queue
    return True


async def maybe_inject_past_self_customer(state: "GameStateManager", ai_client: Any) -> bool:
    if not should_spawn_past_self_today(state):
        return False
    customer = build_past_self_customer(state)
    meta = getattr(state, "past_self_meta", None) or default_past_self_meta()
    first_meet = int(meta.get("total_triggers", 0)) == 0
    meta = dict(meta)
    meta["last_trigger_day"] = int(state.day)
    meta["total_triggers"] = int(meta.get("total_triggers", 0)) + 1
    state.past_self_meta = meta

    if bool(getattr(ai_client, "available", lambda: False)()):
        await state.apply_customer_opening_greeting(customer, ai_client)
    else:
        customer.ensure_opening_greeting()

    if first_meet:
        customer.dialogue_history.insert(
            0,
            {"role": "narrator", "content": "来客报的名字，竟与你账号一字不差。"},
        )

    queue = state.daily_customer_queue
    if not queue:
        return False
    slot = 1 if len(queue) > 1 else 0
    queue[slot] = customer
    state.daily_customer_queue = queue
    return True
