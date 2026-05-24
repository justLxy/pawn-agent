import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

from database import get_connection
from player_cosmetics import merge_cosmetics_into_player
from shop_service import is_shop_admin_username

ONLINE_IDLE_SECONDS = int(os.getenv("PLAYER_ONLINE_IDLE_SECONDS", "300"))


def player_is_online(last_seen: int, now: Optional[int] = None) -> bool:
    """根据最近活跃时间判断是否在线，避免关页未登出时长期显示在线。"""
    if last_seen <= 0:
        return False
    now = now if now is not None else int(time.time())
    return (now - last_seen) < ONLINE_IDLE_SECONDS


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000)
    return digest.hex(), salt


def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = _hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def _public_player(row: Any) -> Dict[str, Any]:
    username = row["username"]
    return {
        "id": row["id"],
        "username": username,
        "shop_name": row["shop_name"],
        "online": player_is_online(row["last_seen"]),
        "reputation": row["reputation"],
        "ranking_badge": row["ranking_badge"],
        "reward_bonus": row["reward_bonus"],
        "created_at": row["created_at"],
        "last_seen": row["last_seen"],
        "is_shop_admin": is_shop_admin_username(username),
    }


def _normalize_username(username: str) -> str:
    return username.strip()


def _validate_username(username: str) -> None:
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少需要 2 个字符。")
    if len(username) > 20:
        raise HTTPException(status_code=400, detail="用户名不能超过 20 个字符。")
    if any(ch.isspace() for ch in username):
        raise HTTPException(status_code=400, detail="用户名不能包含空格。")


def register_player(username: str, password: str, shop_name: str) -> Dict[str, Any]:
    username = _normalize_username(username)
    shop_name = shop_name.strip()
    _validate_username(username)
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="密码至少需要 4 个字符。")
    if not shop_name:
        raise HTTPException(status_code=400, detail="请输入当铺名称。")

    password_hash, salt = _hash_password(password)
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    try:
      with get_connection() as conn:
          conn.execute(
              """
              INSERT INTO players (username, shop_name, password_hash, salt, token, online, created_at, last_seen)
              VALUES (?, ?, ?, ?, ?, 1, ?, ?)
              """,
              (username, shop_name, password_hash, salt, token, now, now),
          )
          player = conn.execute("SELECT * FROM players WHERE username = ?", (username,)).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="用户名已存在。") from exc
    return {"token": token, "player": merge_cosmetics_into_player(_public_player(player), player)}


def count_online_players(now: Optional[int] = None) -> int:
    now = now if now is not None else int(time.time())
    threshold = now - ONLINE_IDLE_SECONDS
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM players WHERE last_seen > ?", (threshold,)).fetchone()
    return int(row["c"] or 0)


def recover_usernames_by_password(password: str) -> list[str]:
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="密码至少需要 4 个字符。")
    matches: list[str] = []
    with get_connection() as conn:
        rows = conn.execute("SELECT username, password_hash, salt FROM players").fetchall()
    for row in rows:
        if _verify_password(password, row["password_hash"], row["salt"]):
            matches.append(row["username"])
    return sorted(matches)


def login_player(username: str, password: str) -> Dict[str, Any]:
    username = _normalize_username(username)
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        player = conn.execute("SELECT * FROM players WHERE username = ?", (username,)).fetchone()
        if not player or not _verify_password(password, player["password_hash"], player["salt"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误。")
        conn.execute("UPDATE players SET token = ?, online = 1, last_seen = ? WHERE id = ?", (token, now, player["id"]))
        player = conn.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
    return {"token": token, "player": merge_cosmetics_into_player(_public_player(player), player)}


def logout_player(player_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE players SET online = 0, token = NULL, last_seen = 0 WHERE id = ?", (player_id,))


def delete_player_account(player_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM leaderboard_snapshots WHERE player_id = ?", (player_id,))
        conn.execute("DELETE FROM players WHERE id = ?", (player_id,))


def get_player_by_token(token: str) -> Dict[str, Any]:
    with get_connection() as conn:
        player = conn.execute("SELECT * FROM players WHERE token = ?", (token,)).fetchone()
        if not player:
            raise HTTPException(status_code=401, detail="登录已失效，请重新登录。")
        conn.execute("UPDATE players SET online = 1, last_seen = ? WHERE id = ?", (int(time.time()), player["id"]))
        player = conn.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
    return merge_cosmetics_into_player(_public_player(player), player)


def current_player(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录。")
    return get_player_by_token(authorization.split(" ", 1)[1].strip())
