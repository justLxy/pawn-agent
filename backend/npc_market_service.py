import json
import random
import secrets
import time
from typing import Any, Dict, List, Optional

from auth import ONLINE_IDLE_SECONDS, _hash_password, player_is_online
from database import get_connection, transaction
from game_state import GameStateManager, Item
from npc_inventory import build_npc_item, persona_list_price, seed_npc_inventory
from npc_market_config import (
    INITIAL_LISTINGS_MAX,
    INITIAL_LISTINGS_MIN,
    INITIAL_SHOWCASE_COUNT,
    INITIAL_INVENTORY_SIZE,
    MAX_ACTIVE_LISTINGS_PER_NPC,
    NPC_TREASURY_CASH,
    STALE_LISTING_DAYS_MAX,
    STALE_LISTING_DAYS_MIN,
    TARGET_ACTIVE_LISTINGS_MAX,
    TARGET_ACTIVE_LISTINGS_MIN,
)
from npc_personas import LEGACY_NPC_USERNAME, NpcPersona, active_personas
from online_services import (
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
    seed_npc_inventory(persona, state, INITIAL_INVENTORY_SIZE, INITIAL_SHOWCASE_COUNT)
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
                monthly_expires_at = NULL
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


def npc_list_stored_item(player_id: int, persona: NpcPersona, listing_created_at: Optional[int] = None) -> Optional[str]:
    state = load_state(player_id)
    if count_active_listings(player_id) >= MAX_ACTIVE_LISTINGS_PER_NPC:
        return None
    stored = [item for item in state.inventory if item.status == "stored"]
    if not stored:
        item = build_npc_item(persona, state)
        state.inventory.append(item)
        stored = [item]
    item = random.choice(stored)
    price = persona_list_price(persona, item)
    result = list_item(player_id, item.id, price)
    listing_id = result.get("listing_id")
    if listing_id and listing_created_at:
        with get_connection() as conn:
            conn.execute(
                "UPDATE market_listings SET created_at = ?, updated_at = ? WHERE id = ?",
                (listing_created_at, listing_created_at, listing_id),
            )
            conn.commit()
    return listing_id


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


def _npc_last_seen_for_state(online: bool, now: int) -> int:
    idle_limit = max(60, ONLINE_IDLE_SECONDS)
    if online:
        return now - random.randint(8, max(12, idle_limit - 20))
    offline_seconds = random.randint(idle_limit + 45, idle_limit + random.randint(240, 1680))
    return now - offline_seconds


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
    else:
        go_online = random.random() < persona.online_return_rate

    new_last_seen = _npc_last_seen_for_state(go_online, now)
    with get_connection() as conn:
        conn.execute("UPDATE players SET last_seen = ? WHERE id = ?", (new_last_seen, player_id))
        conn.commit()
    return go_online


def refresh_all_npc_presence(player_map: Dict[str, int]) -> Dict[str, bool]:
    presence: Dict[str, bool] = {}
    for persona in active_personas():
        player_id = player_map[persona.key]
        presence[persona.key] = refresh_npc_last_seen(player_id, persona)
    return presence


def seed_npc_listings(player_id: int, persona: NpcPersona, count: int) -> List[str]:
    listing_ids: List[str] = []
    now = int(time.time())
    for i in range(count):
        created_at = now - random.randint(3, 10) * 86400 - random.randint(0, 86400)
        listing_id = npc_list_stored_item(player_id, persona, listing_created_at=created_at)
        if listing_id:
            listing_ids.append(listing_id)
    return listing_ids


def seed_npc_showcase_prices(player_id: int, persona: NpcPersona) -> None:
    state = load_state(player_id)
    for item in state.inventory:
        if item.status == "displayed" and not item.showcase_price:
            price = persona_list_price(persona, item, jitter=random.uniform(0.88, 1.12))
            save_state(player_id, state)
            set_showcase_price(player_id, item.id, price)
            state = load_state(player_id)


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
        active = count_active_listings(player_id)
        target = random.randint(INITIAL_LISTINGS_MIN, INITIAL_LISTINGS_MAX)
        needed = max(0, target - active)
        ids = seed_npc_listings(player_id, persona, needed) if needed else []
        seed_npc_showcase_prices(player_id, persona)
        refresh_npc_last_seen(player_id, persona, force_online=random.random() < 0.88)
        summary["listings"][persona.key] = ids
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
        refresh_npc_last_seen(player_id, persona)

    presence = refresh_all_npc_presence(player_map)
    online_count = sum(1 for online in presence.values() if online)
    return {"actions": actions_log, "budget": budget, "online_npcs": online_count, "presence": presence}
