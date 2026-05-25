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
                reward_bonus INTEGER NOT NULL DEFAULT 0,
                is_system_player INTEGER NOT NULL DEFAULT 0
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

            CREATE TABLE IF NOT EXISTS market_offers (
                id TEXT PRIMARY KEY,
                listing_id TEXT NOT NULL,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                buyer_offer INTEGER NOT NULL,
                seller_counter INTEGER,
                status TEXT NOT NULL DEFAULT 'pending_seller',
                round INTEGER NOT NULL DEFAULT 1,
                final_price INTEGER,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                FOREIGN KEY(listing_id) REFERENCES market_listings(id) ON DELETE CASCADE,
                FOREIGN KEY(buyer_id) REFERENCES players(id) ON DELETE CASCADE,
                FOREIGN KEY(seller_id) REFERENCES players(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_offers_listing_status
                ON market_offers(listing_id, status);
            CREATE INDEX IF NOT EXISTS idx_offers_seller_status
                ON market_offers(seller_id, status);
            CREATE INDEX IF NOT EXISTS idx_offers_buyer_status
                ON market_offers(buyer_id, status);

            CREATE TABLE IF NOT EXISTS showcase_likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                liker_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(owner_id) REFERENCES players(id) ON DELETE CASCADE,
                FOREIGN KEY(liker_id) REFERENCES players(id) ON DELETE CASCADE,
                UNIQUE(owner_id, liker_id)
            );

            CREATE INDEX IF NOT EXISTS idx_showcase_likes_owner
                ON showcase_likes(owner_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS showcase_guestbook (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(owner_id) REFERENCES players(id) ON DELETE CASCADE,
                FOREIGN KEY(author_id) REFERENCES players(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_guestbook_owner_created
                ON showcase_guestbook(owner_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS shop_orders (
                id TEXT PRIMARY KEY,
                player_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                amount_fen INTEGER NOT NULL,
                order_no TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending',
                payer_note TEXT,
                created_at INTEGER NOT NULL,
                submitted_at INTEGER,
                fulfilled_at INTEGER,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_shop_orders_player_created
                ON shop_orders(player_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_shop_orders_status
                ON shop_orders(status, created_at DESC);
            """
        )
        _migrate_shop_schema(conn)


def _migrate_shop_schema(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(players)").fetchall()}
    if "monthly_expires_at" not in columns:
        conn.execute("ALTER TABLE players ADD COLUMN monthly_expires_at INTEGER")
    if "shop_emblem" not in columns:
        conn.execute("ALTER TABLE players ADD COLUMN shop_emblem TEXT")
    if "showcase_tagline" not in columns:
        conn.execute("ALTER TABLE players ADD COLUMN showcase_tagline TEXT")
    if "is_system_player" not in columns:
        conn.execute("ALTER TABLE players ADD COLUMN is_system_player INTEGER NOT NULL DEFAULT 0")
