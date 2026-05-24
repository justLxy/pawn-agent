import os
import secrets
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from database import get_connection, transaction
from player_cosmetics import cosmetics_from_row
from shop_catalog import MONTHLY_SECONDS, PRODUCTS, TAGLINE_MAX_LEN, VALID_EMBLEMS


def _now() -> int:
    return int(time.time())


def _generate_order_no(player_id: int) -> str:
    suffix = secrets.token_hex(3).upper()
    return f"PS{player_id}{suffix}"


def get_catalog() -> List[Dict[str, Any]]:
    return [
        {
            "id": product["id"],
            "name": product["name"],
            "price_fen": product["price_fen"],
            "price_label": product["price_label"],
            "description": product["description"],
        }
        for product in PRODUCTS.values()
    ]


def create_manual_order(player_id: int, product_id: str) -> Dict[str, Any]:
    product = PRODUCTS.get(product_id)
    if not product:
        raise HTTPException(status_code=400, detail="未知商品。")
    order_id = secrets.token_urlsafe(12)
    order_no = _generate_order_no(player_id)
    now = _now()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO shop_orders (id, player_id, product_id, amount_fen, order_no, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (order_id, player_id, product_id, product["price_fen"], order_no, now),
        )
    return {
        "order_id": order_id,
        "order_no": order_no,
        "product_id": product_id,
        "product_name": product["name"],
        "amount_fen": product["price_fen"],
        "price_label": product["price_label"],
        "status": "pending",
        "pay_remark": order_no,
        "created_at": now,
        "instructions": f"微信付款时请备注订单号：{order_no}，金额 {product['price_label']}。付款后点击「我已付款」。",
    }


def submit_payment(player_id: int, order_id: str, payer_note: Optional[str] = None) -> Dict[str, Any]:
    note = (payer_note or "").strip()[:120] or None
    now = _now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM shop_orders WHERE id = ? AND player_id = ?",
            (order_id, player_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在。")
        if row["status"] == "fulfilled":
            return _order_payload(row)
        if row["status"] == "cancelled":
            raise HTTPException(status_code=400, detail="订单已取消。")
        conn.execute(
            """
            UPDATE shop_orders
            SET status = 'submitted', payer_note = ?, submitted_at = ?
            WHERE id = ? AND status IN ('pending', 'submitted')
            """,
            (note, now, order_id),
        )
        row = conn.execute("SELECT * FROM shop_orders WHERE id = ?", (order_id,)).fetchone()
    return _order_payload(row)


def list_player_orders(player_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM shop_orders
            WHERE player_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (player_id, limit),
        ).fetchall()
    return [_order_payload(row) for row in rows]


def _order_payload(row: Any) -> Dict[str, Any]:
    product = PRODUCTS.get(row["product_id"], {})
    return {
        "order_id": row["id"],
        "order_no": row["order_no"],
        "product_id": row["product_id"],
        "product_name": product.get("name", row["product_id"]),
        "price_label": product.get("price_label"),
        "amount_fen": row["amount_fen"],
        "status": row["status"],
        "payer_note": row["payer_note"],
        "created_at": row["created_at"],
        "submitted_at": row["submitted_at"],
        "fulfilled_at": row["fulfilled_at"],
    }


def fulfill_order(order_id: Optional[str] = None, order_no: Optional[str] = None) -> Dict[str, Any]:
    if not order_id and not order_no:
        raise HTTPException(status_code=400, detail="请提供 order_id 或 order_no。")
    now = _now()
    with transaction() as conn:
        if order_id:
            row = conn.execute("SELECT * FROM shop_orders WHERE id = ?", (order_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM shop_orders WHERE order_no = ?", (order_no,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="订单不存在。")
        if row["status"] == "fulfilled":
            player = conn.execute("SELECT * FROM players WHERE id = ?", (row["player_id"],)).fetchone()
            return {
                "order": _order_payload(row),
                "cosmetics": cosmetics_from_row(player, now),
                "message": "订单此前已发放。",
            }
        product = PRODUCTS.get(row["product_id"])
        if not product:
            raise HTTPException(status_code=400, detail="订单商品无效。")
        player_id = int(row["player_id"])
        player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        if row["product_id"] == "monthly_card":
            base = max(now, int(player["monthly_expires_at"] or 0))
            conn.execute(
                "UPDATE players SET monthly_expires_at = ? WHERE id = ?",
                (base + MONTHLY_SECONDS, player_id),
            )
        elif row["product_id"] == "plaque_permanent":
            conn.execute(
                "UPDATE players SET shop_emblem = COALESCE(shop_emblem, 'plaque') WHERE id = ?",
                (player_id,),
            )
        conn.execute(
            "UPDATE shop_orders SET status = 'fulfilled', fulfilled_at = ? WHERE id = ?",
            (now, row["id"]),
        )
        player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        row = conn.execute("SELECT * FROM shop_orders WHERE id = ?", (row["id"],)).fetchone()
    return {
        "order": _order_payload(row),
        "cosmetics": cosmetics_from_row(player, now),
        "message": "权益已发放。",
    }


def update_profile_cosmetics(player_id: int, shop_emblem: Optional[str] = None, showcase_tagline: Optional[str] = None) -> Dict[str, Any]:
    with get_connection() as conn:
        player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
        if not player:
            raise HTTPException(status_code=404, detail="玩家不存在。")
        if not player["shop_emblem"]:
            raise HTTPException(status_code=403, detail="请先购买当铺匾额（永久）。")
        updates: List[str] = []
        params: List[Any] = []
        if shop_emblem is not None:
            emblem = shop_emblem.strip()
            if emblem and emblem not in VALID_EMBLEMS:
                raise HTTPException(status_code=400, detail="无效匾额样式。")
            updates.append("shop_emblem = ?")
            params.append(emblem or "plaque")
        if showcase_tagline is not None:
            tagline = showcase_tagline.strip()
            if len(tagline) > TAGLINE_MAX_LEN:
                raise HTTPException(status_code=400, detail=f"橱窗文案不能超过 {TAGLINE_MAX_LEN} 字。")
            updates.append("showcase_tagline = ?")
            params.append(tagline or None)
        if not updates:
            raise HTTPException(status_code=400, detail="没有可更新的内容。")
        params.append(player_id)
        conn.execute(f"UPDATE players SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        player = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    return cosmetics_from_row(player)


def shop_admin_usernames() -> set[str]:
    raw = os.getenv("SHOP_ADMIN_USERNAMES", "milk")
    return {name.strip().lower() for name in raw.split(",") if name.strip()}


def is_shop_admin_username(username: str) -> bool:
    return username.strip().lower() in shop_admin_usernames()


def is_shop_admin_player(player: Dict[str, Any]) -> bool:
    return is_shop_admin_username(str(player.get("username") or ""))


def require_shop_admin(player: Dict[str, Any]) -> None:
    if not is_shop_admin_player(player):
        raise HTTPException(status_code=403, detail="无掌柜铺子管理权限。")


def verify_admin_secret(provided: Optional[str]) -> None:
    expected = os.getenv("SHOP_ADMIN_SECRET", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="未配置 SHOP_ADMIN_SECRET，无法人工发货。")
    if not provided or provided.strip() != expected:
        raise HTTPException(status_code=403, detail="管理密钥错误。")


def require_shop_admin_or_secret(player: Dict[str, Any], secret: Optional[str]) -> None:
    if is_shop_admin_player(player):
        return
    verify_admin_secret(secret)


def list_admin_pending_orders(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT o.*, p.username, p.shop_name
            FROM shop_orders o
            JOIN players p ON p.id = o.player_id
            WHERE o.status = 'submitted'
            ORDER BY COALESCE(o.submitted_at, o.created_at) ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    results = []
    for row in rows:
        payload = _order_payload(row)
        payload["username"] = row["username"]
        payload["shop_name"] = row["shop_name"]
        results.append(payload)
    return results
