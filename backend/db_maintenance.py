"""Production DB hygiene — runs automatically on app startup (Railway-safe)."""
import re
import time
from datetime import date
from typing import List, Tuple

from database import get_connection, transaction

# Obvious automated-test accounts (never real players).
_TEST_USERNAME_PATTERNS = (
    re.compile(r"^seller_[a-z]$"),
    re.compile(r"^buyer_[a-z]$"),
    re.compile(r"^third_g$"),
    re.compile(r"^recover_[ab]_"),
    re.compile(r"^test_"),
    re.compile(r"^shoptest$"),
)


def is_test_username(username: str) -> bool:
    return any(pattern.match(username) for pattern in _TEST_USERNAME_PATTERNS)


def find_test_player_ids() -> List[int]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, username, password_hash, salt
            FROM players
            WHERE COALESCE(is_system_player, 0) = 0
            """
        ).fetchall()
    ids: List[int] = []
    for row in rows:
        username = row["username"]
        if is_test_username(username):
            ids.append(int(row["id"]))
            continue
        if row["password_hash"] == "x" and row["salt"] == "y":
            ids.append(int(row["id"]))
    return ids


def purge_test_players() -> Tuple[int, List[str]]:
    ids = find_test_player_ids()
    if not ids:
        return 0, []
    placeholders = ",".join("?" for _ in ids)
    with get_connection() as conn:
        names = [
            row["username"]
            for row in conn.execute(
                f"SELECT username FROM players WHERE id IN ({placeholders})", ids
            ).fetchall()
        ]
    with transaction() as conn:
        conn.execute(
            f"DELETE FROM market_offers WHERE buyer_id IN ({placeholders}) OR seller_id IN ({placeholders})",
            ids + ids,
        )
        conn.execute(
            f"DELETE FROM market_listings WHERE seller_id IN ({placeholders})",
            ids,
        )
        conn.execute(
            f"DELETE FROM showcase_likes WHERE owner_id IN ({placeholders}) OR liker_id IN ({placeholders})",
            ids + ids,
        )
        conn.execute(
            f"DELETE FROM showcase_guestbook WHERE owner_id IN ({placeholders}) OR author_id IN ({placeholders})",
            ids + ids,
        )
        conn.execute(
            f"DELETE FROM trade_logs WHERE buyer_id IN ({placeholders}) OR seller_id IN ({placeholders})",
            ids + ids,
        )
        conn.execute(
            f"DELETE FROM leaderboard_snapshots WHERE player_id IN ({placeholders})",
            ids,
        )
        conn.execute(
            f"DELETE FROM shop_orders WHERE player_id IN ({placeholders})",
            ids,
        )
        conn.execute(f"DELETE FROM game_saves WHERE player_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM players WHERE id IN ({placeholders})", ids)
    return len(ids), names


def rebuild_today_leaderboard_rewards() -> None:
    """Recompute daily rank badges after removing test accounts."""
    from online_services import _ensure_daily_rewards

    today = date.today().isoformat()
    with get_connection() as conn:
        conn.execute("DELETE FROM leaderboard_snapshots WHERE snapshot_date = ?", (today,))
        conn.execute(
            """
            UPDATE players
            SET ranking_badge = NULL, reward_bonus = 0
            WHERE COALESCE(is_system_player, 0) = 0
            """
        )
        conn.commit()
    _ensure_daily_rewards()


def run_startup_maintenance() -> dict:
    removed, names = purge_test_players()
    if removed:
        rebuild_today_leaderboard_rewards()
    return {"purged_test_players": removed, "purged_usernames": names}
