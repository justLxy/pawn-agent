import os
import tempfile
import time
import unittest

import database
from database import get_connection, init_db
from player_cosmetics import cosmetics_from_row
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

    def test_create_order_reuses_open_pending(self) -> None:
        first = create_manual_order(self.player_id, "monthly_card")
        second = create_manual_order(self.player_id, "monthly_card")
        self.assertEqual(first["order_id"], second["order_id"])
        self.assertTrue(second.get("reused"))

    def test_sponsor_wall_lists_fulfilled_player(self) -> None:
        order = create_manual_order(self.player_id, "monthly_card")
        fulfill_order(order_id=order["order_id"])
        sponsors = list_public_sponsors()
        self.assertTrue(any(item["player_id"] == self.player_id for item in sponsors))

    def test_plaque_fulfill_sets_defaults(self) -> None:
        order = create_manual_order(self.player_id, "plaque_permanent")
        fulfill_order(order_id=order["order_id"])
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM players WHERE id = ?", (self.player_id,)).fetchone()
        cosmetics = cosmetics_from_row(row)
        self.assertEqual(cosmetics["shop_emblem"], "plaque")
        self.assertEqual(cosmetics["plaque_title"], "heritage")
        self.assertEqual(cosmetics["plaque_title_label"], "传世掌柜")
        self.assertEqual(cosmetics["shop_sign_style"], "classic")
        self.assertEqual(cosmetics["showcase_mood"], "plain")
        self.assertEqual(cosmetics["chat_accent"], "default")
        self.assertTrue(cosmetics["has_plaque"])

    def test_plaque_and_profile(self) -> None:
        order = create_manual_order(self.player_id, "plaque_permanent")
        fulfill_order(order_id=order["order_id"])
        cosmetics = update_profile_cosmetics(
            self.player_id,
            shop_emblem="ding",
            showcase_tagline="欢迎光临",
            plaque_title="gilded",
            shop_sign_style="carved",
            showcase_mood="couplet",
            showcase_seal_line="童叟无欺",
            chat_accent="jade",
        )
        self.assertEqual(cosmetics["shop_emblem"], "ding")
        self.assertEqual(cosmetics["shop_emblem_label"], "鼎")
        self.assertEqual(cosmetics["showcase_tagline"], "欢迎光临")
        self.assertEqual(cosmetics["plaque_title_label"], "金字招牌")
        self.assertEqual(cosmetics["shop_sign_style"], "carved")
        self.assertEqual(cosmetics["showcase_mood"], "couplet")
        self.assertEqual(cosmetics["showcase_seal_line"], "童叟无欺")
        self.assertEqual(cosmetics["chat_accent"], "jade")

    def test_plaque_profile_rejects_invalid_fields(self) -> None:
        order = create_manual_order(self.player_id, "plaque_permanent")
        fulfill_order(order_id=order["order_id"])
        with self.assertRaises(Exception):
            update_profile_cosmetics(self.player_id, shop_emblem="invalid")
        with self.assertRaises(Exception):
            update_profile_cosmetics(self.player_id, plaque_title="bogus")
        with self.assertRaises(Exception):
            update_profile_cosmetics(self.player_id, showcase_seal_line="x" * 20)

    def test_monthly_and_plaque_stack(self) -> None:
        monthly = create_manual_order(self.player_id, "monthly_card")
        plaque = create_manual_order(self.player_id, "plaque_permanent")
        fulfill_order(order_id=monthly["order_id"])
        fulfill_order(order_id=plaque["order_id"])
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM players WHERE id = ?", (self.player_id,)).fetchone()
        cosmetics = cosmetics_from_row(row)
        self.assertTrue(cosmetics["is_sponsor"])
        self.assertTrue(cosmetics["has_plaque"])
        self.assertEqual(cosmetics["sponsor_title"], "赞助掌柜")
        self.assertEqual(cosmetics["plaque_title_label"], "传世掌柜")

    def test_sponsor_wall_includes_plaque_title(self) -> None:
        order = create_manual_order(self.player_id, "plaque_permanent")
        fulfill_order(order_id=order["order_id"])
        update_profile_cosmetics(self.player_id, plaque_title="veteran")
        sponsors = list_public_sponsors()
        entry = next(item for item in sponsors if item["player_id"] == self.player_id)
        self.assertTrue(entry["has_plaque"])
        self.assertEqual(entry["plaque_title_label"], "名匾老铺")


if __name__ == "__main__":
    unittest.main()
