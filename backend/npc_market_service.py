import json
import random
import secrets
import time
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from auth import ONLINE_IDLE_SECONDS, _hash_password, player_is_online
from database import get_connection, transaction
from game_state import GameStateManager, Item
from npc_inventory import (
    apply_npc_showcase_layout,
    build_npc_item,
    persona_list_price,
    persona_showcase_target,
    seed_npc_inventory,
)
from npc_market_config import (
    INITIAL_LISTINGS_MAX,
    INITIAL_LISTINGS_MIN,
    INITIAL_INVENTORY_SIZE,
    MAX_ACTIVE_LISTINGS_PER_NPC,
    NPC_DRIFT_DAILY_CASH_RATE,
    NPC_DRIFT_DAILY_PROFIT_SPREAD,
    NPC_DRIFT_MICRO_CASH_RATE,
    NPC_MARKET_ENABLED,
    NPC_ONLINE_TARGET_MAX,
    NPC_ONLINE_TARGET_MIN,
    NPC_PRESENCE_INTERVAL_SEC,
    NPC_TREASURY_CASH,
    STALE_LISTING_DAYS_MAX,
    STALE_LISTING_DAYS_MIN,
    TARGET_ACTIVE_LISTINGS_MAX,
    TARGET_ACTIVE_LISTINGS_MIN,
)
from npc_personas import LEGACY_NPC_USERNAME, NpcPersona, active_personas
from online_services import (
    TRADE_COOLDOWN_SECONDS,
    _execute_market_sale,
    list_item,
    load_state,
    reference_price,
    save_state,
    set_showcase_price,
    unlist_item,
    update_listing_price,
)


def _persona_by_key(key: str) -> Optional[NpcPersona]:
    for persona in active_personas():
        if persona.key == key:
            return persona
    return None


def _persona_by_player_id(player_id: int) -> Optional[NpcPersona]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT username FROM players WHERE id = ? AND COALESCE(is_system_player, 0) = 1",
            (player_id,),
        ).fetchone()
    if not row:
        return None
    username = row["username"]
    for persona in active_personas():
        if persona.username == username:
            return persona
    return None


def _persona_stat_anchors(persona: NpcPersona) -> Dict[str, int]:
    profit_anchor = max(5000, persona.cash - 10000)
    return {
        "cash": persona.cash,
        "reputation": persona.reputation,
        "total_profit": profit_anchor,
        "assets_floor": int(persona.cash * 0.78 + 8000),
        "assets_cap": int(persona.cash * 1.22 + 32000),
    }


def _inventory_asset_value(state: GameStateManager) -> int:
    return int(sum(item.market_value for item in state.inventory if item.status != "sold"))


def _total_assets(state: GameStateManager) -> int:
    return int(state.cash) + _inventory_asset_value(state)


def _clamp_npc_stats(state: GameStateManager, persona: NpcPersona) -> None:
    anchors = _persona_stat_anchors(persona)
    state.cash = max(8000, int(state.cash))
    state.reputation = max(85, min(240, int(state.reputation)))
    state.total_profit = max(0, int(state.total_profit))
    state.day = max(persona.day, int(state.day))

    assets = _total_assets(state)
    if assets > anchors["assets_cap"]:
        scale = anchors["assets_cap"] / max(assets, 1)
        state.cash = max(8000, int(state.cash * scale))
        for item in state.inventory:
            if item.status != "sold":
                item.market_value = max(10, int(item.market_value * scale))
    elif assets < anchors["assets_floor"]:
        boost = anchors["assets_floor"] - assets
        state.cash += int(boost * 0.55)
        for item in state.inventory:
            if item.status != "sold" and random.random() < 0.35:
                item.market_value = max(10, int(item.market_value * 1.01))


def _load_state_payload(player_id: int) -> Tuple[GameStateManager, Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (player_id,)).fetchone()
    if not row:
        raise ValueError(f"missing save for player {player_id}")
    payload = json.loads(row["state_json"])
    return GameStateManager.from_dict(payload), payload


def _save_state_payload(player_id: int, state: GameStateManager, payload: Dict[str, Any]) -> None:
    merged = state.to_dict(for_client=False)
    merged["npc_last_drift_date"] = payload.get("npc_last_drift_date")
    merged["npc_last_micro_drift_at"] = payload.get("npc_last_micro_drift_at")
    now = int(time.time())
    body = json.dumps(merged, ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO game_saves (player_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
            """,
            (player_id, body, now),
        )
        conn.execute("UPDATE players SET reputation = ?, last_seen = last_seen WHERE id = ?", (state.reputation, player_id))
        conn.commit()


def _archetype_daily_bias(persona: NpcPersona) -> Tuple[float, float]:
    """(现金倾向, 盈利倾向) 略偏向人设。"""
    if persona.archetype == "clearance":
        return (-0.012, -0.2)
    if persona.archetype == "luxury":
        return (0.01, 0.25)
    if persona.archetype == "bargain":
        return (-0.006, 0.05)
    if persona.archetype == "collector":
        return (0.006, 0.15)
    return (0.0, 0.0)


def apply_npc_leaderboard_drift(player_id: int, persona: NpcPersona, micro: bool = False) -> Dict[str, Any]:
    """让人设排行榜数值每日可见变化，并锚定在配置附近，避免碾压真人。"""
    state, payload = _load_state_payload(player_id)
    today = date.today().isoformat()
    now = int(time.time())
    cash_bias, profit_bias = _archetype_daily_bias(persona)
    changed = False
    mode = "none"

    if not micro and payload.get("npc_last_drift_date") != today:
        mode = "daily"
        cash_rate = random.uniform(-NPC_DRIFT_DAILY_CASH_RATE, NPC_DRIFT_DAILY_CASH_RATE) + cash_bias
        state.cash = int(state.cash * (1 + cash_rate))
        profit_delta = int(NPC_DRIFT_DAILY_PROFIT_SPREAD * random.uniform(-0.55 + profit_bias, 0.85 + profit_bias))
        state.total_profit = max(0, state.total_profit + profit_delta)
        state.reputation += random.randint(-2, 4)
        if random.random() < 0.35:
            state.successful_trades += 1
        if random.random() < 0.28:
            state.positive_reviews += 1
        state.day += 1
        for item in state.inventory:
            if item.status in ("sold", "listed"):
                continue
            if random.random() < 0.72:
                item.market_value = max(10, int(item.market_value * random.uniform(0.985, 1.018)))
        payload["npc_last_drift_date"] = today
        changed = True

    last_micro = int(payload.get("npc_last_micro_drift_at") or 0)
    if micro and now - last_micro >= 240:
        mode = "daily+micro" if changed else "micro"
        micro_rate = random.uniform(-NPC_DRIFT_MICRO_CASH_RATE, NPC_DRIFT_MICRO_CASH_RATE)
        state.cash = int(state.cash * (1 + micro_rate))
        candidates = [item for item in state.inventory if item.status not in ("sold", "listed")]
        touched = random.sample(candidates, k=min(3, len(candidates))) if candidates else []
        for item in touched:
            item.market_value = max(10, int(item.market_value * random.uniform(0.996, 1.006)))
        if random.random() < 0.08:
            state.total_profit += random.randint(80, 420)
        payload["npc_last_micro_drift_at"] = now
        changed = True

    if not changed:
        return {"player_id": player_id, "mode": "none", "assets": _total_assets(state)}

    _clamp_npc_stats(state, persona)
    _save_state_payload(player_id, state, payload)
    return {
        "player_id": player_id,
        "mode": mode,
        "assets": _total_assets(state),
        "cash": state.cash,
        "profit": state.total_profit,
        "reputation": state.reputation,
        "day": state.day,
    }


def drift_all_npc_leaderboards(player_map: Dict[str, int], micro: bool = True) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for persona in active_personas():
        player_id = player_map[persona.key]
        results.append(apply_npc_leaderboard_drift(player_id, persona, micro=micro))
    return results


def build_npc_game_state(persona: NpcPersona) -> GameStateManager:
    state = GameStateManager(initialize=False)
    state.shop_name = persona.shop_name
    state.shop_level = persona.shop_level
    state.reputation = persona.reputation
    state.day = persona.day
    state.cash = persona.cash
    state.total_profit = max(0, persona.cash - 10000)
    state.successful_trades = random.randint(12, 48)
    state.positive_reviews = random.randint(8, 36)
    state.economy_index = 1.0
    state.market_trends = {category: round(random.uniform(0.92, 1.08), 2) for category in state.market_trends}
    state.facilities["showcase"] = max(0, min(2, persona.showcase_facility_level))
    seed_npc_inventory(persona, state, INITIAL_INVENTORY_SIZE)
    _clamp_npc_stats(state, persona)
    return state


def get_system_player_ids() -> List[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id FROM players WHERE COALESCE(is_system_player, 0) = 1 ORDER BY id"
        ).fetchall()
    return [int(row["id"]) for row in rows]


def get_persona_player_map() -> Dict[str, int]:
    personas = active_personas()
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, username FROM players
            WHERE COALESCE(is_system_player, 0) = 1
              AND username IN ({','.join('?' for _ in personas)})
            """,
            [p.username for p in personas],
        ).fetchall()
    return {row["username"]: int(row["id"]) for row in rows}


def _clear_npc_cosmetics(player_id: int, shop_name: str) -> None:
    """NPC 与真人一致走市场/排行，但不展示赞助、匾额、橱窗文案等付费定制。"""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE players
            SET is_system_player = 1,
                shop_name = ?,
                showcase_tagline = NULL,
                shop_emblem = NULL,
                monthly_expires_at = NULL,
                plaque_title = NULL,
                shop_sign_style = NULL,
                showcase_mood = NULL,
                showcase_seal_line = NULL,
                chat_accent = NULL
            WHERE id = ?
            """,
            (shop_name, player_id),
        )
        conn.commit()


def _sync_npc_profile(player_id: int, persona: NpcPersona) -> None:
    _clear_npc_cosmetics(player_id, persona.shop_name)
    with get_connection() as conn:
        has_save = conn.execute("SELECT 1 FROM game_saves WHERE player_id = ?", (player_id,)).fetchone()
    if not has_save:
        save_state(player_id, build_npc_game_state(persona))
        return
    state = load_state(player_id)
    changed = False
    if state.shop_name != persona.shop_name:
        state.shop_name = persona.shop_name
        changed = True
    if state.shop_level != persona.shop_level:
        state.shop_level = persona.shop_level
        changed = True
    if changed:
        save_state(player_id, state)
    _maybe_refresh_npc_showcase(player_id, persona, state)


def _maybe_refresh_npc_showcase(player_id: int, persona: NpcPersona, state: Optional[GameStateManager] = None) -> None:
    state = state or load_state(player_id)
    displayed = [i for i in state.inventory if i.status == "displayed"]
    lo = max(1, persona.showcase_count_min)
    hi = max(lo, min(persona.showcase_count_max, state.display_capacity()))
    if len(displayed) == hi == lo or (lo <= len(displayed) <= hi and random.random() > 0.22):
        return
    apply_npc_showcase_layout(state, persona)
    seed_npc_showcase_prices(player_id, persona, state=state)
    save_state(player_id, state)


def _find_npc_player_id(persona: NpcPersona) -> Optional[int]:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM players WHERE username = ?", (persona.username,)).fetchone()
        if row:
            return int(row["id"])
        for old_username, new_username in LEGACY_NPC_USERNAME.items():
            if new_username != persona.username:
                continue
            legacy = conn.execute(
                "SELECT id FROM players WHERE username = ? AND COALESCE(is_system_player, 0) = 1",
                (old_username,),
            ).fetchone()
            if legacy:
                conn.execute(
                    "UPDATE players SET username = ?, shop_name = ? WHERE id = ?",
                    (persona.username, persona.shop_name, int(legacy["id"])),
                )
                conn.commit()
                return int(legacy["id"])
    return None


def ensure_npc_players() -> Dict[str, int]:
    result: Dict[str, int] = {}
    now = int(time.time())
    for persona in active_personas():
        player_id = _find_npc_player_id(persona)
        if player_id is not None:
            _sync_npc_profile(player_id, persona)
            result[persona.key] = player_id
            continue

        password = secrets.token_urlsafe(32)
        password_hash, salt = _hash_password(password)
        token = secrets.token_urlsafe(32)
        created_back = now - random.randint(30, 120) * 86400
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO players (
                    username, shop_name, password_hash, salt, token, online,
                    reputation, created_at, last_seen, is_system_player,
                    showcase_tagline, shop_emblem, monthly_expires_at
                )
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, 1, NULL, NULL, NULL)
                """,
                (
                    persona.username,
                    persona.shop_name,
                    password_hash,
                    salt,
                    token,
                    persona.reputation,
                    created_back,
                    created_back - random.randint(3600, 86400),
                ),
            )
            player = conn.execute("SELECT id FROM players WHERE username = ?", (persona.username,)).fetchone()
            conn.commit()
        player_id = int(player["id"])
        save_state(player_id, build_npc_game_state(persona))
        result[persona.key] = player_id
    return result


def count_active_listings(player_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM market_listings WHERE seller_id = ? AND status = 'active'",
            (player_id,),
        ).fetchone()
    return int(row["c"] or 0)


def _npc_listable_stored(state: GameStateManager) -> List[Item]:
    now = int(time.time())
    return [
        item
        for item in state.inventory
        if item.status == "stored"
        and (not item.last_trade_at or now - int(item.last_trade_at) >= TRADE_COOLDOWN_SECONDS)
    ]


def npc_list_stored_item(player_id: int, persona: NpcPersona, listing_created_at: Optional[int] = None) -> Optional[str]:
    state = load_state(player_id)
    if count_active_listings(player_id) >= MAX_ACTIVE_LISTINGS_PER_NPC:
        return None
    stored = _npc_listable_stored(state)
    if not stored:
        item = build_npc_item(persona, state)
        state.inventory.append(item)
        save_state(player_id, state)
        stored = [item]
    candidates = stored[:]
    random.shuffle(candidates)
    for item in candidates[:8]:
        price = persona_list_price(persona, item)
        try:
            result = list_item(player_id, item.id, price)
        except HTTPException:
            continue
        listing_id = result.get("listing_id")
        if listing_id and listing_created_at:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE market_listings SET created_at = ?, updated_at = ? WHERE id = ?",
                    (listing_created_at, listing_created_at, listing_id),
                )
                conn.commit()
        return listing_id
    return None


def npc_reprice_listing(player_id: int, persona: NpcPersona) -> bool:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, item_json, reference_price, price
            FROM market_listings
            WHERE seller_id = ? AND status = 'active'
            ORDER BY updated_at ASC
            LIMIT 5
            """,
            (player_id,),
        ).fetchall()
    if not rows:
        return False
    row = random.choice(rows)
    item = Item.from_dict(json.loads(row["item_json"]))
    ref = int(row["reference_price"])
    old_price = int(row["price"])
    jitter = random.uniform(0.94, 1.08)
    new_price = persona_list_price(persona, item, jitter=jitter)
    if abs(new_price - old_price) < max(5, int(ref * 0.03)):
        direction = -1 if old_price > ref else 1
        new_price = _clamp_listing_price(ref, old_price + direction * max(5, int(ref * 0.05)))
    update_listing_price(player_id, row["id"], new_price)
    ts = int(time.time()) - random.randint(0, 3600)
    with get_connection() as conn:
        conn.execute("UPDATE market_listings SET updated_at = ? WHERE id = ?", (ts, row["id"]))
        conn.commit()
    return True


def _clamp_listing_price(ref: int, price: int) -> int:
    return max(int(ref * 0.3), min(int(ref * 3), price))


def npc_unlist_stale(player_id: int) -> bool:
    cutoff = int(time.time()) - random.randint(STALE_LISTING_DAYS_MIN, STALE_LISTING_DAYS_MAX) * 86400
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id FROM market_listings
            WHERE seller_id = ? AND status = 'active' AND created_at < ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (player_id, cutoff),
        ).fetchone()
    if not row:
        return False
    unlist_item(player_id, row["id"])
    return True


def _ensure_npc_cash(state: GameStateManager, needed: int) -> None:
    if state.cash < needed:
        state.cash = max(state.cash, needed) + NPC_TREASURY_CASH // 10


def npc_simulate_sale(listing_id: str) -> bool:
    with get_connection() as conn:
        listing = conn.execute(
            "SELECT * FROM market_listings WHERE id = ? AND status = 'active'",
            (listing_id,),
        ).fetchone()
    if not listing:
        return False
    seller_id = int(listing["seller_id"])
    buyer_candidates = [pid for pid in get_system_player_ids() if pid != seller_id]
    if not buyer_candidates:
        return False
    buyer_id = random.choice(buyer_candidates)
    price = int(listing["price"])

    with transaction() as conn:
        buyer_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (buyer_id,)).fetchone()
        seller_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (seller_id,)).fetchone()
        if not buyer_row or not seller_row:
            return False
        buyer = GameStateManager.from_dict(json.loads(buyer_row["state_json"]))
        seller = GameStateManager.from_dict(json.loads(seller_row["state_json"]))
        _ensure_npc_cash(buyer, price)
        item = Item.from_dict(json.loads(listing["item_json"]))
        _execute_market_sale(conn, buyer, seller, item, price, listing_id, buyer_id, seller_id, "sale")
    return True


def npc_rotate_showcase(player_id: int, persona: NpcPersona) -> bool:
    state = load_state(player_id)
    if random.random() < 0.18:
        target = persona_showcase_target(persona, state)
        apply_npc_showcase_layout(state, persona, target=target)
        save_state(player_id, state)
        seed_npc_showcase_prices(player_id, persona, state=state)
        return True
    displayed = [item for item in state.inventory if item.status == "displayed"]
    stored = [item for item in state.inventory if item.status == "stored"]
    if stored and (not displayed or random.random() < 0.5):
        if displayed:
            old = random.choice(displayed)
            old.status = "stored"
            old.display_slot = None
            old.showcase_price = None
        item = random.choice(stored)
        item.status = "displayed"
        item.display_slot = len([i for i in state.inventory if i.status == "displayed"]) - 1
        price = persona_list_price(persona, item, jitter=random.uniform(0.9, 1.15))
        save_state(player_id, state)
        set_showcase_price(player_id, item.id, price)
        return True
    if displayed:
        item = random.choice(displayed)
        if random.random() < 0.35:
            item.showcase_price = None
        else:
            item.showcase_price = persona_list_price(persona, item, jitter=random.uniform(0.92, 1.1))
        save_state(player_id, state)
        return True
    return False


def _presence_refresh_interval_sec() -> int:
    return max(60, min(NPC_PRESENCE_INTERVAL_SEC, ONLINE_IDLE_SECONDS - 45))


def _npc_last_seen_for_state(online: bool, now: int) -> int:
    idle_limit = max(60, ONLINE_IDLE_SECONDS)
    if online:
        return now - random.randint(2, min(90, idle_limit - 25))
    offline_seconds = random.randint(idle_limit + 40, idle_limit + random.randint(180, 720))
    return now - offline_seconds


def _npc_heartbeat(player_id: int, now: Optional[int] = None) -> None:
    now = now if now is not None else int(time.time())
    last_seen = now - random.randint(2, min(75, ONLINE_IDLE_SECONDS - 30))
    with get_connection() as conn:
        conn.execute("UPDATE players SET last_seen = ? WHERE id = ?", (last_seen, player_id))
        conn.commit()


def refresh_npc_last_seen(player_id: int, persona: NpcPersona, force_online: Optional[bool] = None) -> bool:
    """按人设概率刷新在线状态；返回当前是否在线。"""
    now = int(time.time())
    with get_connection() as conn:
        row = conn.execute("SELECT last_seen FROM players WHERE id = ?", (player_id,)).fetchone()
    last_seen = int(row["last_seen"] or 0) if row else 0
    currently_online = player_is_online(last_seen, now) if last_seen > 0 else False

    if force_online is not None:
        go_online = force_online
    elif currently_online:
        go_online = random.random() >= persona.online_drop_rate
        if go_online:
            _npc_heartbeat(player_id, now)
            return True
    else:
        go_online = random.random() < persona.online_return_rate

    new_last_seen = _npc_last_seen_for_state(go_online, now)
    with get_connection() as conn:
        conn.execute("UPDATE players SET last_seen = ? WHERE id = ?", (new_last_seen, player_id))
        conn.commit()
    return go_online


def _npc_online_quota(persona_count: int) -> int:
    if persona_count <= 1:
        return 1
    lo = max(1, min(NPC_ONLINE_TARGET_MIN, persona_count - 1))
    hi = max(lo, min(NPC_ONLINE_TARGET_MAX, persona_count - 1))
    return random.randint(lo, hi)


def refresh_all_npc_presence(player_map: Dict[str, int], drift_micro: bool = True) -> Dict[str, bool]:
    if drift_micro:
        drift_all_npc_leaderboards(player_map, micro=True)
    personas = active_personas()
    quota = _npc_online_quota(len(personas))
    online_keys = set(random.sample([p.key for p in personas], quota))
    presence: Dict[str, bool] = {}
    for persona in personas:
        player_id = player_map[persona.key]
        presence[persona.key] = refresh_npc_last_seen(
            player_id,
            persona,
            force_online=persona.key in online_keys,
        )
    return presence


def nudge_npc_display_presence() -> int:
    """排行榜/市场打开时，仅给「已经在线」的 NPC 续心跳，不把离线强行拉上线。"""
    if not NPC_MARKET_ENABLED:
        return 0
    player_map = ensure_npc_players()
    now = int(time.time())
    stale_before = now - max(90, ONLINE_IDLE_SECONDS - 80)
    refreshed = 0
    for persona in active_personas():
        player_id = player_map[persona.key]
        with get_connection() as conn:
            row = conn.execute("SELECT last_seen FROM players WHERE id = ?", (player_id,)).fetchone()
        last_seen = int(row["last_seen"] or 0) if row else 0
        if not player_is_online(last_seen, now):
            continue
        if last_seen >= stale_before:
            continue
        _npc_heartbeat(player_id, now)
        refreshed += 1
    return refreshed


def seed_npc_listings(player_id: int, persona: NpcPersona, count: int) -> List[str]:
    listing_ids: List[str] = []
    now = int(time.time())
    for i in range(count):
        created_at = now - random.randint(3, 10) * 86400 - random.randint(0, 86400)
        listing_id = npc_list_stored_item(player_id, persona, listing_created_at=created_at)
        if listing_id:
            listing_ids.append(listing_id)
    return listing_ids


def seed_npc_showcase_prices(player_id: int, persona: NpcPersona, state: Optional[GameStateManager] = None) -> None:
    state = state or load_state(player_id)
    changed = False
    for item in state.inventory:
        if item.status == "displayed" and not item.showcase_price:
            item.showcase_price = persona_list_price(persona, item, jitter=random.uniform(0.88, 1.12))
            changed = True
    if changed:
        save_state(player_id, state)


def clear_npc_market_data() -> None:
    ids = get_system_player_ids()
    if not ids:
        return
    now = int(time.time())
    placeholders = ",".join("?" for _ in ids)
    with transaction() as conn:
        conn.execute(
            f"DELETE FROM market_offers WHERE seller_id IN ({placeholders}) OR buyer_id IN ({placeholders})",
            ids + ids,
        )
        active_rows = conn.execute(
            f"""
            SELECT seller_id, item_json FROM market_listings
            WHERE seller_id IN ({placeholders}) AND status = 'active'
            """,
            ids,
        ).fetchall()
        conn.execute(
            f"UPDATE market_listings SET status = 'cancelled', updated_at = ? WHERE seller_id IN ({placeholders}) AND status = 'active'",
            [now, *ids],
        )
        by_seller: Dict[int, List[Item]] = {}
        for row in active_rows:
            seller_id = int(row["seller_id"])
            by_seller.setdefault(seller_id, []).append(Item.from_dict(json.loads(row["item_json"])))
        for player_id, items in by_seller.items():
            save_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (player_id,)).fetchone()
            if not save_row:
                continue
            state = GameStateManager.from_dict(json.loads(save_row["state_json"]))
            for item in items:
                item.status = "stored"
                item.display_slot = None
                if not state.get_item(item.id):
                    state.inventory.append(item)
            conn.execute(
                "UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?",
                (json.dumps(state.to_dict(), ensure_ascii=False), now, player_id),
            )


def full_seed_npc_shops(reset: bool = False) -> Dict[str, Any]:
    if reset:
        clear_npc_market_data()
    player_map = ensure_npc_players()
    summary: Dict[str, Any] = {"players": player_map, "listings": {}}
    for persona in active_personas():
        player_id = player_map[persona.key]
        if reset:
            persona_obj = persona
            save_state(player_id, build_npc_game_state(persona_obj))
        else:
            state = load_state(player_id)
            state.facilities["showcase"] = max(0, min(2, persona.showcase_facility_level))
            apply_npc_showcase_layout(state, persona)
            save_state(player_id, state)
            seed_npc_showcase_prices(player_id, persona, state=state)
        active = count_active_listings(player_id)
        target = random.randint(INITIAL_LISTINGS_MIN, INITIAL_LISTINGS_MAX)
        needed = max(0, target - active)
        ids = seed_npc_listings(player_id, persona, needed) if needed else []
        seed_npc_showcase_prices(player_id, persona)
        summary["listings"][persona.key] = ids
    drift_all_npc_leaderboards(player_map, micro=False)
    summary["presence"] = refresh_all_npc_presence(player_map)
    return summary


def pick_stale_listing_for_sale(player_id: int) -> Optional[str]:
    cutoff = int(time.time()) - random.randint(5, 9) * 86400
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id FROM market_listings
            WHERE seller_id = ? AND status = 'active' AND created_at < ?
            ORDER BY RANDOM()
            LIMIT 1
            """,
            (player_id, cutoff),
        ).fetchone()
    return str(row["id"]) if row else None


def run_npc_tick() -> Dict[str, Any]:
    from npc_market_config import DAILY_ACTION_BUDGET_MAX, DAILY_ACTION_BUDGET_MIN

    player_map = ensure_npc_players()
    budget = random.randint(DAILY_ACTION_BUDGET_MIN, DAILY_ACTION_BUDGET_MAX)
    actions_log: List[str] = []
    personas = active_personas()
    random.shuffle(personas)

    for _ in range(budget):
        persona = random.choice(personas)
        player_id = player_map[persona.key]
        weights = [
            ("list", persona.list_action_weight),
            ("reprice", persona.reprice_action_weight),
            ("delist", persona.delist_action_weight),
            ("trade", persona.trade_action_weight),
            ("showcase", persona.showcase_action_weight),
        ]
        action = random.choices([w[0] for w in weights], weights=[w[1] for w in weights], k=1)[0]
        ok = False
        if action == "list":
            active = count_active_listings(player_id)
            if active < TARGET_ACTIVE_LISTINGS_MAX:
                ok = bool(npc_list_stored_item(player_id, persona))
        elif action == "reprice":
            ok = npc_reprice_listing(player_id, persona)
        elif action == "delist":
            ok = npc_unlist_stale(player_id)
        elif action == "trade":
            listing_id = pick_stale_listing_for_sale(player_id)
            if listing_id:
                ok = npc_simulate_sale(listing_id)
            elif random.random() < 0.4:
                with get_connection() as conn:
                    row = conn.execute(
                        "SELECT id FROM market_listings WHERE seller_id = ? AND status = 'active' ORDER BY RANDOM() LIMIT 1",
                        (player_id,),
                    ).fetchone()
                if row:
                    ok = npc_simulate_sale(str(row["id"]))
        elif action == "showcase":
            ok = npc_rotate_showcase(player_id, persona)
        if ok:
            actions_log.append(f"{persona.key}:{action}")

    drift_all_npc_leaderboards(player_map, micro=False)
    presence = refresh_all_npc_presence(player_map)
    online_count = sum(1 for online in presence.values() if online)
    return {"actions": actions_log, "budget": budget, "online_npcs": online_count, "presence": presence}
