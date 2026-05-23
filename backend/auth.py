import hashlib
import hmac
import os
import secrets
import time
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

from database import get_connection


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000)
    return digest.hex(), salt


def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = _hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def _public_player(row: Any) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "shop_name": row["shop_name"],
        "online": bool(row["online"]),
        "reputation": row["reputation"],
        "ranking_badge": row["ranking_badge"],
        "reward_bonus": row["reward_bonus"],
        "created_at": row["created_at"],
        "last_seen": row["last_seen"],
    }


def register_player(username: str, password: str, shop_name: str) -> Dict[str, Any]:
    username = username.strip().lower()
    shop_name = shop_name.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少需要 3 个字符。")
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
    return {"token": token, "player": _public_player(player)}


def login_player(username: str, password: str) -> Dict[str, Any]:
    username = username.strip().lower()
    now = int(time.time())
    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        player = conn.execute("SELECT * FROM players WHERE username = ?", (username,)).fetchone()
        if not player or not _verify_password(password, player["password_hash"], player["salt"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误。")
        conn.execute("UPDATE players SET token = ?, online = 1, last_seen = ? WHERE id = ?", (token, now, player["id"]))
        player = conn.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
    return {"token": token, "player": _public_player(player)}


def logout_player(player_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE players SET online = 0, token = NULL, last_seen = ? WHERE id = ?", (int(time.time()), player_id))


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
    return _public_player(player)


def current_player(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录。")
    return get_player_by_token(authorization.split(" ", 1)[1].strip())
