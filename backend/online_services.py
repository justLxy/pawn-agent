import json
import time
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from auth import player_is_online
from database import get_connection, transaction
from game_state import GameStateManager, Item


MARKET_TAX_RATE = 0.05
TRADE_COOLDOWN_SECONDS = 24 * 60 * 60
OFFER_EXPIRY_SECONDS = 48 * 60 * 60
MAX_OFFER_ROUNDS = 3
ACTIVE_OFFER_STATUSES = ("pending_seller", "countered")
GUESTBOOK_COOLDOWN_SECONDS = 10 * 60
HOT_SHOWCASE_WINDOW_SECONDS = 7 * 24 * 60 * 60


def create_initial_state(shop_name: str) -> GameStateManager:
    state = GameStateManager()
    state.shop_name = shop_name
    return state


def load_state(player_id: int) -> GameStateManager:
    with get_connection() as conn:
        row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (player_id,)).fetchone()
    if not row:
        return GameStateManager()
    return GameStateManager.from_dict(json.loads(row["state_json"]))


def save_state(player_id: int, state: GameStateManager) -> None:
    now = int(time.time())
    payload = json.dumps(state.to_dict(), ensure_ascii=False)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO game_saves (player_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
            """,
            (player_id, payload, now),
        )
        conn.execute(
            "UPDATE players SET reputation = ?, ranking_badge = ?, reward_bonus = ?, last_seen = ? WHERE id = ?",
            (state.reputation, state.ranking_badge, state.ranking_reward_bonus, now, player_id),
        )


async def ensure_player_state(player: Dict[str, Any], ai_client: Any) -> GameStateManager:
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM game_saves WHERE player_id = ?", (player["id"],)).fetchone()
    if exists:
        return load_state(player["id"])
    state = create_initial_state(player["shop_name"])
    await state.async_initialize_day_with_fallback(ai_client)
    save_state(player["id"], state)
    return state


def import_state(player_id: int, state_dict: Dict[str, Any], shop_name: Optional[str] = None) -> GameStateManager:
    state = GameStateManager.from_dict(state_dict)
    if shop_name:
        state.shop_name = shop_name
    save_state(player_id, state)
    return state


def _resolve_trade_item_id(conn: Any, listing_id: Optional[str]) -> Optional[str]:
    if not listing_id:
        return None
    if listing_id.startswith("showcase:"):
        return listing_id.split(":", 1)[1]
    row = conn.execute("SELECT item_id FROM market_listings WHERE id = ?", (listing_id,)).fetchone()
    return str(row["item_id"]) if row else None


def _collect_recoverable_item_ids(conn: Any, buyer_id: int, old_state: GameStateManager) -> set[str]:
    item_ids = {item.id for item in old_state.inventory}
    rows = conn.execute(
        "SELECT item_id FROM market_listings WHERE seller_id = ? AND status = 'active'",
        (buyer_id,),
    ).fetchall()
    item_ids.update(str(row["item_id"]) for row in rows)
    return item_ids


def _item_snapshot_for_rollback(
    conn: Any,
    trade: Any,
    item_id: str,
    buyer_id: int,
    old_state: GameStateManager,
) -> Optional[Item]:
    listing_id = trade["listing_id"] or ""
    if listing_id.startswith("showcase:"):
        item = old_state.get_item(item_id)
        if item:
            return item
        row = conn.execute(
            "SELECT item_json FROM market_listings WHERE seller_id = ? AND item_id = ? AND status = 'active'",
            (buyer_id, item_id),
        ).fetchone()
        if row:
            return Item.from_dict(json.loads(row["item_json"]))
        return None

    row = conn.execute("SELECT item_json FROM market_listings WHERE id = ?", (listing_id,)).fetchone()
    if not row:
        return None
    return Item.from_dict(json.loads(row["item_json"]))


def _restore_item_for_seller(item: Item) -> Item:
    restored = Item.from_dict(item.to_dict())
    restored.status = "stored"
    restored.display_slot = None
    restored.showcase_price = None
    return restored


def _rollback_buyer_trades(conn: Any, buyer_id: int, old_state: GameStateManager) -> int:
    trades = conn.execute(
        "SELECT * FROM trade_logs WHERE buyer_id = ? ORDER BY created_at DESC",
        (buyer_id,),
    ).fetchall()
    if not trades:
        return 0

    recoverable = _collect_recoverable_item_ids(conn, buyer_id, old_state)
    sellers: Dict[int, GameStateManager] = {}
    processed_items: set[str] = set()
    rolled_back = 0
    now = int(time.time())

    for trade in trades:
        item_id = _resolve_trade_item_id(conn, trade["listing_id"])
        if not item_id or item_id not in recoverable or item_id in processed_items:
            continue

        item = _item_snapshot_for_rollback(conn, trade, item_id, buyer_id, old_state)
        if not item:
            continue

        seller_id = int(trade["seller_id"])
        if seller_id not in sellers:
            row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (seller_id,)).fetchone()
            if not row:
                continue
            sellers[seller_id] = GameStateManager.from_dict(json.loads(row["state_json"]))

        seller = sellers[seller_id]
        seller.cash -= int(trade["price"]) - int(trade["tax"])
        seller.inventory.append(_restore_item_for_seller(item))

        active_listing = conn.execute(
            "SELECT id FROM market_listings WHERE seller_id = ? AND item_id = ? AND status = 'active'",
            (buyer_id, item_id),
        ).fetchone()
        if active_listing:
            _cancel_listing_offers(conn, active_listing["id"], now)
            conn.execute(
                "UPDATE market_listings SET status = 'cancelled', updated_at = ? WHERE id = ?",
                (now, active_listing["id"]),
            )

        processed_items.add(item_id)
        recoverable.discard(item_id)
        rolled_back += 1

    for seller_id, seller in sellers.items():
        conn.execute(
            "UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?",
            (json.dumps(seller.to_dict(), ensure_ascii=False), now, seller_id),
        )
        conn.execute("UPDATE players SET reputation = ? WHERE id = ?", (seller.reputation, seller_id))

    return rolled_back


def reset_player_data(player_id: int, shop_name: str, state: Optional[GameStateManager] = None) -> GameStateManager:
    state = state or GameStateManager()
    state.shop_name = shop_name
    if not state.active_customer and not state.daily_customer_queue:
        state.initialize_day_fast()
    old_state = load_state(player_id)
    now = int(time.time())
    with transaction() as conn:
        _rollback_buyer_trades(conn, player_id, old_state)
        conn.execute("DELETE FROM market_offers WHERE buyer_id = ? OR seller_id = ?", (player_id, player_id))
        conn.execute("DELETE FROM market_listings WHERE seller_id = ?", (player_id,))
        conn.execute("DELETE FROM showcase_likes WHERE owner_id = ? OR liker_id = ?", (player_id, player_id))
        conn.execute("DELETE FROM showcase_guestbook WHERE owner_id = ? OR author_id = ?", (player_id, player_id))
        conn.execute("DELETE FROM trade_logs WHERE buyer_id = ? OR seller_id = ?", (player_id, player_id))
        conn.execute("DELETE FROM leaderboard_snapshots WHERE player_id = ?", (player_id,))
        conn.execute(
            """
            INSERT INTO game_saves (player_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
            """,
            (player_id, json.dumps(state.to_dict(), ensure_ascii=False), now),
        )
        conn.execute(
            "UPDATE players SET reputation = ?, ranking_badge = NULL, reward_bonus = 0, last_seen = ? WHERE id = ?",
            (state.reputation, now, player_id),
        )
    return state


def active_listing_limit(shop_level: int) -> int:
    return min(45, int(5 + max(0, shop_level - 1) * 6.25))


def reference_price(item: Item) -> int:
    return max(10, int(item.market_value))


def list_item(player_id: int, item_id: str, price: int) -> Dict[str, Any]:
    state = load_state(player_id)
    item = state.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到该物品。")
    if item.status not in ["stored", "displayed"]:
        raise HTTPException(status_code=400, detail="只有仓库或展示中的物品可以挂售。")
    if item.last_trade_at and int(time.time()) - int(item.last_trade_at) < TRADE_COOLDOWN_SECONDS:
        raise HTTPException(status_code=400, detail="该物品刚从玩家市场购入，24小时内不能再次挂售。")

    ref = reference_price(item)
    min_price = int(ref * 0.3)
    max_price = int(ref * 3)
    if price < min_price or price > max_price:
        raise HTTPException(status_code=400, detail=f"挂售价必须在参考价区间 ${min_price} - ${max_price} 内。")

    with get_connection() as conn:
        active_count = conn.execute(
            "SELECT COUNT(*) AS c FROM market_listings WHERE seller_id = ? AND status = 'active'",
            (player_id,),
        ).fetchone()["c"]
    if active_count >= active_listing_limit(state.shop_level):
        raise HTTPException(status_code=400, detail="当前摊位已满，请升级当铺或下架其他物品。")

    state.inventory = [existing for existing in state.inventory if existing.id != item_id]
    item.status = "listed"
    item.display_slot = None
    state._record_item_encounter(item, "market_list")
    now = int(time.time())
    listing_id = str(uuid.uuid4())[:12]
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO market_listings
            (id, seller_id, item_id, item_json, item_name, rarity, category, condition, price, reference_price, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                listing_id,
                player_id,
                item.id,
                json.dumps(item.to_dict(), ensure_ascii=False),
                item.name,
                item.rarity,
                item.category,
                item.condition,
                price,
                ref,
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO game_saves (player_id, state_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET state_json = excluded.state_json, updated_at = excluded.updated_at
            """,
            (player_id, json.dumps(state.to_dict(), ensure_ascii=False), now),
        )
    return {"success": True, "message": f"【{item.name}】已挂售，标价 ${price}。", "listing_id": listing_id}


def unlist_item(player_id: int, listing_id: str) -> Dict[str, Any]:
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM market_listings WHERE id = ? AND seller_id = ? AND status = 'active'",
            (listing_id, player_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="未找到可下架的挂售。")
        state_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (player_id,)).fetchone()
        state = GameStateManager.from_dict(json.loads(state_row["state_json"]))
        item = Item.from_dict(json.loads(row["item_json"]))
        item.status = "stored"
        item.display_slot = None
        state.inventory.append(item)
        state._record_item_encounter(item, "market_unlist")
        now = int(time.time())
        _cancel_listing_offers(conn, listing_id, now)
        conn.execute("UPDATE market_listings SET status = 'cancelled', updated_at = ? WHERE id = ?", (now, listing_id))
        conn.execute("UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?", (json.dumps(state.to_dict(), ensure_ascii=False), now, player_id))
    return {"success": True, "message": f"【{row['item_name']}】已下架并回到仓库。"}


def update_listing_price(player_id: int, listing_id: str, price: int) -> Dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT reference_price, item_name FROM market_listings WHERE id = ? AND seller_id = ? AND status = 'active'",
            (listing_id, player_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到可改价的挂售。")
    min_price = int(row["reference_price"] * 0.3)
    max_price = int(row["reference_price"] * 3)
    if price < min_price or price > max_price:
        raise HTTPException(status_code=400, detail=f"挂售价必须在参考价区间 ${min_price} - ${max_price} 内。")
    with get_connection() as conn:
        conn.execute("UPDATE market_listings SET price = ?, updated_at = ? WHERE id = ?", (price, int(time.time()), listing_id))
    return {"success": True, "message": f"【{row['item_name']}】已改价为 ${price}。"}


def _public_item(item: Item) -> Dict[str, Any]:
    return item.to_dict()


def set_showcase_price(player_id: int, item_id: str, price: Optional[int]) -> Dict[str, Any]:
    state = load_state(player_id)
    item = state.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到该展示品。")
    if item.status != "displayed":
        raise HTTPException(status_code=400, detail="只有展示柜里的物品可以设置橱窗售价。")
    if price is None or price <= 0:
        item.showcase_price = None
        save_state(player_id, state)
        return {"success": True, "message": f"【{item.name}】已取消橱窗售价。"}

    ref = reference_price(item)
    min_price = int(ref * 0.3)
    max_price = int(ref * 3)
    if price < min_price or price > max_price:
        raise HTTPException(status_code=400, detail=f"橱窗售价必须在 ${min_price} - ${max_price} 内。")
    item.showcase_price = int(price)
    save_state(player_id, state)
    return {"success": True, "message": f"【{item.name}】橱窗售价已设为 ${price}。"}


def get_player_showcase(viewer_id: int, owner_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        owner = conn.execute("SELECT id, shop_name, last_seen, reputation, ranking_badge FROM players WHERE id = ?", (owner_id,)).fetchone()
        save = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (owner_id,)).fetchone()
        if not owner or not save:
            raise HTTPException(status_code=404, detail="未找到该玩家当铺。")
        like_stats = _showcase_like_stats(conn, owner_id, viewer_id)
        guestbook = _guestbook_entries(conn, owner_id)

    state = GameStateManager.from_dict(json.loads(save["state_json"]))
    items = [_public_item(item) for item in state.inventory if item.status == "displayed"]
    hot_rank = _showcase_hot_rank(owner_id)
    return {
        "owner": {
            "id": owner["id"],
            "shop_name": state.shop_name or owner["shop_name"],
            "online": player_is_online(owner["last_seen"]),
            "reputation": state.reputation,
            "ranking_badge": owner["ranking_badge"],
            "is_self": viewer_id == owner_id,
        },
        "items": items,
        "display_capacity": state.display_capacity(),
        "like_count": like_stats["like_count"],
        "recent_like_count": like_stats["recent_like_count"],
        "liked_by_me": like_stats["liked_by_me"],
        "guestbook": guestbook,
        "hot_rank": hot_rank,
    }


def buy_showcase_item(buyer_id: int, owner_id: int, item_id: str) -> Dict[str, Any]:
    if buyer_id == owner_id:
        raise HTTPException(status_code=400, detail="不能购买自己橱窗里的物品。")
    with transaction() as conn:
        buyer_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (buyer_id,)).fetchone()
        owner_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (owner_id,)).fetchone()
        if not buyer_row or not owner_row:
            raise HTTPException(status_code=404, detail="交易双方存档不完整。")

        buyer = GameStateManager.from_dict(json.loads(buyer_row["state_json"]))
        owner = GameStateManager.from_dict(json.loads(owner_row["state_json"]))
        item = owner.get_item(item_id)
        if not item or item.status != "displayed":
            raise HTTPException(status_code=404, detail="该展示品已不在橱窗中。")
        if not item.showcase_price:
            raise HTTPException(status_code=400, detail="该展示品只展示不出售。")

        price = int(item.showcase_price)
        if buyer.cash < price:
            raise HTTPException(status_code=400, detail="现金不足，无法购买该展示品。")

        tax = int(price * MARKET_TAX_RATE)
        owner_income = price - tax
        original_purchase_price = int(item.purchase_price or 0)
        owner.inventory = [existing for existing in owner.inventory if existing.id != item_id]
        item.status = "stored"
        item.display_slot = None
        item.showcase_price = None
        item.purchase_price = price
        item.last_trade_at = int(time.time())
        item.acquired_at = int(time.time())
        item.acquired_day = buyer.day
        item.last_value_update_day = buyer.day
        item.base_value_at_purchase = item.market_value
        item.holding_cost_paid = 0
        item.value_history = [{"day": buyer.day, "market_value": item.market_value, "delta": 0, "holding_cost": 0}]
        item.value_trend_note = "今天从玩家橱窗购入，尚未产生持有成本。"
        buyer.cash -= price
        buyer.inventory.append(item)
        owner.cash += owner_income
        buyer._record_item_encounter(item, "showcase_buy")
        owner._record_item_encounter(item, "showcase_sell")
        buyer.transaction_log.append({"day": buyer.day, "type": "showcase_buy", "item": item.name, "amount": -price})
        owner.transaction_log.append({"day": owner.day, "type": "showcase_sell", "item": item.name, "amount": owner_income})
        buyer.successful_trades += 1
        buyer.reputation += 1
        owner.successful_trades += 1
        owner.positive_reviews += 1
        owner.reputation += 2
        owner.total_profit += max(0, owner_income - original_purchase_price)
        buyer._check_achievements("showcase_buy", {"item": item.to_dict(), "price": price})
        owner._check_achievements("showcase_sell", {"item": item.to_dict(), "price": owner_income})
        now = int(time.time())

        conn.execute(
            "INSERT INTO trade_logs (buyer_id, seller_id, listing_id, item_name, price, tax, trade_type, created_at) VALUES (?, ?, ?, ?, ?, ?, 'showcase_sale', ?)",
            (buyer_id, owner_id, f"showcase:{item_id}", item.name, price, tax, now),
        )
        conn.execute("UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?", (json.dumps(buyer.to_dict(), ensure_ascii=False), now, buyer_id))
        conn.execute("UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?", (json.dumps(owner.to_dict(), ensure_ascii=False), now, owner_id))
        conn.execute("UPDATE players SET reputation = ? WHERE id = ?", (buyer.reputation, buyer_id))
        conn.execute("UPDATE players SET reputation = ? WHERE id = ?", (owner.reputation, owner_id))
    return {"success": True, "message": f"你从对方橱窗买下了【{item.name}】，支付 ${price}。", "tax": tax}


def _price_bounds(reference_price: int) -> tuple[int, int]:
    ref = int(reference_price)
    return int(ref * 0.3), int(ref * 3)


def _cancel_listing_offers(conn: Any, listing_id: str, now: int) -> None:
    conn.execute(
        """
        UPDATE market_offers
        SET status = 'cancelled', updated_at = ?
        WHERE listing_id = ? AND status IN ('pending_seller', 'countered')
        """,
        (now, listing_id),
    )


def expire_stale_offers() -> None:
    now = int(time.time())
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE market_offers
            SET status = 'expired', updated_at = ?
            WHERE status IN ('pending_seller', 'countered') AND expires_at < ?
            """,
            (now, now),
        )
        conn.commit()


def _execute_market_sale(
    conn: Any,
    buyer: GameStateManager,
    seller: GameStateManager,
    item: Item,
    price: int,
    listing_id: str,
    buyer_id: int,
    seller_id: int,
    trade_type: str,
) -> int:
    tax = int(price * MARKET_TAX_RATE)
    seller_income = price - tax
    original_purchase_price = int(item.purchase_price or 0)
    item.status = "stored"
    item.purchase_price = price
    item.last_trade_at = int(time.time())
    item.acquired_at = int(time.time())
    item.acquired_day = buyer.day
    item.last_value_update_day = buyer.day
    item.base_value_at_purchase = item.market_value
    item.holding_cost_paid = 0
    item.value_history = [{"day": buyer.day, "market_value": item.market_value, "delta": 0, "holding_cost": 0}]
    item.value_trend_note = "今天从玩家市场购入，尚未产生持有成本。"
    item.display_slot = None
    buyer.cash -= price
    buyer.inventory.append(item)
    buyer._record_item_encounter(item, "market_buy")
    seller._record_item_encounter(item, "market_sell")
    buyer.transaction_log.append({"day": buyer.day, "type": "market_buy", "item": item.name, "amount": -price})
    buyer.successful_trades += 1
    buyer.reputation += 1
    seller.cash += seller_income
    seller.transaction_log.append({"day": seller.day, "type": "market_sell", "item": item.name, "amount": seller_income})
    seller.successful_trades += 1
    seller.positive_reviews += 1
    seller.reputation += 2
    seller.total_profit += max(0, seller_income - original_purchase_price)
    buyer._check_achievements("market_buy", {"item": item.to_dict(), "price": price})
    seller._check_achievements("market_sell", {"item": item.to_dict(), "price": seller_income})
    now = int(time.time())
    conn.execute("UPDATE market_listings SET status = 'sold', updated_at = ? WHERE id = ?", (now, listing_id))
    _cancel_listing_offers(conn, listing_id, now)
    conn.execute(
        "INSERT INTO trade_logs (buyer_id, seller_id, listing_id, item_name, price, tax, trade_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (buyer_id, seller_id, listing_id, item.name, price, tax, trade_type, now),
    )
    conn.execute("UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?", (json.dumps(buyer.to_dict(), ensure_ascii=False), now, buyer_id))
    conn.execute("UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?", (json.dumps(seller.to_dict(), ensure_ascii=False), now, seller_id))
    conn.execute("UPDATE players SET reputation = ? WHERE id = ?", (buyer.reputation, buyer_id))
    conn.execute("UPDATE players SET reputation = ? WHERE id = ?", (seller.reputation, seller_id))
    return tax


def buy_listing(buyer_id: int, listing_id: str) -> Dict[str, Any]:
    expire_stale_offers()
    with transaction() as conn:
        listing = conn.execute(
            "SELECT ml.*, p.shop_name AS seller_shop FROM market_listings ml JOIN players p ON p.id = ml.seller_id WHERE ml.id = ? AND ml.status = 'active'",
            (listing_id,),
        ).fetchone()
        if not listing:
            raise HTTPException(status_code=404, detail="该挂售已不存在或已售出。")
        if listing["seller_id"] == buyer_id:
            raise HTTPException(status_code=400, detail="不能购买自己挂售的物品。")

        buyer_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (buyer_id,)).fetchone()
        seller_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (listing["seller_id"],)).fetchone()
        if not buyer_row or not seller_row:
            raise HTTPException(status_code=400, detail="交易双方存档不完整。")
        buyer = GameStateManager.from_dict(json.loads(buyer_row["state_json"]))
        seller = GameStateManager.from_dict(json.loads(seller_row["state_json"]))
        price = int(listing["price"])
        if buyer.cash < price:
            raise HTTPException(status_code=400, detail="现金不足，无法购买。")

        item = Item.from_dict(json.loads(listing["item_json"]))
        tax = _execute_market_sale(conn, buyer, seller, item, price, listing_id, buyer_id, listing["seller_id"], "sale")
    return {"success": True, "message": f"购入【{item.name}】成功，支付 ${price}。", "tax": tax}


def _offer_to_dict(row: Any) -> Dict[str, Any]:
    listing = json.loads(row["item_json"]) if isinstance(row["item_json"], str) else row["item_json"]
    return {
        "id": row["offer_id"],
        "listing_id": row["listing_id"],
        "buyer_id": row["buyer_id"],
        "seller_id": row["seller_id"],
        "buyer_shop": row["buyer_shop"],
        "seller_shop": row["seller_shop"],
        "buyer_offer": row["buyer_offer"],
        "seller_counter": row["seller_counter"],
        "status": row["status"],
        "round": row["round"],
        "final_price": row["final_price"],
        "listing_price": row["listing_price"],
        "reference_price": row["reference_price"],
        "item_name": row["item_name"],
        "item": listing,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "expires_at": row["expires_at"],
    }


def _get_active_listing(conn: Any, listing_id: str) -> Any:
    return conn.execute(
        "SELECT * FROM market_listings WHERE id = ? AND status = 'active'",
        (listing_id,),
    ).fetchone()


def _validate_buyer_offer(price: int, listing: Any) -> None:
    min_price, max_price = _price_bounds(int(listing["reference_price"]))
    list_price = int(listing["price"])
    if price < min_price or price > max_price:
        raise HTTPException(status_code=400, detail=f"出价必须在参考价区间 ${min_price} - ${max_price} 内。")
    if price > list_price:
        raise HTTPException(status_code=400, detail=f"出价不能高于挂售价 ${list_price}。")


def _validate_seller_counter(counter_price: int, buyer_offer: int, listing: Any) -> None:
    list_price = int(listing["price"])
    if counter_price < buyer_offer:
        raise HTTPException(status_code=400, detail="反价不能低于买家出价。")
    if counter_price > list_price:
        raise HTTPException(status_code=400, detail=f"反价不能高于挂售价 ${list_price}。")


def _complete_offer_sale(conn: Any, offer: Any, listing: Any, final_price: int) -> Dict[str, Any]:
    buyer_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (offer["buyer_id"],)).fetchone()
    seller_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (offer["seller_id"],)).fetchone()
    if not buyer_row or not seller_row:
        raise HTTPException(status_code=400, detail="交易双方存档不完整。")
    buyer = GameStateManager.from_dict(json.loads(buyer_row["state_json"]))
    seller = GameStateManager.from_dict(json.loads(seller_row["state_json"]))
    if buyer.cash < final_price:
        raise HTTPException(status_code=400, detail="买家现金不足，无法完成议价成交。")
    item = Item.from_dict(json.loads(listing["item_json"]))
    now = int(time.time())
    tax = _execute_market_sale(conn, buyer, seller, item, final_price, listing["id"], offer["buyer_id"], offer["seller_id"], "negotiated_sale")
    conn.execute(
        "UPDATE market_offers SET status = 'accepted', final_price = ?, updated_at = ? WHERE id = ?",
        (final_price, now, offer["id"]),
    )
    return {"success": True, "message": f"议价成交【{item.name}】，成交价 ${final_price}。", "tax": tax, "final_price": final_price}


def create_offer(buyer_id: int, listing_id: str, price: int) -> Dict[str, Any]:
    expire_stale_offers()
    with get_connection() as conn:
        listing = _get_active_listing(conn, listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="该挂售已不存在或已售出。")
        if listing["seller_id"] == buyer_id:
            raise HTTPException(status_code=400, detail="不能对自己的挂售发起议价。")
        _validate_buyer_offer(price, listing)
        existing = conn.execute(
            """
            SELECT id FROM market_offers
            WHERE listing_id = ? AND buyer_id = ? AND status IN ('pending_seller', 'countered')
            """,
            (listing_id, buyer_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="你已有该挂售的进行中议价，请先处理或撤回。")
        buyer_state = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (buyer_id,)).fetchone()
        if not buyer_state:
            raise HTTPException(status_code=400, detail="买家存档不完整。")
        buyer = GameStateManager.from_dict(json.loads(buyer_state["state_json"]))
        if buyer.cash < price:
            raise HTTPException(status_code=400, detail="现金不足，无法发起该出价。")

    now = int(time.time())
    offer_id = str(uuid.uuid4())[:12]
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO market_offers
            (id, listing_id, buyer_id, seller_id, buyer_offer, seller_counter, status, round, final_price, created_at, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, NULL, 'pending_seller', 1, NULL, ?, ?, ?)
            """,
            (offer_id, listing_id, buyer_id, listing["seller_id"], price, now, now, now + OFFER_EXPIRY_SECONDS),
        )
    return {"success": True, "message": f"已出价 ${price}，等待卖家回应。", "offer_id": offer_id}


def respond_offer(seller_id: int, offer_id: str, action: str, counter_price: Optional[int] = None) -> Dict[str, Any]:
    expire_stale_offers()
    action = action.strip().lower()
    if action not in {"accept", "counter", "reject"}:
        raise HTTPException(status_code=400, detail="无效操作。")

    with transaction() as conn:
        offer = conn.execute("SELECT * FROM market_offers WHERE id = ?", (offer_id,)).fetchone()
        if not offer:
            raise HTTPException(status_code=404, detail="未找到该议价。")
        if offer["seller_id"] != seller_id:
            raise HTTPException(status_code=403, detail="无权处理该议价。")
        if offer["status"] != "pending_seller":
            raise HTTPException(status_code=400, detail="该议价当前不在等待卖家回应。")

        listing = _get_active_listing(conn, offer["listing_id"])
        if not listing:
            now = int(time.time())
            conn.execute("UPDATE market_offers SET status = 'cancelled', updated_at = ? WHERE id = ?", (now, offer_id))
            raise HTTPException(status_code=404, detail="挂售已失效，议价已关闭。")

        now = int(time.time())
        if action == "reject":
            conn.execute("UPDATE market_offers SET status = 'rejected', updated_at = ? WHERE id = ?", (now, offer_id))
            return {"success": True, "message": "已拒绝该出价。"}

        if action == "accept":
            final_price = int(offer["buyer_offer"])
            return _complete_offer_sale(conn, offer, listing, final_price)

        if counter_price is None:
            raise HTTPException(status_code=400, detail="反价需要提供价格。")
        if int(offer["round"]) >= MAX_OFFER_ROUNDS:
            raise HTTPException(status_code=400, detail="已达最大议价轮次，只能接受或拒绝。")
        _validate_seller_counter(int(counter_price), int(offer["buyer_offer"]), listing)
        conn.execute(
            """
            UPDATE market_offers
            SET seller_counter = ?, status = 'countered', round = round + 1, updated_at = ?
            WHERE id = ?
            """,
            (int(counter_price), now, offer_id),
        )
        return {"success": True, "message": f"已反价 ${int(counter_price)}，等待买家回应。"}


def buyer_respond_offer(buyer_id: int, offer_id: str, action: str, price: Optional[int] = None) -> Dict[str, Any]:
    expire_stale_offers()
    action = action.strip().lower()
    if action not in {"accept", "counter", "cancel"}:
        raise HTTPException(status_code=400, detail="无效操作。")

    with transaction() as conn:
        offer = conn.execute("SELECT * FROM market_offers WHERE id = ?", (offer_id,)).fetchone()
        if not offer:
            raise HTTPException(status_code=404, detail="未找到该议价。")
        if offer["buyer_id"] != buyer_id:
            raise HTTPException(status_code=403, detail="无权处理该议价。")
        if offer["status"] != "countered":
            raise HTTPException(status_code=400, detail="该议价当前不在等待买家回应。")
        if not offer["seller_counter"]:
            raise HTTPException(status_code=400, detail="缺少卖家反价。")

        listing = _get_active_listing(conn, offer["listing_id"])
        if not listing:
            now = int(time.time())
            conn.execute("UPDATE market_offers SET status = 'cancelled', updated_at = ? WHERE id = ?", (now, offer_id))
            raise HTTPException(status_code=404, detail="挂售已失效，议价已关闭。")

        now = int(time.time())
        if action == "cancel":
            conn.execute("UPDATE market_offers SET status = 'cancelled', updated_at = ? WHERE id = ?", (now, offer_id))
            return {"success": True, "message": "已撤回议价。"}

        if action == "accept":
            final_price = int(offer["seller_counter"])
            return _complete_offer_sale(conn, offer, listing, final_price)

        if price is None:
            raise HTTPException(status_code=400, detail="再出价需要提供价格。")
        if int(offer["round"]) >= MAX_OFFER_ROUNDS:
            raise HTTPException(status_code=400, detail="已达最大议价轮次，只能接受反价或撤回。")
        _validate_buyer_offer(int(price), listing)
        buyer_row = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (buyer_id,)).fetchone()
        buyer = GameStateManager.from_dict(json.loads(buyer_row["state_json"]))
        if buyer.cash < int(price):
            raise HTTPException(status_code=400, detail="现金不足，无法发起该出价。")
        conn.execute(
            """
            UPDATE market_offers
            SET buyer_offer = ?, seller_counter = NULL, status = 'pending_seller', round = round + 1, updated_at = ?
            WHERE id = ?
            """,
            (int(price), now, offer_id),
        )
        return {"success": True, "message": f"已更新出价为 ${int(price)}，等待卖家回应。"}


def get_my_offers(player_id: int) -> Dict[str, Any]:
    expire_stale_offers()
    query = """
        SELECT mo.id AS offer_id, mo.*, ml.item_json, ml.item_name, ml.price AS listing_price, ml.reference_price,
               bp.shop_name AS buyer_shop, sp.shop_name AS seller_shop
        FROM market_offers mo
        JOIN market_listings ml ON ml.id = mo.listing_id
        JOIN players bp ON bp.id = mo.buyer_id
        JOIN players sp ON sp.id = mo.seller_id
        WHERE mo.buyer_id = ? OR mo.seller_id = ?
        ORDER BY mo.updated_at DESC
        LIMIT 100
    """
    with get_connection() as conn:
        rows = conn.execute(query, (player_id, player_id)).fetchall()
    sent: List[Dict[str, Any]] = []
    received: List[Dict[str, Any]] = []
    for row in rows:
        payload = _offer_to_dict(row)
        if row["buyer_id"] == player_id:
            sent.append(payload)
        if row["seller_id"] == player_id:
            received.append(payload)
    return {"sent": sent, "received": received}


def _showcase_like_stats(conn: Any, owner_id: int, viewer_id: int) -> Dict[str, Any]:
    now = int(time.time())
    recent_cutoff = now - HOT_SHOWCASE_WINDOW_SECONDS
    like_count = conn.execute("SELECT COUNT(*) AS c FROM showcase_likes WHERE owner_id = ?", (owner_id,)).fetchone()["c"]
    recent_like_count = conn.execute(
        "SELECT COUNT(*) AS c FROM showcase_likes WHERE owner_id = ? AND created_at >= ?",
        (owner_id, recent_cutoff),
    ).fetchone()["c"]
    liked_by_me = bool(
        conn.execute(
            "SELECT 1 FROM showcase_likes WHERE owner_id = ? AND liker_id = ?",
            (owner_id, viewer_id),
        ).fetchone()
    )
    return {"like_count": int(like_count), "recent_like_count": int(recent_like_count), "liked_by_me": liked_by_me}


def _showcase_hot_rank(owner_id: int) -> Optional[int]:
    hot = get_hot_showcases(limit=100)
    for entry in hot:
        if entry["player_id"] == owner_id:
            return entry["rank"]
    return None


def toggle_showcase_like(liker_id: int, owner_id: int) -> Dict[str, Any]:
    if liker_id == owner_id:
        raise HTTPException(status_code=400, detail="不能给自己的橱窗点赞。")
    with get_connection() as conn:
        owner = conn.execute("SELECT id FROM players WHERE id = ?", (owner_id,)).fetchone()
        if not owner:
            raise HTTPException(status_code=404, detail="未找到该玩家当铺。")
        existing = conn.execute(
            "SELECT id FROM showcase_likes WHERE owner_id = ? AND liker_id = ?",
            (owner_id, liker_id),
        ).fetchone()
        now = int(time.time())
        if existing:
            conn.execute("DELETE FROM showcase_likes WHERE owner_id = ? AND liker_id = ?", (owner_id, liker_id))
            conn.commit()
            liked = False
            message = "已取消点赞。"
        else:
            conn.execute(
                "INSERT INTO showcase_likes (owner_id, liker_id, created_at) VALUES (?, ?, ?)",
                (owner_id, liker_id, now),
            )
            conn.commit()
            liked = True
            message = "点赞成功。"
        stats = _showcase_like_stats(conn, owner_id, liker_id)
    return {"success": True, "message": message, "liked": liked, **stats}


def post_guestbook(author_id: int, owner_id: int, content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="留言不能为空。")
    if len(text) > 200:
        raise HTTPException(status_code=400, detail="留言不能超过 200 字。")
    with get_connection() as conn:
        owner = conn.execute("SELECT id FROM players WHERE id = ?", (owner_id,)).fetchone()
        if not owner:
            raise HTTPException(status_code=404, detail="未找到该玩家当铺。")
        recent = conn.execute(
            """
            SELECT created_at FROM showcase_guestbook
            WHERE owner_id = ? AND author_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (owner_id, author_id),
        ).fetchone()
        now = int(time.time())
        if recent and now - int(recent["created_at"]) < GUESTBOOK_COOLDOWN_SECONDS:
            raise HTTPException(status_code=400, detail="留言太频繁，请稍后再试。")
        cursor = conn.execute(
            "INSERT INTO showcase_guestbook (owner_id, author_id, content, created_at) VALUES (?, ?, ?, ?)",
            (owner_id, author_id, text, now),
        )
        message_id = cursor.lastrowid
        conn.commit()
        author = conn.execute("SELECT shop_name FROM players WHERE id = ?", (author_id,)).fetchone()
    return {
        "success": True,
        "message": "留言已发布。",
        "entry": {
            "id": message_id,
            "owner_id": owner_id,
            "author_id": author_id,
            "author_shop": author["shop_name"] if author else "访客",
            "content": text,
            "created_at": now,
        },
    }


def delete_guestbook(owner_id: int, message_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM showcase_guestbook WHERE id = ? AND owner_id = ?", (message_id, owner_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="未找到该留言。")
        conn.execute("DELETE FROM showcase_guestbook WHERE id = ?", (message_id,))
        conn.commit()
    return {"success": True, "message": "留言已删除。"}


def get_hot_showcases(limit: int = 20) -> List[Dict[str, Any]]:
    now = int(time.time())
    recent_cutoff = now - HOT_SHOWCASE_WINDOW_SECONDS
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT sl.owner_id,
                   SUM(CASE WHEN sl.created_at >= ? THEN 1 ELSE 0 END) AS recent_likes,
                   COUNT(*) AS total_likes,
                   p.shop_name, p.last_seen, p.ranking_badge, gs.state_json
            FROM showcase_likes sl
            JOIN players p ON p.id = sl.owner_id
            LEFT JOIN game_saves gs ON gs.player_id = sl.owner_id
            GROUP BY sl.owner_id
            HAVING recent_likes >= 1
            ORDER BY recent_likes DESC, total_likes DESC
            LIMIT ?
            """,
            (recent_cutoff, max(limit * 3, limit)),
        ).fetchall()

    entries: List[Dict[str, Any]] = []
    for row in rows:
        if not row["state_json"]:
            continue
        state = GameStateManager.from_dict(json.loads(row["state_json"]))
        displayed = sum(1 for item in state.inventory if item.status == "displayed")
        if displayed <= 0:
            continue
        entries.append(
            {
                "player_id": row["owner_id"],
                "shop_name": state.shop_name or row["shop_name"],
                "online": player_is_online(row["last_seen"]),
                "ranking_badge": row["ranking_badge"],
                "recent_likes": int(row["recent_likes"]),
                "total_likes": int(row["total_likes"]),
                "displayed_count": displayed,
                "display_capacity": state.display_capacity(),
            }
        )
        if len(entries) >= limit:
            break
    for index, entry in enumerate(entries, start=1):
        entry["rank"] = index
    return entries


def _guestbook_entries(conn: Any, owner_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT g.*, p.shop_name AS author_shop
        FROM showcase_guestbook g
        JOIN players p ON p.id = g.author_id
        WHERE g.owner_id = ?
        ORDER BY g.created_at DESC
        LIMIT ?
        """,
        (owner_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _listing_to_dict(row: Any) -> Dict[str, Any]:
    item = json.loads(row["item_json"])
    return {
        "id": row["id"],
        "seller_id": row["seller_id"],
        "seller_shop": row["seller_shop"],
        "seller_online": player_is_online(row["seller_last_seen"]),
        "item": item,
        "item_name": row["item_name"],
        "rarity": row["rarity"],
        "category": row["category"],
        "condition": row["condition"],
        "price": row["price"],
        "reference_price": row["reference_price"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_market_listings(
    search: str = "",
    rarity: str = "",
    category: str = "",
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    sort: str = "newest",
) -> List[Dict[str, Any]]:
    clauses = ["ml.status = 'active'"]
    params: List[Any] = []
    if search:
        clauses.append("ml.item_name LIKE ?")
        params.append(f"%{search}%")
    if rarity:
        clauses.append("ml.rarity = ?")
        params.append(rarity)
    if category:
        clauses.append("ml.category = ?")
        params.append(category)
    if min_price is not None:
        clauses.append("ml.price >= ?")
        params.append(min_price)
    if max_price is not None:
        clauses.append("ml.price <= ?")
        params.append(max_price)
    order = {
        "price_asc": "ml.price ASC",
        "price_desc": "ml.price DESC",
    }.get(sort, "ml.created_at DESC")
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT ml.*, p.shop_name AS seller_shop, p.last_seen AS seller_last_seen
            FROM market_listings ml JOIN players p ON p.id = ml.seller_id
            WHERE {' AND '.join(clauses)}
            ORDER BY {order}
            LIMIT 100
            """,
            params,
        ).fetchall()
    return [_listing_to_dict(row) for row in rows]


def get_my_listings(player_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ml.*, p.shop_name AS seller_shop, p.last_seen AS seller_last_seen
            FROM market_listings ml JOIN players p ON p.id = ml.seller_id
            WHERE ml.seller_id = ? AND ml.status = 'active'
            ORDER BY ml.created_at DESC
            """,
            (player_id,),
        ).fetchall()
    return [_listing_to_dict(row) for row in rows]


def get_trade_logs(player_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT tl.*, bp.shop_name AS buyer_shop, sp.shop_name AS seller_shop
            FROM trade_logs tl
            LEFT JOIN players bp ON bp.id = tl.buyer_id
            LEFT JOIN players sp ON sp.id = tl.seller_id
            WHERE tl.buyer_id = ? OR tl.seller_id = ?
            ORDER BY tl.created_at DESC
            LIMIT 80
            """,
            (player_id, player_id),
        ).fetchall()
    return [dict(row) for row in rows]


def _scores_for_state(state: GameStateManager) -> Dict[str, int]:
    assets = int(state.cash + sum(item.market_value for item in state.inventory))
    success_rate = int((state.successful_trades / max(1, state.successful_trades + 2)) * 100)
    review_rate = int((state.positive_reviews / max(1, state.successful_trades)) * 100)
    reputation_score = int(state.reputation * 10 + success_rate * 3 + review_rate * 2)
    collection = 0
    for item in state.inventory:
        collection += {"common": 1, "rare": 3, "epic": 8, "legendary": 20}.get(item.rarity, 1)
    return {
        "assets": assets,
        "reputation": reputation_score,
        "profit": int(state.total_profit),
        "collection": collection,
    }


def _ensure_daily_rewards() -> None:
    today = date.today().isoformat()
    now = int(time.time())
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM leaderboard_snapshots WHERE snapshot_date = ? LIMIT 1", (today,)).fetchone()
        if exists:
            return
        saves = conn.execute(
            """
            SELECT gs.player_id, gs.state_json
            FROM game_saves gs
            """
        ).fetchall()
        rows: List[tuple[int, str, int]] = []
        for save in saves:
            state = GameStateManager.from_dict(json.loads(save["state_json"]))
            rows.append((save["player_id"], "assets", _scores_for_state(state)["assets"]))
        rows.sort(key=lambda item: item[2], reverse=True)
        for rank, (player_id, board_type, score) in enumerate(rows[:100], start=1):
            conn.execute(
                "INSERT OR IGNORE INTO leaderboard_snapshots (snapshot_date, board_type, player_id, rank, score, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (today, board_type, player_id, rank, score, now),
            )
            badge = "全服第一当铺" if rank == 1 else None
            bonus = max(1, 101 - rank)
            conn.execute("UPDATE players SET ranking_badge = COALESCE(?, ranking_badge), reward_bonus = ? WHERE id = ?", (badge, bonus, player_id))


def get_leaderboard(board_type: str, player_id: int) -> Dict[str, Any]:
    if board_type not in ["assets", "reputation", "profit", "collection"]:
        raise HTTPException(status_code=400, detail="未知排行榜类型。")
    _ensure_daily_rewards()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.username, p.shop_name, p.last_seen, p.ranking_badge, gs.state_json
            FROM game_saves gs JOIN players p ON p.id = gs.player_id
            """
        ).fetchall()
    now = int(time.time())
    ranking = []
    for row in rows:
        state = GameStateManager.from_dict(json.loads(row["state_json"]))
        scores = _scores_for_state(state)
        ranking.append(
            {
                "player_id": row["id"],
                "username": row["username"],
                "shop_name": state.shop_name or row["shop_name"],
                "online": player_is_online(row["last_seen"], now),
                "badge": row["ranking_badge"],
                "score": scores[board_type],
                "assets": scores["assets"],
                "reputation": state.reputation,
                "profit": state.total_profit,
                "collection": scores["collection"],
            }
        )
    ranking.sort(key=lambda item: item["score"], reverse=True)
    for index, item in enumerate(ranking, start=1):
        item["rank"] = index
    my_rank = next((item for item in ranking if item["player_id"] == player_id), None)
    return {"type": board_type, "entries": ranking[:100], "my_rank": my_rank, "updated_at": int(time.time())}
