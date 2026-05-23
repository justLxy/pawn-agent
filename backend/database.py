import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DB_PATH = Path(os.getenv("PAWNSHOP_DB_PATH", Path(__file__).with_name("pawnshop_online.db")))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                shop_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                token TEXT UNIQUE,
                online INTEGER NOT NULL DEFAULT 0,
                reputation INTEGER NOT NULL DEFAULT 100,
                created_at INTEGER NOT NULL,
                last_seen INTEGER NOT NULL,
                ranking_badge TEXT,
                reward_bonus INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS game_saves (
                player_id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS market_listings (
                id TEXT PRIMARY KEY,
                seller_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                item_json TEXT NOT NULL,
                item_name TEXT NOT NULL,
                rarity TEXT NOT NULL,
                category TEXT NOT NULL,
                condition TEXT NOT NULL,
                price INTEGER NOT NULL,
                reference_price INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY(seller_id) REFERENCES players(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_market_status_created
                ON market_listings(status, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_market_seller_status
                ON market_listings(seller_id, status);

            CREATE TABLE IF NOT EXISTS trade_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER,
                seller_id INTEGER,
                listing_id TEXT,
                item_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                tax INTEGER NOT NULL,
                trade_type TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(buyer_id) REFERENCES players(id) ON DELETE SET NULL,
                FOREIGN KEY(seller_id) REFERENCES players(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                board_type TEXT NOT NULL,
                player_id INTEGER NOT NULL,
                rank INTEGER NOT NULL,
                score INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                UNIQUE(snapshot_date, board_type, player_id)
            );
            """
        )
