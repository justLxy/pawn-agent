import json
import time
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from database import get_connection, transaction
from game_state import GameStateManager, Item


MARKET_TAX_RATE = 0.05
TRADE_COOLDOWN_SECONDS = 24 * 60 * 60


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
    await state.async_initialize_day(ai_client)
    save_state(player["id"], state)
    return state


def import_state(player_id: int, state_dict: Dict[str, Any], shop_name: Optional[str] = None) -> GameStateManager:
    state = GameStateManager.from_dict(state_dict)
    if shop_name:
        state.shop_name = shop_name
    save_state(player_id, state)
    return state


def reset_player_data(player_id: int, shop_name: str) -> GameStateManager:
    state = GameStateManager()
    state.shop_name = shop_name
    state.initialize_day_fast()
    now = int(time.time())
    with transaction() as conn:
        conn.execute("DELETE FROM market_listings WHERE seller_id = ?", (player_id,))
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
    return min(30, int(5 + max(0, shop_level - 1) * 6.25))


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
        now = int(time.time())
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
        owner = conn.execute("SELECT id, shop_name, online, reputation, ranking_badge FROM players WHERE id = ?", (owner_id,)).fetchone()
        save = conn.execute("SELECT state_json FROM game_saves WHERE player_id = ?", (owner_id,)).fetchone()
    if not owner or not save:
        raise HTTPException(status_code=404, detail="未找到该玩家当铺。")

    state = GameStateManager.from_dict(json.loads(save["state_json"]))
    items = [_public_item(item) for item in state.inventory if item.status == "displayed"]
    return {
        "owner": {
            "id": owner["id"],
            "shop_name": state.shop_name or owner["shop_name"],
            "online": bool(owner["online"]),
            "reputation": state.reputation,
            "ranking_badge": owner["ranking_badge"],
            "is_self": viewer_id == owner_id,
        },
        "items": items,
        "display_capacity": state.display_capacity(),
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


def buy_listing(buyer_id: int, listing_id: str) -> Dict[str, Any]:
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

        tax = int(price * MARKET_TAX_RATE)
        seller_income = price - tax
        item = Item.from_dict(json.loads(listing["item_json"]))
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
        conn.execute(
            "INSERT INTO trade_logs (buyer_id, seller_id, listing_id, item_name, price, tax, trade_type, created_at) VALUES (?, ?, ?, ?, ?, ?, 'sale', ?)",
            (buyer_id, listing["seller_id"], listing_id, item.name, price, tax, now),
        )
        conn.execute("UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?", (json.dumps(buyer.to_dict(), ensure_ascii=False), now, buyer_id))
        conn.execute("UPDATE game_saves SET state_json = ?, updated_at = ? WHERE player_id = ?", (json.dumps(seller.to_dict(), ensure_ascii=False), now, listing["seller_id"]))
        conn.execute("UPDATE players SET reputation = ? WHERE id = ?", (buyer.reputation, buyer_id))
        conn.execute("UPDATE players SET reputation = ? WHERE id = ?", (seller.reputation, listing["seller_id"]))
    return {"success": True, "message": f"购入【{item.name}】成功，支付 ${price}。", "tax": tax}


def _listing_to_dict(row: Any) -> Dict[str, Any]:
    item = json.loads(row["item_json"])
    return {
        "id": row["id"],
        "seller_id": row["seller_id"],
        "seller_shop": row["seller_shop"],
        "seller_online": bool(row["seller_online"]),
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
        "value_gap": "(ml.reference_price - ml.price) DESC",
    }.get(sort, "ml.created_at DESC")
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT ml.*, p.shop_name AS seller_shop, p.online AS seller_online
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
            SELECT ml.*, p.shop_name AS seller_shop, p.online AS seller_online
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
            SELECT p.id, p.shop_name, p.online, p.ranking_badge, gs.state_json
            FROM game_saves gs JOIN players p ON p.id = gs.player_id
            """
        ).fetchall()
    ranking = []
    for row in rows:
        state = GameStateManager.from_dict(json.loads(row["state_json"]))
        scores = _scores_for_state(state)
        ranking.append(
            {
                "player_id": row["id"],
                "shop_name": state.shop_name or row["shop_name"],
                "online": bool(row["online"]),
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
