import os
import tempfile
import time
import unittest

import database
from database import get_connection, init_db
from shop_service import create_manual_order, fulfill_order, list_public_sponsors, submit_payment, update_profile_cosmetics


class ShopFulfillTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        database.DB_PATH = database.Path(self._tmp.name)
        init_db()
        now = int(time.time())
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO players (username, shop_name, password_hash, salt, token, online, created_at, last_seen)
                VALUES ('shoptest', '测试当铺', 'h', 's', ?, 1, ?, ?)
                """,
                (f"tok_{now}", now, now),
            )
            conn.commit()
            row = conn.execute("SELECT id FROM players WHERE username = 'shoptest'").fetchone()
            self.player_id = int(row["id"])

    def tearDown(self) -> None:
        os.unlink(self._tmp.name)

    def test_monthly_fulfill_extends_expiry(self) -> None:
        order = create_manual_order(self.player_id, "monthly_card")
        submit_payment(self.player_id, order["order_id"], "已付")
        result = fulfill_order(order_no=order["order_no"])
        self.assertEqual(result["order"]["status"], "fulfilled")
        self.assertTrue(result["cosmetics"]["is_sponsor"])
        self.assertIsNotNone(result["cosmetics"]["monthly_expires_at"])

    def test_sponsor_wall_lists_fulfilled_player(self) -> None:
        order = create_manual_order(self.player_id, "monthly_card")
        fulfill_order(order_id=order["order_id"])
        sponsors = list_public_sponsors()
        self.assertTrue(any(item["player_id"] == self.player_id for item in sponsors))

    def test_plaque_and_profile(self) -> None:
        order = create_manual_order(self.player_id, "plaque_permanent")
        fulfill_order(order_id=order["order_id"])
        cosmetics = update_profile_cosmetics(self.player_id, shop_emblem="seal", showcase_tagline="欢迎光临")
        self.assertEqual(cosmetics["shop_emblem"], "seal")
        self.assertEqual(cosmetics["showcase_tagline"], "欢迎光临")


if __name__ == "__main__":
    unittest.main()
