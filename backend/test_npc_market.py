import json
import os
import tempfile
import unittest

# Isolate DB per test module run
_test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["PAWNSHOP_DB_PATH"] = _test_db.name

from database import get_connection, init_db
from npc_inventory import build_npc_item, persona_list_price
from npc_market_config import MAX_ACTIVE_LISTINGS_PER_NPC
from npc_market_service import (
    build_npc_game_state,
    clear_npc_market_data,
    count_active_listings,
    ensure_npc_players,
    full_seed_npc_shops,
    get_system_player_ids,
)
from npc_personas import active_personas
from online_services import get_leaderboard, reference_price
from auth import recover_usernames_by_password
from db_maintenance import is_test_username, purge_test_players


class NpcMarketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        with get_connection() as conn:
            conn.execute("DELETE FROM market_offers")
            conn.execute("DELETE FROM market_listings")
            conn.execute("DELETE FROM trade_logs")
            conn.execute("DELETE FROM game_saves")
            conn.execute("DELETE FROM players")
            conn.commit()

    def test_persona_pricing_bounds(self):
        persona = active_personas()[0]
        state = build_npc_game_state(persona)
        for _ in range(30):
            item = build_npc_item(persona, state)
            ref = reference_price(item)
            price = persona_list_price(persona, item)
            self.assertGreaterEqual(price, int(ref * 0.3))
            self.assertLessEqual(price, int(ref * 3))
            if item.rarity == "legendary":
                self.assertGreaterEqual(price, int(ref * 0.85))
            if item.rarity == "common":
                self.assertLessEqual(price, int(ref * 1.4))

    def test_npc_has_no_sponsor_or_showcase_cosmetics(self):
        full_seed_npc_shops(reset=True)
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT username, monthly_expires_at, shop_emblem, showcase_tagline
                FROM players WHERE COALESCE(is_system_player, 0) = 1
                """
            ).fetchall()
        self.assertGreaterEqual(len(rows), 1)
        for row in rows:
            self.assertIsNone(row["monthly_expires_at"])
            self.assertIsNone(row["shop_emblem"])
            self.assertIsNone(row["showcase_tagline"])

    def test_ensure_npc_players_are_system_only(self):
        player_map = ensure_npc_players()
        self.assertEqual(len(player_map), len(active_personas()))
        with get_connection() as conn:
            for row in conn.execute("SELECT username, is_system_player FROM players").fetchall():
                self.assertEqual(int(row["is_system_player"]), 1)

    def test_seed_listings_within_cap(self):
        full_seed_npc_shops(reset=True)
        for persona in active_personas():
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT id FROM players WHERE username = ?", (persona.username,)
                ).fetchone()
            player_id = int(row["id"])
            active = count_active_listings(player_id)
            self.assertGreaterEqual(active, 1)
            self.assertLessEqual(active, MAX_ACTIVE_LISTINGS_PER_NPC)

    def test_system_players_on_leaderboard(self):
        full_seed_npc_shops(reset=True)
        real_id = self._create_real_player("real_trader", "真实当铺")
        board = get_leaderboard("assets", real_id)
        board_ids = {entry["player_id"] for entry in board["entries"]}
        npc_ids = get_system_player_ids()
        self.assertTrue(npc_ids)
        self.assertTrue(any(npc_id in board_ids for npc_id in npc_ids))

    def test_purge_test_players(self):
        self._create_real_player("seller_a", "seller_a铺")
        self._create_real_player("milk2", "牛奶店", "pw5678")
        removed, names = purge_test_players()
        self.assertEqual(removed, 1)
        self.assertIn("seller_a", names)
        with get_connection() as conn:
            left = conn.execute("SELECT username FROM players").fetchall()
        usernames = {row["username"] for row in left}
        self.assertIn("milk2", usernames)
        self.assertNotIn("seller_a", usernames)

    def test_is_test_username_patterns(self):
        self.assertTrue(is_test_username("seller_a"))
        self.assertTrue(is_test_username("buyer_f"))
        self.assertTrue(is_test_username("recover_a_abc123"))
        self.assertFalse(is_test_username("milk"))

    def test_recover_username_skips_system_players(self):
        full_seed_npc_shops(reset=True)
        password = "testpass1234"
        self._create_real_player("human_one", "人类当铺", password)
        names = recover_usernames_by_password(password)
        self.assertEqual(names, ["human_one"])
        for persona in active_personas():
            self.assertNotIn(persona.username, names)

    def _create_real_player(self, username: str, shop_name: str, password: str = "pw1234") -> int:
        import secrets

        from auth import _hash_password

        password_hash, salt = _hash_password(password)
        now = 1000
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO players (
                    username, shop_name, password_hash, salt, token, online,
                    reputation, created_at, last_seen, is_system_player
                )
                VALUES (?, ?, ?, ?, ?, 0, 100, ?, ?, 0)
                """,
                (username, shop_name, password_hash, salt, secrets.token_urlsafe(16), now, now),
            )
            row = conn.execute("SELECT id FROM players WHERE username = ?", (username,)).fetchone()
            player_id = int(row["id"])
            state = build_npc_game_state(active_personas()[0])
            state.shop_name = shop_name
            state.cash = 50000
            conn.execute(
                "INSERT INTO game_saves (player_id, state_json, updated_at) VALUES (?, ?, ?)",
                (player_id, json.dumps(state.to_dict(), ensure_ascii=False), now),
            )
            conn.commit()
        return player_id


if __name__ == "__main__":
    unittest.main()
